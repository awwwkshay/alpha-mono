from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from alpha_chat.endpoints.slack._utils import parse_slack_form, verify_slack_signature
from alpha_chat.log import logger
from alpha_chat.schemas.slack import SlackAction

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter


def build_actions_router(adapter: SlackAdapter) -> APIRouter:
    actions_router = APIRouter()

    @actions_router.post("/actions")
    async def slack_actions(request: Request, background_tasks: BackgroundTasks) -> Any:
        body = await request.body()
        verify_slack_signature(adapter.signing_secret, body, dict(request.headers))

        form = parse_slack_form(body)
        payload_str = form.get("payload", "")
        if not payload_str:
            raise HTTPException(status_code=400, detail="Missing payload")

        payload: dict[str, Any] = json.loads(str(payload_str))
        action = SlackAction(
            type=payload.get("type", ""),
            actions=payload.get("actions", []),
            user=payload.get("user", {}),
            channel=payload.get("channel"),
            trigger_id=payload.get("trigger_id", ""),
            response_url=payload.get("response_url"),
            payload=payload,
        )
        logger.info(
            f"Slack action type={action.type} from user={action.user.get('id')}"
        )
        background_tasks.add_task(adapter.handle_action, action)
        return {"ok": True}

    return actions_router


__all__ = ["build_actions_router"]
