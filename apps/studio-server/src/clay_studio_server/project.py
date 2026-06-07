from __future__ import annotations

import sys
import tomllib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from clay_studio_server.schemas import StudioAppModel, StudioProjectModel


CLAY_YAML = "clay.yaml"
STUDIO_ENVIRONMENTS = frozenset({"development", "preproduction", "production"})


class ProjectError(RuntimeError):
    """Raised when a Clay project cannot be loaded."""


@dataclass(frozen=True)
class ClayProject:
    root: Path
    app_ref: str | None

    @property
    def clay_yaml_path(self) -> Path:
        return self.root / CLAY_YAML


@dataclass(frozen=True)
class StudioSettings:
    mode: str = "production"
    host: str = "127.0.0.1"
    port: int = 3000
    open_browser: bool = True
    client_host: str = "127.0.0.1"
    client_port: int = 5173


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise ProjectError("Could not find pyproject.toml in the current directory tree.")


def read_configured_app_ref(root: Path) -> str | None:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    clay_config = data.get("tool", {}).get("clay", {})
    app_ref = clay_config.get("app")
    return app_ref if isinstance(app_ref, str) and app_ref else None


def read_studio_settings(root: Path) -> StudioSettings:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return StudioSettings()

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    studio_config = data.get("tool", {}).get("clay", {}).get("studio", {})
    if not isinstance(studio_config, dict):
        return StudioSettings()

    mode = studio_config.get("mode", StudioSettings.mode)
    host = studio_config.get("host", StudioSettings.host)
    port = studio_config.get("port", StudioSettings.port)
    open_browser = studio_config.get("open_browser", StudioSettings.open_browser)
    client_host = studio_config.get("client_host", StudioSettings.client_host)
    client_port = studio_config.get("client_port", StudioSettings.client_port)

    resolved_mode = mode if isinstance(mode, str) and mode else StudioSettings.mode
    if resolved_mode not in STUDIO_ENVIRONMENTS:
        resolved_mode = StudioSettings.mode

    return StudioSettings(
        mode=resolved_mode,
        host=host if isinstance(host, str) and host else StudioSettings.host,
        port=port if isinstance(port, int) else StudioSettings.port,
        open_browser=(
            open_browser
            if isinstance(open_browser, bool)
            else StudioSettings.open_browser
        ),
        client_host=(
            client_host
            if isinstance(client_host, str) and client_host
            else StudioSettings.client_host
        ),
        client_port=(
            client_port if isinstance(client_port, int) else StudioSettings.client_port
        ),
    )


def read_git_branch(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError, subprocess.CalledProcessError:
        return None

    branch = result.stdout.strip()
    if branch and branch != "HEAD":
        return branch

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError, subprocess.CalledProcessError:
        return None

    commit = result.stdout.strip()
    return f"detached@{commit}" if commit else None


def load_project(
    start: Path | None = None, *, app_ref: str | None = None
) -> ClayProject:
    root = find_project_root(start)
    return ClayProject(root=root, app_ref=app_ref or read_configured_app_ref(root))


def ensure_project_import_path(root: Path) -> None:
    for candidate in (root / "src", root):
        path = str(candidate)
        if candidate.exists() and path not in sys.path:
            sys.path.insert(0, path)


def read_studio_project(project: ClayProject) -> StudioProjectModel:
    path = project.clay_yaml_path
    if not path.exists():
        return StudioProjectModel(app=StudioAppModel(name=project.root.name))

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ProjectError(f"{path} must contain a YAML mapping.")
    return StudioProjectModel.model_validate(raw)


def write_studio_project(project: ClayProject, model: StudioProjectModel) -> None:
    payload = model.model_dump(mode="json", exclude_none=True)
    project.clay_yaml_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def update_mapping_item(
    project: ClayProject,
    section: str,
    item_id: str,
    payload: dict[str, Any],
) -> StudioProjectModel:
    model = read_studio_project(project)
    section_value = getattr(model, section)
    section_value[item_id] = payload
    write_studio_project(project, model)
    return model


def delete_mapping_item(
    project: ClayProject,
    section: str,
    item_id: str,
) -> StudioProjectModel:
    model = read_studio_project(project)
    section_value = getattr(model, section)
    section_value.pop(item_id, None)
    write_studio_project(project, model)
    return model
