from __future__ import annotations

from pathlib import Path

from clay_core import LocalFilesystemConfig, LocalSandboxConfig, WorkspaceConfig


WORKSPACE_DIR = Path(__file__).parents[3] / "workspaces" / "sales-workspace"

LOCAL_WORKSPACE = WorkspaceConfig(
    name="sales-workspace",
    description="Local workspace for sales app files and generated artifacts.",
    filesystem=LocalFilesystemConfig(base_path=WORKSPACE_DIR),
    sandbox=LocalSandboxConfig(
        working_directory=WORKSPACE_DIR,
        timeout=30,
    ),
)


__all__ = ["LOCAL_WORKSPACE", "WORKSPACE_DIR"]
