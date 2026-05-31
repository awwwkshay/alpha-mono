from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from slack_sdk.signature import SignatureVerifier

from alpha_chat.log import logger

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter

# Deduplicates Slack retries — Slack resends events if it doesn't get a 200 within 3s.
_SEEN_EVENT_IDS: set[str] = set()
_MAX_SEEN = 2000


def _verify_slack_signature(
    signing_secret: str, request_body: bytes, headers: dict
) -> None:
    verifier = SignatureVerifier(signing_secret)
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not verifier.is_valid(request_body.decode(), timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


def build_events_router(adapter: SlackAdapter) -> APIRouter:
    events_router = APIRouter()

    @events_router.post("/events")
    async def slack_events(request: Request) -> Any:
        body = await request.body()
        _verify_slack_signature(
            adapter.signing_secret,
            body,
            dict(request.headers),
        )

        payload: dict[str, Any] = json.loads(body)
        event_type = payload.get("type")

        if event_type == "url_verification":
            return {"challenge": payload["challenge"]}

        if event_type == "event_callback":
            event_id = payload.get("event_id", "")
            if event_id:
                if event_id in _SEEN_EVENT_IDS:
                    logger.debug(f"Dropping duplicate Slack event {event_id}")
                    return {"ok": True}
                _SEEN_EVENT_IDS.add(event_id)
                if len(_SEEN_EVENT_IDS) > _MAX_SEEN:
                    _SEEN_EVENT_IDS.clear()

            event = payload.get("event", {})
            if (
                event.get("type") == "message"
                and not event.get("bot_id")
                and not event.get("subtype")
            ):
                logger.info(f"Slack message event from user={event.get('user')}")
                asyncio.create_task(adapter.handle_event(event))

        return {"ok": True}

    return events_router


__all__ = ["build_events_router"]
