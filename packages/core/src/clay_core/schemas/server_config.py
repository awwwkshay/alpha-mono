from __future__ import annotations

from pydantic import BaseModel, Field


class CorsConfig(BaseModel):
    """CORS policy for the server."""

    allow_origins: list[str] = Field(default=["*"])
    allow_methods: list[str] = Field(default=["*"])
    allow_headers: list[str] = Field(default=["*"])
    allow_credentials: bool = Field(default=False)
    max_age: int = Field(
        default=600, description="Pre-flight cache duration in seconds"
    )


class ServerConfig(BaseModel):
    """HTTP server configuration passed to ClayApp."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    title: str | None = Field(
        default=None, description="API title shown in OpenAPI docs"
    )

    timeout: int | None = Field(
        default=None,
        description="Request timeout in seconds. None means no limit.",
    )
    cors: CorsConfig | bool = Field(
        default=True,
        description=(
            "CORS policy. True uses permissive defaults (allow *), "
            "False disables CORS, or pass a CorsConfig for fine-grained control."
        ),
    )
    body_size_limit: int | None = Field(
        default=None,
        description="Max request body size in bytes. None means no limit.",
    )
    openapi_enabled: bool = Field(
        default=True,
        description="Serve OpenAPI schema at /openapi.json.",
    )
    swagger_ui_enabled: bool = Field(
        default=True,
        description="Serve Swagger UI at /docs. Requires openapi_enabled=True.",
    )


__all__ = ["CorsConfig", "ServerConfig"]
