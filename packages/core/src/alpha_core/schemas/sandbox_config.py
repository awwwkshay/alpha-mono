from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LocalSandboxConfig(BaseModel):
    type: Literal["local"] = "local"
    working_directory: Path | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    isolation: Literal["none", "seatbelt", "bwrap"] = "none"


class E2BSandboxConfig(BaseModel):
    type: Literal["e2b"] = "e2b"
    template: str
    api_key: str | None = None
    timeout: int = 60


SandboxConfig = Annotated[
    LocalSandboxConfig | E2BSandboxConfig,
    Field(discriminator="type"),
]


__all__ = [
    "E2BSandboxConfig",
    "LocalSandboxConfig",
    "SandboxConfig",
]
