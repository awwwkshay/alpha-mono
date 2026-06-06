from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LocalFilesystemConfig(BaseModel):
    type: Literal["local"] = "local"
    base_path: Path
    contained: bool = True
    read_only: bool = False
    allowed_paths: list[Path] = Field(default_factory=list)


class S3FilesystemConfig(BaseModel):
    type: Literal["s3"] = "s3"
    bucket: str
    prefix: str = ""
    region: str | None = None
    read_only: bool = False


FilesystemConfig = Annotated[
    LocalFilesystemConfig | S3FilesystemConfig,
    Field(discriminator="type"),
]


__all__ = [
    "FilesystemConfig",
    "LocalFilesystemConfig",
    "S3FilesystemConfig",
]
