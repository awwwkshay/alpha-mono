from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alpha_core.domain.agent.agent import (
    Agent,
    _accumulate_tool_call_delta,
    _build_system,
)
from alpha_core.domain.evals.scorer import Scorer, ScorerConfig, ScorerResult
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext
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


def _make_agent(*, workspace=None, scorers=None) -> Agent:
    config = AgentConfig(
        name="Test",
        system_prompt="Be helpful.",
        model="test/model",
        scorers=scorers or {},
    )
    return Agent(config=config, workspace=workspace)


def _make_context() -> AppContext:
    return AppContext(config=AppConfig(name="test"))


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
# _build_system
# ---------------------------------------------------------------------------


def test_build_system_no_workspace():
    config = AgentConfig(name="A", system_prompt="Base prompt.", model="m")
    result = _build_system(config, None)
    assert result == "Base prompt."


def test_build_system_workspace_no_additions():
    config = AgentConfig(name="A", system_prompt="Base.", model="m")
    ws = MagicMock()
    ws.get_system_prompt_additions.return_value = ""
    assert _build_system(config, ws) == "Base."


def test_build_system_workspace_with_additions():
    config = AgentConfig(name="A", system_prompt="Base.", model="m")
    ws = MagicMock()
    ws.get_system_prompt_additions.return_value = "Extra context."
    result = _build_system(config, ws)
    assert result == "Base.\n\nExtra context."


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
        result = await agent._generate_raw("Say hi")
    assert result == "Hi there"


async def test_generate_raw_normalises_empty_tool_calls_list():
    """LiteLLM/Gemini may return tool_calls=[] — must not be treated as tool calls."""
    agent = _make_agent()
    response = _make_response(content="Hello", tool_calls=[])
    with patch("litellm.acompletion", AsyncMock(return_value=response)):
        result = await agent._generate_raw("Hi")
    assert result == "Hello"


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
    ws = MagicMock()
    ws.get_tools.return_value = [
        {"type": "function", "function": {"name": "read_file"}}
    ]
    ws.get_system_prompt_additions.return_value = ""
    ws.execute_tool = AsyncMock(return_value='{"content": "file data"}')

    agent = _make_agent(workspace=ws)

    first = _make_response(
        content=None, tool_calls=[_make_tool_call("read_file", '{"path":"f.txt"}')]
    )
    second = _make_response(content="The file says: file data")

    with patch("litellm.acompletion", AsyncMock(side_effect=[first, second])):
        result = await agent._generate_raw("Read f.txt")

    assert result == "The file says: file data"
    ws.execute_tool.assert_awaited_once_with("read_file", {"path": "f.txt"})


async def test_generate_raw_returns_tool_result_when_no_content_after_tool_cycle():
    """Gemini may return content=None after executing tools; agent should return last tool result."""
    ws = MagicMock()
    ws.get_tools.return_value = [
        {"type": "function", "function": {"name": "read_file"}}
    ]
    ws.get_system_prompt_additions.return_value = ""
    ws.execute_tool = AsyncMock(return_value="raw file content")

    agent = _make_agent(workspace=ws)

    first = _make_response(content=None, tool_calls=[_make_tool_call()])
    second = _make_response(content=None, tool_calls=None)

    with patch("litellm.acompletion", AsyncMock(side_effect=[first, second])):
        result = await agent._generate_raw("Read it")

    assert result == "raw file content"


async def test_generate_raw_max_iterations_raises():
    ws = MagicMock()
    ws.get_tools.return_value = [{"type": "function", "function": {"name": "loop"}}]
    ws.get_system_prompt_additions.return_value = ""
    ws.execute_tool = AsyncMock(return_value='{"ok": true}')

    agent = _make_agent(workspace=ws)
    always_tool = _make_response(
        content=None, tool_calls=[_make_tool_call("loop", "{}")]
    )

    with patch("litellm.acompletion", AsyncMock(return_value=always_tool)):
        with pytest.raises(RuntimeError, match="exceeded"):
            await agent._generate_raw("Loop forever")


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


async def test_stream_async_max_iterations_raises():
    ws = MagicMock()
    ws.get_tools.return_value = [{"type": "function", "function": {"name": "loop"}}]
    ws.get_system_prompt_additions.return_value = ""
    ws.execute_tool = AsyncMock(return_value='{"ok": true}')

    agent = _make_agent(workspace=ws)

    def _tool_chunk():
        tc_delta = MagicMock()
        tc_delta.index = 0
        tc_delta.id = "c1"
        tc_delta.function.name = "loop"
        tc_delta.function.arguments = "{}"
        return _AsyncChunks([_make_stream_chunk(tool_calls=[tc_delta])])

    with patch("litellm.acompletion", AsyncMock(side_effect=lambda **_: _tool_chunk())):
        with pytest.raises(RuntimeError, match="exceeded"):
            async for _ in agent.stream_async("Hi", _make_context()):
                pass
