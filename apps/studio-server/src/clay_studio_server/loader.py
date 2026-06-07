from __future__ import annotations

import importlib
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
    module = importlib.import_module(module_name)
    app = module
    for part in attr_name.split("."):
        app = getattr(app, part)
    return app
