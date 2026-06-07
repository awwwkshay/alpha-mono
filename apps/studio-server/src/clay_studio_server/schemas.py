from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StudioAppModel(BaseModel):
    name: str
    description: str | None = None


class StudioProjectModel(BaseModel):
    version: int = 1
    app: StudioAppModel
    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    workflows: dict[str, dict[str, Any]] = Field(default_factory=dict)
    workspaces: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ProjectInfo(BaseModel):
    root: str
    app_ref: str | None = None
    clay_yaml: str
    has_clay_yaml: bool
    git_branch: str | None = None


class AgentCreateRequest(BaseModel):
    id: str
    name: str
    model: str
    system_prompt: str
    description: str | None = None


class ModelOption(BaseModel):
    id: str


class AgentSummary(BaseModel):
    id: str
    name: str
    model: str | None = None
    description: str | None = None
    system_prompt: str | None = None


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    input_schema: str | None = None
    output_schema: str | None = None
    step_count: int | None = None


class WorkspaceSummary(BaseModel):
    id: str
    config: dict[str, Any]
