from __future__ import annotations

from pydantic import BaseModel


class CommandResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


class BackgroundCommandResult(BaseModel):
    pid: int
    background: bool


class ProcessOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int | None
    running: bool


__all__ = ["CommandResult", "BackgroundCommandResult", "ProcessOutput"]
