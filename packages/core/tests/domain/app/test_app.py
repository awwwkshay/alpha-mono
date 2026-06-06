from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from alpha_app.app.app import AlphaApp
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.filesystem_config import LocalFilesystemConfig
from alpha_core.schemas.workspace_config import WorkspaceConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_config(**overrides) -> AppConfig:
    defaults: dict = {"name": "test-app"}
    defaults.update(overrides)
    return AppConfig(**defaults)


def _agent_cfg(
    name: str = "a", workspace: WorkspaceConfig | None = None
) -> AgentConfig:
    return AgentConfig(
        name=name, system_prompt="Prompt.", model="test/model", workspace=workspace
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_init_creates_agents():
    config = _simple_config(agents={"a": _agent_cfg("A"), "b": _agent_cfg("B")})
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    assert set(app.agents.keys()) == {"a", "b"}


def test_init_creates_workflows(tmp_path):
    from pydantic import BaseModel
    from alpha_core.schemas.workflow_config import WorkflowConfig, WorkflowStepConfig

    class In(BaseModel):
        x: str

    class Out(BaseModel):
        x: str

    async def _step(inp: In, _ctx) -> Out:
        return Out(x=inp.x)

    step = WorkflowStepConfig.create(
        name="s", input_schema=In, output_schema=Out, execute=_step
    )
    wf = WorkflowConfig.create(
        name="wf", input_schema=In, output_schema=Out, steps={"s": step}
    )

    config = _simple_config(workflows={"wf": wf})
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    assert "wf" in app.workflows


def test_init_builds_context():
    config = _simple_config(agents={"a": _agent_cfg("A")})
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    assert "a" in app.context.agents
    assert app.context.config is config


# ---------------------------------------------------------------------------
# Global workspace deduplication
# ---------------------------------------------------------------------------


def test_global_workspace_shared_across_agents(tmp_path):
    """Agents without a per-agent workspace all share the same Workspace instance."""
    ws_cfg = WorkspaceConfig(
        name="shared",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A"), "b": _agent_cfg("B")},
        workspace=ws_cfg,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    # Only one unique workspace instance despite two agents
    assert len(app._workspaces) == 1


def test_per_agent_workspace_overrides_global(tmp_path):
    global_ws = WorkspaceConfig(
        name="global",
        filesystem=LocalFilesystemConfig(base_path=tmp_path / "global"),
    )
    agent_ws = WorkspaceConfig(
        name="agent",
        filesystem=LocalFilesystemConfig(base_path=tmp_path / "agent"),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A", workspace=agent_ws), "b": _agent_cfg("B")},
        workspace=global_ws,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    # Two distinct workspace instances
    assert len(app._workspaces) == 2


def test_agent_context_uses_assigned_workspace(tmp_path):
    global_ws = WorkspaceConfig(
        name="global",
        filesystem=LocalFilesystemConfig(base_path=tmp_path / "global"),
    )
    agent_ws = WorkspaceConfig(
        name="agent",
        filesystem=LocalFilesystemConfig(base_path=tmp_path / "agent"),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A", workspace=agent_ws), "b": _agent_cfg("B")},
        workspace=global_ws,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)

    agent_context = app.get_agent_context("a")
    fallback_context = app.get_agent_context("b")

    assert agent_context.workspace is not None
    assert fallback_context.workspace is not None
    assert fallback_context.workspace is app.context.workspace
    assert agent_context.workspace is not fallback_context.workspace
    assert agent_context.workspace.config.name == "agent"
    assert fallback_context.workspace.config.name == "global"
    assert agent_context.agent_contexts is app.context.agent_contexts
    assert fallback_context.agent_contexts is app.context.agent_contexts
    assert agent_context.agent_contexts["b"] is fallback_context


# ---------------------------------------------------------------------------
# Lifecycle: setup / teardown
# ---------------------------------------------------------------------------


async def test_setup_calls_workspace_setup(tmp_path):
    ws_cfg = WorkspaceConfig(
        name="ws",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A")},
        workspace=ws_cfg,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)

    with patch.object(list(app._workspaces)[0], "setup", AsyncMock()) as mock_setup:
        await app.setup()
        mock_setup.assert_awaited_once()


async def test_teardown_calls_workspace_teardown(tmp_path):
    ws_cfg = WorkspaceConfig(
        name="ws",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A")},
        workspace=ws_cfg,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)

    with patch.object(list(app._workspaces)[0], "teardown", AsyncMock()) as mock_td:
        await app.teardown()
        mock_td.assert_awaited_once()


async def test_context_manager_calls_setup_and_teardown(tmp_path):
    ws_cfg = WorkspaceConfig(
        name="ws",
        filesystem=LocalFilesystemConfig(base_path=tmp_path),
    )
    config = _simple_config(
        agents={"a": _agent_cfg("A")},
        workspace=ws_cfg,
    )
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)

    ws = list(app._workspaces)[0]
    with (
        patch.object(ws, "setup", AsyncMock()) as s,
        patch.object(ws, "teardown", AsyncMock()) as td,
    ):
        async with app:
            s.assert_awaited_once()
        td.assert_awaited_once()


# ---------------------------------------------------------------------------
# execute_workflow
# ---------------------------------------------------------------------------


async def test_execute_workflow_delegates_to_workflow():
    from pydantic import BaseModel
    from alpha_core.schemas.workflow_config import WorkflowConfig, WorkflowStepConfig

    class In(BaseModel):
        v: int

    class Out(BaseModel):
        v: int

    async def _step(inp: In, _ctx) -> Out:
        return Out(v=inp.v * 2)

    step = WorkflowStepConfig.create(
        name="s", input_schema=In, output_schema=Out, execute=_step
    )
    wf = WorkflowConfig.create(
        name="wf", input_schema=In, output_schema=Out, steps={"s": step}
    )

    config = _simple_config(workflows={"wf": wf})
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)

    result = await app.execute_workflow("wf", {"v": 3})
    assert result.model_dump() == {"v": 6}


async def test_execute_workflow_unknown_id_raises():
    config = _simple_config()
    with patch("alpha_app.app.app.load_dotenv"):
        app = AlphaApp(config=config)
    with pytest.raises(KeyError):
        await app.execute_workflow("no_such_workflow", {})
