from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from clay_core import (
    BackgroundCommandResult,
    CommandResult,
    ProcessOutput,
    SandboxContract,
)


@dataclass
class _BackgroundProcess:
    proc: asyncio.subprocess.Process
    stdout_buf: list[str] = field(default_factory=list)
    stderr_buf: list[str] = field(default_factory=list)
    _reader_task: asyncio.Task | None = None


class LocalSandbox(SandboxContract):
    """
    Subprocess-backed sandbox that runs commands on the local machine.

    Args:
        working_directory: Working directory for all commands.
        env:               Extra environment variables merged on top of the
                           current process environment.
        timeout:           Per-command timeout in seconds for foreground
                           commands (default: 30).
        isolation:         OS-level sandbox wrapper applied to every command:
                           - "none"      — no extra isolation (default)
                           - "seatbelt"  — macOS sandbox-exec (read-only FS)
                           - "bwrap"     — Linux bubblewrap (read-only bind mount)
    """

    def __init__(
        self,
        *,
        working_directory: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 30,
        isolation: Literal["none", "seatbelt", "bwrap"] = "none",
    ) -> None:
        self._cwd = str(working_directory) if working_directory else None
        self._env = {**os.environ, **(env or {})}
        self._timeout = timeout
        self._isolation = isolation
        self._fg_processes: dict[int, asyncio.subprocess.Process] = {}
        self._bg_processes: dict[int, _BackgroundProcess] = {}

    def _wrap_command(self, command: str) -> str:
        if self._isolation == "seatbelt" and sys.platform == "darwin":
            policy = "(version 1)(allow default)(deny file-write*)"
            return f"sandbox-exec -p '{policy}' sh -c {_shell_quote(command)}"
        if self._isolation == "bwrap" and sys.platform.startswith("linux"):  # type: ignore[unreachable]
            return (
                "bwrap --ro-bind / / --tmpfs /tmp --unshare-all "
                f"-- sh -c {_shell_quote(command)}"
            )
        return command

    # ------------------------------------------------------------------
    # Foreground execution
    # ------------------------------------------------------------------

    async def execute_command(
        self,
        command: str,
        *,
        background: bool = False,
    ) -> CommandResult | BackgroundCommandResult:
        wrapped = self._wrap_command(command)

        if background:
            return await self._spawn_background(wrapped)

        proc = await asyncio.create_subprocess_shell(
            wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env=self._env,
        )
        self._fg_processes[proc.pid] = proc
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except TimeoutError:
            proc.kill()
            raise TimeoutError(f"Command timed out after {self._timeout}s: {command!r}")
        finally:
            self._fg_processes.pop(proc.pid, None)

        return CommandResult(
            stdout=stdout_b.decode(errors="replace"),
            stderr=stderr_b.decode(errors="replace"),
            exit_code=proc.returncode if proc.returncode is not None else -1,
        )

    # ------------------------------------------------------------------
    # Background process management
    # ------------------------------------------------------------------

    async def _spawn_background(self, command: str) -> BackgroundCommandResult:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env=self._env,
        )
        bg = _BackgroundProcess(proc=proc)
        self._bg_processes[proc.pid] = bg
        bg._reader_task = asyncio.create_task(self._read_bg_output(bg))
        return BackgroundCommandResult(pid=proc.pid, background=True)

    @staticmethod
    async def _read_bg_output(bg: _BackgroundProcess) -> None:
        assert bg.proc.stdout and bg.proc.stderr

        async def drain(stream: asyncio.StreamReader, buf: list[str]) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                buf.append(line.decode(errors="replace"))

        await asyncio.gather(
            drain(bg.proc.stdout, bg.stdout_buf),
            drain(bg.proc.stderr, bg.stderr_buf),
        )
        await bg.proc.wait()

    async def get_process_output(
        self,
        pid: int,
        *,
        tail: int | None = None,
        wait: bool = False,
    ) -> ProcessOutput:
        bg = self._bg_processes.get(pid)
        if bg is None:
            raise ValueError(f"No background process with pid {pid}")

        if wait and bg._reader_task is not None:
            await bg._reader_task

        stdout_lines = bg.stdout_buf
        stderr_lines = bg.stderr_buf
        if tail is not None:
            stdout_lines = stdout_lines[-tail:]
            stderr_lines = stderr_lines[-tail:]

        running = bg.proc.returncode is None
        return ProcessOutput(
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            exit_code=bg.proc.returncode,
            running=running,
        )

    # ------------------------------------------------------------------
    # Process control
    # ------------------------------------------------------------------

    async def kill_process(self, pid: int) -> None:
        bg = self._bg_processes.pop(pid, None)
        if bg is not None:
            try:
                bg.proc.kill()
            except ProcessLookupError:
                pass
            return

        fg = self._fg_processes.pop(pid, None)
        if fg is not None:
            try:
                fg.kill()
            except ProcessLookupError:
                pass
            return

        raise ValueError(f"No tracked process with pid {pid}")

    async def teardown(self) -> None:
        for bg in list(self._bg_processes.values()):
            try:
                bg.proc.kill()
            except ProcessLookupError:
                pass
        self._bg_processes.clear()

        for proc in list(self._fg_processes.values()):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        self._fg_processes.clear()


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


__all__ = ["LocalSandbox"]
