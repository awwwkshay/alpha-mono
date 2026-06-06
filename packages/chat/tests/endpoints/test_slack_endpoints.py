from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from alpha_chat.endpoints.slack.actions import build_actions_router
from alpha_chat.endpoints.slack.commands import build_commands_router


def _make_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.signing_secret = "secret"
    adapter.handle_command = AsyncMock()
    adapter.handle_action = AsyncMock()
    return adapter


def test_slack_commands_acknowledge_immediately() -> None:
    adapter = _make_adapter()
    app = FastAPI()
    app.include_router(build_commands_router(adapter))
    client = TestClient(app)

    with patch(
        "alpha_chat.endpoints.slack._utils.SignatureVerifier.is_valid",
        return_value=True,
    ):
        response = client.post(
            "/commands",
            data={
                "command": "/ask",
                "text": "hello",
                "user_id": "U123",
                "channel_id": "C123",
                "response_url": "https://example.com/response",
                "trigger_id": "trigger-1",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"response_type": "in_channel", "text": "Processing..."}
    adapter.handle_command.assert_awaited_once()


def test_slack_actions_acknowledge_immediately() -> None:
    adapter = _make_adapter()
    app = FastAPI()
    app.include_router(build_actions_router(adapter))
    client = TestClient(app)

    with patch(
        "alpha_chat.endpoints.slack._utils.SignatureVerifier.is_valid",
        return_value=True,
    ):
        response = client.post(
            "/actions",
            data={
                "payload": json.dumps(
                    {
                        "type": "block_actions",
                        "actions": [{"action_id": "approve", "value": "yes"}],
                        "user": {"id": "U123"},
                        "trigger_id": "trigger-1",
                        "response_url": "https://example.com/response",
                    }
                )
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    adapter.handle_action.assert_awaited_once()
