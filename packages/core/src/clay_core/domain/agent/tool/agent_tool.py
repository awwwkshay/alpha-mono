from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Callable, TypeVar

from pydantic import BaseModel

from clay_core.contracts.executable import Executable

if TYPE_CHECKING:
    from clay_core.schemas.app_context import AppContext

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentTool(Executable[InputT, OutputT]):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        execute: Callable[[InputT, AppContext], Awaitable[OutputT]],
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self._execute_fn = execute

    async def execute(self, input_data: InputT, context: AppContext) -> OutputT:
        return await self._execute_fn(input_data, context)


__all__ = ["AgentTool"]
