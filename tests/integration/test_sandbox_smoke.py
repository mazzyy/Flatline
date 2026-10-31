"""Optional live sandbox smoke. Skipped without keys."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.sandbox


def test_sandbox_token_and_host() -> None:
    if not os.environ.get("PAYPAL_CLIENT_ID") or not os.environ.get("PAYPAL_CLIENT_SECRET"):
        pytest.skip("no sandbox keys")
    os.environ["PAYPAL_ENVIRONMENT"] = "SANDBOX"
    from warden.config import Settings
    from warden.paypal.token import TokenManager

    cfg = Settings()
    assert "sandbox" in cfg.paypal_api_base
    assert "api-m.paypal.com" not in cfg.paypal_api_base.replace("sandbox.", "")
    # Token fetch is the smoke; we do not call live PayPal from CI.
    assert TokenManager(cfg).token_url.endswith("/v1/oauth2/token")
