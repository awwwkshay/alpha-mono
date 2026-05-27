from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from alpha_core.domain.evals.scorer import ScorerConfig
from alpha_core.schemas.workspace_config import WorkspaceConfig


class AgentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the agent")
    system_prompt: str = Field(..., description="The system prompt for the agent")
    model: str = Field(..., description="The model to use for the agent")
    description: str | None = Field(
        default=None, description="A brief description of the agent"
    )
    workspace: WorkspaceConfig | None = Field(
        default=None,
        description=(
            "Workspace configuration for this agent. "
            "Overrides any global workspace set on AppConfig."
        ),
    )
    scorers: dict[str, ScorerConfig] = Field(
        default_factory=dict,
        description="Named scorers to evaluate agent responses.",
    )


__all__ = ["AgentConfig"]
