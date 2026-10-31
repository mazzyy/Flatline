"""Shared fixtures. Tests always run in MOCK + mock LLM with no secrets."""

from __future__ import annotations

import os

import pytest

from flatline.config import reset_settings

SAFE_ENV = {
    "PAYPAL_ENVIRONMENT": "MOCK",
    "LLM_MODE": "mock",
    "PAYPAL_CLIENT_ID": "",
    "PAYPAL_CLIENT_SECRET": "",
    "AZURE_API_KEY": "",
    "GITHUB_TOKEN": "",
    "DASHBOARD_PASSCODE": "demo-judge",
    "INJECT_TOKEN": "test-inject",
    "DEMO_MODE": "true",
    "VERIFY_MINUTES": "1",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in SAFE_ENV.items():
        monkeypatch.setenv(key, value)
    # Prevent a leftover .env from a sandbox run leaking into tests.
    monkeypatch.chdir(os.path.dirname(__file__) + "/..")
    reset_settings()
    yield
    reset_settings()
