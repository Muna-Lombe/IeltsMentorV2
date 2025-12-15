import json
import types
from unittest.mock import AsyncMock

import pytest

import app as app_module


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    @property
    def is_success(self):
        return 200 <= self.status_code < 300

    @property
    def text(self):
        return json.dumps(self._payload)


@pytest.fixture(autouse=True)
def reset_bot_status(monkeypatch):
    status = app_module.BotStatus()
    monkeypatch.setattr(app_module, "bot_status", status)
    return status


@pytest.fixture(autouse=True)
def mock_bot(monkeypatch):
    monkeypatch.setattr(
        type(app_module.application.bot),
        "get_me",
        AsyncMock(return_value=types.SimpleNamespace(username="mockbot", id=12345)),
    )


def test_initialize_webhook_bot_sets_status(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("DOMAIN_URL", "example.com")

    responses = [
        DummyResponse({"ok": True}),  # deleteWebhook
        DummyResponse({"ok": True, "result": True}),  # setWebhook
    ]
    monkeypatch.setattr(
        app_module,
        "_telegram_api_get",
        AsyncMock(side_effect=responses),
    )

    app_module.create_app("testing")

    assert app_module.bot_status.webhook_url == "https://example.com/webhook"
    assert app_module.bot_status.error is None
    assert app_module.bot_status.telegram_bot_username == "https://t.me/mockbot"


def test_initialize_webhook_bot_records_error_on_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("DOMAIN_URL", "example.com")

    responses = [
        DummyResponse({"ok": True}),  # deleteWebhook
        DummyResponse({"ok": False, "description": "invalid"}),
    ]
    monkeypatch.setattr(
        app_module,
        "_telegram_api_get",
        AsyncMock(side_effect=responses),
    )

    app_module.create_app("testing")

    assert app_module.bot_status.webhook_url is None
    assert app_module.bot_status.error is not None
    assert "Failed to set webhook" in app_module.bot_status.error
