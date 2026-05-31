from __future__ import annotations

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    title: str | None = Field(default=None)


__all__ = ["ServerConfig"]
