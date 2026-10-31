"""Notify sink never treats comments or empty values as webhook URLs."""

from __future__ import annotations

from warden.config import reset_settings
from warden.notify.sinks import send_alert


def test_blank_and_comment_urls_log_only(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "# Slack/Telegram/ntfy webhook for alerts")
    reset_settings()
    assert send_alert("hello") == {"ok": True, "channel": "log"}
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "")
    reset_settings()
    assert send_alert("hello") == {"ok": True, "channel": "log"}
