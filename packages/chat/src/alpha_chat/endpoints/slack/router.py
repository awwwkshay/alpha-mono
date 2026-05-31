from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from alpha_chat.endpoints.slack.events import build_events_router
from alpha_chat.endpoints.slack.commands import build_commands_router
from alpha_chat.endpoints.slack.actions import build_actions_router

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter


def build_slack_router(adapter: SlackAdapter) -> APIRouter:
    """Return a router with all Slack endpoints mounted."""
    slack_router = APIRouter()
    slack_router.include_router(build_events_router(adapter))
    slack_router.include_router(build_commands_router(adapter))
    slack_router.include_router(build_actions_router(adapter))
    return slack_router


__all__ = ["build_slack_router"]
