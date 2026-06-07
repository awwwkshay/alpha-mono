from __future__ import annotations

from typing import Any

from clay_studio_server.schemas import AgentSummary, WorkflowSummary, WorkspaceSummary


def summarize_agents(app: Any) -> list[AgentSummary]:
    config = getattr(app, "config", None)
    agents = getattr(config, "agents", {}) if config is not None else {}
    return [
        AgentSummary(
            id=str(agent_id),
            name=agent_config.name,
            model=agent_config.model,
            description=agent_config.description,
            system_prompt=agent_config.system_prompt,
        )
        for agent_id, agent_config in agents.items()
    ]


def summarize_workflows(app: Any) -> list[WorkflowSummary]:
    config = getattr(app, "config", None)
    workflows = getattr(config, "workflows", {}) if config is not None else {}
    summaries = []
    for workflow_id, workflow_config in workflows.items():
        input_schema = getattr(workflow_config.input_schema, "__name__", None)
        output_schema = getattr(workflow_config.output_schema, "__name__", None)
        summaries.append(
            WorkflowSummary(
                id=str(workflow_id),
                name=workflow_config.name,
                description=workflow_config.description,
                input_schema=input_schema,
                output_schema=output_schema,
                step_count=len(workflow_config.steps),
            )
        )
    return summaries


def summarize_workspaces(app: Any) -> list[WorkspaceSummary]:
    config = getattr(app, "config", None)
    workspace = getattr(config, "workspace", None) if config is not None else None
    if workspace is None:
        return []
    return [
        WorkspaceSummary(
            id=workspace.name,
            config=workspace.model_dump(mode="json", exclude_none=True),
        )
    ]
