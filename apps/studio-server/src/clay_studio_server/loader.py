from __future__ import annotations

import importlib
import os
from typing import Any

from clay_studio_server.project import (
    ClayProject,
    ProjectError,
    ensure_project_import_path,
)


def load_app(project: ClayProject) -> Any | None:
    if project.app_ref is None:
        return None

    module_name, separator, attr_name = project.app_ref.partition(":")
    if not separator or not module_name or not attr_name:
        raise ProjectError(
            "Clay app reference must use the format 'module.path:OBJECT'."
        )

    ensure_project_import_path(project.root)
    _load_project_env(project)
    module = importlib.import_module(module_name)
    app = module
    for part in attr_name.split("."):
        app = getattr(app, part)
    return app


def _load_project_env(project: ClayProject) -> None:
    env_path = project.root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip().strip('"').strip("'")
    return key, value
