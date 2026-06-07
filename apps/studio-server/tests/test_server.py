from __future__ import annotations

from fastapi.testclient import TestClient

from clay_studio_server.server import create_studio_app


def test_studio_server_exposes_health_and_spa(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    app = create_studio_app(project_root=tmp_path)
    client = TestClient(app)

    health = client.get("/api/health")
    project = client.get("/api/project")
    index = client.get("/some/react/route")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert project.status_code == 200
    assert "git_branch" in project.json()
    assert index.status_code == 200
    assert "Clay Studio" in index.text


def test_models_endpoint_returns_litellm_models(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    app = create_studio_app(project_root=tmp_path)
    client = TestClient(app)

    response = client.get("/api/models")

    assert response.status_code == 200
    assert {"id": "gpt-3.5-turbo"} in response.json()


def test_sync_updates_workspaces_from_loaded_app(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.0.1"

[tool.clay]
app = "demo_app:APP"
""",
        encoding="utf-8",
    )
    (tmp_path / "workspaces" / "sales").mkdir(parents=True)
    (tmp_path / "demo_app.py").write_text(
        """
from pathlib import Path

from clay_app import ClayApp
from clay_core import AppConfig, LocalFilesystemConfig, LocalSandboxConfig, WorkspaceConfig

ROOT = Path(__file__).parent
WORKSPACE = ROOT / "workspaces" / "sales"
APP = ClayApp(
    config=AppConfig(
        name="demo",
        workspace=WorkspaceConfig(
            name="sales",
            filesystem=LocalFilesystemConfig(base_path=WORKSPACE),
            sandbox=LocalSandboxConfig(working_directory=WORKSPACE),
        ),
    )
)
""",
        encoding="utf-8",
    )
    app = create_studio_app(project_root=tmp_path)
    client = TestClient(app)

    response = client.post("/api/sync")

    assert response.status_code == 200
    assert response.json()["workspaces"]["sales"]["filesystem"]["base_path"] == (
        "workspaces/sales"
    )


def test_create_agent_writes_project_files(tmp_path):
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
    package_dir = tmp_path / "src" / "demo"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "main.py").write_text(
        """
from __future__ import annotations

from clay_app import ClayApp
from clay_core import AppConfig


APP_CONFIG = AppConfig(
    name="demo",
    agents={},
    workflows={},
)

APP = ClayApp(config=APP_CONFIG)
""",
        encoding="utf-8",
    )

    app = create_studio_app(project_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/agents",
        json={
            "id": "sales_assistant",
            "name": "Sales Assistant",
            "model": "gemini/gemini-2.0-flash",
            "system_prompt": "Help qualify leads.",
            "description": "Qualifies leads.",
        },
    )

    assert response.status_code == 200
    assert (package_dir / "agents" / "sales_assistant.py").exists()
    assert "from demo.agents import AGENTS" in (package_dir / "main.py").read_text(
        encoding="utf-8"
    )
    assert "agents=AGENTS" in (package_dir / "main.py").read_text(encoding="utf-8")
    assert response.json()["agents"]["sales_assistant"]["module"] == (
        "demo.agents.sales_assistant:AGENT"
    )
