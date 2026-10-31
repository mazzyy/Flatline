"""Demo shop source guards. Runtime is exercised in docker / make up."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "demo-shop"


def test_shop_refuses_live_environment() -> None:
    src = (ROOT / "server.js").read_text()
    assert 'PAYPAL_ENV !== "MOCK" && PAYPAL_ENV !== "SANDBOX"' in src
    assert "api-m.sandbox.paypal.com" in src
    assert "api-m.paypal.com" not in src.replace("api-m.sandbox.paypal.com", "")


def test_shop_has_mock_pay_and_v6() -> None:
    js = (ROOT / "public" / "shop.js").read_text()
    assert "Pay (mock)" in js
    assert "web-sdk/v6/core" in js
    assert (ROOT / "Dockerfile").exists()
