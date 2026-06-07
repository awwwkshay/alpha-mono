from __future__ import annotations

import subprocess

from clay_studio_server.project import (
    load_project,
    read_git_branch,
    read_studio_project,
    read_studio_settings,
)


def test_load_project_reads_tool_clay_app_ref(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.0.1"

[tool.clay]
app = "demo.main:APP"
""",
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    assert project.root == tmp_path
    assert project.app_ref == "demo.main:APP"


def test_read_studio_settings_reads_tool_clay_studio(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.0.1"

[tool.clay.studio]
mode = "development"
host = "0.0.0.0"
port = 8123
open_browser = false
client_host = "127.0.0.1"
client_port = 5174
""",
        encoding="utf-8",
    )

    settings = read_studio_settings(tmp_path)

    assert settings.mode == "development"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8123
    assert settings.open_browser is False
    assert settings.client_host == "127.0.0.1"
    assert settings.client_port == 5174


def test_read_studio_settings_ignores_unknown_mode(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.0.1"

[tool.clay.studio]
mode = "staging"
""",
        encoding="utf-8",
    )

    settings = read_studio_settings(tmp_path)

    assert settings.mode == "production"


def test_read_studio_project_defaults_to_directory_name(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    model = read_studio_project(project)

    assert model.app.name == tmp_path.name
    assert model.agents == {}


def test_read_git_branch_returns_current_branch(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", "-b", "studio-dashboard"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    assert read_git_branch(tmp_path) == "studio-dashboard"
