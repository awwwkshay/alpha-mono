from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from alpha_app import AgentTool

if TYPE_CHECKING:
    from alpha_app import AppContext


class GetDatetimeInput(BaseModel):
    pass


class GetDatetimeOutput(BaseModel):
    datetime: str
    timezone: str


async def _execute(_inp: GetDatetimeInput, _ctx: AppContext) -> GetDatetimeOutput:
    now = datetime.datetime.now().astimezone()
    return GetDatetimeOutput(
        datetime=now.strftime("%Y-%m-%d %H:%M:%S"),
        timezone=str(now.tzinfo),
    )


get_datetime_tool: AgentTool[GetDatetimeInput, GetDatetimeOutput] = AgentTool(
    name="get_current_datetime",
    description="Get the current date, time, and timezone.",
    input_schema=GetDatetimeInput,
    output_schema=GetDatetimeOutput,
    execute=_execute,
)

__all__ = ["get_datetime_tool"]
