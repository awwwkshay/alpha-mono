from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from pydantic import BaseModel

from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionAssistantToolCall,
    ChatCompletionSystemMessage,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolMessage,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    ChatCompletionUserMessage,
)

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from alpha_app.log import logger
from alpha_app.constants.otel_constants import (
    AGENT_DESCRIPTION,
    AGENT_HAS_HISTORY,
    AGENT_HAS_SCORERS,
    AGENT_HAS_TOOLS,
    AGENT_NAME,
    AGENT_PROMPT_LENGTH,
    AGENT_PROMPT,
    AGENT_RESPONSE,
    AGENT_RESPONSE_LENGTH,
    AGENT_RESPONSE_MODEL,
    AGENT_TOOL_COUNT,
    AGENT_TOTAL_ITERATIONS,
    AGENT_TOTAL_TOOL_CALLS,
    ERROR_MESSAGE,
    ERROR_TYPE,
    EVENT_ASSISTANT_MESSAGE,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    EVENT_USER_MESSAGE,
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_FINISH_REASON,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_SYSTEM,
    GEN_AI_USAGE_CACHE_CREATION_TOKENS,
    GEN_AI_USAGE_CACHE_READ_TOKENS,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_USAGE_THINKING_TOKENS,
    GEN_AI_USAGE_TOTAL_TOKENS,
    LLM_HAS_TOOLS,
    LLM_ITERATION,
    LLM_MESSAGE_COUNT,
    LLM_RETURNED_TOOL_CALLS,
    LLM_TOOL_DEFINITION_COUNT,
    SPAN_AGENT_GENERATE,
    SPAN_AGENT_GENERATE_STREAM,
    SPAN_AGENT_GENERATE_STRUCTURED,
    SPAN_AGENT_GENERATE_WITH_EVALS,
    SPAN_AGENT_TOOL_CALL,
    SPAN_LLM_CHAT,
    SPAN_LLM_CHAT_STREAM,
    TOOL_INPUT,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_RESULT_LENGTH,
    TOOL_TYPE,
)
from alpha_app.evals.runner import run_scorers
from alpha_core import AgentConfig, AgentTool, AppContext, ScorerResult

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse
    from alpha_app.workflow.workflow import Workflow

AgentConfig.model_rebuild()

_MAX_TOOL_ITERATIONS = 20
_T = TypeVar("_T", bound=BaseModel)

_tracer = trace.get_tracer(__name__)


def _workflow_to_tool(name: str, workflow: Workflow) -> ChatCompletionToolParam:
    schema = workflow.config.input_schema.model_json_schema()
    return ChatCompletionToolParam(
        type="function",
        function=ChatCompletionToolParamFunctionChunk(
            name=name,
            description=f"Execute the '{workflow.config.name}' workflow",
            parameters=schema,
        ),
    )


def _agent_tool_to_tool(name: str, tool: AgentTool) -> ChatCompletionToolParam:
    schema = tool.input_schema.model_json_schema()
    return ChatCompletionToolParam(
        type="function",
        function=ChatCompletionToolParamFunctionChunk(
            name=name,
            description=tool.description,
            parameters=schema,
        ),
    )


def _tool_name(tool: ChatCompletionToolParam) -> str:
    function = tool["function"]
    return str(function["name"])


def _accumulate_tool_call_delta(
    tc_delta: Any, collected: dict[int, ChatCompletionAssistantToolCall]
) -> None:
    idx: int = tc_delta.index
    if idx not in collected:
        collected[idx] = ChatCompletionAssistantToolCall(
            id=tc_delta.id or "",
            type="function",
            function=ChatCompletionToolCallFunctionChunk(name="", arguments=""),
        )
    entry = collected[idx]
    if tc_delta.id:
        entry["id"] = tc_delta.id
    if tc_delta.function:
        fn = entry["function"]
        if tc_delta.function.name:
            fn["name"] = (fn.get("name") or "") + tc_delta.function.name
        if tc_delta.function.arguments:
            fn["arguments"] = (fn.get("arguments") or "") + tc_delta.function.arguments


def _record_usage(span: trace.Span, usage: Any) -> None:
    """Write all available token-usage fields from a LiteLLM usage object onto span."""
    if usage is None:
        return
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_tokens", None)
    if prompt is not None:
        span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, int(prompt))
    if completion is not None:
        span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, int(completion))
    if total is not None:
        span.set_attribute(GEN_AI_USAGE_TOTAL_TOKENS, int(total))

    # Anthropic extended-thinking / prompt-caching extras
    thinking = getattr(usage, "thinking_tokens", None)
    cache_read = getattr(usage, "cache_read_input_tokens", None)
    cache_creation = getattr(usage, "cache_creation_input_tokens", None)
    if thinking is not None:
        span.set_attribute(GEN_AI_USAGE_THINKING_TOKENS, int(thinking))
    if cache_read is not None:
        span.set_attribute(GEN_AI_USAGE_CACHE_READ_TOKENS, int(cache_read))
    if cache_creation is not None:
        span.set_attribute(GEN_AI_USAGE_CACHE_CREATION_TOKENS, int(cache_creation))


def _record_error(span: trace.Span, exc: Exception) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    span.set_attribute(ERROR_TYPE, type(exc).__name__)
    span.set_attribute(ERROR_MESSAGE, str(exc))


class Agent:
    config: AgentConfig

    def __init__(self, *, config: AgentConfig) -> None:
        from alpha_app.workflow.workflow import Workflow as _Workflow

        self.config = config
        self._workflows: dict[str, _Workflow] = {
            name: _Workflow(config=wf_config)
            for name, wf_config in config.workflows.items()
        }
        self._tools: dict[str, AgentTool[Any, Any]] = dict(config.tools)

    def _build_system_prompt(self, context: AppContext | None = None) -> str:
        prompt = self.config.system_prompt
        workspace = getattr(context, "workspace", None)
        if workspace is None:
            return prompt

        additions = workspace.get_system_prompt_additions()
        if not additions:
            return prompt
        return f"{prompt}\n\n{additions}"

    def _get_tools(
        self, context: AppContext | None = None
    ) -> list[ChatCompletionToolParam] | None:
        params = [
            *(_workflow_to_tool(n, w) for n, w in self._workflows.items()),
            *(_agent_tool_to_tool(n, t) for n, t in self._tools.items()),
        ]
        workspace = getattr(context, "workspace", None)
        if workspace is not None:
            params.extend(workspace.get_tools())
        seen: set[str] = set()
        duplicates: set[str] = set()
        for tool in params:
            name = _tool_name(tool)
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ValueError(
                f"Agent '{self.config.name}' has duplicate tool name(s): {names}"
            )
        return params if params else None

    async def _dispatch_tool(
        self, name: str, arguments: dict, context: AppContext | None
    ) -> str:
        if context is None:
            raise RuntimeError(f"Cannot execute tool '{name}': no AppContext available")

        workspace = getattr(context, "workspace", None)
        tool_type = (
            "workflow"
            if name in self._workflows
            else "function"
            if name in self._tools
            else "workspace"
            if workspace is not None
            else "unknown"
        )
        with _tracer.start_as_current_span(
            f"{SPAN_AGENT_TOOL_CALL}/{name}",
            attributes={
                TOOL_NAME: name,
                TOOL_TYPE: tool_type,
                AGENT_NAME: self.config.name,
            },
        ) as span:
            span.set_attribute(TOOL_INPUT, json.dumps(arguments))
            span.add_event(EVENT_TOOL_CALL, {"tool.name": name, "tool.input": json.dumps(arguments)})
            try:
                if name in self._workflows:
                    wf = self._workflows[name]
                    input_data = wf.config.input_schema.model_validate(arguments)
                    output = await wf.execute(input_data, context)
                    result = (
                        output.model_dump_json()
                        if hasattr(output, "model_dump_json")
                        else json.dumps(output)
                    )
                elif name in self._tools:
                    tool = self._tools[name]
                    input_data = tool.input_schema.model_validate(arguments)
                    output = await tool.execute(input_data, context)
                    result = (
                        output.model_dump_json()
                        if hasattr(output, "model_dump_json")
                        else json.dumps(output)
                    )
                elif workspace is not None:
                    result = await workspace.execute_tool(name, arguments)
                else:
                    raise RuntimeError(f"Tool '{name}' not found")

                span.set_attribute(TOOL_RESULT_LENGTH, len(result))
                span.set_attribute(TOOL_OUTPUT, result)
                span.add_event(EVENT_TOOL_RESULT, {"tool.name": name, "tool.output": result})
                return result
            except Exception as exc:
                _record_error(span, exc)
                raise

    async def _generate_raw(
        self,
        user_prompt: str,
        context: AppContext | None = None,
        history: list[AllMessageValues] | None = None,
        on_tool_start: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str, int, int]:
        """
        Returns (content, total_iterations, total_tool_calls).
        Emits one ``gen_ai.chat`` child span per LLM call with token-usage attrs.
        """
        from litellm import acompletion

        messages: list[AllMessageValues] = [
            ChatCompletionSystemMessage(
                role="system", content=self._build_system_prompt(context)
            ),
            *(history or []),
            ChatCompletionUserMessage(role="user", content=user_prompt),
        ]
        tools = self._get_tools(context)
        total_tool_calls = 0

        for iteration in range(_MAX_TOOL_ITERATIONS):
            kwargs: dict[str, Any] = {"model": self.config.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools

            # --- per-LLM-call span -------------------------------------------
            with _tracer.start_as_current_span(
                SPAN_LLM_CHAT,
                kind=SpanKind.CLIENT,
                attributes={
                    GEN_AI_SYSTEM: "litellm",
                    GEN_AI_OPERATION_NAME: "chat",
                    GEN_AI_REQUEST_MODEL: self.config.model,
                    AGENT_NAME: self.config.name,
                    LLM_ITERATION: iteration,
                    LLM_MESSAGE_COUNT: len(messages),
                    LLM_HAS_TOOLS: tools is not None,
                    LLM_TOOL_DEFINITION_COUNT: len(tools) if tools else 0,
                },
            ) as llm_span:
                try:
                    response = cast("ModelResponse", await acompletion(**kwargs))
                except Exception as exc:
                    _record_error(llm_span, exc)
                    raise

                _record_usage(llm_span, getattr(response, "usage", None))
                actual_model = getattr(response, "model", None) or self.config.model
                llm_span.set_attribute(GEN_AI_RESPONSE_MODEL, actual_model)

                msg = response.choices[0].message
                finish_reason = getattr(response.choices[0], "finish_reason", None)
                if finish_reason:
                    llm_span.set_attribute(GEN_AI_RESPONSE_FINISH_REASON, finish_reason)

                # Normalise: empty list → None
                tool_calls = getattr(msg, "tool_calls", None) or None
                llm_span.set_attribute(LLM_RETURNED_TOOL_CALLS, tool_calls is not None)
            # -----------------------------------------------------------------

            if not tool_calls:
                content = msg.content
                if content is None:
                    if total_tool_calls > 0:
                        for entry in reversed(messages):
                            if entry["role"] == "tool":
                                raw = entry.get("content", "")  # type: ignore[union-attr]
                                return (raw if isinstance(raw, str) else ""), iteration + 1, total_tool_calls
                        return "", iteration + 1, total_tool_calls
                    raise ValueError("Model returned no content")
                return content, iteration + 1, total_tool_calls

            messages.append(
                ChatCompletionAssistantMessage(
                    role="assistant",
                    content=msg.content,
                    tool_calls=[
                        ChatCompletionAssistantToolCall(
                            id=tc.id,
                            type="function",
                            function=ChatCompletionToolCallFunctionChunk(
                                name=tc.function.name,
                                arguments=tc.function.arguments,
                            ),
                        )
                        for tc in tool_calls
                    ],
                )
            )
            for tc in tool_calls:
                name: str = tc.function.name or ""
                logger.debug(f"Agent '{self.config.name}' calling tool '{name}'")
                if on_tool_start:
                    await on_tool_start(name)
                result = await self._dispatch_tool(
                    name, json.loads(tc.function.arguments), context
                )
                total_tool_calls += 1
                messages.append(
                    ChatCompletionToolMessage(
                        role="tool",
                        tool_call_id=tc.id,
                        content=result,
                    )
                )

        raise RuntimeError(
            f"Agent '{self.config.name}' exceeded"
            f" {_MAX_TOOL_ITERATIONS} tool-call iterations"
        )

    async def generate_async(
        self,
        user_prompt: str,
        _context: AppContext,
        history: list[AllMessageValues] | None = None,
        on_tool_start: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        tool_count = len(self._tools) + len(self._workflows)
        with _tracer.start_as_current_span(
            f"{SPAN_AGENT_GENERATE}/{self.config.name}",
            attributes={
                AGENT_NAME: self.config.name,
                AGENT_DESCRIPTION: self.config.description or "",
                GEN_AI_REQUEST_MODEL: self.config.model,
                GEN_AI_OPERATION_NAME: "chat",
                AGENT_PROMPT_LENGTH: len(user_prompt),
                AGENT_HAS_HISTORY: bool(history),
                AGENT_HAS_TOOLS: tool_count > 0,
                AGENT_TOOL_COUNT: tool_count,
                AGENT_HAS_SCORERS: bool(self.config.scorers),
            },
        ) as span:
            span.set_attribute(AGENT_PROMPT, user_prompt)
            span.add_event(EVENT_USER_MESSAGE, {"content": user_prompt})
            try:
                logger.info(f"Agent '{self.config.name}' generating response")
                content, iterations, tool_calls = await self._generate_raw(
                    user_prompt, _context, history=history, on_tool_start=on_tool_start
                )
                span.set_attribute(AGENT_RESPONSE_LENGTH, len(content))
                span.set_attribute(AGENT_RESPONSE, content)
                span.set_attribute(AGENT_TOTAL_ITERATIONS, iterations)
                span.set_attribute(AGENT_TOTAL_TOOL_CALLS, tool_calls)
                span.add_event(EVENT_ASSISTANT_MESSAGE, {"content": content})
                if self.config.scorers:
                    asyncio.create_task(
                        run_scorers(self.config.scorers, user_prompt, content)
                    )
                return content
            except Exception as exc:
                _record_error(span, exc)
                raise

    async def generate_with_evals_async(
        self, user_prompt: str, _context: AppContext
    ) -> tuple[str, dict[str, ScorerResult]]:
        tool_count = len(self._tools) + len(self._workflows)
        with _tracer.start_as_current_span(
            f"{SPAN_AGENT_GENERATE_WITH_EVALS}/{self.config.name}",
            attributes={
                AGENT_NAME: self.config.name,
                AGENT_DESCRIPTION: self.config.description or "",
                GEN_AI_REQUEST_MODEL: self.config.model,
                GEN_AI_OPERATION_NAME: "chat",
                AGENT_PROMPT_LENGTH: len(user_prompt),
                AGENT_HAS_TOOLS: tool_count > 0,
                AGENT_TOOL_COUNT: tool_count,
                AGENT_HAS_SCORERS: bool(self.config.scorers),
            },
        ) as span:
            span.set_attribute(AGENT_PROMPT, user_prompt)
            span.add_event(EVENT_USER_MESSAGE, {"content": user_prompt})
            try:
                logger.info(f"Agent '{self.config.name}' generating response with evals")
                content, iterations, tool_calls = await self._generate_raw(
                    user_prompt, _context
                )
                span.set_attribute(AGENT_RESPONSE_LENGTH, len(content))
                span.set_attribute(AGENT_RESPONSE, content)
                span.set_attribute(AGENT_TOTAL_ITERATIONS, iterations)
                span.set_attribute(AGENT_TOTAL_TOOL_CALLS, tool_calls)
                span.add_event(EVENT_ASSISTANT_MESSAGE, {"content": content})
                scores = await run_scorers(self.config.scorers, user_prompt, content)
                return content, scores
            except Exception as exc:
                _record_error(span, exc)
                raise

    async def generate_structured_async(
        self, user_prompt: str, _context: AppContext, response_model: type[_T]
    ) -> _T:
        from litellm import acompletion

        with _tracer.start_as_current_span(
            f"{SPAN_AGENT_GENERATE_STRUCTURED}/{self.config.name}",
            attributes={
                AGENT_NAME: self.config.name,
                AGENT_DESCRIPTION: self.config.description or "",
                GEN_AI_REQUEST_MODEL: self.config.model,
                GEN_AI_OPERATION_NAME: "chat",
                AGENT_PROMPT_LENGTH: len(user_prompt),
                AGENT_RESPONSE_MODEL: response_model.__name__,
            },
        ) as span:
            try:
                logger.info(f"Agent '{self.config.name}' generating structured response")
                messages: list[AllMessageValues] = [
                    ChatCompletionSystemMessage(
                        role="system", content=self._build_system_prompt(_context)
                    ),
                    ChatCompletionUserMessage(role="user", content=user_prompt),
                ]

                with _tracer.start_as_current_span(
                    SPAN_LLM_CHAT,
                    kind=SpanKind.CLIENT,
                    attributes={
                        GEN_AI_SYSTEM: "litellm",
                        GEN_AI_OPERATION_NAME: "chat",
                        GEN_AI_REQUEST_MODEL: self.config.model,
                        AGENT_NAME: self.config.name,
                        LLM_ITERATION: 0,
                        LLM_MESSAGE_COUNT: len(messages),
                        LLM_HAS_TOOLS: False,
                        LLM_TOOL_DEFINITION_COUNT: 0,
                        "llm.structured_output": response_model.__name__,
                    },
                ) as llm_span:
                    try:
                        response = cast(
                            "ModelResponse",
                            await acompletion(
                                model=self.config.model,
                                messages=messages,
                                response_format=response_model,
                            ),
                        )
                    except Exception as exc:
                        _record_error(llm_span, exc)
                        raise

                    _record_usage(llm_span, getattr(response, "usage", None))
                    actual_model = getattr(response, "model", None) or self.config.model
                    llm_span.set_attribute(GEN_AI_RESPONSE_MODEL, actual_model)
                    finish_reason = getattr(response.choices[0], "finish_reason", None)
                    if finish_reason:
                        llm_span.set_attribute(GEN_AI_RESPONSE_FINISH_REASON, finish_reason)

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Model returned no content")

                span.set_attribute(AGENT_RESPONSE_LENGTH, len(content))
                return response_model.model_validate_json(content)
            except Exception as exc:
                _record_error(span, exc)
                raise

    async def stream_async(
        self, user_prompt: str, _context: AppContext
    ) -> AsyncIterator[str]:
        tool_count = len(self._tools) + len(self._workflows)
        with _tracer.start_as_current_span(
            f"{SPAN_AGENT_GENERATE_STREAM}/{self.config.name}",
            attributes={
                AGENT_NAME: self.config.name,
                AGENT_DESCRIPTION: self.config.description or "",
                GEN_AI_REQUEST_MODEL: self.config.model,
                GEN_AI_OPERATION_NAME: "chat",
                AGENT_PROMPT_LENGTH: len(user_prompt),
                AGENT_HAS_TOOLS: tool_count > 0,
                AGENT_TOOL_COUNT: tool_count,
            },
        ) as span:
            span.set_attribute(AGENT_PROMPT, user_prompt)
            span.add_event(EVENT_USER_MESSAGE, {"content": user_prompt})
            try:
                logger.info(f"Agent '{self.config.name}' streaming response")
                from litellm import acompletion

                messages: list[AllMessageValues] = [
                    ChatCompletionSystemMessage(
                        role="system", content=self._build_system_prompt(_context)
                    ),
                    ChatCompletionUserMessage(role="user", content=user_prompt),
                ]
                tools = self._get_tools(_context)
                total_chunks = 0
                total_tool_calls = 0

                for iteration in range(_MAX_TOOL_ITERATIONS):
                    kwargs: dict[str, Any] = {
                        "model": self.config.model,
                        "messages": messages,
                        "stream": True,
                    }
                    if tools:
                        kwargs["tools"] = tools

                    with _tracer.start_as_current_span(
                        SPAN_LLM_CHAT_STREAM,
                        kind=SpanKind.CLIENT,
                        attributes={
                            GEN_AI_SYSTEM: "litellm",
                            GEN_AI_OPERATION_NAME: "chat",
                            GEN_AI_REQUEST_MODEL: self.config.model,
                            AGENT_NAME: self.config.name,
                            LLM_ITERATION: iteration,
                            LLM_MESSAGE_COUNT: len(messages),
                            LLM_HAS_TOOLS: tools is not None,
                            LLM_TOOL_DEFINITION_COUNT: len(tools) if tools else 0,
                        },
                    ) as llm_span:
                        try:
                            response = cast(
                                "CustomStreamWrapper", await acompletion(**kwargs)
                            )
                        except Exception as exc:
                            _record_error(llm_span, exc)
                            raise

                        collected_content: list[str] = []
                        collected_tool_calls: dict[
                            int, ChatCompletionAssistantToolCall
                        ] = {}
                        iteration_chunks = 0

                        async for chunk in response:
                            delta = chunk.choices[0].delta
                            if delta.content is not None:
                                collected_content.append(delta.content)
                                yield delta.content
                                iteration_chunks += 1
                                total_chunks += 1
                            tc_deltas = getattr(delta, "tool_calls", None)
                            if tc_deltas:
                                for tc_delta in tc_deltas:
                                    _accumulate_tool_call_delta(
                                        tc_delta, collected_tool_calls
                                    )
                            # Capture usage from final chunk if provider sends it
                            usage = getattr(chunk, "usage", None)
                            if usage is not None:
                                _record_usage(llm_span, usage)

                        llm_span.set_attribute("llm.chunk_count", iteration_chunks)
                        llm_span.set_attribute(
                            LLM_RETURNED_TOOL_CALLS, bool(collected_tool_calls)
                        )

                    if not collected_tool_calls:
                        final_content = "".join(collected_content)
                        span.set_attribute(AGENT_TOTAL_ITERATIONS, iteration + 1)
                        span.set_attribute(AGENT_TOTAL_TOOL_CALLS, total_tool_calls)
                        span.set_attribute("agent.stream.total_chunks", total_chunks)
                        span.set_attribute(AGENT_RESPONSE, final_content)
                        span.add_event(EVENT_ASSISTANT_MESSAGE, {"content": final_content})
                        return

                    messages.append(
                        ChatCompletionAssistantMessage(
                            role="assistant",
                            content="".join(collected_content) or None,
                            tool_calls=list(collected_tool_calls.values()),
                        )
                    )
                    for tc in collected_tool_calls.values():
                        name: str = tc["function"].get("name") or ""
                        logger.debug(
                            f"Agent '{self.config.name}' calling tool '{name}'"
                        )
                        result = await self._dispatch_tool(
                            name,
                            json.loads(tc["function"].get("arguments") or "{}"),
                            _context,
                        )
                        total_tool_calls += 1
                        messages.append(
                            ChatCompletionToolMessage(
                                role="tool",
                                tool_call_id=tc["id"] or "",
                                content=result,
                            )
                        )

                raise RuntimeError(
                    f"Agent '{self.config.name}' exceeded"
                    f" {_MAX_TOOL_ITERATIONS} tool-call iterations"
                )
            except Exception as exc:
                _record_error(span, exc)
                raise


__all__ = ["Agent", "_workflow_to_tool"]
