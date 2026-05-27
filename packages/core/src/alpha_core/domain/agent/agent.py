from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, cast

from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionAssistantToolCall,
    ChatCompletionSystemMessage,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolMessage,
    ChatCompletionUserMessage,
)

from opentelemetry import trace

from alpha_core.log import logger
from alpha_core.domain.evals.runner import run_scorers
from alpha_core.domain.evals.scorer import ScorerResult
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_context import AppContext

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse

    from alpha_core.domain.workspace.workspace import Workspace

_MAX_TOOL_ITERATIONS = 20


def _build_system(config: AgentConfig, workspace: Workspace | None) -> str:
    system = config.system_prompt
    if workspace:
        additions = workspace.get_system_prompt_additions()
        if additions:
            return f"{system}\n\n{additions}"
    return system


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

    def __init__(
        self, *, config: AgentConfig, workspace: Workspace | None = None
    ) -> None:
        self.config = config
        self._workspace = workspace

    async def _generate_raw(self, user_prompt: str) -> str:
        from litellm import acompletion

        messages: list[AllMessageValues] = [
            ChatCompletionSystemMessage(
                role="system", content=_build_system(self.config, self._workspace)
            ),
            ChatCompletionUserMessage(role="user", content=user_prompt),
        ]
        tools = self._workspace.get_tools() if self._workspace else None
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
            assert self._workspace is not None
            for tc in tool_calls:
                name: str = tc.function.name or ""
                logger.debug(f"Agent '{self.config.name}' calling tool '{name}'")
                result = await self._workspace.execute_tool(
                    name, json.loads(tc.function.arguments)
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

    async def generate_async(self, user_prompt: str, _context: AppContext) -> str:
        tracer = trace.get_tracer(__name__)
        logger.info(f"Agent '{self.config.name}' generating response")
        with tracer.start_as_current_span(
            f"Agent.generate_async/{self.config.name}",
            attributes={"agent_name": self.config.name, "model": self.config.model},
        ):
            content = await self._generate_raw(user_prompt)
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
            content = await self._generate_raw(user_prompt)
            scores = await run_scorers(self.config.scorers, user_prompt, content)
            return content, scores

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
                    role="system", content=_build_system(self.config, self._workspace)
                ),
                ChatCompletionUserMessage(role="user", content=user_prompt),
            ]
        tools = self._workspace.get_tools() if self._workspace else None

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
            assert self._workspace is not None
            for tc in collected_tool_calls.values():
                name: str = tc["function"].get("name") or ""
                logger.debug(f"Agent '{self.config.name}' calling tool '{name}'")
                result = await self._workspace.execute_tool(
                    name,
                    json.loads(tc["function"].get("arguments") or "{}"),
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


__all__ = ["Agent"]
