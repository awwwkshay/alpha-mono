from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from clay_chat.contracts import ChatContract
from clay_chat.log import logger

_PUBLIC_URL_ENV = "PUBLIC_URL"


@dataclass
class TelegramChat(ChatContract):
    """
    Telegram chat integration for ``AgentConfig.chat``.

    Reads the bot token from ``TELEGRAM_BOT_TOKEN`` at mount time.
    On ``ClayApp.setup()``, automatically registers the webhook URL with Telegram.
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
    secret_token_env: str = field(default="TELEGRAM_WEBHOOK_SECRET")
    base_url: str | None = field(default=None)

    def mount(self, app: Any, agent: Any, agent_id: str) -> None:
        from clay_chat.adapters.telegram_adapter import TelegramAdapter
        from clay_chat.clients.telegram_client import TelegramClient
        from clay_chat.endpoints.telegram.webhook import build_telegram_router

        self._agent_id = agent_id
        _raw = os.environ.get(self.secret_token_env)
        if _raw is not None and not _raw:
            raise ValueError(
                f"Environment variable '{self.secret_token_env}' is set but empty; "
                "provide a non-empty token or remove the variable to disable webhook auth"
            )
        if _raw is None:
            logger.warning(
                f"'{self.secret_token_env}' is not set; the Telegram webhook endpoint "
                "has no authentication and will accept requests from any caller. "
                "Set this variable to a random secret to enable signature verification."
            )
        self._secret_token: str | None = _raw
        self._client = TelegramClient(token=os.environ[self.token_env])
        adapter = TelegramAdapter(
            agent=agent,
            context=app.get_agent_context(agent_id),
            telegram_client=self._client,
        )
        prefix = f"/telegram/{agent_id}"
        app.mount_router(
            build_telegram_router(adapter, secret_token=self._secret_token),
            prefix=prefix,
        )

    async def setup(self) -> None:
        base = self.base_url or os.environ.get(_PUBLIC_URL_ENV)
        if not base:
            return
        url = f"{base.rstrip('/')}/telegram/{self._agent_id}/webhook"
        try:
            await self._client.set_webhook(url, secret_token=self._secret_token)
            logger.info(f"Telegram handlers listening at {url}")
        except Exception as exc:
            logger.warning(
                f"Failed to register Telegram webhook at {url}: {exc}. "
                "Telegram updates will not be received until the webhook is registered."
            )


__all__ = ["TelegramChat"]
