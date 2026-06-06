from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from alpha_chat.contracts import ChatContract
from alpha_chat.log import logger


@dataclass
class SlackChat(ChatContract):
    """
    Slack chat integration for ``AgentConfig.chat``.

    Reads bot token and signing secret from environment variables at mount time.
    Override ``token_env`` / ``signing_secret_env`` to use custom variable names.

    Example::

        AgentConfig(
            ...
            chat=[SlackChat()],
        )
    """

    token_env: str = field(default="SLACK_BOT_TOKEN")
    signing_secret_env: str = field(default="SLACK_SIGNING_SECRET")

    def mount(self, app: Any, agent: Any, agent_id: str) -> None:
        from alpha_chat.adapters.slack_adapter import SlackAdapter
        from alpha_chat.clients.slack_client import SlackClient
        from alpha_chat.endpoints.slack.router import build_slack_router

        slack_client = SlackClient(
            token=os.environ[self.token_env],
            signing_secret=os.environ[self.signing_secret_env],
        )
        adapter = SlackAdapter(
            agent=agent,
            context=app.get_agent_context(agent_id),
            slack_client=slack_client,
        )
        self._agent_id = agent_id
        prefix = f"/slack/{agent_id}"
        app.mount_router(build_slack_router(adapter), prefix=prefix)

    async def setup(self) -> None:
        base = os.environ.get("PUBLIC_URL", "").rstrip("/")
        prefix = f"/slack/{self._agent_id}"
        base_url = f"{base}{prefix}" if base else prefix
        logger.info(f"Slack handlers listening at {base_url}/{{events,commands,actions}}")


__all__ = ["SlackChat"]
