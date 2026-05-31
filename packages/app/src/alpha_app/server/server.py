from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alpha_core.log import logger
from alpha_core.schemas.server_config import CorsConfig, ServerConfig

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi import APIRouter


class Server:
    """Owns FastAPI app creation, middleware wiring, router mounting, and serving."""

    def __init__(self, *, config: ServerConfig) -> None:
        self.config = config
        self._routers: list[APIRouter] = []

    def mount_router(self, router: APIRouter) -> None:
        self._routers.append(router)

    def build(self) -> FastAPI:
        from fastapi import FastAPI

        cfg = self.config
        docs_url = "/docs" if cfg.swagger_ui_enabled and cfg.openapi_enabled else None
        openapi_url = "/openapi.json" if cfg.openapi_enabled else None

        app = FastAPI(
            title=cfg.title or "AlphaApp",
            docs_url=docs_url,
            openapi_url=openapi_url,
        )

        self._add_cors(app)
        self._add_timeout(app)
        self._add_body_size_limit(app)

        for router in self._routers:
            app.include_router(router)

        return app

    def _add_cors(self, app: FastAPI) -> None:
        if self.config.cors is False:
            return
        from starlette.middleware.cors import CORSMiddleware

        cors = (
            self.config.cors
            if isinstance(self.config.cors, CorsConfig)
            else CorsConfig()
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors.allow_origins,
            allow_methods=cors.allow_methods,
            allow_headers=cors.allow_headers,
            allow_credentials=cors.allow_credentials,
            max_age=cors.max_age,
        )

    def _add_timeout(self, app: FastAPI) -> None:
        if self.config.timeout is None:
            return

        import asyncio

        timeout_secs = self.config.timeout
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class _TimeoutMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                try:
                    return await asyncio.wait_for(
                        call_next(request), timeout=timeout_secs
                    )
                except TimeoutError:
                    return Response(content="Request timed out.", status_code=504)

        app.add_middleware(_TimeoutMiddleware)

    def _add_body_size_limit(self, app: FastAPI) -> None:
        if self.config.body_size_limit is None:
            return

        limit = self.config.body_size_limit

        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class _BodySizeLimitMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > limit:
                    return Response(
                        content=f"Request body exceeds limit of {limit} bytes.",
                        status_code=413,
                    )
                return await call_next(request)

        app.add_middleware(_BodySizeLimitMiddleware)

    def serve(self) -> None:
        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError(
                "uvicorn is required to call Server.serve(). "
                "Install it or add alpha-chat as a dependency."
            ) from exc

        fastapi_app = self.build()
        logger.info(f"Starting server on {self.config.host}:{self.config.port}")
        uvicorn.run(fastapi_app, host=self.config.host, port=self.config.port)


__all__ = ["Server"]
