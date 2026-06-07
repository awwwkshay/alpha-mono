from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


EnvVarName = Annotated[
    str,
    Field(
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Uppercase environment variable name starting with a letter.",
    ),
]


class StudioAppModel(BaseModel):
    name: str
    description: str | None = None


class StudioProjectModel(BaseModel):
    version: int = 1
    app: StudioAppModel
    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    workflows: dict[str, dict[str, Any]] = Field(default_factory=dict)
    workspaces: dict[str, dict[str, Any]] = Field(default_factory=dict)
    interfaces: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)


class ProjectInfo(BaseModel):
    root: str
    app_ref: str | None = None
    clay_yaml: str
    has_clay_yaml: bool
    git_branch: str | None = None


class EnvVarItem(BaseModel):
    key: EnvVarName
    value: str
    description: str | None = None


class EnvUpdateRequest(BaseModel):
    values: dict[EnvVarName, EnvVarItem]

    @model_validator(mode="after")
    def validate_item_keys(self) -> Self:
        for key, item in self.values.items():
            if item.key != key:
                raise ValueError(f"Env var payload key does not match item key: {key}")
        return self


class AgentCreateRequest(BaseModel):
    id: str
    name: str
    model: str
    system_prompt: str
    description: str | None = None


class AgentUpdateRequest(BaseModel):
    name: str
    model: str
    system_prompt: str
    description: str | None = None


class ModelOption(BaseModel):
    id: str


class ToolSummary(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    source_file: str | None = None


class InterfaceConfig(BaseModel):
    id: str | None = None
    type: Literal["slack", "telegram"]
    token_env: str = "SLACK_BOT_TOKEN"
    token: str | None = None
    signing_secret_env: str | None = None
    signing_secret: str | None = None
    secret_token_env: str | None = None
    secret_token: str | None = None
    base_url: str | None = None
    agent_id: str | None = None


class AgentSummary(BaseModel):
    id: str
    name: str
    model: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    chat: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[ToolSummary] = Field(default_factory=list)


class ToolFieldDef(BaseModel):
    name: str
    type: str = "str"
    description: str | None = None
    required: bool = True


class ToolCreateRequest(BaseModel):
    tool_id: str
    name: str
    description: str
    execute_body: str
    input_fields: list[ToolFieldDef] = Field(default_factory=list)
    output_fields: list[ToolFieldDef] = Field(default_factory=list)
    agent_id: str | None = None


class LspCompletionRequest(BaseModel):
    source: str
    line: int
    column: int


class LspCompletionItem(BaseModel):
    label: str
    kind: int
    detail: str | None = None
    documentation: str | None = None
    insert_text: str


class LspHoverRequest(BaseModel):
    source: str
    line: int
    column: int


class LspHoverResponse(BaseModel):
    signature: str | None = None
    documentation: str | None = None


class ToolSourceResponse(BaseModel):
    source_file: str
    content: str


class ToolSourceUpdateRequest(BaseModel):
    content: str


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    input_schema: str | None = None
    output_schema: str | None = None
    step_count: int | None = None


class LspDiagnosticRequest(BaseModel):
    source: str
    source_file: str | None = None


class LspDiagnosticItem(BaseModel):
    message: str
    severity: int  # Monaco MarkerSeverity: 8=Error, 4=Warning, 2=Info, 1=Hint
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    code: str | None = None


class WorkspaceSummary(BaseModel):
    id: str
    config: dict[str, Any]
