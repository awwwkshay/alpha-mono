from __future__ import annotations

from pydantic import BaseModel


class FileStat(BaseModel):
    path: str
    size: int
    mtime: float
    is_file: bool
    is_dir: bool


__all__ = ["FileStat"]
