from __future__ import annotations

from alpha_core import (
    BackgroundCommandResult,
    CommandResult,
    ProcessOutput,
    SandboxContract,
)


class E2BSandbox(SandboxContract):
    """
    E2B cloud sandbox (stub — not yet implemented).

    Expected constructor args:
        template:  E2B sandbox template ID (e.g. "python-3.11")
        api_key:   E2B API key (default: from E2B_API_KEY env var)
        timeout:   Per-command timeout in seconds (default: 60)
    """

    def __init__(
        self,
        template: str,
        *,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        self._template = template
        self._api_key = api_key
        self._timeout = timeout

    async def setup(self) -> None:
        raise NotImplementedError("E2BSandbox is not yet implemented")

    async def teardown(self) -> None:
        raise NotImplementedError("E2BSandbox is not yet implemented")

    async def execute_command(
        self,
        command: str,
        *,
        background: bool = False,
    ) -> CommandResult | BackgroundCommandResult:
        raise NotImplementedError("E2BSandbox is not yet implemented")

    async def get_process_output(
        self,
        pid: int,
        *,
        tail: int | None = None,
        wait: bool = False,
    ) -> ProcessOutput:
        raise NotImplementedError("E2BSandbox is not yet implemented")

    async def kill_process(self, pid: int) -> None:
        raise NotImplementedError("E2BSandbox is not yet implemented")


__all__ = ["E2BSandbox"]
