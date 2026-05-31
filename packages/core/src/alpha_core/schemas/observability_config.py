from __future__ import annotations

from pydantic import BaseModel, Field


class ObservabilityConfig(BaseModel):
    """
    OpenTelemetry tracing configuration for AlphaApp.

    When present on ``AppConfig``, ``AlphaApp`` automatically sets up a
    ``TracerProvider`` with an OTLP gRPC exporter and ``BatchSpanProcessor``.
    The service name defaults to ``AppConfig.name`` if not overridden.

    Example::

        AppConfig(
            name="my-app",
            observability=ObservabilityConfig(endpoint="http://localhost:4317"),
        )
    """

    enabled: bool = Field(
        default=True,
        description="Whether to enable OpenTelemetry tracing.",
    )
    endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP gRPC collector endpoint.",
    )
    insecure: bool = Field(
        default=True,
        description="Disable TLS for the OTLP connection (suitable for local collectors).",
    )
    service_name: str | None = Field(
        default=None,
        description="Service name reported in traces. Defaults to AppConfig.name.",
    )


__all__ = ["ObservabilityConfig"]
