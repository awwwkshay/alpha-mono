from __future__ import annotations

from pathlib import Path

from alpha_app import AlphaApp, AppConfig, ServerConfig

from personal_agent.agents import personal_agent_config

APP = AlphaApp(
    config=AppConfig(
        name="personal-agent",
        env_file=Path(__file__).parents[2] / ".env",
        server=ServerConfig(host="0.0.0.0", port=8001),
        agents={"jarvis": personal_agent_config},
    ),
)

__all__ = ["APP"]
