from __future__ import annotations

from typing import Any
from alpha_core.schemas.app_context import AppContext

from alpha_chat.clients.telegram_client import TelegramClient
from alpha_chat.log import logger
from alpha_chat.schemas.telegram import TelegramUpdate


class TelegramAdapter:
    """Bridges inbound Telegram updates to an Agent and replies via TelegramClient."""

    def __init__(
        self,
        *,
        agent: Any,
        context: AppContext,
        telegram_client: TelegramClient,
    ) -> None:
        self._agent = agent
        self._context = context
        self._telegram_client = telegram_client

    async def handle_update(self, update: TelegramUpdate) -> None:
        message = update.message or update.edited_message
        if not message or not message.text:
            return
        chat_id = message.chat.id
        text = message.text
        logger.info(f"TelegramAdapter handling message in chat_id={chat_id}")
        response = await self._agent.generate_async(text, self._context)
        await self._telegram_client.send_message(chat_id, response)


__all__ = ["TelegramAdapter"]
