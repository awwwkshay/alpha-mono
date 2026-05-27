from __future__ import annotations

from abc import ABC, abstractmethod


from alpha_core.schemas.sandbox import (
    BackgroundCommandResult,
    CommandResult,
    ProcessOutput,
)


class SandboxContract(ABC):
    """
    Abstract command-execution backend.  Implement this to plug in any sandbox
    (local subprocess, E2B, Daytona, Modal, etc.) and pass an instance to WorkspaceConfig.
    """

    async def setup(self) -> None:
        """Called once by Workspace.setup(). Pre-provision resources, warm containers, etc."""

    async def teardown(self) -> None:
        """Called by Workspace.teardown(). Release resources, kill processes, close sessions."""

    @abstractmethod
    async def execute_command(
        self,
        command: str,
        *,
        background: bool = False,
    ) -> CommandResult | BackgroundCommandResult:
        """
        Run a shell command.

        background=False (default): wait for exit and return
            {"stdout": str, "stderr": str, "exit_code": int}

        background=True: spawn without waiting and return immediately with
            {"pid": int, "background": True}
        """
        ...

    @abstractmethod
    async def get_process_output(
        self,
        pid: int,
        *,
        tail: int | None = None,
        wait: bool = False,
    ) -> ProcessOutput:
        """
        Retrieve accumulated output from a background process.

        Args:
            pid:  Process ID returned by execute_command(background=True).
            tail: Return only the last N lines of stdout/stderr.
            wait: Block until the process exits before returning.

        Returns:
            {"stdout": str, "stderr": str, "exit_code": int | None, "running": bool}
        """
        ...

    @abstractmethod
    async def kill_process(self, pid: int) -> None: ...


__all__ = ["SandboxContract"]
