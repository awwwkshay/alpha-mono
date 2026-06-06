from __future__ import annotations

from typing import TYPE_CHECKING, Any

import hmac

from fastapi import APIRouter, HTTPException, Request

from alpha_chat.log import logger
from alpha_chat.schemas.telegram import TelegramUpdate

if TYPE_CHECKING:
    from alpha_chat.adapters.telegram_adapter import TelegramAdapter


def build_telegram_router(
    adapter: TelegramAdapter, *, secret_token: str | None = None
) -> APIRouter:
    """Return a router with the Telegram webhook endpoint."""
    telegram_router = APIRouter()

    @telegram_router.post("/webhook")
    async def telegram_webhook(request: Request) -> Any:
        if secret_token is not None:
            request_secret = request.headers.get("x-telegram-bot-api-secret-token", "")
            if not hmac.compare_digest(request_secret, secret_token):
                raise HTTPException(status_code=401, detail="Invalid Telegram secret")

        payload = await request.json()
        update = TelegramUpdate.model_validate(payload)
        logger.info(f"Telegram update id={update.update_id}")
        await adapter.handle_update(update)
        return {"ok": True}

    return telegram_router


__all__ = ["build_telegram_router"]
