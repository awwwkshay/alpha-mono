from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SlackMessageEvent(BaseModel):
    type: str
    user: str | None = None
    text: str | None = None
    channel: str
    ts: str
    thread_ts: str | None = None
    bot_id: str | None = None


class SlackEventCallback(BaseModel):
    type: str = "event_callback"
    team_id: str
    event: dict[str, Any]
    event_id: str
    event_time: int


class SlackUrlVerification(BaseModel):
    type: str = "url_verification"
    challenge: str
    token: str | None = None


class SlackCommand(BaseModel):
    command: str
    text: str
    user_id: str
    channel_id: str
    response_url: str
    trigger_id: str


class SlackAction(BaseModel):
    type: str
    actions: list[dict[str, Any]]
    user: dict[str, Any]
    channel: dict[str, Any] | None = None
    trigger_id: str
    response_url: str | None = None
    payload: dict[str, Any] | None = None


__all__ = [
    "SlackAction",
    "SlackCommand",
    "SlackEventCallback",
    "SlackMessageEvent",
    "SlackUrlVerification",
]
