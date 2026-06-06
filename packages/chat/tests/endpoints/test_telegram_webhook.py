from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from alpha_chat.endpoints.telegram.webhook import build_telegram_router


def _make_app(secret_token: str | None = "secret-token") -> tuple[TestClient, MagicMock]:
    adapter = MagicMock()
    adapter.handle_update = AsyncMock()
    app = FastAPI()
    app.include_router(build_telegram_router(adapter, secret_token=secret_token))
    return TestClient(app), adapter


def _telegram_payload() -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "date": 1,
            "chat": {"id": 100, "type": "private"},
            "from": {"id": 200, "first_name": "Ada", "is_bot": False},
            "text": "hello",
        },
    }


def test_telegram_webhook_rejects_invalid_secret() -> None:
    client, adapter = _make_app()

    response = client.post("/webhook", json=_telegram_payload())

    assert response.status_code == 401
    adapter.handle_update.assert_not_called()


def test_telegram_webhook_accepts_valid_secret() -> None:
    client, adapter = _make_app()

    response = client.post(
        "/webhook",
        json=_telegram_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    adapter.handle_update.assert_awaited_once()


def test_telegram_webhook_accepts_any_request_when_no_secret_configured() -> None:
    client, adapter = _make_app(secret_token=None)

    response = client.post("/webhook", json=_telegram_payload())

    assert response.status_code == 200
    adapter.handle_update.assert_awaited_once()
