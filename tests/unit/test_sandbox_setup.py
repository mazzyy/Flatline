"""scripts/sandbox_setup.py: requests it sends, against a fake PayPal."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from flatline.config import Settings

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sandbox_setup.py"
spec = importlib.util.spec_from_file_location("sandbox_setup", SCRIPT)
assert spec and spec.loader
sandbox_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox_setup)


def _cfg(**extra: str) -> Settings:
    return Settings(
        PAYPAL_ENVIRONMENT="SANDBOX",
        PAYPAL_CLIENT_ID="id",
        PAYPAL_CLIENT_SECRET="secret",
        **extra,
    )


def _fake_paypal(calls: list[httpx.Request], existing_plan: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api-m.sandbox.paypal.com"
        path = request.url.path
        if path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if path == "/v1/catalogs/products":
            return httpx.Response(201, json={"id": "PROD-1"})
        if path == "/v1/billing/plans" and request.method == "POST":
            return httpx.Response(201, json={"id": "P-NEW"})
        if path.startswith("/v1/billing/plans/"):
            if existing_plan:
                return httpx.Response(200, json={"id": "P-OLD", "product_id": "PROD-OLD"})
            return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND"})
        return httpx.Response(500)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_creates_product_then_monthly_plan() -> None:
    calls: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=_fake_paypal(calls)) as client:
        product_id, plan_id, created = await sandbox_setup.setup(_cfg(), client)

    assert (product_id, plan_id, created) == ("PROD-1", "P-NEW", True)
    assert [c.url.path for c in calls] == [
        "/v1/oauth2/token",
        "/v1/catalogs/products",
        "/v1/billing/plans",
    ]
    plan = json.loads(calls[2].content)
    assert plan["product_id"] == "PROD-1"
    cycle = plan["billing_cycles"][0]
    assert cycle["frequency"] == {"interval_unit": "MONTH", "interval_count": 1}
    assert cycle["pricing_scheme"]["fixed_price"] == {"value": "14.00", "currency_code": "USD"}
    assert calls[2].headers["Authorization"] == "Bearer tok"


@pytest.mark.asyncio
async def test_existing_plan_is_reused() -> None:
    calls: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=_fake_paypal(calls, existing_plan=True)) as client:
        result = await sandbox_setup.setup(_cfg(PAYPAL_SANDBOX_PLAN_ID="P-OLD"), client)

    assert result == ("PROD-OLD", "P-OLD", False)
    assert all(c.method != "POST" or c.url.path == "/v1/oauth2/token" for c in calls)


@pytest.mark.asyncio
async def test_missing_plan_id_is_recreated_on_known_product() -> None:
    calls: list[httpx.Request] = []
    cfg = _cfg(PAYPAL_SANDBOX_PLAN_ID="P-GONE", PAYPAL_SANDBOX_PRODUCT_ID="PROD-KEEP")
    async with httpx.AsyncClient(transport=_fake_paypal(calls)) as client:
        result = await sandbox_setup.setup(cfg, client)

    assert result == ("PROD-KEEP", "P-NEW", True)
    assert "/v1/catalogs/products" not in [c.url.path for c in calls]
