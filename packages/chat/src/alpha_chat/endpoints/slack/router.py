from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

from alpha_chat.contracts import ChatContract
from alpha_chat.endpoints.slack.actions import build_actions_router
from alpha_chat.endpoints.slack.commands import build_commands_router
from alpha_chat.endpoints.slack.events import build_events_router

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter


def build_slack_router(adapter: SlackAdapter) -> APIRouter:
    """Return a router with all Slack endpoints mounted."""
    slack_router = APIRouter()
    slack_router.include_router(build_events_router(adapter))
    slack_router.include_router(build_commands_router(adapter))
    slack_router.include_router(build_actions_router(adapter))
    return slack_router


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

    def mount(self, app: Any, agent: Any) -> None:
        from alpha_chat.adapters.slack_adapter import SlackAdapter
        from alpha_chat.clients.slack_client import SlackClient

        slack_client = SlackClient(
            token=os.environ[self.token_env],
            signing_secret=os.environ[self.signing_secret_env],
        )
        adapter = SlackAdapter(
            agent=agent, context=app.context, slack_client=slack_client
        )
        app.mount_router(build_slack_router(adapter))


__all__ = ["SlackChat", "build_slack_router"]
