from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def get_studio_dist() -> Path:
    return Path(__file__).parent / "studio_dist"


def mount_studio_static(app: FastAPI) -> None:
    dist = get_studio_dist()
    index_path = dist / "index.html"
    assets_path = dist / "assets"

    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="studio-assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        requested = (dist / path).resolve()
        if requested.is_file() and requested.is_relative_to(dist):
            return FileResponse(requested)
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(
            status_code=404,
            detail="Embedded Studio build was not found.",
        )
