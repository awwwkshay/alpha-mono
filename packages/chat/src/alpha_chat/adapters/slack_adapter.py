from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from alpha_core.schemas.app_context import AppContext

if TYPE_CHECKING:
    from litellm.types.llms.openai import AllMessageValues

from alpha_chat.clients.slack_client import SlackClient
from alpha_chat.log import logger
from alpha_chat.schemas.slack import SlackAction, SlackCommand

_MAX_HISTORY_TURNS = 10  # kept per conversation; 10 turns = 20 messages

_TOOL_STATUS: dict[str, str] = {
    "web_search": "is searching the web...",
    "summarise_url": "is reading the page...",
    "get_current_datetime": "is checking the time...",
}


class SlackAdapter:
    """Bridges inbound Slack events/commands/actions to an Agent and replies via SlackClient."""

    def __init__(
        self,
        *,
        agent: Any,
        context: AppContext,
        slack_client: SlackClient,
    ) -> None:
        self._agent = agent
        self._context = context
        self._slack_client = slack_client
        self._history: dict[str, list[AllMessageValues]] = {}

    @property
    def signing_secret(self) -> str:
        return self._slack_client.signing_secret

    def _conversation_key(self, event: dict[str, Any]) -> str:
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts")
        return f"{channel}:{thread_ts}" if thread_ts else channel

    async def handle_event(self, event: dict[str, Any]) -> None:
        text = event.get("text", "")
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        if not text or not channel or not thread_ts:
            return

        key = self._conversation_key(event)
        history = self._history.get(key, [])

        logger.info(f"SlackAdapter handling message event in channel={channel}")

        await self._set_status(channel, thread_ts, "is thinking...")

        async def _on_tool_start(tool_name: str) -> None:
            status = _TOOL_STATUS.get(tool_name, f"is calling {tool_name}...")
            await self._set_status(channel, thread_ts, status)

        try:
            response = await self._agent.generate_async(
                text, self._context, history=history, on_tool_start=_on_tool_start
            )
        except Exception as exc:
            logger.error(f"Agent error in channel={channel}: {exc}")
            await self._set_status(channel, thread_ts, "")
            await self._slack_client.send_message(
                channel,
                "Sorry, I ran into an error. Please try again.",
                thread_ts=thread_ts,
            )
            return

        updated = history + cast(
            "list[AllMessageValues]",
            [
                {"role": "user", "content": text},
                {"role": "assistant", "content": response},
            ],
        )
        self._history[key] = updated[-(2 * _MAX_HISTORY_TURNS) :]

        await self._slack_client.send_message(channel, response, thread_ts=thread_ts)

    async def _set_status(self, channel: str, thread_ts: str, status: str) -> None:
        try:
            await self._slack_client.set_status(channel, thread_ts, status)
        except Exception as exc:
            logger.debug(f"set_status failed (non-fatal): {exc}")

    async def handle_command(self, command: SlackCommand) -> None:
        text = command.text or command.command
        logger.info(f"SlackAdapter handling command={command.command}")
        response = await self._agent.generate_async(text, self._context)
        await self._slack_client.ack_slash_command(command.response_url, response)

    async def handle_action(self, action: SlackAction) -> None:
        action_values = " ".join(
            str(a.get("value", a.get("action_id", ""))) for a in action.actions
        )
        text = f"Action triggered: {action_values}"
        logger.info(f"SlackAdapter handling action type={action.type}")
        response = await self._agent.generate_async(text, self._context)
        if action.response_url:
            await self._slack_client.ack_slash_command(action.response_url, response)


__all__ = ["SlackAdapter"]
