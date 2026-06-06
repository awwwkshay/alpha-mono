from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from clay_chat.adapters.slack_adapter import SlackAdapter
from clay_core.schemas.app_config import AppConfig
from clay_core.schemas.app_context import AppContext


def _make_adapter() -> SlackAdapter:
    agent = MagicMock()
    slack_client = MagicMock()
    slack_client.signing_secret = "secret"
    return SlackAdapter(
        agent=agent,
        context=AppContext(config=MagicMock(spec=AppConfig)),
        slack_client=slack_client,
    )


def test_conversation_key_groups_top_level_messages_by_channel() -> None:
    adapter = _make_adapter()

    key = adapter._conversation_key({"channel": "C123", "ts": "12345.678"})

    assert key == "C123"


def test_conversation_key_scopes_thread_replies_by_thread_ts() -> None:
    adapter = _make_adapter()

    key = adapter._conversation_key(
        {"channel": "C123", "ts": "12345.679", "thread_ts": "12345.678"}
    )

    assert key == "C123:12345.678"


async def test_handle_command_posts_error_response_on_failure() -> None:
    adapter = _make_adapter()
    adapter._agent.generate_async = AsyncMock(side_effect=RuntimeError("boom"))
    ack_mock = AsyncMock()

    with patch.object(adapter._slack_client, "ack_slash_command", ack_mock):
        await adapter.handle_command(
            MagicMock(
                command="/ask",
                text="hello",
                user_id="U123",
                channel_id="C123",
                response_url="https://example.com/response",
            )
        )

    ack_mock.assert_awaited_once_with(
        "https://example.com/response",
        "Sorry, I ran into an error. Please try again.",
    )
