"""Mock gateway, token manager, and read-only wrapper."""

from __future__ import annotations

import time

import httpx
import pytest

from flatline.config import Settings
from flatline.paypal.factory import build_gateway
from flatline.paypal.gateway import ReadOnlyGateway, WriteAccessError
from flatline.paypal.mock_gateway import MockGateway
from flatline.paypal.sandbox_gateway import SandboxGateway
from flatline.paypal.token import TokenManager


@pytest.mark.asyncio
async def test_mock_gateway_reads_fixtures() -> None:
    gw = MockGateway()
    order = await gw.get_order("ORDER-HOUSE-1")
    assert order["status"] == "COMPLETED"
    plan = await gw.get_plan("P-COFFEECLUB")
    assert plan["name"] == "Coffee Club"
    txs = await gw.list_transactions(product_id="house-blend")
    assert len(txs) == 1


@pytest.mark.asyncio
async def test_mock_gateway_writes_are_recorded() -> None:
    gw = MockGateway()
    refund = await gw.create_refund("CAP-OK-1", "5.00", "USD")
    assert refund["status"] == "COMPLETED"
    assert gw.writes[0]["op"] == "create_refund"
    cap = await gw.capture_subscription_outstanding("I-COFFEECLUB-1", "retry")
    assert cap["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_readonly_wrapper_blocks_writes() -> None:
    ro = ReadOnlyGateway(MockGateway())
    order = await ro.get_order("ORDER-HOUSE-1")
    assert order["id"] == "ORDER-HOUSE-1"
    with pytest.raises(WriteAccessError):
        await ro.create_refund("CAP-OK-1", "1.00", "USD")  # type: ignore[attr-defined]


def test_factory_returns_mock_in_mock_mode() -> None:
    gw = build_gateway(Settings(PAYPAL_ENVIRONMENT="MOCK"))
    assert isinstance(gw, MockGateway)


def test_sandbox_gateway_refuses_mock() -> None:
    with pytest.raises(RuntimeError, match="SANDBOX"):
        SandboxGateway(Settings(PAYPAL_ENVIRONMENT="MOCK"))


@pytest.mark.asyncio
async def test_token_manager_caches_and_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    cfg = Settings()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert str(request.url) == "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        return httpx.Response(
            200,
            json={"access_token": f"tok-{calls['n']}", "expires_in": 28800, "token_type": "Bearer"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        tm = TokenManager(cfg, client=client)
        a = await tm.get_token()
        b = await tm.get_token()
        assert a == b == "tok-1"
        assert tm._token is not None
        tm._token.expires_at = time.time()  # force refresh
        c = await tm.get_token()
        assert c == "tok-2"


def test_no_live_host_in_paypal_package() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "flatline" / "paypal"
    for path in root.glob("*.py"):
        text = path.read_text()
        # Allow the sandbox hostname; forbid the live hostname.
        stripped = text.replace("api-m.sandbox.paypal.com", "")
        stripped = stripped.replace("api.sandbox.paypal.com", "")
        assert "api-m.paypal.com" not in stripped, path.name
        assert "api.paypal.com" not in stripped or "sandbox" in text
