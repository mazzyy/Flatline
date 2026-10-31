"""Sandbox guard and mode flags. These must stay green on every milestone."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from flatline.config import SandboxGuardError, Settings


def test_mock_environment_is_accepted() -> None:
    s = Settings(PAYPAL_ENVIRONMENT="MOCK", LLM_MODE="mock")
    assert s.paypal_environment == "MOCK"
    assert s.is_mock_paypal is True
    assert s.is_mock_llm is True
    assert s.paypal_api_base == ""


def test_sandbox_environment_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    monkeypatch.setenv("LLM_MODE", "live")
    s = Settings()
    assert s.paypal_environment == "SANDBOX"
    assert s.is_mock_paypal is False
    assert s.is_mock_llm is False
    assert s.paypal_api_base == "https://api-m.sandbox.paypal.com"


def test_environment_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("LLM_MODE", "MOCK")
    s = Settings()
    assert s.paypal_environment == "SANDBOX"
    assert s.llm_mode == "mock"


@pytest.mark.parametrize("value", ["LIVE", "PRODUCTION", "live", "prod", "", "STAGE"])
def test_live_and_unknown_environments_are_refused(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", value)
    with pytest.raises(SandboxGuardError) as exc:
        Settings()
    assert "MOCK" in str(exc.value)
    assert "SANDBOX" in str(exc.value)
    assert "Live PayPal is impossible" in str(exc.value)


def test_invalid_llm_mode_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "gemini")
    with pytest.raises(ValidationError):
        Settings()


def test_demo_mode_caps_verify_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("VERIFY_MINUTES", "10")
    s = Settings()
    assert s.effective_verify_minutes == 1


def test_no_live_paypal_host_constant() -> None:
    """Refuse to ship a live PayPal host string anywhere in config."""
    import inspect

    source = inspect.getsource(Settings)
    assert "api-m.paypal.com" not in source.replace("api-m.sandbox.paypal.com", "")
    s = Settings()
    # Default test env is MOCK, so the host is empty — never the live host.
    assert s.paypal_api_base in ("", "https://api-m.sandbox.paypal.com")
    assert s.paypal_api_base.replace("sandbox.", "") != "api-m.paypal.com"
