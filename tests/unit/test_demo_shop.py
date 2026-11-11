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


def test_shop_offers_checkout_without_a_paypal_login() -> None:
    js = (ROOT / "public" / "shop.js").read_text()
    server = (ROOT / "server.js").read_text()
    assert "Pay without a PayPal login (demo)" in js
    assert "/api/demo-pay" in js and '"/api/demo-pay"' in server
    # The demo checkout never calls PayPal and always says it is simulated.
    handler = server.split('app.post("/api/demo-pay"')[1].split("app.post(")[0]
    assert "simulated: true" in handler
    assert "API_BASE" not in handler and "sandboxToken" not in handler


def test_shop_can_be_served_under_a_path() -> None:
    js = (ROOT / "public" / "shop.js").read_text()
    server = (ROOT / "server.js").read_text()
    assert "SHOP_BASE_PATH" in server and "window.__BASE__" in server
    # Every link and request in the client goes through BASE.
    assert 'fetch("/' not in js and "fetch(`/" not in js and 'href="/' not in js
