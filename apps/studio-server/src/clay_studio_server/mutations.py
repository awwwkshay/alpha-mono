from __future__ import annotations

import keyword
import re
from pathlib import Path

from clay_studio_server.project import (
    ClayProject,
    ProjectError,
    read_studio_project,
    write_studio_project,
)
from clay_studio_server.schemas import AgentCreateRequest, StudioProjectModel


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
    agent_path.write_text(_agent_module(request), encoding="utf-8")
    _write_agents_init(package_name, agents_dir)
    _ensure_main_uses_agents(main_path, package_name)

    model = read_studio_project(project)
    model.agents[agent_id] = {
        "id": agent_id,
        "name": request.name,
        "model": request.model,
        "description": request.description,
        "system_prompt": request.system_prompt,
        "module": f"{package_name}.agents.{agent_id}:AGENT",
    }
    write_studio_project(project, model)
    return model


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


def _agent_module(request: AgentCreateRequest) -> str:
    description = (
        f"    description={request.description!r},\n" if request.description else ""
    )
    return f"""from __future__ import annotations

from clay_core import AgentConfig


AGENT = AgentConfig(
    name={request.name!r},
    system_prompt={request.system_prompt!r},
    model={request.model!r},
{description})


__all__ = ["AGENT"]
"""


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
