from __future__ import annotations

from pathlib import Path

from clay_app import ClayApp
from clay_core import AppConfig, ObservabilityConfig, ServerConfig

from personal_agent.agents import AGENTS

APP = ClayApp(
    config=AppConfig(
        name="personal-agent",
        env_file=Path(__file__).parents[2] / ".env",
        server=ServerConfig(host="0.0.0.0", port=8001),
        agents=AGENTS,
        observability=ObservabilityConfig(endpoint="http://localhost:4317"),
    ),
)

__all__ = ["APP"]
