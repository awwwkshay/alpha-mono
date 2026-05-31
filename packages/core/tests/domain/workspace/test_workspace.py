from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_app.workspace.workspace import Workspace, _load_skills
from alpha_core.schemas.filesystem_config import LocalFilesystemConfig
from alpha_core.schemas.sandbox_config import LocalSandboxConfig
from alpha_core.schemas.workspace_config import WorkspaceConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ws(tmp_path: Path, *, with_sandbox: bool = False) -> Workspace:
    sandbox = LocalSandboxConfig(working_directory=tmp_path) if with_sandbox else None
    cfg = WorkspaceConfig(
        name="test",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
        sandbox=sandbox,
    )
    return Workspace(cfg)


# ---------------------------------------------------------------------------
# _load_skills
# ---------------------------------------------------------------------------


def test_load_skills_finds_skill_directories(tmp_path):
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("# My Skill\nDo things.")
    (skill_dir / "data.json").write_text('{"key": "value"}')

    skills = _load_skills([tmp_path / "skills"])
    assert len(skills) == 1
    assert skills[0].name == "my_skill"
    assert "Do things" in skills[0].instructions
    assert "data.json" in skills[0].files


def test_load_skills_ignores_dirs_without_skill_md(tmp_path):
    bad_dir = tmp_path / "skills" / "no_instructions"
    bad_dir.mkdir(parents=True)
    (bad_dir / "readme.txt").write_text("no skill.md here")

    skills = _load_skills([tmp_path / "skills"])
    assert skills == []


def test_load_skills_nonexistent_path_returns_empty(tmp_path):
    skills = _load_skills([tmp_path / "does_not_exist"])
    assert skills == []


# ---------------------------------------------------------------------------
# Workspace.setup / teardown
# ---------------------------------------------------------------------------


async def test_workspace_setup_initialises_fs(tmp_path):
    ws = _ws(tmp_path)
    assert ws._fs is None
    await ws.setup()
    assert ws._fs is not None


async def test_workspace_setup_initialises_sandbox(tmp_path):
    ws = _ws(tmp_path, with_sandbox=True)
    assert ws._sandbox is None
    await ws.setup()
    assert ws._sandbox is not None
    await ws.teardown()


async def test_workspace_teardown_without_sandbox_does_not_raise(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()
    await ws.teardown()  # no sandbox — should be a no-op


# ---------------------------------------------------------------------------
# Workspace.get_tools
# ---------------------------------------------------------------------------


async def test_get_tools_empty_before_setup(tmp_path):
    ws = _ws(tmp_path)
    # Before setup, _fs is None → no tools
    assert ws.get_tools() == []


async def test_get_tools_returns_fs_tools_after_setup(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()
    tools = ws.get_tools()
    names = {t["function"]["name"] for t in tools}
    assert "read_file" in names
    assert "write_file" in names


async def test_get_tools_includes_sandbox_tools(tmp_path):
    ws = _ws(tmp_path, with_sandbox=True)
    await ws.setup()
    tools = ws.get_tools()
    names = {t["function"]["name"] for t in tools}
    assert "execute_command" in names
    await ws.teardown()


# ---------------------------------------------------------------------------
# Workspace.execute_tool — filesystem operations
# ---------------------------------------------------------------------------


async def test_execute_tool_write_and_read(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()

    await ws.execute_tool("write_file", {"path": "out.txt", "content": "hello"})
    result_json = await ws.execute_tool("read_file", {"path": "out.txt"})
    result = json.loads(result_json)
    assert result["content"] == "hello"


async def test_execute_tool_exception_returns_error_json(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()

    result_json = await ws.execute_tool("read_file", {"path": "nonexistent.txt"})
    result = json.loads(result_json)
    assert "error" in result


async def test_execute_tool_unknown_tool_returns_error_json(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()

    result_json = await ws.execute_tool("nonexistent_tool", {})
    result = json.loads(result_json)
    assert "error" in result


# ---------------------------------------------------------------------------
# Workspace._read_skill_file
# ---------------------------------------------------------------------------


def _ws_with_skill(tmp_path: Path) -> Workspace:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("instructions")
    (skill_dir / "data.json").write_text('{"x": 1}')

    from alpha_core.schemas.workspace_config import SkillsConfig

    cfg = WorkspaceConfig(
        name="test",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
        skills=SkillsConfig(paths=[tmp_path / "skills"]),
    )
    return Workspace(cfg)


async def test_read_skill_file_returns_content(tmp_path):
    ws = _ws_with_skill(tmp_path)
    await ws.setup()
    content = ws._read_skill_file("my_skill", "data.json")
    assert content == '{"x": 1}'


async def test_read_skill_file_unknown_skill_raises(tmp_path):
    ws = _ws_with_skill(tmp_path)
    await ws.setup()
    with pytest.raises(FileNotFoundError, match="missing_skill"):
        ws._read_skill_file("missing_skill", "data.json")


async def test_read_skill_file_unknown_file_raises(tmp_path):
    ws = _ws_with_skill(tmp_path)
    await ws.setup()
    with pytest.raises(FileNotFoundError, match="missing.txt"):
        ws._read_skill_file("my_skill", "missing.txt")


# ---------------------------------------------------------------------------
# Workspace.get_system_prompt_additions
# ---------------------------------------------------------------------------


async def test_get_system_prompt_additions_includes_skill_instructions(tmp_path):
    ws = _ws_with_skill(tmp_path)
    await ws.setup()
    additions = ws.get_system_prompt_additions()
    assert "my_skill" in additions
    assert "instructions" in additions


async def test_get_system_prompt_additions_empty_when_no_skills(tmp_path):
    ws = _ws(tmp_path)
    await ws.setup()
    additions = ws.get_system_prompt_additions()
    assert additions == ""
