from __future__ import annotations

import os
from pathlib import Path

from alpha_chat.adapters.slack_adapter import SlackAdapter
from alpha_chat.clients.slack_client import SlackClient
from alpha_chat.endpoints.slack.router import build_slack_router
from alpha_core.domain.app.app import AlphaApp
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.server_config import ServerConfig

from personal_agent.agents.jarvis import jarvis

_ENV_FILE = Path(__file__).parents[2] / ".env"

APP = AlphaApp(
    config=AppConfig(
        name="personal-agent",
        env_file=_ENV_FILE,
        server=ServerConfig(host="0.0.0.0", port=8001),
    )
)

_slack_client = SlackClient(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)
_adapter = SlackAdapter(
    agent=jarvis,
    context=APP.context,
    slack_client=_slack_client,
)
APP.mount_router(build_slack_router(_adapter))

__all__ = ["APP"]
