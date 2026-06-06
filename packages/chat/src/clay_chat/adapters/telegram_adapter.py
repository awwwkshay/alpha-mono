from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from clay_core import AppContext

from clay_chat.clients.telegram_client import TelegramClient
from clay_chat.log import logger
from clay_chat.schemas.telegram import TelegramUpdate

_tracer = trace.get_tracer(__name__)


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
        text = "[Platform: Telegram]\n" + message.text

        with _tracer.start_as_current_span(
            "chat.telegram.message",
            kind=SpanKind.SERVER,
            attributes={
                "chat.platform": "telegram",
                "chat.chat_id": str(chat_id),
                "chat.user_id": str(message.from_.id) if message.from_ else "",
                "chat.is_edit": update.edited_message is not None,
            },
        ) as span:
            span.set_attribute("user.prompt", text)
            span.add_event(
                "chat.user.message", {"content": text, "chat_id": str(chat_id)}
            )
            logger.info(f"TelegramAdapter handling message in chat_id={chat_id}")
            try:
                response = await self._agent.generate_async(text, self._context)
            except Exception as exc:
                logger.error(f"Agent error for chat_id={chat_id}: {exc}")
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                await self._telegram_client.send_message(
                    chat_id, "Sorry, I ran into an error. Please try again."
                )
                return
            span.set_attribute("agent.response", response)
            span.add_event(
                "chat.assistant.message", {"content": response, "chat_id": str(chat_id)}
            )
            await self._telegram_client.send_message(chat_id, response)


__all__ = ["TelegramAdapter"]
