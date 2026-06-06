from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Request

from clay_chat.endpoints.slack._utils import verify_slack_signature
from clay_chat.log import logger

if TYPE_CHECKING:
    from clay_chat.adapters.slack_adapter import SlackAdapter

# Deduplicates Slack retries — Slack resends events if it doesn't get a 200 within 3s.
# Stored as an ordered dict so we can evict the oldest entries without wiping the whole set.
_SEEN_EVENT_IDS: dict[str, None] = {}
_MAX_SEEN = 2000
_EVICT_COUNT = _MAX_SEEN // 10  # evict 10% (200) when the cap is hit


def build_events_router(adapter: SlackAdapter) -> APIRouter:
    events_router = APIRouter()

    @events_router.post("/events")
    async def slack_events(request: Request, background_tasks: BackgroundTasks) -> Any:
        body = await request.body()
        verify_slack_signature(
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
                _SEEN_EVENT_IDS[event_id] = None
                if len(_SEEN_EVENT_IDS) > _MAX_SEEN:
                    for k in list(_SEEN_EVENT_IDS.keys())[:_EVICT_COUNT]:
                        del _SEEN_EVENT_IDS[k]

            event = payload.get("event", {})
            if (
                event.get("type") in ("message", "app_mention")
                and not event.get("bot_id")
                and not event.get("subtype")
            ):
                logger.info(f"Slack message event from user={event.get('user')}")
                background_tasks.add_task(adapter.handle_event, event)

        return {"ok": True}

    return events_router


__all__ = ["build_events_router"]
