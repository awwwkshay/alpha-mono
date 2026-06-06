from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from clay_core.contracts.chat_contract import ChatContract
from pydantic import BaseModel, ConfigDict, Field, model_validator

from clay_core.contracts.evals.scorer_contract import ScorerConfig
from clay_core.domain.agent.tool.agent_tool import AgentTool
from clay_core.schemas.workflow_config import WorkflowConfig
from clay_core.schemas.workspace_config import WorkspaceConfig


class AgentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the agent")
    system_prompt: str = Field(
        default="", description="The system prompt for the agent"
    )
    system_prompt_md_path: Path | None = Field(
        default=None,
        description="Path to a markdown file whose contents become the system prompt.",
    )
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
    workflows: dict[str, WorkflowConfig[Any, Any]] = Field(
        default_factory=dict,
        description="Named workflow configs the agent can invoke as tools.",
    )
    tools: dict[str, AgentTool[Any, Any]] = Field(
        default_factory=dict,
        description="Named tools the agent can invoke directly.",
    )
    scorers: dict[str, ScorerConfig] = Field(
        default_factory=dict,
        description="Named scorers to evaluate agent responses.",
    )
    chat: Sequence[ChatContract] = Field(
        default_factory=list,
        description=(
            "Chat-platform integrations (clay_chat.contracts.ChatContract). "
            "Each has its mount(app, agent) called by ClayApp at startup. "
            "Add one per platform (e.g. [SlackChat(), TelegramChat()])."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_system_prompt(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        sp = data.get("system_prompt", "")
        spp = data.get("system_prompt_md_path")
        if sp and spp is not None:
            raise ValueError(
                "Provide either system_prompt or system_prompt_md_path, not both"
            )
        if spp is not None:
            data["system_prompt"] = Path(spp).read_text()
        elif not sp:
            raise ValueError(
                "Either system_prompt or system_prompt_md_path is required"
            )
        return data


__all__ = ["AgentConfig"]
