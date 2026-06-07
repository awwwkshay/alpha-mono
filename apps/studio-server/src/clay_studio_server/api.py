from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from clay_studio_server.introspection import (
    summarize_agents,
    summarize_workflows,
    summarize_workspaces,
    tool_schema,
)
from clay_studio_server.loader import load_app
from clay_studio_server.mutations import (
    add_agent_interface,
    create_agent_files,
    create_standalone_interface,
    create_tool_file,
    get_tool_source,
    remove_agent_interface,
    remove_standalone_interface,
    save_tool_source,
    update_agent_files,
)
from clay_studio_server.project import (
    ClayProject,
    ProjectError,
    delete_mapping_item,
    ensure_project_import_path,
    read_git_branch,
    read_studio_project,
    update_mapping_item,
    write_studio_project,
)
from clay_studio_server.schemas import (
    AgentCreateRequest,
    EnvUpdateRequest,
    EnvVarItem,
    AgentUpdateRequest,
    InterfaceConfig,
    LspCompletionItem,
    LspCompletionRequest,
    LspDiagnosticItem,
    LspDiagnosticRequest,
    LspHoverRequest,
    LspHoverResponse,
    ModelOption,
    ProjectInfo,
    StudioProjectModel,
    ToolCreateRequest,
    ToolSourceResponse,
    ToolSourceUpdateRequest,
)


def build_api_router(project: ClayProject) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/project")
    def get_project() -> ProjectInfo:
        return ProjectInfo(
            root=str(project.root),
            app_ref=project.app_ref,
            clay_yaml=str(project.clay_yaml_path),
            has_clay_yaml=project.clay_yaml_path.exists(),
            git_branch=read_git_branch(project.root),
        )

    @router.get("/sync")
    def get_sync() -> StudioProjectModel:
        try:
            return read_studio_project(project)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/models")
    def get_models() -> list[ModelOption]:
        try:
            import litellm
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail="LiteLLM is not installed in this environment.",
            ) from exc

        models = sorted(set(getattr(litellm, "model_list", []) or []))
        return [ModelOption(id=model) for model in models]

    @router.post("/sync")
    def update_sync(
        payload: StudioProjectModel | None = Body(default=None),
    ) -> StudioProjectModel:
        if payload is not None:
            write_studio_project(project, payload)
            return payload

        app = _load_app_or_500(project)
        model = read_studio_project(project)
        if app is not None:
            model.workspaces = _workspace_configs_for_project(project, app)
            write_studio_project(project, model)
        return model

    router.include_router(_build_agents_router(project))
    router.include_router(_build_tools_router(project))
    router.include_router(_build_interfaces_router(project))
    router.include_router(_build_env_router(project))
    router.include_router(_build_workflows_router(project))
    router.include_router(_build_workspaces_router(project))
    router.include_router(_build_lsp_router(project))
    return router


def _build_env_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/env")
    def get_env() -> list[EnvVarItem]:
        return sorted(_read_env_file(project), key=lambda item: item.key)

    @router.put("/env")
    def put_env(payload: EnvUpdateRequest) -> list[EnvVarItem]:
        _write_env_values(project, payload.values)
        for key, item in payload.values.items():
            os.environ[key] = item.value
        return get_env()

    return router


def _read_env_file(project: ClayProject) -> list[EnvVarItem]:
    env_path = project.root / ".env"
    if not env_path.exists():
        return []
    values: list[EnvVarItem] = []
    pending_description: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        comment = _parse_env_comment(raw_line)
        if comment is not None:
            pending_description.append(comment)
            continue
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            pending_description = []
            continue
        key, value = parsed
        description = "\n".join(pending_description).strip() or None
        values.append(EnvVarItem(key=key, value=value, description=description))
        pending_description = []
    return values


def _write_env_values(project: ClayProject, values: dict[str, EnvVarItem]) -> None:
    env_path = project.root / ".env"
    lines = (
        env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    )
    remaining = dict(values)
    next_lines: list[str] = []
    pending_description: list[str] = []
    for line in lines:
        comment = _parse_env_comment(line)
        if comment is not None:
            pending_description.append(comment)
            continue
        parsed = _parse_env_line(line)
        if parsed is None:
            if pending_description:
                next_lines.extend(f"# {part}" for part in pending_description)
                pending_description = []
            next_lines.append(line)
            continue
        key, _ = parsed
        if key in remaining:
            item = remaining.pop(key)
            next_lines.extend(_env_item_lines(item))
        else:
            if pending_description:
                next_lines.extend(f"# {part}" for part in pending_description)
                pending_description = []
            next_lines.append(line)
        pending_description = []

    if pending_description:
        next_lines.extend(f"# {part}" for part in pending_description)

    for item in remaining.values():
        next_lines.extend(_env_item_lines(item))

    env_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
    _sync_env_example(project)


def _sync_env_example(project: ClayProject) -> None:
    env_values = {item.key: item for item in _read_env_file(project)}
    example_path = project.root / ".env.example"
    example_values = _read_env_example(example_path)
    keys = sorted({*example_values, *env_values})
    lines: list[str] = []
    for key in keys:
        item = env_values.get(key) or example_values.get(key)
        description = item.description if item is not None else None
        if description:
            lines.extend(f"# {part}" for part in description.splitlines() if part)
        lines.append(f"{key}=")
    example_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _read_env_example(path: Path) -> dict[str, EnvVarItem]:
    if not path.exists():
        return {}
    values: dict[str, EnvVarItem] = {}
    pending_description: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        comment = _parse_env_comment(raw_line)
        if comment is not None:
            pending_description.append(comment)
            continue
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            pending_description = []
            continue
        key, value = parsed
        description = "\n".join(pending_description).strip() or None
        values[key] = EnvVarItem(key=key, value=value, description=description)
        pending_description = []
    return values


def _env_item_lines(item: EnvVarItem) -> list[str]:
    lines: list[str] = []
    if item.description:
        lines.extend(f"# {part}" for part in item.description.splitlines() if part)
    lines.append(f"{item.key}={_quote_env_value(item.value)}")
    return lines


def _parse_env_comment(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    return stripped.removeprefix("#").strip()


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    return key, value.strip().strip('"').strip("'")


def _quote_env_value(value: str) -> str:
    if value == "" or re.search(r"\s|#|'|\"", value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _load_app_or_500(project: ClayProject) -> Any:
    try:
        return load_app(project)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _workspace_configs_for_project(
    project: ClayProject,
    app: Any,
) -> dict[str, dict[str, Any]]:
    workspaces = summarize_workspaces(app)
    return {
        workspace.id: _relativize_project_paths(project.root, workspace.config)
        for workspace in workspaces
    }


def _relativize_project_paths(root: Path, value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _relativize_project_paths(root, item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_relativize_project_paths(root, item) for item in value]
    if not isinstance(value, str):
        return value

    try:
        path = Path(value)
        relative = path.resolve().relative_to(root.resolve())
    except OSError, ValueError:
        return value
    return relative.as_posix()


def _build_agents_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/agents")
    def get_agents() -> list[Any]:
        app = _load_app_or_500(project)
        configured_agents = read_studio_project(project).agents
        if app is None:
            return list(configured_agents.values())

        summaries = [agent.model_dump(mode="json") for agent in summarize_agents(app)]
        known_ids = {agent["id"] for agent in summaries}
        summaries.extend(
            {"id": agent_id, **agent_config}
            for agent_id, agent_config in configured_agents.items()
            if agent_id not in known_ids
        )
        return summaries

    @router.post("/agents")
    def post_agent(payload: AgentCreateRequest) -> StudioProjectModel:
        try:
            return create_agent_files(project, payload)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.put("/agents/{agent_id}")
    def put_agent(agent_id: str, payload: AgentUpdateRequest) -> StudioProjectModel:
        try:
            return update_agent_files(project, agent_id, payload)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/agents/{agent_id}")
    def delete_agent(agent_id: str) -> StudioProjectModel:
        return delete_mapping_item(project, "agents", agent_id)

    _register_agent_interface_routes(router, project)
    _register_agent_tool_routes(router, project)

    return router


def _register_agent_interface_routes(router: APIRouter, project: ClayProject) -> None:
    @router.post("/agents/{agent_id}/interfaces")
    def post_agent_interface(
        agent_id: str, payload: InterfaceConfig
    ) -> StudioProjectModel:
        try:
            return add_agent_interface(project, agent_id, payload)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/agents/{agent_id}/interfaces/{interface_id}")
    def delete_agent_interface(agent_id: str, interface_id: str) -> StudioProjectModel:
        try:
            return remove_agent_interface(project, agent_id, interface_id)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


def _register_agent_tool_routes(router: APIRouter, project: ClayProject) -> None:
    @router.post("/agents/{agent_id}/tools")
    def post_agent_tool(
        agent_id: str, payload: ToolCreateRequest
    ) -> StudioProjectModel:
        try:
            return create_tool_file(
                project,
                payload.tool_id,
                payload.name,
                payload.description,
                payload.execute_body,
                agent_id=agent_id,
            )
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/agents/{agent_id}/tools/{tool_name}/source")
    def get_agent_tool_source(agent_id: str, tool_name: str) -> ToolSourceResponse:
        app = _load_app_or_500(project)
        if app is None:
            raise HTTPException(status_code=404, detail="App not loaded")
        from clay_studio_server.introspection import summarize_agents

        summaries = summarize_agents(app)
        agent = next((a for a in summaries if a.id == agent_id), None)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        tool = next((t for t in agent.tools if t.name == tool_name), None)
        if tool is None or tool.source_file is None:
            raise HTTPException(
                status_code=404, detail=f"Tool '{tool_name}' source not found"
            )
        try:
            content = get_tool_source(project, tool.source_file)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ToolSourceResponse(source_file=tool.source_file, content=content)

    @router.put("/agents/{agent_id}/tools/{tool_name}/source")
    def put_agent_tool_source(
        agent_id: str, tool_name: str, payload: ToolSourceUpdateRequest
    ) -> ToolSourceResponse:
        app = _load_app_or_500(project)
        if app is None:
            raise HTTPException(status_code=404, detail="App not loaded")
        from clay_studio_server.introspection import summarize_agents

        summaries = summarize_agents(app)
        agent = next((a for a in summaries if a.id == agent_id), None)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        tool = next((t for t in agent.tools if t.name == tool_name), None)
        if tool is None or tool.source_file is None:
            raise HTTPException(
                status_code=404, detail=f"Tool '{tool_name}' source not found"
            )
        try:
            save_tool_source(project, tool.source_file, payload.content)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ToolSourceResponse(source_file=tool.source_file, content=payload.content)


def _build_tools_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/tools")
    def get_tools() -> list[Any]:
        return [
            _standalone_tool_response(project, tool)
            for tool in read_studio_project(project).tools
        ]

    @router.post("/tools")
    def post_tool(payload: ToolCreateRequest) -> StudioProjectModel:
        try:
            return create_tool_file(
                project,
                payload.tool_id,
                payload.name,
                payload.description,
                payload.execute_body,
                input_fields=[f.model_dump() for f in payload.input_fields],
                output_fields=[f.model_dump() for f in payload.output_fields],
                agent_id=payload.agent_id or None,
            )
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/tools/{tool_id}/source")
    def get_tool_by_id_source(tool_id: str) -> ToolSourceResponse:
        path = _resolve_tool_path_or_404(project, tool_id)
        return ToolSourceResponse(
            source_file=str(path), content=path.read_text(encoding="utf-8")
        )

    @router.put("/tools/{tool_id}/source")
    def put_tool_by_id_source(
        tool_id: str, payload: ToolSourceUpdateRequest
    ) -> ToolSourceResponse:
        path = _resolve_tool_path_or_404(project, tool_id)
        path.write_text(payload.content, encoding="utf-8")
        return ToolSourceResponse(source_file=str(path), content=payload.content)

    return router


def _standalone_tool_response(
    project: ClayProject, tool_entry: dict[str, Any]
) -> dict[str, Any]:
    response = dict(tool_entry)
    tool = _load_tool_from_source(project, tool_entry.get("source"))
    if tool is None:
        return response

    response["input_schema"] = tool_schema(tool, "input_schema")
    response["output_schema"] = tool_schema(tool, "output_schema")

    execute_fn = getattr(tool, "_execute_fn", None)
    if execute_fn is not None:
        try:
            response["source_file"] = inspect.getsourcefile(execute_fn)
        except Exception:
            pass

    return response


def _load_tool_from_source(project: ClayProject, source: Any) -> Any | None:
    if not isinstance(source, str):
        return None

    module_name, separator, attr_name = source.partition(":")
    if not separator or not module_name or not attr_name:
        return None

    try:
        ensure_project_import_path(project.root)
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    except Exception:
        return None


def _resolve_tool_path_or_404(project: ClayProject, tool_id: str) -> "Path":
    from clay_studio_server.mutations import _resolve_app_package, _resolve_package_dir

    try:
        package_name, _ = _resolve_app_package(project)
        package_dir = _resolve_package_dir(project.root, package_name)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path = package_dir / "agents" / "tools" / f"{tool_id}.py"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    return path


def _build_interfaces_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/interfaces")
    def get_interfaces() -> list[Any]:
        return _interface_response_items(read_studio_project(project).interfaces)

    @router.post("/interfaces")
    def post_interface(payload: InterfaceConfig) -> StudioProjectModel:
        if payload.agent_id:
            try:
                return add_agent_interface(project, payload.agent_id, payload)
            except ProjectError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            return create_standalone_interface(project, payload)
        except ProjectError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/interfaces/{interface_id}")
    def delete_interface(interface_id: str) -> StudioProjectModel:
        return remove_standalone_interface(project, interface_id)

    return router


def _interface_response_items(interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": _interface_response_id(interface, index),
            **interface,
        }
        for index, interface in enumerate(interfaces, start=1)
    ]


def _interface_response_id(interface: dict[str, Any], index: int) -> str:
    raw_id = interface.get("id")
    if isinstance(raw_id, str) and raw_id:
        return raw_id
    raw_type = interface.get("type")
    platform = raw_type if isinstance(raw_type, str) and raw_type else "chat"
    return f"{platform}_chat" if index == 1 else f"{platform}_chat_{index}"


def _build_workflows_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/workflows")
    def get_workflows() -> list[Any]:
        app = _load_app_or_500(project)
        if app is None:
            return list(read_studio_project(project).workflows.values())
        return summarize_workflows(app)

    @router.put("/workflows/{workflow_id}")
    def put_workflow(workflow_id: str, payload: dict[str, Any]) -> StudioProjectModel:
        return update_mapping_item(project, "workflows", workflow_id, payload)

    @router.delete("/workflows/{workflow_id}")
    def delete_workflow(workflow_id: str) -> StudioProjectModel:
        return delete_mapping_item(project, "workflows", workflow_id)

    return router


def _build_workspaces_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.get("/workspaces")
    def get_workspaces() -> list[Any]:
        app = _load_app_or_500(project)
        if app is None:
            return list(read_studio_project(project).workspaces.values())
        return summarize_workspaces(app)

    @router.put("/workspaces/{workspace_id}")
    def put_workspace(workspace_id: str, payload: dict[str, Any]) -> StudioProjectModel:
        return update_mapping_item(project, "workspaces", workspace_id, payload)

    @router.delete("/workspaces/{workspace_id}")
    def delete_workspace(workspace_id: str) -> StudioProjectModel:
        return delete_mapping_item(project, "workspaces", workspace_id)

    return router


_CLAY_PREAMBLE = """\
from __future__ import annotations
from typing import TypeAlias, Any
from pydantic import BaseModel
from clay_core import AgentTool, AppContext

class Input(BaseModel):
    pass

class Output(BaseModel):
    pass

"""
_PREAMBLE_LINES = _CLAY_PREAMBLE.count("\n")
_CLAY_IMPORT_MODULES = ("clay_app", "clay_chat", "clay_core")


def _prepare_source(source: str, line: int) -> tuple[str, int]:
    """Prepend Clay imports + class stubs when source is a bare execute body (no imports)."""
    if "import" in source:
        return source, line
    return _CLAY_PREAMBLE + source, line + _PREAMBLE_LINES


def _build_lsp_router(project: ClayProject) -> APIRouter:
    router = APIRouter()

    @router.post("/lsp/completions")
    def lsp_completions(payload: LspCompletionRequest) -> list[LspCompletionItem]:
        try:
            import jedi
        except ImportError:
            return []

        source, line = _prepare_source(payload.source, payload.line)
        script = jedi.Script(
            code=source,
            path=None,
            project=_jedi_project(jedi, project),
        )
        try:
            completions = script.complete(line + 1, payload.column)
        except Exception:
            return []

        items = [
            LspCompletionItem(
                label=c.name,
                kind=_jedi_kind(c.type),
                detail=c.type,
                documentation=c.docstring(raw=True) or None,
                insert_text=c.name,
            )
            for c in completions
        ]
        return _with_clay_import_completions(items, source, line, payload.column)

    @router.post("/lsp/hover")
    def lsp_hover(payload: LspHoverRequest) -> LspHoverResponse | None:
        try:
            import jedi
        except ImportError:
            return None

        source, line = _prepare_source(payload.source, payload.line)
        script = jedi.Script(
            code=source,
            path=None,
            project=_jedi_project(jedi, project),
        )
        try:
            names = script.infer(line + 1, payload.column)
        except Exception:
            return None

        if not names:
            return None

        name = names[0]
        sigs: list[Any] = []
        try:
            sigs = script.get_signatures(line + 1, payload.column)
        except Exception:
            pass

        sig_str = sigs[0].to_string() if sigs else name.full_name or name.name
        return LspHoverResponse(
            signature=sig_str,
            documentation=name.docstring(raw=True) or None,
        )

    @router.post("/lsp/diagnostics")
    def lsp_diagnostics(payload: LspDiagnosticRequest) -> list[LspDiagnosticItem]:
        ty_bin = _find_ty_binary()
        if ty_bin is None:
            return [
                _diagnostic_message(
                    "ty is not installed in the studio server environment.",
                    code="ty-unavailable",
                    severity=2,
                )
            ]

        source, line_offset = _prepare_source(payload.source, 0)
        fd, tmp_path = _make_diagnostic_tempfile(project, payload.source_file)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(source)
            result = subprocess.run(
                [
                    str(ty_bin),
                    "check",
                    "--project",
                    str(project.root),
                    "--output-format",
                    "gitlab",
                    "--no-progress",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                cwd=project.root,
                check=False,
            )
            try:
                raw = json.loads(result.stdout)
            except Exception:
                message = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "ty did not return diagnostics."
                )
                return [
                    _diagnostic_message(
                        message,
                        code="ty-run-failed",
                        severity=8,
                    )
                ]
        finally:
            os.unlink(tmp_path)

        items: list[LspDiagnosticItem] = []
        for d in raw:
            loc = d.get("location", {}).get("positions", {})
            begin = loc.get("begin", {})
            end = loc.get("end", {})
            start_line = begin.get("line", 1) - line_offset
            end_line = end.get("line", 1) - line_offset
            if start_line < 1:
                continue  # error is inside the injected preamble, skip it
            severity = _ty_severity(d.get("severity", "major"))
            description = d.get("description", "")
            code = d.get("check_name")
            items.append(
                LspDiagnosticItem(
                    message=description,
                    severity=severity,
                    start_line=start_line,
                    start_column=begin.get("column", 1),
                    end_line=end_line,
                    end_column=max(
                        end.get("column", 1),
                        begin.get("column", 1) + 1,
                    ),
                    code=code,
                )
            )
        return items

    return router


def _jedi_project(jedi: Any, project: ClayProject) -> Any:
    return jedi.Project(
        path=str(project.root),
        added_sys_path=[str(path) for path in _clay_source_paths(project)],
    )


def _clay_source_paths(project: ClayProject) -> list[Path]:
    roots = [project.root, *project.root.parents]
    source_paths: list[Path] = []
    for root in roots:
        packages_dir = root / "packages"
        if not packages_dir.exists():
            continue
        for package_name in ("app", "chat", "core"):
            candidate = packages_dir / package_name / "src"
            if candidate.exists():
                source_paths.append(candidate)
        break
    return source_paths


def _with_clay_import_completions(
    items: list[LspCompletionItem],
    source: str,
    line: int,
    column: int,
) -> list[LspCompletionItem]:
    if not _is_top_level_import_completion_context(source, line, column):
        return items

    by_label = {item.label: item for item in items}
    clay_items = [
        by_label.get(module)
        or LspCompletionItem(
            label=module,
            kind=_jedi_kind("module"),
            detail="module",
            documentation=None,
            insert_text=module,
        )
        for module in _CLAY_IMPORT_MODULES
    ]
    remaining = [item for item in items if item.label not in _CLAY_IMPORT_MODULES]
    return clay_items + remaining


def _is_top_level_import_completion_context(
    source: str, line: int, column: int
) -> bool:
    lines = source.splitlines()
    if line < 0 or line >= len(lines):
        return False
    before_cursor = lines[line][:column]
    return bool(re.match(r"^\s*(?:import\s+[\w.]*|from\s+[\w.]*)\s*$", before_cursor))


def _is_import_completion_context(source: str, line: int, column: int) -> bool:
    lines = source.splitlines()
    if line < 0 or line >= len(lines):
        return False
    before_cursor = lines[line][:column]
    return bool(
        re.match(
            r"^\s*(?:import\s+[\w.]*|from\s+[\w.]+(?:\s+import\s+[\w]*)?)\s*$",
            before_cursor,
        )
    )


def _find_ty_binary() -> Path | None:
    candidates = [
        Path(sys.executable).with_name("ty"),
        Path(sys.executable).with_name("ty.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    found = shutil.which("ty")
    if found is None:
        return None
    return Path(found)


def _make_diagnostic_tempfile(
    project: ClayProject,
    source_file: str | None,
) -> tuple[int, str]:
    temp_dir = project.root
    temp_suffix = ".py"

    if source_file is not None:
        try:
            source_path = Path(source_file).resolve()
            source_path.relative_to(project.root.resolve())
            if source_path.parent.exists():
                temp_dir = source_path.parent
                temp_suffix = source_path.suffix or ".py"
        except OSError, ValueError:
            pass

    return tempfile.mkstemp(
        prefix=".clay-studio-ty-",
        suffix=temp_suffix,
        dir=temp_dir,
    )


def _diagnostic_message(
    message: str,
    *,
    code: str,
    severity: int,
) -> LspDiagnosticItem:
    return LspDiagnosticItem(
        message=message,
        severity=severity,
        start_line=1,
        start_column=1,
        end_line=1,
        end_column=2,
        code=code,
    )


def _ty_severity(ty_severity: str) -> int:
    """Map ty GitLab severity to Monaco MarkerSeverity (8=Error, 4=Warning, 2=Info, 1=Hint)."""
    return {"major": 8, "critical": 8, "minor": 4, "info": 2}.get(ty_severity, 8)


def _jedi_kind(jedi_type: str) -> int:
    """Map Jedi completion type to LSP CompletionItemKind."""
    return {
        "module": 9,
        "class": 7,
        "instance": 6,
        "function": 3,
        "param": 6,
        "path": 17,
        "keyword": 14,
        "property": 10,
        "statement": 6,
    }.get(jedi_type, 1)
