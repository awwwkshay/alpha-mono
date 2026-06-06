from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from clay_app.agent.agent import (
    Agent,
    _accumulate_tool_call_delta,
    _workflow_to_tool,
)
from clay_core import (
    AgentConfig,
    AppConfig,
    AppContext,
    Scorer,
    ScorerConfig,
    ScorerResult,
    WorkflowConfig,
    WorkflowStepConfig,
)
from litellm.types.llms.openai import ChatCompletionAssistantToolCall


class _MockScorer(Scorer):
    def __init__(self, result: ScorerResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str]] = []

    async def score(self, input: str, output: str) -> ScorerResult:
        self.calls.append((input, output))
        return self._result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(*, scorers=None) -> Agent:
    config = AgentConfig(
        name="Test",
        system_prompt="Be helpful.",
        model="test/model",
        scorers=scorers or {},
    )
    return Agent(config=config)


def _make_context(workspace: _WorkspaceStub | None = None) -> AppContext:
    return AppContext(config=AppConfig(name="test"), workspace=workspace)


class _WorkspaceStub:
    def __init__(
        self,
        *,
        tool_name: str = "workspace_tool",
        tool_result: str = '{"ok": true}',
        prompt_additions: str = "Workspace instructions",
    ) -> None:
        self.tool_name = tool_name
        self.tool_result = tool_result
        self.prompt_additions = prompt_additions
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_tools(self) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": self.tool_name,
                    "description": "Workspace tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    async def execute_tool(self, name: str, arguments: dict[str, object]) -> str:
        self.calls.append((name, arguments))
        return self.tool_result

    def get_system_prompt_additions(self) -> str:
        return self.prompt_additions


def _make_response(content: str | None = "Hello", tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(name: str = "read_file", arguments: str = '{"path": "f.txt"}'):
    tc = MagicMock()
    tc.id = "call_1"
    tc.type = "function"
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


# ---------------------------------------------------------------------------
# _accumulate_tool_call_delta
# ---------------------------------------------------------------------------


def _make_delta(
    index: int, tc_id: str | None = None, name: str = "", arguments: str = ""
):
    delta = MagicMock()
    delta.index = index
    delta.id = tc_id
    fn = MagicMock()
    fn.name = name
    fn.arguments = arguments
    delta.function = fn
    return delta


def test_accumulate_creates_new_entry():
    collected: dict[int, ChatCompletionAssistantToolCall] = {}
    delta = _make_delta(0, tc_id="call_1", name="tool_a", arguments='{"x"')
    _accumulate_tool_call_delta(delta, collected)

    assert 0 in collected
    assert collected[0]["id"] == "call_1"
    assert collected[0]["function"]["name"] == "tool_a"
    assert collected[0]["function"]["arguments"] == '{"x"'


def test_accumulate_appends_to_existing():
    collected: dict[int, ChatCompletionAssistantToolCall] = {}
    _accumulate_tool_call_delta(
        _make_delta(0, tc_id="call_1", name="fn", arguments='{"a"'), collected
    )
    _accumulate_tool_call_delta(
        _make_delta(0, tc_id=None, name="", arguments=": 1}"), collected
    )

    assert collected[0]["function"]["arguments"] == '{"a": 1}'


def test_accumulate_updates_id_when_provided():
    collected: dict[int, ChatCompletionAssistantToolCall] = {}
    _accumulate_tool_call_delta(
        _make_delta(0, tc_id=None, name="fn", arguments=""), collected
    )
    _accumulate_tool_call_delta(
        _make_delta(0, tc_id="late_id", name="", arguments=""), collected
    )
    assert collected[0]["id"] == "late_id"


def test_accumulate_multiple_indices():
    collected: dict[int, ChatCompletionAssistantToolCall] = {}
    _accumulate_tool_call_delta(
        _make_delta(0, tc_id="c0", name="fn0", arguments=""), collected
    )
    _accumulate_tool_call_delta(
        _make_delta(1, tc_id="c1", name="fn1", arguments=""), collected
    )
    assert len(collected) == 2
    assert collected[0]["function"]["name"] == "fn0"
    assert collected[1]["function"]["name"] == "fn1"


# ---------------------------------------------------------------------------
# Agent._generate_raw — non-tool path
# ---------------------------------------------------------------------------


async def test_generate_raw_simple_text_response():
    agent = _make_agent()
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_response("Hi there"))
    ):
        content, iterations, tool_calls = await agent._generate_raw("Say hi")
    assert content == "Hi there"
    assert iterations == 1
    assert tool_calls == 0


async def test_generate_raw_normalises_empty_tool_calls_list():
    """LiteLLM/Gemini may return tool_calls=[] — must not be treated as tool calls."""
    agent = _make_agent()
    response = _make_response(content="Hello", tool_calls=[])
    with patch("litellm.acompletion", AsyncMock(return_value=response)):
        content, iterations, tool_calls = await agent._generate_raw("Hi")
    assert content == "Hello"
    assert iterations == 1
    assert tool_calls == 0


async def test_generate_raw_no_content_no_tools_raises():
    agent = _make_agent()
    response = _make_response(content=None, tool_calls=None)
    with patch("litellm.acompletion", AsyncMock(return_value=response)):
        with pytest.raises(ValueError, match="Model returned no content"):
            await agent._generate_raw("Hi")


async def test_generate_raw_empty_tool_calls_and_no_content_raises():
    """Empty list is normalised to None; then content=None → ValueError (no prior tool calls)."""
    agent = _make_agent()
    response = _make_response(content=None, tool_calls=[])
    with patch("litellm.acompletion", AsyncMock(return_value=response)):
        with pytest.raises(ValueError, match="Model returned no content"):
            await agent._generate_raw("Hi")


# ---------------------------------------------------------------------------
# Agent._generate_raw — tool call path
# ---------------------------------------------------------------------------


async def test_generate_raw_tool_call_cycle():
    mock_fn, wf_config = _make_workflow_config("read_file")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"read_file": wf_config}
    )
    agent = Agent(config=config)

    first = _make_response(
        content=None, tool_calls=[_make_tool_call("read_file", '{"value": 1}')]
    )
    second = _make_response(content="The file says: file data")

    with patch("litellm.acompletion", AsyncMock(side_effect=[first, second])):
        content, iterations, tool_calls = await agent._generate_raw(
            "Read f.txt", _make_context()
        )

    assert content == "The file says: file data"
    assert iterations == 2
    assert tool_calls == 1
    mock_fn.assert_awaited_once()


async def test_generate_raw_returns_tool_result_when_no_content_after_tool_cycle():
    """Gemini may return content=None after executing tools; agent should return last tool result."""
    mock_fn, wf_config = _make_workflow_config("read_file")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"read_file": wf_config}
    )
    agent = Agent(config=config)

    first = _make_response(
        content=None, tool_calls=[_make_tool_call("read_file", '{"value": 1}')]
    )
    second = _make_response(content=None, tool_calls=None)

    with patch("litellm.acompletion", AsyncMock(side_effect=[first, second])):
        content, iterations, tool_calls = await agent._generate_raw(
            "Read it", _make_context()
        )

    assert content == _WfOutput(result="doubled").model_dump_json()
    assert iterations == 2
    assert tool_calls == 1


async def test_generate_raw_max_iterations_raises():
    _, wf_config = _make_workflow_config("loop")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"loop": wf_config}
    )
    agent = Agent(config=config)
    always_tool = _make_response(
        content=None, tool_calls=[_make_tool_call("loop", '{"value": 1}')]
    )

    with patch("litellm.acompletion", AsyncMock(return_value=always_tool)):
        with pytest.raises(RuntimeError, match="exceeded"):
            await agent._generate_raw("Loop forever", _make_context())


async def test_generate_raw_appends_workspace_prompt_additions():
    agent = _make_agent()
    workspace = _WorkspaceStub(prompt_additions="Use the workspace carefully.")
    mock_completion = AsyncMock(return_value=_make_response("Hello"))

    with patch("litellm.acompletion", mock_completion):
        await agent._generate_raw("Hi", _make_context(workspace))

    await_args = mock_completion.await_args
    assert await_args is not None
    system_message = await_args.kwargs["messages"][0]
    assert "Use the workspace carefully." in system_message["content"]


# ---------------------------------------------------------------------------
# Agent.generate_async
# ---------------------------------------------------------------------------


async def test_generate_async_returns_content():
    agent = _make_agent()
    with patch("litellm.acompletion", AsyncMock(return_value=_make_response("Answer"))):
        result = await agent.generate_async("Question", _make_context())
    assert result == "Answer"


async def test_generate_async_creates_scorer_task():
    scorer = _MockScorer(ScorerResult(score=0.9))
    scorer_cfg = ScorerConfig(scorer=scorer)

    agent = _make_agent(scorers={"q": scorer_cfg})

    with patch("litellm.acompletion", AsyncMock(return_value=_make_response("Out"))):
        await agent.generate_async("In", _make_context())
        # Drain pending background tasks: gather all non-current tasks
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    assert len(scorer.calls) == 1


# ---------------------------------------------------------------------------
# Agent.generate_with_evals_async
# ---------------------------------------------------------------------------


async def test_generate_with_evals_async_returns_tuple():
    scorer = _MockScorer(ScorerResult(score=0.8, reason="good"))
    scorer_cfg = ScorerConfig(scorer=scorer)

    agent = _make_agent(scorers={"s": scorer_cfg})

    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_response("Content"))
    ):
        content, scores = await agent.generate_with_evals_async(
            "Input", _make_context()
        )

    assert content == "Content"
    assert "s" in scores
    assert scores["s"].score == 0.8


# ---------------------------------------------------------------------------
# Agent.stream_async
# ---------------------------------------------------------------------------


class _AsyncChunks:
    def __init__(self, chunks: list) -> None:
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


def _make_stream_chunk(content: str | None = None, tool_calls=None):
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta = delta
    return chunk


async def test_stream_async_yields_content():
    agent = _make_agent()
    chunks = _AsyncChunks(
        [
            _make_stream_chunk("Hello"),
            _make_stream_chunk(" world"),
        ]
    )
    with patch("litellm.acompletion", AsyncMock(return_value=chunks)):
        parts = [chunk async for chunk in agent.stream_async("Hi", _make_context())]
    assert parts == ["Hello", " world"]


async def test_stream_async_yields_content_before_and_after_tool_calls():
    _, wf_config = _make_workflow_config("lookup")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"lookup": wf_config}
    )
    agent = Agent(config=config)

    tc_delta = MagicMock()
    tc_delta.index = 0
    tc_delta.id = "c1"
    tc_delta.function.name = "lookup"
    tc_delta.function.arguments = '{"value": 1}'

    first_turn = _AsyncChunks(
        [
            _make_stream_chunk("draft before tool"),
            _make_stream_chunk(tool_calls=[tc_delta]),
        ]
    )
    second_turn = _AsyncChunks([_make_stream_chunk("final after tool")])

    with patch("litellm.acompletion", AsyncMock(side_effect=[first_turn, second_turn])):
        parts = [chunk async for chunk in agent.stream_async("Hi", _make_context())]

    assert parts == ["draft before tool", "final after tool"]


# ---------------------------------------------------------------------------
# Agent.generate_structured_async
# ---------------------------------------------------------------------------


class _Point(BaseModel):
    x: int
    y: int


async def test_generate_structured_async_returns_parsed_model():
    agent = _make_agent()
    with patch(
        "litellm.acompletion",
        AsyncMock(return_value=_make_response('{"x": 1, "y": 2}')),
    ):
        result = await agent.generate_structured_async(
            "Give me a point", _make_context(), _Point
        )
    assert isinstance(result, _Point)
    assert result.x == 1
    assert result.y == 2


async def test_generate_structured_async_no_content_raises():
    agent = _make_agent()
    with patch(
        "litellm.acompletion",
        AsyncMock(return_value=_make_response(None)),
    ):
        with pytest.raises(ValueError, match="Model returned no content"):
            await agent.generate_structured_async(
                "Give me a point", _make_context(), _Point
            )


async def test_generate_structured_async_invalid_json_raises():
    agent = _make_agent()
    with patch(
        "litellm.acompletion",
        AsyncMock(return_value=_make_response("not json")),
    ):
        with pytest.raises(Exception):
            await agent.generate_structured_async(
                "Give me a point", _make_context(), _Point
            )


async def test_stream_async_max_iterations_raises():
    _, wf_config = _make_workflow_config("loop")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"loop": wf_config}
    )
    agent = Agent(config=config)

    def _tool_chunk():
        tc_delta = MagicMock()
        tc_delta.index = 0
        tc_delta.id = "c1"
        tc_delta.function.name = "loop"
        tc_delta.function.arguments = '{"value": 1}'
        return _AsyncChunks([_make_stream_chunk(tool_calls=[tc_delta])])

    with patch("litellm.acompletion", AsyncMock(side_effect=lambda **_: _tool_chunk())):
        with pytest.raises(RuntimeError, match="exceeded"):
            async for _ in agent.stream_async("Hi", _make_context()):
                pass


# ---------------------------------------------------------------------------
# Workflows as tools
# ---------------------------------------------------------------------------


class _WfInput(BaseModel):
    value: int


class _WfOutput(BaseModel):
    result: str


def _make_workflow_config(name: str = "double") -> tuple[AsyncMock, WorkflowConfig]:
    mock_fn: AsyncMock = AsyncMock(return_value=_WfOutput(result="doubled"))
    config = WorkflowConfig.create(
        name=name,
        input_schema=_WfInput,
        output_schema=_WfOutput,
        steps={
            name: WorkflowStepConfig.create(
                name=name,
                input_schema=_WfInput,
                output_schema=_WfOutput,
                execute=mock_fn,
            )
        },
    )
    return mock_fn, config


def test_workflow_to_tool_schema():
    wf = MagicMock()
    wf.config.name = "my_workflow"
    wf.config.input_schema = _WfInput
    tool = _workflow_to_tool("my_workflow", wf)

    assert tool["type"] == "function"
    assert tool["function"]["name"] == "my_workflow"
    assert "my_workflow" in tool["function"]["description"]
    params = tool["function"]["parameters"]
    assert params["type"] == "object"
    assert "value" in params["properties"]


async def test_agent_with_workflow_tool_invokes_workflow():
    mock_fn, wf_config = _make_workflow_config("double")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"double": wf_config}
    )
    agent = Agent(config=config)

    first = _make_response(
        content=None,
        tool_calls=[_make_tool_call("double", '{"value": 5}')],
    )
    second = _make_response(content="The result is doubled")

    with patch("litellm.acompletion", AsyncMock(side_effect=[first, second])):
        content, iterations, tool_calls = await agent._generate_raw(
            "Double 5", _make_context()
        )

    assert content == "The result is doubled"
    assert iterations == 2
    assert tool_calls == 1
    mock_fn.assert_awaited_once()
    call_args = mock_fn.call_args
    assert call_args[0][0].value == 5


def test_agent_get_tools_includes_workspace_tools():
    agent = _make_agent()
    workspace = _WorkspaceStub(tool_name="workspace_search")

    tools = agent._get_tools(_make_context(workspace))

    assert tools is not None
    names = [t["function"]["name"] for t in tools]
    assert "workspace_search" in names


def test_agent_get_tools_rejects_duplicate_workspace_tool_names():
    _, wf_config = _make_workflow_config("read_file")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"read_file": wf_config}
    )
    agent = Agent(config=config)
    workspace = _WorkspaceStub(tool_name="read_file")

    with pytest.raises(ValueError, match="duplicate tool name"):
        agent._get_tools(_make_context(workspace))


async def test_dispatch_tool_executes_workspace_tool():
    agent = _make_agent()
    workspace = _WorkspaceStub(
        tool_name="workspace_read",
        tool_result='{"content":"workspace data"}',
    )

    result = await agent._dispatch_tool(
        "workspace_read",
        {"path": "notes.txt"},
        _make_context(workspace),
    )

    assert result == '{"content":"workspace data"}'
    assert workspace.calls == [("workspace_read", {"path": "notes.txt"})]


async def test_agent_workflow_tool_appears_in_tool_list():
    _, wf_config = _make_workflow_config("summarise")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"summarise": wf_config}
    )
    agent = Agent(config=config)

    tools = agent._get_tools()
    assert tools is not None
    names = [t["function"]["name"] for t in tools]
    assert "summarise" in names


async def test_dispatch_tool_raises_without_context_for_workflow():
    _, wf_config = _make_workflow_config("run")
    config = AgentConfig(
        name="A", system_prompt="s", model="m", workflows={"run": wf_config}
    )
    agent = Agent(config=config)

    with pytest.raises(RuntimeError, match="no AppContext"):
        await agent._dispatch_tool("run", {"value": 1}, None)


async def test_dispatch_tool_raises_for_unknown_tool():
    config = AgentConfig(name="A", system_prompt="s", model="m")
    agent = Agent(config=config)

    with pytest.raises(RuntimeError, match="not found"):
        await agent._dispatch_tool("unknown", {}, _make_context())
