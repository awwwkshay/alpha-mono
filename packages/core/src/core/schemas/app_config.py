from pathlib import Path

from pydantic import BaseModel, Field

from core.schemas.agent_config import AgentConfig
from core.schemas.workflow_config import WorkflowConfig
from core.schemas.workspace_config import WorkspaceConfig
from core.types.app_id import AppId


class AppConfig(BaseModel):
    """
    Configuration for the AlphaApp. This class can be extended to include any necessary
    configuration parameters.
    """

    name: str = Field(..., description="The name of the AlphaApp")
    description: str | None = Field(
        default=None, description="A brief description of the AlphaApp"
    )
    env_file: Path | None = Field(
        default=None,
        description="Path to the .env file to load environment variables from",
    )
    agents: dict[AppId, AgentConfig] = Field(
        default_factory=dict,
        description="A dictionary of agents that the AlphaApp will use",
    )
    workflows: dict[AppId, WorkflowConfig] = Field(
        default_factory=dict,
        description="A dictionary of workflows that the AlphaApp will execute",
    )
    workspace: WorkspaceConfig | None = Field(
        default=None,
        description=(
            "Global workspace inherited by all agents that do not declare their own."
        ),
    )


__all__ = ["AppConfig"]
