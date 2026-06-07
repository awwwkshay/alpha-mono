from __future__ import annotations

import keyword
import re
from pathlib import Path
from typing import Any

from clay_studio_server.project import (
    ClayProject,
    ProjectError,
    read_studio_project,
    write_studio_project,
)
from clay_studio_server.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    InterfaceConfig,
    StudioProjectModel,
)


def create_agent_files(
    project: ClayProject,
    request: AgentCreateRequest,
) -> StudioProjectModel:
    agent_id = _to_identifier(request.id)
    if agent_id != request.id:
        request = request.model_copy(update={"id": agent_id})

    package_name, main_path = _resolve_app_package(project)
    package_dir = _resolve_package_dir(project.root, package_name)
    agents_dir = package_dir / "agents"
    agent_path = agents_dir / f"{agent_id}.py"

    if agent_path.exists():
        raise ProjectError(f"Agent file already exists: {agent_path}")

    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_path.write_text(_agent_module(request, chat=[]), encoding="utf-8")
    _write_agents_init(package_name, agents_dir)
    _ensure_main_uses_agents(main_path, package_name)

    model = read_studio_project(project)
    model.agents[agent_id] = {
        "id": agent_id,
        "name": request.name,
        "model": request.model,
        "description": request.description,
        "system_prompt": request.system_prompt,
        "chat": [],
        "module": f"{package_name}.agents.{agent_id}:AGENT",
    }
    write_studio_project(project, model)
    return model


def update_agent_files(
    project: ClayProject,
    agent_id: str,
    request: AgentUpdateRequest,
) -> StudioProjectModel:
    package_name, _ = _resolve_app_package(project)
    package_dir = _resolve_package_dir(project.root, package_name)
    agent_path = package_dir / "agents" / f"{agent_id}.py"

    model = read_studio_project(project)
    current = model.agents.get(agent_id, {})
    chat: list[dict[str, Any]] = current.get("chat", [])

    if agent_path.exists():
        create_req = AgentCreateRequest(
            id=agent_id,
            name=request.name,
            model=request.model,
            system_prompt=request.system_prompt,
            description=request.description,
        )
        agent_path.write_text(_agent_module(create_req, chat=chat), encoding="utf-8")

    model.agents[agent_id] = {
        **current,
        "id": agent_id,
        "name": request.name,
        "model": request.model,
        "system_prompt": request.system_prompt,
        "description": request.description,
        "chat": chat,
        "module": current.get("module", f"{package_name}.agents.{agent_id}:AGENT"),
    }
    write_studio_project(project, model)
    return model


def add_agent_interface(
    project: ClayProject,
    agent_id: str,
    interface: InterfaceConfig,
) -> StudioProjectModel:
    package_name, _ = _resolve_app_package(project)
    package_dir = _resolve_package_dir(project.root, package_name)
    agent_path = package_dir / "agents" / f"{agent_id}.py"

    model = read_studio_project(project)
    current = model.agents.get(agent_id, {})
    chat: list[dict[str, Any]] = list(current.get("chat", []))
    entry = _interface_entry(interface, chat)
    chat.append(entry)

    if agent_path.exists():
        create_req = AgentCreateRequest(
            id=agent_id,
            name=current.get("name", agent_id),
            model=current.get("model", ""),
            system_prompt=current.get("system_prompt", ""),
            description=current.get("description"),
        )
        agent_path.write_text(_agent_module(create_req, chat=chat), encoding="utf-8")

    current["chat"] = chat
    model.agents[agent_id] = current
    write_studio_project(project, model)
    return model


def remove_agent_interface(
    project: ClayProject,
    agent_id: str,
    interface_id: str,
) -> StudioProjectModel:
    package_name, _ = _resolve_app_package(project)
    package_dir = _resolve_package_dir(project.root, package_name)
    agent_path = package_dir / "agents" / f"{agent_id}.py"

    model = read_studio_project(project)
    current = model.agents.get(agent_id, {})
    chat: list[dict[str, Any]] = [
        c for c in current.get("chat", []) if not _interface_matches(c, interface_id)
    ]

    if agent_path.exists():
        create_req = AgentCreateRequest(
            id=agent_id,
            name=current.get("name", agent_id),
            model=current.get("model", ""),
            system_prompt=current.get("system_prompt", ""),
            description=current.get("description"),
        )
        agent_path.write_text(_agent_module(create_req, chat=chat), encoding="utf-8")

    current["chat"] = chat
    model.agents[agent_id] = current
    write_studio_project(project, model)
    return model


def create_tool_file(
    project: ClayProject,
    tool_id: str,
    name: str,
    description: str,
    execute_body: str,
    input_fields: list[dict[str, Any]] | None = None,
    output_fields: list[dict[str, Any]] | None = None,
    agent_id: str | None = None,
) -> StudioProjectModel:
    tool_id = _to_identifier(tool_id)
    package_name, _ = _resolve_app_package(project)
    package_dir = _resolve_package_dir(project.root, package_name)
    tools_dir = package_dir / "agents" / "tools"
    tool_path = tools_dir / f"{tool_id}.py"

    if tool_path.exists():
        raise ProjectError(f"Tool file already exists: {tool_path}")

    tools_dir.mkdir(parents=True, exist_ok=True)
    tool_path.write_text(
        _tool_module(
            tool_id,
            name,
            description,
            execute_body,
            input_fields=input_fields or [],
            output_fields=output_fields or [],
        ),
        encoding="utf-8",
    )
    _write_tools_init(package_name, tools_dir)

    model = read_studio_project(project)

    if agent_id:
        # Wire the tool into the agent's Python file
        agent_path = package_dir / "agents" / f"{agent_id}.py"
        if agent_path.exists():
            _ensure_agent_uses_tool(agent_path, package_name, tool_id, name)
    else:
        # Store as a standalone tool in clay.yaml for later assignment
        tool_entry = {
            "tool_id": tool_id,
            "name": name,
            "description": description,
            "source": f"{package_name}.agents.tools.{tool_id}:{tool_id}_tool",
        }
        model.tools.append(tool_entry)
        write_studio_project(project, model)

    return read_studio_project(project)


def create_standalone_interface(
    project: ClayProject,
    interface: InterfaceConfig,
) -> StudioProjectModel:
    model = read_studio_project(project)
    entry = _interface_entry(interface, model.interfaces)
    entry.pop("agent_id", None)
    model.interfaces.append(entry)
    write_studio_project(project, model)
    return model


def remove_standalone_interface(
    project: ClayProject,
    interface_id: str,
) -> StudioProjectModel:
    model = read_studio_project(project)
    model.interfaces = [
        i for i in model.interfaces if not _interface_matches(i, interface_id)
    ]
    write_studio_project(project, model)
    return model


def get_tool_source(project: ClayProject, source_file: str) -> str:
    path = _safe_project_path(project, source_file)
    return path.read_text(encoding="utf-8")


def save_tool_source(project: ClayProject, source_file: str, content: str) -> None:
    path = _safe_project_path(project, source_file)
    path.write_text(content, encoding="utf-8")


def _safe_project_path(project: ClayProject, source_file: str) -> Path:
    target = Path(source_file).resolve()
    root = project.root.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ProjectError(f"Path is outside the project root: {source_file}") from exc
    if not target.exists():
        raise ProjectError(f"File not found: {source_file}")
    return target


# ── internal helpers ──────────────────────────────────────────────────────────


def _resolve_app_package(project: ClayProject) -> tuple[str, Path]:
    if project.app_ref is None:
        raise ProjectError("Cannot create an agent without [tool.clay].app configured.")

    module_name = project.app_ref.split(":", 1)[0]
    module_parts = module_name.split(".")
    if not module_parts:
        raise ProjectError("Invalid [tool.clay].app module path.")

    package_name = module_parts[0]
    main_path = _resolve_module_path(project.root, module_name)
    return package_name, main_path


def _resolve_package_dir(root: Path, package_name: str) -> Path:
    src_package = root / "src" / package_name
    if src_package.exists():
        return src_package
    package = root / package_name
    if package.exists():
        return package
    raise ProjectError(f"Could not find app package '{package_name}'.")


def _resolve_module_path(root: Path, module_name: str) -> Path:
    relative = Path(*module_name.split(".")).with_suffix(".py")
    for base in (root / "src", root):
        candidate = base / relative
        if candidate.exists():
            return candidate
    raise ProjectError(f"Could not find module file for '{module_name}'.")


def _to_identifier(value: str) -> str:
    identifier = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip().lower())
    identifier = re.sub(r"_+", "_", identifier).strip("_")
    if not identifier:
        raise ProjectError("Agent id must contain at least one letter or number.")
    if identifier[0].isdigit():
        identifier = f"agent_{identifier}"
    if keyword.iskeyword(identifier):
        identifier = f"{identifier}_agent"
    return identifier


def _interface_entry(
    interface: InterfaceConfig,
    existing: list[dict[str, Any]],
) -> dict[str, Any]:
    entry = interface.model_dump(exclude_none=True)
    entry["id"] = _interface_id(interface, existing)
    if any(_interface_key(current) == entry["id"] for current in existing):
        raise ProjectError(f"Chat interface id already exists: {entry['id']}")
    return entry


def _interface_id(
    interface: InterfaceConfig,
    existing: list[dict[str, Any]],
) -> str:
    if interface.id:
        return _to_identifier(interface.id)
    base = f"{interface.type}_chat"
    if not any(_interface_key(current) == base for current in existing):
        return base
    index = 2
    while any(_interface_key(current) == f"{base}_{index}" for current in existing):
        index += 1
    return f"{base}_{index}"


def _interface_key(interface: dict[str, Any]) -> str:
    raw_id = interface.get("id")
    if isinstance(raw_id, str) and raw_id:
        return _to_identifier(raw_id)
    raw_type = interface.get("type")
    if isinstance(raw_type, str) and raw_type:
        return f"{raw_type}_chat"
    return ""


def _interface_matches(interface: dict[str, Any], interface_id: str) -> bool:
    normalized_id = _to_identifier(interface_id)
    legacy_type = interface.get("type")
    return _interface_key(interface) == normalized_id or legacy_type == interface_id


def _agent_module(request: AgentCreateRequest, chat: list[dict[str, Any]]) -> str:
    lines = ["from __future__ import annotations", ""]

    chat_imports = _chat_imports(chat)
    if chat_imports:
        lines.append(f"from clay_chat import {', '.join(chat_imports)}")

    lines += ["from clay_core import AgentConfig", "", ""]

    description_line = (
        f"    description={request.description!r},\n" if request.description else ""
    )
    chat_line = _chat_line(chat) if chat else ""

    body = (
        f"AGENT = AgentConfig(\n"
        f"    name={request.name!r},\n"
        f"    system_prompt={request.system_prompt!r},\n"
        f"    model={request.model!r},\n"
        f"{description_line}"
        f"{chat_line}"
        f")\n"
        f"\n"
        f"\n"
        f'__all__ = ["AGENT"]\n'
    )
    return "\n".join(lines) + "\n" + body


def _chat_imports(chat: list[dict[str, Any]]) -> list[str]:
    imports: list[str] = []
    types = {c.get("type") for c in chat}
    if "slack" in types:
        imports.append("SlackChat")
    if "telegram" in types:
        imports.append("TelegramChat")
    return imports


def _chat_line(chat: list[dict[str, Any]]) -> str:
    entries: list[str] = []
    for c in chat:
        if c.get("type") == "slack":
            params = _chat_constructor_params(
                c,
                defaults={
                    "token_env": "SLACK_BOT_TOKEN",
                    "signing_secret_env": "SLACK_SIGNING_SECRET",
                },
                fields=(
                    "id",
                    "token_env",
                    "signing_secret_env",
                    "token",
                    "signing_secret",
                ),
            )
            entries.append(
                f"SlackChat({', '.join(params)})" if params else "SlackChat()"
            )
        elif c.get("type") == "telegram":
            params = _chat_constructor_params(
                c,
                defaults={
                    "token_env": "TELEGRAM_BOT_TOKEN",
                    "secret_token_env": "TELEGRAM_WEBHOOK_SECRET",
                },
                fields=(
                    "id",
                    "token_env",
                    "secret_token_env",
                    "token",
                    "secret_token",
                    "base_url",
                ),
            )
            entries.append(f"TelegramChat({', '.join(params)})")
    return f"    chat=[{', '.join(entries)}],\n"


def _chat_constructor_params(
    config: dict[str, Any],
    *,
    defaults: dict[str, str],
    fields: tuple[str, ...],
) -> list[str]:
    params: list[str] = []
    for field in fields:
        value = config.get(field)
        if value is None or value == "":
            continue
        if defaults.get(field) == value:
            continue
        params.append(f"{field}={value!r}")
    return params


def _tool_module(
    tool_id: str,
    name: str,
    description: str,
    execute_body: str,
    input_fields: list[dict[str, Any]] | None = None,
    output_fields: list[dict[str, Any]] | None = None,
) -> str:
    class_name = tool_id.title().replace("_", "")
    input_body = _pydantic_fields(input_fields or []) or "    pass"
    output_body = _pydantic_fields(output_fields or []) or "    result: str"
    return f"""from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel

from clay_core import AgentTool, AppContext


class {class_name}Input(BaseModel):
{input_body}


class {class_name}Output(BaseModel):
{output_body}


# Typed aliases so the execute body can use Input / Output as shorthand
Input: TypeAlias = {class_name}Input
Output: TypeAlias = {class_name}Output


{execute_body}


{tool_id}_tool: AgentTool[{class_name}Input, {class_name}Output] = AgentTool(
    name={name!r},
    description={description!r},
    input_schema={class_name}Input,
    output_schema={class_name}Output,
    execute=_execute,
)

__all__ = ["{tool_id}_tool"]
"""


def _pydantic_fields(fields: list[dict[str, Any]]) -> str:
    lines = []
    for f in fields:
        field_name = f.get("name", "")
        field_type = f.get("type", "str")
        required = f.get("required", True)
        description = f.get("description")
        if not field_name:
            continue
        py_type = field_type if required else f"{field_type} | None"
        default = "" if required else " = None"
        if description:
            lines.append(f"    {field_name}: {py_type}{default}  # {description}")
        else:
            lines.append(f"    {field_name}: {py_type}{default}")
    return "\n".join(lines)


def _write_tools_init(package_name: str, tools_dir: Path) -> None:
    tool_modules = sorted(
        path.stem for path in tools_dir.glob("*.py") if path.name != "__init__.py"
    )
    imports = []
    entries = []
    for module_name in tool_modules:
        alias = f"{module_name.upper()}_TOOL"
        imports.append(
            f"from {package_name}.agents.tools.{module_name} import {module_name}_tool as {alias}"
        )
        entries.append(f"    {module_name!r}: {alias},")

    content = "\n".join(imports)
    if content:
        content += "\n\n"
    content += "TOOLS = {\n" + "\n".join(entries) + "\n}\n\n"
    content += '__all__ = ["TOOLS"]\n'
    (tools_dir / "__init__.py").write_text(content, encoding="utf-8")


def _ensure_agent_uses_tool(
    agent_path: Path, package_name: str, tool_id: str, tool_name: str
) -> None:
    content = agent_path.read_text(encoding="utf-8")
    alias = f"{tool_id.upper()}_TOOL"
    import_line = (
        f"from {package_name}.agents.tools.{tool_id} import {tool_id}_tool as {alias}"
    )
    if import_line not in content:
        insert_after = "from clay_core import AgentConfig"
        if insert_after not in content:
            return
        content = content.replace(insert_after, f"{insert_after}\n{import_line}", 1)

    tool_entry = f'    "{tool_name}": {alias},'
    if tool_entry not in content:
        if "tools={}" in content:
            content = content.replace("tools={}", f"tools={{\n{tool_entry}\n    }}", 1)
        elif "tools={" in content:
            content = content.replace("tools={", f"tools={{\n{tool_entry}\n    ", 1)

    agent_path.write_text(content, encoding="utf-8")


def _write_agents_init(package_name: str, agents_dir: Path) -> None:
    agent_modules = sorted(
        path.stem for path in agents_dir.glob("*.py") if path.name != "__init__.py"
    )
    imports = []
    entries = []
    for module_name in agent_modules:
        alias = f"{module_name.upper()}_AGENT"
        imports.append(
            f"from {package_name}.agents.{module_name} import AGENT as {alias}"
        )
        entries.append(f"    {module_name!r}: {alias},")

    content = "\n".join(imports)
    if content:
        content += "\n\n"
    content += "AGENTS = {\n" + "\n".join(entries) + "\n}\n\n"
    content += '__all__ = ["AGENTS"]\n'
    (agents_dir / "__init__.py").write_text(content, encoding="utf-8")


def _ensure_main_uses_agents(main_path: Path, package_name: str) -> None:
    content = main_path.read_text(encoding="utf-8")
    import_line = f"from {package_name}.agents import AGENTS"
    if import_line not in content:
        marker = (
            "\n\nENV_FILE = " if "\n\nENV_FILE = " in content else "\n\nAPP_CONFIG = "
        )
        if marker not in content:
            raise ProjectError(
                f"Could not patch {main_path}; expected generated app layout."
            )
        content = content.replace(marker, f"\n{import_line}\n{marker}", 1)

    if "agents={}," in content:
        content = content.replace("agents={},", "agents=AGENTS,", 1)
    elif "agents=AGENTS," not in content:
        raise ProjectError(
            f"Could not patch {main_path}; expected an empty agents={{}} config."
        )

    main_path.write_text(content, encoding="utf-8")
