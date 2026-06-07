from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from clay_core.contracts.chat_contract import ChatContract
from clay_core.contracts.evals.scorer_contract import ScorerConfig
from clay_core.domain.agent.tool.agent_tool import AgentTool
from clay_core.schemas.agent_config import AgentConfig
from clay_core.schemas.observability_config import ObservabilityConfig
from clay_core.schemas.server_config import ServerConfig
from clay_core.schemas.workflow_config import AnyStepConfig, WorkflowConfig
from clay_core.schemas.workspace_config import WorkspaceConfig
from clay_core.types.app_id import AppId


class AppConfig(BaseModel):
    """
    Configuration for the ClayApp. This class can be extended to include any necessary
    configuration parameters.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
    steps: dict[AppId, AnyStepConfig] = Field(
        default_factory=dict,
        description=(
            "App-level workflow steps not tied to a specific workflow. "
            "Use WorkflowConfig.steps to attach steps to a particular workflow."
        ),
    )
    tools: dict[AppId, AgentTool[Any, Any]] = Field(
        default_factory=dict,
        description=(
            "App-level tools not tied to a specific agent. "
            "Use AgentConfig.tools to attach tools to a particular agent."
        ),
    )
    scorers: dict[AppId, ScorerConfig] = Field(
        default_factory=dict,
        description=(
            "App-level scorers not tied to a specific agent. "
            "Use AgentConfig.scorers to attach scorers to a particular agent."
        ),
    )
    chat_apps: dict[AppId, ChatContract] = Field(
        default_factory=dict,
        description=(
            "App-level chat-platform integrations not tied to a specific agent. "
            "Use AgentConfig.chat to wire an integration to a particular agent."
        ),
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
