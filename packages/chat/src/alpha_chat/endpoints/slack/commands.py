from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from slack_sdk.signature import SignatureVerifier

from alpha_chat.log import logger
from alpha_chat.schemas.slack import SlackCommand

if TYPE_CHECKING:
    from alpha_chat.adapters.slack_adapter import SlackAdapter


def build_commands_router(adapter: SlackAdapter) -> APIRouter:
    commands_router = APIRouter()

    @commands_router.post("/commands")
    async def slack_commands(request: Request) -> Any:
        body = await request.body()
        verifier = SignatureVerifier(adapter.signing_secret)
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        signature = request.headers.get("x-slack-signature", "")
        if not verifier.is_valid(body.decode(), timestamp, signature):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

        form = await request.form()
        command = SlackCommand(
            command=str(form.get("command", "")),
            text=str(form.get("text", "")),
            user_id=str(form.get("user_id", "")),
            channel_id=str(form.get("channel_id", "")),
            response_url=str(form.get("response_url", "")),
            trigger_id=str(form.get("trigger_id", "")),
        )
        logger.info(f"Slack command {command.command} from user={command.user_id}")
        await adapter.handle_command(command)
        return {"response_type": "in_channel", "text": "Processing..."}

    return commands_router


__all__ = ["build_commands_router"]
