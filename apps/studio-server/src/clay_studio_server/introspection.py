from __future__ import annotations

from typing import Any

from clay_studio_server.schemas import (
    AgentSummary,
    ToolSummary,
    WorkflowSummary,
    WorkspaceSummary,
)


def summarize_agents(app: Any) -> list[AgentSummary]:
    config = getattr(app, "config", None)
    agents = getattr(config, "agents", {}) if config is not None else {}
    summaries = []
    for agent_id, agent_config in agents.items():
        chat = _extract_chat_configs(agent_config)
        tools = _extract_tool_summaries(agent_config)
        summaries.append(
            AgentSummary(
                id=str(agent_id),
                name=agent_config.name,
                model=agent_config.model,
                description=agent_config.description,
                system_prompt=agent_config.system_prompt,
                chat=chat,
                tools=tools,
            )
        )
    return summaries


def _extract_chat_configs(agent_config: Any) -> list[dict[str, Any]]:
    chat = getattr(agent_config, "chat", []) or []
    result = []
    for index, integration in enumerate(chat, start=1):
        class_name = type(integration).__name__
        if class_name == "SlackChat":
            entry = {
                "id": getattr(integration, "id", None)
                or _fallback_chat_id("slack", index),
                "type": "slack",
                "token_env": getattr(integration, "token_env", "SLACK_BOT_TOKEN"),
                "signing_secret_env": getattr(
                    integration, "signing_secret_env", "SLACK_SIGNING_SECRET"
                ),
            }
            if getattr(integration, "token", None):
                entry["token"] = "<direct>"
            if getattr(integration, "signing_secret", None):
                entry["signing_secret"] = "<direct>"
            result.append(entry)
        elif class_name == "TelegramChat":
            entry: dict[str, Any] = {
                "id": getattr(integration, "id", None)
                or _fallback_chat_id("telegram", index),
                "type": "telegram",
                "token_env": getattr(integration, "token_env", "TELEGRAM_BOT_TOKEN"),
                "secret_token_env": getattr(
                    integration, "secret_token_env", "TELEGRAM_WEBHOOK_SECRET"
                ),
            }
            if getattr(integration, "token", None):
                entry["token"] = "<direct>"
            if getattr(integration, "secret_token", None):
                entry["secret_token"] = "<direct>"
            base_url = getattr(integration, "base_url", None)
            if base_url:
                entry["base_url"] = base_url
            result.append(entry)
    return result


def _fallback_chat_id(platform: str, index: int) -> str:
    return f"{platform}_chat" if index == 1 else f"{platform}_chat_{index}"


def _extract_tool_summaries(agent_config: Any) -> list[ToolSummary]:
    import inspect

    tools = getattr(agent_config, "tools", {}) or {}
    summaries = []
    for tool_id, tool in tools.items():
        source_file = None
        execute_fn = getattr(tool, "_execute_fn", None)
        if execute_fn is not None:
            try:
                source_file = inspect.getsourcefile(execute_fn)
            except Exception:
                pass

        summaries.append(
            ToolSummary(
                name=getattr(tool, "name", tool_id),
                description=getattr(tool, "description", None),
                input_schema=tool_schema(tool, "input_schema"),
                output_schema=tool_schema(tool, "output_schema"),
                source_file=source_file,
            )
        )
    return summaries


def tool_schema(tool: Any, attr_name: str) -> dict[str, Any] | None:
    schema_cls = getattr(tool, attr_name, None)
    if schema_cls is not None and hasattr(schema_cls, "model_json_schema"):
        try:
            return schema_cls.model_json_schema()
        except Exception:
            return None
    return None


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
