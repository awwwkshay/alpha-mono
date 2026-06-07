from __future__ import annotations

import webbrowser
import os
import subprocess
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from clay_studio_server.api import build_api_router
from clay_studio_server.project import (
    STUDIO_ENVIRONMENTS,
    load_project,
    read_studio_settings,
)
from clay_studio_server.static import mount_studio_static


_PROJECT_ROOT_ENV = "CLAY_STUDIO_PROJECT_ROOT"
_APP_REF_ENV = "CLAY_STUDIO_APP_REF"


def _default_studio_client_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "studio-client"


def _vp_command(client_dir: Path) -> str | Path:
    local_vp = client_dir / "node_modules" / ".bin" / "vp"
    if local_vp.exists():
        return local_vp
    return "vp"


def _start_client_dev_server(
    *,
    client_dir: Path,
    client_host: str,
    client_port: int,
    api_url: str,
) -> subprocess.Popen[str]:
    if not client_dir.exists():
        raise RuntimeError(f"Studio client source not found at {client_dir}")

    env = os.environ.copy()
    env["CLAY_STUDIO_API_URL"] = api_url
    return subprocess.Popen(
        [
            str(_vp_command(client_dir)),
            "dev",
            "--host",
            client_host,
            "--port",
            str(client_port),
        ],
        cwd=client_dir,
        env=env,
        text=True,
    )


def create_studio_app(
    *,
    project_root: Path | None = None,
    app_ref: str | None = None,
) -> FastAPI:
    project = load_project(project_root, app_ref=app_ref)
    app = FastAPI(title="Clay Studio")
    app.include_router(build_api_router(project))
    mount_studio_static(app)
    return app


def create_studio_app_from_env() -> FastAPI:
    project_root_value = os.environ.get(_PROJECT_ROOT_ENV)
    app_ref = os.environ.get(_APP_REF_ENV) or None
    project_root = Path(project_root_value) if project_root_value else None
    return create_studio_app(project_root=project_root, app_ref=app_ref)


def run_studio(
    *,
    mode: str | None = None,
    host: str | None = None,
    port: int | None = None,
    project_root: Path | None = None,
    app_ref: str | None = None,
    open_browser: bool | None = None,
    client_host: str | None = None,
    client_port: int | None = None,
    client_dir: Path | None = None,
) -> None:
    project = load_project(project_root, app_ref=app_ref)
    settings = read_studio_settings(project.root)
    resolved_mode = mode or settings.mode
    if resolved_mode not in STUDIO_ENVIRONMENTS:
        raise RuntimeError(
            "Studio mode must be one of: development, preproduction, production."
        )
    resolved_host = host or settings.host
    resolved_port = port or settings.port
    resolved_client_host = client_host or settings.client_host
    resolved_client_port = client_port or settings.client_port
    resolved_open_browser = (
        open_browser if open_browser is not None else settings.open_browser
    )

    app = create_studio_app(project_root=project.root, app_ref=project.app_ref)
    api_url = f"http://{resolved_host}:{resolved_port}"
    client_process: subprocess.Popen[str] | None = None
    browser_url = api_url

    if resolved_mode == "development":
        client_process = _start_client_dev_server(
            client_dir=client_dir or _default_studio_client_dir(),
            client_host=resolved_client_host,
            client_port=resolved_client_port,
            api_url=api_url,
        )
        browser_url = f"http://{resolved_client_host}:{resolved_client_port}"

    print(f"Clay Studio API running at {api_url}")
    if resolved_mode == "development":
        print(f"Clay Studio client running at {browser_url}")
    if resolved_open_browser:
        webbrowser.open(browser_url)

    try:
        if resolved_mode == "development":
            os.environ[_PROJECT_ROOT_ENV] = str(project.root)
            if project.app_ref is not None:
                os.environ[_APP_REF_ENV] = project.app_ref
            else:
                os.environ.pop(_APP_REF_ENV, None)
            uvicorn.run(
                "clay_studio_server.server:create_studio_app_from_env",
                factory=True,
                host=resolved_host,
                port=resolved_port,
                reload=True,
                reload_dirs=[
                    str(project.root),
                    str(Path(__file__).resolve().parents[2]),
                ],
            )
        else:
            uvicorn.run(app, host=resolved_host, port=resolved_port)
    finally:
        if client_process is not None:
            client_process.terminate()
