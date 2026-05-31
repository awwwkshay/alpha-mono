from __future__ import annotations


import pytest

from alpha_app.workspace.sandboxes.local_sandbox import LocalSandbox
from alpha_core.schemas.sandbox import BackgroundCommandResult, CommandResult


# ---------------------------------------------------------------------------
# execute_command — foreground
# ---------------------------------------------------------------------------


async def test_execute_command_captures_stdout():
    sb = LocalSandbox()
    result = await sb.execute_command("echo hello")
    assert isinstance(result, CommandResult)
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0


async def test_execute_command_captures_stderr():
    sb = LocalSandbox()
    result = await sb.execute_command("echo err >&2")
    assert isinstance(result, CommandResult)
    assert "err" in result.stderr


async def test_execute_command_nonzero_exit_code():
    sb = LocalSandbox()
    result = await sb.execute_command(
        "exit 42",
    )
    assert isinstance(result, CommandResult)
    assert result.exit_code == 42


async def test_execute_command_timeout_raises():
    sb = LocalSandbox(timeout=1)
    with pytest.raises(TimeoutError, match="timed out"):
        await sb.execute_command("sleep 10")


async def test_execute_command_uses_working_directory(tmp_path):
    (tmp_path / "hello.txt").write_text("content")
    sb = LocalSandbox(working_directory=tmp_path)
    result = await sb.execute_command("ls hello.txt")
    assert isinstance(result, CommandResult)
    assert "hello.txt" in result.stdout


# ---------------------------------------------------------------------------
# Background processes
# ---------------------------------------------------------------------------


async def test_execute_command_background_returns_pid():
    sb = LocalSandbox()
    result = await sb.execute_command("sleep 5", background=True)
    assert isinstance(result, BackgroundCommandResult)
    assert hasattr(result, "pid")
    assert result.background is True
    # Cleanup
    await sb.kill_process(result.pid)


async def test_get_process_output_with_wait(tmp_path):
    sb = LocalSandbox()
    bg = await sb.execute_command("echo bg_output", background=True)
    assert isinstance(bg, BackgroundCommandResult)
    out = await sb.get_process_output(bg.pid, wait=True)
    assert "bg_output" in out.stdout
    assert out.running is False


async def test_get_process_output_tail(tmp_path):
    sb = LocalSandbox()
    # Produce many lines
    bg = await sb.execute_command(
        "for i in $(seq 1 10); do echo line$i; done", background=True
    )
    assert isinstance(bg, BackgroundCommandResult)
    output = await sb.get_process_output(bg.pid, wait=True, tail=3)
    lines = output.stdout.strip().splitlines()
    assert len(lines) <= 3


async def test_get_process_output_unknown_pid_raises():
    sb = LocalSandbox()
    with pytest.raises(ValueError, match="No background process"):
        await sb.get_process_output(99999)


async def test_kill_process_background(tmp_path):
    sb = LocalSandbox()
    bg = await sb.execute_command("sleep 30", background=True)
    assert isinstance(bg, BackgroundCommandResult)
    await sb.kill_process(bg.pid)
    # Process should no longer be tracked
    with pytest.raises(ValueError):
        await sb.get_process_output(bg.pid)


async def test_kill_process_unknown_raises():
    sb = LocalSandbox()
    with pytest.raises(ValueError, match="No tracked process"):
        await sb.kill_process(99999)


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


async def test_teardown_kills_background_processes():
    sb = LocalSandbox()
    bg = await sb.execute_command("sleep 60", background=True)
    assert isinstance(bg, BackgroundCommandResult)
    pid = bg.pid
    await sb.teardown()
    # After teardown the bg dict is cleared
    assert pid not in sb._bg_processes


async def test_teardown_clears_all_process_dicts():
    sb = LocalSandbox()
    await sb.execute_command("sleep 60", background=True)
    await sb.teardown()
    assert sb._bg_processes == {}
    assert sb._fg_processes == {}
