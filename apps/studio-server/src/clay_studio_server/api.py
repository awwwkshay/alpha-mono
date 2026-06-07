from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from clay_studio_server.introspection import (
    summarize_agents,
    summarize_workflows,
    summarize_workspaces,
)
from clay_studio_server.loader import load_app
from clay_studio_server.mutations import create_agent_files
from clay_studio_server.project import (
    ClayProject,
    ProjectError,
    delete_mapping_item,
    read_git_branch,
    read_studio_project,
    update_mapping_item,
    write_studio_project,
)
from clay_studio_server.schemas import (
    AgentCreateRequest,
    ModelOption,
    ProjectInfo,
    StudioProjectModel,
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
    router.include_router(_build_workflows_router(project))
    router.include_router(_build_workspaces_router(project))
    return router


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
    def put_agent(agent_id: str, payload: dict[str, Any]) -> StudioProjectModel:
        return update_mapping_item(project, "agents", agent_id, payload)

    @router.delete("/agents/{agent_id}")
    def delete_agent(agent_id: str) -> StudioProjectModel:
        return delete_mapping_item(project, "agents", agent_id)

    return router


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
