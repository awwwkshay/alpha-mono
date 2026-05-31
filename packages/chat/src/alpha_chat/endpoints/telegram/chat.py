from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from alpha_chat.contracts import ChatContract
from alpha_chat.log import logger

_PUBLIC_URL_ENV = "PUBLIC_URL"


@dataclass
class TelegramChat(ChatContract):
    """
    Telegram chat integration for ``AgentConfig.chat``.

    Reads the bot token from ``TELEGRAM_BOT_TOKEN`` at mount time.
    On ``AlphaApp.setup()``, automatically registers the webhook URL with Telegram.
    The URL is constructed as ``{base_url}/telegram/{agent_id}/webhook``.

    ``base_url`` can be passed explicitly or read from the ``PUBLIC_URL``
    environment variable (loaded from ``.env`` before setup runs).

    Example::

        AgentConfig(
            ...
            chat=[TelegramChat()],          # uses PUBLIC_URL env var
        )

    Or with an explicit base URL::

        AgentConfig(
            ...
            chat=[TelegramChat(base_url="https://your-host")],
        )
    """

    token_env: str = field(default="TELEGRAM_BOT_TOKEN")
    base_url: str | None = field(default=None)

    def mount(self, app: Any, agent: Any, agent_id: str) -> None:
        from alpha_chat.adapters.telegram_adapter import TelegramAdapter
        from alpha_chat.clients.telegram_client import TelegramClient
        from alpha_chat.endpoints.telegram.webhook import build_telegram_router

        self._agent_id = agent_id
        self._client = TelegramClient(token=os.environ[self.token_env])
        adapter = TelegramAdapter(
            agent=agent, context=app.context, telegram_client=self._client
        )
        prefix = f"/telegram/{agent_id}"
        app.mount_router(build_telegram_router(adapter), prefix=prefix)

    async def setup(self) -> None:
        base = self.base_url or os.environ.get(_PUBLIC_URL_ENV)
        if base:
            url = f"{base.rstrip('/')}/telegram/{self._agent_id}/webhook"
            await self._client.set_webhook(url)
            logger.info(f"Telegram handlers listening at {url}")


__all__ = ["TelegramChat"]
