from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.schemas.app_config import AppConfig
from core.types.app_id import AppId

if TYPE_CHECKING:
    from core.domain.agent.agent import Agent
    from core.domain.workflow.workflow import Workflow


@dataclass
class AppContext:
    config: AppConfig
    workflows: dict[AppId, Workflow] = field(default_factory=dict)
    agents: dict[AppId, Agent] = field(default_factory=dict)


__all__ = ["AppContext"]
