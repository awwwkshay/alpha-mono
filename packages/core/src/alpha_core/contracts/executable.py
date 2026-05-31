from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from alpha_core.schemas.app_context import AppContext

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Executable(ABC, Generic[InputT, OutputT]):
    input_schema: type[InputT]
    output_schema: type[OutputT]

    @abstractmethod
    async def execute(self, input_data: InputT, context: AppContext) -> OutputT: ...


__all__ = ["Executable"]
