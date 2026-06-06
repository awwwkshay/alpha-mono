from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from alpha_core.schemas.app_config import AppConfig
from alpha_core.types.app_id import AppId


@dataclass
class AppContext:
    config: AppConfig
    workflows: dict[AppId, Any] = field(default_factory=dict)
    agents: dict[AppId, Any] = field(default_factory=dict)
    workspace: Any | None = None
    agent_contexts: dict[AppId, Any] = field(default_factory=dict)


__all__ = ["AppContext"]
