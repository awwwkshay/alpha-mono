from __future__ import annotations

import asyncio
from typing import Any

from slack_sdk import WebClient
from slack_sdk.web.slack_response import SlackResponse

from clay_chat.log import logger


class SlackClient:
    """Async-friendly wrapper around slack_sdk.WebClient."""

    def __init__(self, *, token: str, signing_secret: str) -> None:
        self._client = WebClient(token=token)
        self.signing_secret = signing_secret

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
    ) -> SlackResponse:
        kwargs: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        logger.debug(f"Sending Slack message to channel={channel}")
        return await asyncio.to_thread(self._client.chat_postMessage, **kwargs)

    async def set_status(
        self,
        channel: str,
        thread_ts: str,
        status: str,
    ) -> SlackResponse:
        logger.debug(f"Setting assistant status='{status}' in channel={channel}")
        return await asyncio.to_thread(
            self._client.assistant_threads_setStatus,
            channel_id=channel,
            thread_ts=thread_ts,
            status=status,
        )

    async def react(self, channel: str, ts: str, emoji: str) -> SlackResponse:
        logger.debug(f"Adding reaction :{emoji}: in channel={channel}")
        return await asyncio.to_thread(
            self._client.reactions_add, channel=channel, timestamp=ts, name=emoji
        )

    async def open_modal(self, trigger_id: str, view: dict[str, Any]) -> SlackResponse:
        logger.debug("Opening Slack modal")
        return await asyncio.to_thread(
            self._client.views_open, trigger_id=trigger_id, view=view
        )

    async def ack_slash_command(self, response_url: str, text: str) -> None:
        """Post an immediate visible response to a slash command via response_url."""
        import httpx

        async with httpx.AsyncClient() as http:
            await http.post(response_url, json={"text": text})


__all__ = ["SlackClient"]
