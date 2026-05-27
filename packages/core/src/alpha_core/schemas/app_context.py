from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from alpha_core.schemas.app_config import AppConfig
from alpha_core.types.app_id import AppId

if TYPE_CHECKING:
    from alpha_core.domain.agent.agent import Agent
    from alpha_core.domain.workflow.workflow import Workflow


@dataclass
class AppContext:
    config: AppConfig
    workflows: dict[AppId, Workflow] = field(default_factory=dict)
    agents: dict[AppId, Agent] = field(default_factory=dict)


__all__ = ["AppContext"]
