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

from alpha_core.log import logger
from alpha_core.domain.agent.tool.agent_tool import AgentTool
from alpha_core.domain.evals.runner import run_scorers
from alpha_core.contracts.evals.scorer_contract import ScorerResult
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_context import AppContext

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse
    from alpha_core.domain.workflow.workflow import Workflow

AgentConfig.model_rebuild()

_MAX_TOOL_ITERATIONS = 20
_T = TypeVar("_T", bound=BaseModel)


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


class Agent:
    config: AgentConfig

    def __init__(self, *, config: AgentConfig) -> None:
        from alpha_core.domain.workflow.workflow import Workflow as _Workflow

        self.config = config
        self._workflows: dict[str, _Workflow] = {
            name: _Workflow(config=wf_config)
            for name, wf_config in config.workflows.items()
        }
        self._tools: dict[str, AgentTool[Any, Any]] = dict(config.tools)

    def _get_tools(self) -> list[ChatCompletionToolParam] | None:
        params = [
            *(_workflow_to_tool(n, w) for n, w in self._workflows.items()),
            *(_agent_tool_to_tool(n, t) for n, t in self._tools.items()),
        ]
        return params if params else None

    async def _dispatch_tool(
        self, name: str, arguments: dict, context: AppContext | None
    ) -> str:
        if context is None:
            raise RuntimeError(f"Cannot execute tool '{name}': no AppContext available")
        if name in self._workflows:
            wf = self._workflows[name]
            input_data = wf.config.input_schema.model_validate(arguments)
            output = await wf.execute(input_data, context)
            return (
                output.model_dump_json()
                if hasattr(output, "model_dump_json")
                else json.dumps(output)
            )
        if name in self._tools:
            tool = self._tools[name]
            input_data = tool.input_schema.model_validate(arguments)
            output = await tool.execute(input_data, context)
            return (
                output.model_dump_json()
                if hasattr(output, "model_dump_json")
                else json.dumps(output)
            )
        raise RuntimeError(f"Tool '{name}' not found")

    async def _generate_raw(
        self,
        user_prompt: str,
        context: AppContext | None = None,
        history: list[AllMessageValues] | None = None,
        on_tool_start: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        from litellm import acompletion

        messages: list[AllMessageValues] = [
            ChatCompletionSystemMessage(
                role="system", content=self.config.system_prompt
            ),
            *(history or []),
            ChatCompletionUserMessage(role="user", content=user_prompt),
        ]
        tools = self._get_tools()
        tool_calls_executed = False

        for _ in range(_MAX_TOOL_ITERATIONS):
            kwargs: dict[str, Any] = {"model": self.config.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools

            response = cast("ModelResponse", await acompletion(**kwargs))
            msg = response.choices[0].message
            # Normalise: LiteLLM/Gemini may return [] instead of None when there
            # are no tool calls — an empty list is falsy but should be treated as None.
            tool_calls = getattr(msg, "tool_calls", None) or None

            if not tool_calls:
                content = msg.content
                if content is None:
                    if tool_calls_executed:
                        # Gemini sometimes returns no content after completing a
                        # tool-call cycle; the tool results are the answer.
                        # Return the most recent tool result from the message history.
                        for entry in reversed(messages):
                            if entry["role"] == "tool":
                                raw = entry.get("content", "")  # type: ignore[union-attr]
                                return raw if isinstance(raw, str) else ""
                        return ""
                    raise ValueError("Model returned no content")
                return content

            tool_calls_executed = True

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
        tracer = trace.get_tracer(__name__)
        logger.info(f"Agent '{self.config.name}' generating response")
        with tracer.start_as_current_span(
            f"Agent.generate_async/{self.config.name}",
            attributes={"agent_name": self.config.name, "model": self.config.model},
        ):
            content = await self._generate_raw(
                user_prompt, _context, history=history, on_tool_start=on_tool_start
            )
            if self.config.scorers:
                asyncio.create_task(
                    run_scorers(self.config.scorers, user_prompt, content)
                )
            return content

    async def generate_with_evals_async(
        self, user_prompt: str, _context: AppContext
    ) -> tuple[str, dict[str, ScorerResult]]:
        tracer = trace.get_tracer(__name__)
        logger.info(f"Agent '{self.config.name}' generating response with evals")
        with tracer.start_as_current_span(
            f"Agent.generate_with_evals_async/{self.config.name}",
            attributes={"agent_name": self.config.name, "model": self.config.model},
        ):
            content = await self._generate_raw(user_prompt, _context)
            scores = await run_scorers(self.config.scorers, user_prompt, content)
            return content, scores

    async def generate_structured_async(
        self, user_prompt: str, _context: AppContext, response_model: type[_T]
    ) -> _T:
        from litellm import acompletion

        tracer = trace.get_tracer(__name__)
        logger.info(f"Agent '{self.config.name}' generating structured response")
        with tracer.start_as_current_span(
            f"Agent.generate_structured_async/{self.config.name}",
            attributes={"agent_name": self.config.name, "model": self.config.model},
        ):
            messages: list[AllMessageValues] = [
                ChatCompletionSystemMessage(
                    role="system", content=self.config.system_prompt
                ),
                ChatCompletionUserMessage(role="user", content=user_prompt),
            ]
            response = cast(
                "ModelResponse",
                await acompletion(
                    model=self.config.model,
                    messages=messages,
                    response_format=response_model,
                ),
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Model returned no content")
            return response_model.model_validate_json(content)

    async def stream_async(
        self, user_prompt: str, _context: AppContext
    ) -> AsyncIterator[str]:
        tracer = trace.get_tracer(__name__)
        logger.info(f"Agent '{self.config.name}' streaming response")
        with tracer.start_as_current_span(
            f"Agent.stream_async/{self.config.name}",
            attributes={"agent_name": self.config.name, "model": self.config.model},
        ):
            from litellm import acompletion

            messages: list[AllMessageValues] = [
                ChatCompletionSystemMessage(
                    role="system", content=self.config.system_prompt
                ),
                ChatCompletionUserMessage(role="user", content=user_prompt),
            ]
            tools = self._get_tools()

            for _ in range(_MAX_TOOL_ITERATIONS):
                kwargs: dict[str, Any] = {
                    "model": self.config.model,
                    "messages": messages,
                    "stream": True,
                }
                if tools:
                    kwargs["tools"] = tools

                response = cast("CustomStreamWrapper", await acompletion(**kwargs))
                collected_content: list[str] = []
                collected_tool_calls: dict[int, ChatCompletionAssistantToolCall] = {}

                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content is not None:
                        collected_content.append(delta.content)
                        yield delta.content
                    tc_deltas = getattr(delta, "tool_calls", None)
                    if tc_deltas:
                        for tc_delta in tc_deltas:
                            _accumulate_tool_call_delta(tc_delta, collected_tool_calls)

                if not collected_tool_calls:
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
                    logger.debug(f"Agent '{self.config.name}' calling tool '{name}'")
                    result = await self._dispatch_tool(
                        name,
                        json.loads(tc["function"].get("arguments") or "{}"),
                        _context,
                    )
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


__all__ = ["Agent", "_workflow_to_tool"]
