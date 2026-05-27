from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, cast

from core.schemas.agent_config import AgentConfig
from core.schemas.app_context import AppContext

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse

    from core.domain.workspace.workspace import Workspace

_MAX_TOOL_ITERATIONS = 20


def _build_system(config: AgentConfig, workspace: Workspace | None) -> str:
    system = config.system_prompt
    if workspace:
        additions = workspace.get_system_prompt_additions()
        if additions:
            return f"{system}\n\n{additions}"
    return system


def _accumulate_tool_call_delta(
    tc_delta: Any, collected: dict[int, dict[str, Any]]
) -> None:
    idx: int = tc_delta.index
    if idx not in collected:
        collected[idx] = {
            "id": tc_delta.id or "",
            "type": "function",
            "function": {"name": "", "arguments": ""},
        }
    entry = collected[idx]
    if tc_delta.id:
        entry["id"] = tc_delta.id
    if tc_delta.function:
        if tc_delta.function.name:
            entry["function"]["name"] += tc_delta.function.name
        if tc_delta.function.arguments:
            entry["function"]["arguments"] += tc_delta.function.arguments


class Agent:
    config: AgentConfig

    def __init__(
        self, *, config: AgentConfig, workspace: Workspace | None = None
    ) -> None:
        self.config = config
        self._workspace = workspace

    async def generate_async(self, user_prompt: str, context: AppContext) -> str:
        from litellm import acompletion

        messages: list[Any] = [
            {"role": "system", "content": _build_system(self.config, self._workspace)},
            {"role": "user", "content": user_prompt},
        ]
        tools = self._workspace.get_tools() if self._workspace else None

        for _ in range(_MAX_TOOL_ITERATIONS):
            kwargs: dict[str, Any] = {"model": self.config.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools

            response = cast("ModelResponse", await acompletion(**kwargs))
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            if not tool_calls:
                content = msg.content
                if content is None:
                    raise ValueError("Model returned no content")
                return content

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            assert self._workspace is not None
            for tc in tool_calls:
                name: str = tc.function.name or ""
                result = await self._workspace.execute_tool(
                    name, json.loads(tc.function.arguments)
                )
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )

        raise RuntimeError(
            f"Agent '{self.config.name}' exceeded"
            f" {_MAX_TOOL_ITERATIONS} tool-call iterations"
        )

    async def stream_async(
        self, user_prompt: str, context: AppContext
    ) -> AsyncIterator[str]:
        from litellm import acompletion

        messages: list[Any] = [
            {"role": "system", "content": _build_system(self.config, self._workspace)},
            {"role": "user", "content": user_prompt},
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
            collected_tool_calls: dict[int, dict[str, Any]] = {}

            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    collected_content.append(delta.content)
                    yield delta.content
                tool_calls = getattr(delta, "tool_calls", None)
                if tool_calls:
                    for tc_delta in tool_calls:
                        _accumulate_tool_call_delta(tc_delta, collected_tool_calls)

            if not collected_tool_calls:
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(collected_content) or None,
                    "tool_calls": list(collected_tool_calls.values()),
                }
            )
            assert self._workspace is not None
            for tc in collected_tool_calls.values():
                result = await self._workspace.execute_tool(
                    tc["function"]["name"],
                    json.loads(tc["function"]["arguments"]),
                )
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

        raise RuntimeError(
            f"Agent '{self.config.name}' exceeded"
            f" {_MAX_TOOL_ITERATIONS} tool-call iterations"
        )


__all__ = ["Agent"]
