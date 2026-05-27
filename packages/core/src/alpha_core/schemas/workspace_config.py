from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from alpha_core.schemas.filesystem_config import FilesystemConfig
from alpha_core.schemas.sandbox_config import SandboxConfig


class SkillsConfig(BaseModel):
    paths: list[Path] = Field(
        ..., description="Directories to scan for skill sub-directories"
    )


class WorkspaceConfig(BaseModel):
    name: str = Field(..., description="Identifier for this workspace")
    description: str | None = Field(default=None)
    filesystem: FilesystemConfig | None = Field(
        default=None,
        description="Filesystem provider config (e.g. LocalFilesystemConfig, S3FilesystemConfig)",
    )
    sandbox: SandboxConfig | None = Field(
        default=None,
        description="Sandbox provider config (e.g. LocalSandboxConfig, E2BSandboxConfig)",
    )
    skills: SkillsConfig | None = Field(default=None)


__all__ = [
    "SkillsConfig",
    "WorkspaceConfig",
]
