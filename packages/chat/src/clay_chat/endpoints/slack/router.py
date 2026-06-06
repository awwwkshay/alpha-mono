from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from clay_chat.endpoints.slack.actions import build_actions_router
from clay_chat.endpoints.slack.commands import build_commands_router
from clay_chat.endpoints.slack.events import build_events_router

if TYPE_CHECKING:
    from clay_chat.adapters.slack_adapter import SlackAdapter


def build_slack_router(adapter: SlackAdapter) -> APIRouter:
    """Return a router with all Slack endpoints mounted."""
    slack_router = APIRouter()
    slack_router.include_router(build_events_router(adapter))
    slack_router.include_router(build_commands_router(adapter))
    slack_router.include_router(build_actions_router(adapter))
    return slack_router


__all__ = ["build_slack_router"]
