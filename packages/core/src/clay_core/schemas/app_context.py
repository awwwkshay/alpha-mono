from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from clay_core.schemas.app_config import AppConfig
from clay_core.types.app_id import AppId

if TYPE_CHECKING:
    from clay_app.agent.agent import Agent
    from clay_app.workflow.workflow import Workflow


class AppContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: AppConfig
    workflows: dict[AppId, Workflow] = Field(default_factory=dict)
    agents: dict[AppId, Agent] = Field(default_factory=dict)
    workspace: Any = None
    agent_contexts: dict[AppId, Any] = Field(default_factory=dict)


__all__ = ["AppContext"]
