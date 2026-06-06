from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Request

from alpha_chat.endpoints.slack._utils import parse_slack_form, verify_slack_signature
from alpha_chat.log import logger
from alpha_chat.schemas.slack import SlackCommand

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter


def build_commands_router(adapter: SlackAdapter) -> APIRouter:
    commands_router = APIRouter()

    @commands_router.post("/commands")
    async def slack_commands(request: Request, background_tasks: BackgroundTasks) -> Any:
        body = await request.body()
        verify_slack_signature(adapter.signing_secret, body, dict(request.headers))

        form = parse_slack_form(body)
        command = SlackCommand(
            command=str(form.get("command", "")),
            text=str(form.get("text", "")),
            user_id=str(form.get("user_id", "")),
            channel_id=str(form.get("channel_id", "")),
            response_url=str(form.get("response_url", "")),
            trigger_id=str(form.get("trigger_id", "")),
        )
        logger.info(f"Slack command {command.command} from user={command.user_id}")
        background_tasks.add_task(adapter.handle_command, command)
        return {"response_type": "in_channel", "text": "Processing..."}

    return commands_router


__all__ = ["build_commands_router"]
