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
            agent=agent, context=app.context, slack_client=slack_client
        )
        prefix = f"/slack/{agent_id}"
        logger.info(f"Mounting Slack endpoints at {prefix}/{{events,commands,actions}}")
        app.mount_router(build_slack_router(adapter), prefix=prefix)


__all__ = ["SlackChat"]
