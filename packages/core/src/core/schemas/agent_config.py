from __future__ import annotations

from pydantic import BaseModel, Field

from core.schemas.workspace_config import WorkspaceConfig


class AgentConfig(BaseModel):
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


__all__ = ["AgentConfig"]
