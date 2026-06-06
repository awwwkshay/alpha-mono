from __future__ import annotations

from telegram import Bot

from alpha_chat.log import logger


class TelegramClient:
    """Async wrapper around python-telegram-bot's Bot."""

    def __init__(self, *, token: str) -> None:
        self._bot = Bot(token=token)

    async def send_message(self, chat_id: int | str, text: str) -> None:
        logger.debug(f"Sending Telegram message to chat_id={chat_id}")
        async with self._bot:
            await self._bot.send_message(chat_id=chat_id, text=text)

    async def set_webhook(self, url: str, secret_token: str | None = None) -> None:
        async with self._bot:
            await self._bot.set_webhook(url=url, secret_token=secret_token)

    async def delete_webhook(self) -> None:
        logger.info("Deleting Telegram webhook")
        async with self._bot:
            await self._bot.delete_webhook()


__all__ = ["TelegramClient"]
