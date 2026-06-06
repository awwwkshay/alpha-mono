from pathlib import Path

from pydantic import BaseModel, Field

from clay_core.schemas.agent_config import AgentConfig
from clay_core.schemas.observability_config import ObservabilityConfig
from clay_core.schemas.server_config import ServerConfig
from clay_core.schemas.workflow_config import WorkflowConfig
from clay_core.schemas.workspace_config import WorkspaceConfig
from clay_core.types.app_id import AppId


class AppConfig(BaseModel):
    """
    Configuration for the ClayApp. This class can be extended to include any necessary
    configuration parameters.
    """

    name: str = Field(..., description="The name of the ClayApp")
    description: str | None = Field(
        default=None, description="A brief description of the ClayApp"
    )
    env_file: Path | None = Field(
        default=None,
        description="Path to the .env file to load environment variables from",
    )
    agents: dict[AppId, AgentConfig] = Field(
        default_factory=dict,
        description="A dictionary of agents that the ClayApp will use",
    )
    workflows: dict[AppId, WorkflowConfig] = Field(
        default_factory=dict,
        description="A dictionary of workflows that the ClayApp will execute",
    )
    workspace: WorkspaceConfig | None = Field(
        default=None,
        description=(
            "Global workspace inherited by all agents that do not declare their own."
        ),
    )
    server: ServerConfig | None = Field(
        default=None,
        description="HTTP server configuration. Required to call ClayApp.serve().",
    )
    observability: ObservabilityConfig | None = Field(
        default=None,
        description=(
            "OpenTelemetry tracing configuration. When set, ClayApp automatically "
            "configures a TracerProvider with an OTLP gRPC exporter pointed at the "
            "given endpoint. Service name defaults to AppConfig.name."
        ),
    )
    debug: bool = Field(
        default=False,
        description="Whether to run the application in debug mode",
    )


__all__ = ["AppConfig"]
