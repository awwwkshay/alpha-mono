from __future__ import annotations

from unittest.mock import MagicMock, patch


from clay_chat.clients.slack_client import SlackClient


def _make_client() -> SlackClient:
    return SlackClient(token="xoxb-test", signing_secret="secret123")


async def test_send_message_calls_chat_post_message():
    client = _make_client()
    mock_response = MagicMock()

    with patch.object(
        client._client, "chat_postMessage", return_value=mock_response
    ) as mock_post:
        result = await client.send_message("C123", "Hello")

    mock_post.assert_called_once_with(channel="C123", text="Hello")
    assert result is mock_response


async def test_send_message_includes_thread_ts():
    client = _make_client()

    with patch.object(
        client._client, "chat_postMessage", return_value=MagicMock()
    ) as mock_post:
        await client.send_message("C123", "Reply", thread_ts="12345.67890")

    mock_post.assert_called_once_with(
        channel="C123", text="Reply", thread_ts="12345.67890"
    )


async def test_react_calls_reactions_add():
    client = _make_client()

    with patch.object(
        client._client, "reactions_add", return_value=MagicMock()
    ) as mock_react:
        await client.react("C123", "12345.0", "thumbsup")

    mock_react.assert_called_once_with(
        channel="C123", timestamp="12345.0", name="thumbsup"
    )


async def test_open_modal_calls_views_open():
    client = _make_client()
    view = {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Test"},
        "blocks": [],
    }

    with patch.object(
        client._client, "views_open", return_value=MagicMock()
    ) as mock_open:
        await client.open_modal("trigger_abc", view)

    mock_open.assert_called_once_with(trigger_id="trigger_abc", view=view)


async def test_signing_secret_stored():
    client = _make_client()
    assert client.signing_secret == "secret123"
