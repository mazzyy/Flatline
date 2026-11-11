"""Ingest endpoints: webhooks, telemetry, synthetic, SSE, shop config."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flatline.db.session import create_schema, ensure_default_config, get_sessionmaker, reset_engine
from flatline.ingest.app import create_app

WEBHOOKS = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures" / "paypal" / "webhooks.json").read_text()
)


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/ingest.db")
    monkeypatch.setenv("INJECT_TOKEN", "test-inject")
    monkeypatch.setenv("DASHBOARD_PASSCODE", "demo-judge")
    reset_engine()
    create_schema()
    db = get_sessionmaker()()
    try:
        ensure_default_config(db)
    finally:
        db.close()
    app = create_app()
    with TestClient(app) as c:
        yield c
    reset_engine()


def test_healthz(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["paypal_environment"] == "MOCK"


def test_webhook_idempotent(client: TestClient) -> None:
    payload = WEBHOOKS["PAYMENT.CAPTURE.COMPLETED"]
    a = client.post("/webhooks/paypal", json=payload)
    b = client.post("/webhooks/paypal", json=payload)
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    events = client.get("/api/events").json()
    assert events["lastRow"] == 1


def test_telemetry_and_synthetic(client: TestClient) -> None:
    tel = client.post(
        "/api/telemetry",
        json={
            "type": "checkout.capture",
            "ok": False,
            "error_code": "INSTRUMENT_DECLINED",
            "order_id": "ORD-1",
            "amount": "18.00",
            "currency": "USD",
            "product_id": "house-blend",
        },
    )
    assert tel.status_code == 200
    denied = client.post(
        "/api/synthetic/events",
        headers={"X-Inject-Token": "test-inject"},
        json=WEBHOOKS["PAYMENT.CAPTURE.DENIED"],
    )
    assert denied.status_code == 200
    events = client.get("/api/events").json()["rows"]
    synth = [e for e in events if e["synthetic"]]
    assert synth
    assert synth[0]["synthetic"] is True


def test_synthetic_requires_token(client: TestClient) -> None:
    res = client.post("/api/synthetic/events", json={"event_type": "x"})
    assert res.status_code == 401


def test_shop_config_and_chaos(client: TestClient) -> None:
    cfg = client.get("/api/shop/config").json()
    assert cfg["currency"] == "USD"
    res = client.post(
        "/api/chaos",
        headers={"X-Passcode": "demo-judge", "X-Inject-Token": "test-inject"},
        json={"chaos": {"mock_response": "INSTRUMENT_DECLINED"}},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["injected"]) >= 5
    assert body["incidents"]
    cfg = client.get("/api/shop/config").json()
    assert cfg["chaos"]["mock_response"] == "INSTRUMENT_DECLINED"
    incidents = client.get("/api/incidents").json()["items"]
    assert any(i["playbook"] == "checkout_failure_spike" for i in incidents)


def test_chaos_bad_currency_and_webhook_break(client: TestClient) -> None:
    res = client.post(
        "/api/chaos",
        headers={"X-Passcode": "demo-judge", "X-Inject-Token": "test-inject"},
        json={"chaos": {"bad_currency": True}, "note": "bad currency"},
    )
    assert res.status_code == 200
    assert res.json()["injected"]
    cfg = client.get("/api/shop/config").json()
    assert cfg["currency"] == "EUR"
    broken = client.post(
        "/api/chaos",
        headers={"X-Passcode": "demo-judge", "X-Inject-Token": "test-inject"},
        json={"chaos": {"webhook_broken": True}},
    )
    assert broken.status_code == 200
    assert broken.json()["injected"] == []
    hook = client.post("/webhooks/paypal", json=WEBHOOKS["PAYMENT.CAPTURE.COMPLETED"])
    assert hook.status_code == 500


def test_sse_emits_on_ingest(client: TestClient) -> None:
    with client.stream("GET", "/api/stream") as stream:
        # First line(s) are the ready event; then ingest one telemetry row.
        # TestClient stream needs us to consume incrementally.
        client.post(
            "/api/telemetry",
            json={"type": "checkout.create", "ok": True, "amount": "18.00", "currency": "USD"},
        )
        buf = ""
        for chunk in stream.iter_text():
            buf += chunk
            if "event.ingested" in buf or "ready" in buf:
                break
        assert "ready" in buf or "event.ingested" in buf


def test_audit_written(client: TestClient) -> None:
    client.post(
        "/api/telemetry",
        json={"type": "checkout.capture", "ok": True, "amount": "18.00"},
    )
    audit = client.get("/api/audit").json()
    assert audit["lastRow"] >= 1


def test_recovery_over_the_api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Break checkout, approve the fix, approve the recovery, let customers pay."""
    import asyncio

    from flatline.config import reset_settings
    from flatline.db.models import Incident
    from flatline.loop import process_incident

    monkeypatch.setenv("VERIFY_MINUTES", "0")  # the metric is quiet the moment we look
    reset_settings()
    auth = {"X-Passcode": "demo-judge", "X-Inject-Token": "test-inject"}
    chaos = client.post("/api/chaos", headers=auth, json={"chaos": {"bad_currency": True}})
    incident_id = chaos.json()["incidents"][0]

    db = get_sessionmaker()()  # the agents worker's part
    try:
        asyncio.run(process_incident(db, db.get(Incident, UUID(incident_id))))
        db.commit()
    finally:
        db.close()

    def proposals() -> dict[str, dict]:
        body = client.get(f"/api/incidents/{incident_id}").json()
        return {p["action"]: p for p in body["proposals"]}

    assert "recovery.payment_links.send" not in proposals()  # not before the fix is verified
    rollback = proposals()["shop.config.rollback"]
    assert client.post(f"/api/proposals/{rollback['id']}/approve", headers=auth).status_code == 200
    body = client.get(f"/api/incidents/{incident_id}").json()
    assert body["status"] == "resolved"
    assert body["money"]["impact"] == "108.00" and body["money"]["requested"] == "0.00"
    assert [s["node"] for s in body["steps"]][-1] == "recovery"

    recovery = proposals()["recovery.payment_links.send"]
    assert (recovery["tier"], recovery["status"]) == ("approval", "pending")
    sent = client.post(f"/api/proposals/{recovery['id']}/approve", headers=auth).json()
    assert sent["status"] == "executed"
    body = client.get(f"/api/incidents/{incident_id}").json()
    assert body["status"] == "resolved"  # approving a recovery does not reopen or re-verify
    assert [s["node"] for s in body["steps"]].count("verifier") == 1
    assert body["money"]["requested"] == "108.00"

    assert client.post("/api/synthetic/recovery-payments").status_code == 401
    paid = client.post("/api/synthetic/recovery-payments", headers=auth).json()
    assert len(paid["injected"]) == 4
    totals = client.get("/api/money").json()
    assert (totals["impact"], totals["requested"], totals["recovered"]) == (
        "108.00",
        "108.00",
        "72.00",
    )
    assert totals["simulated"] is True  # mock PayPal, synthetic payments


def test_policy_catalog_lists_the_money_limits(client: TestClient) -> None:
    body = client.get("/api/policy/catalog").json()
    limits = {row["key"]: row["value"] for row in body["limits"]}
    assert limits["AUTO_REFUND_MAX"] == 0  # off unless the merchant turns it on
    assert limits["REFUND_APPROVAL_MAX"] == 50 and limits["DAILY_REFUND_BUDGET"] == 200
    recovery = next(i for i in body["items"] if i["key"] == "recovery.payment_links.send")
    assert recovery["tier"] == "approval" and recovery["planner_only"] is True


def test_site_endpoint_and_shop_proxy_are_off_by_default(client: TestClient) -> None:
    site = client.get("/api/site").json()
    assert site == {"shop_url": "", "paypal_environment": "MOCK", "llm_mode": "mock"}
    # Without SHOP_INTERNAL_URL the API does not pass anything on.
    assert client.get("/shop/").status_code == 404
    assert client.post("/shop/api/demo-pay", json={}).status_code == 404


def test_shop_proxy_passes_requests_on_to_the_configured_shop_only(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx

    from flatline.config import reset_settings

    seen: list[str] = []

    class FakeClient:
        def __init__(self, **_: object) -> None: ...
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: object) -> None: ...
        async def request(self, method: str, url: str, **_: object) -> httpx.Response:
            seen.append(f"{method} {url}")
            return httpx.Response(200, text="<h1>Lumen</h1>", headers={"content-type": "text/html"})

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setenv("SHOP_INTERNAL_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("SHOP_PUBLIC_URL", "/shop")
    reset_settings()
    page = client.get("/shop/checkout/house-blend")
    assert page.status_code == 200 and "Lumen" in page.text
    # A path can not steer the request to another host.
    client.get("/shop/http://example.com/x")
    assert seen[0] == "GET http://127.0.0.1:3000/shop/checkout/house-blend"
    assert all(
        url.startswith(("GET http://127.0.0.1:3000/shop", "POST http://127.0.0.1:3000/shop"))
        for url in seen
    )
    assert client.get("/api/site").json()["shop_url"] == "/shop"


def test_a_no_login_demo_checkout_is_stored_as_simulated(client: TestClient) -> None:
    body = {
        "type": "checkout.capture",
        "ok": False,
        "error_code": "CURRENCY_MISMATCH",
        "order_id": "DEMO-1",
        "amount": "18.00",
    }
    client.post("/api/telemetry", json={**body, "simulated": True})
    client.post("/api/telemetry", json={**body, "order_id": "ORD-REAL"})
    rows = {r["resource_id"]: r["synthetic"] for r in client.get("/api/events").json()["rows"]}
    assert rows == {"DEMO-1": True, "ORD-REAL": False}


def test_a_simulated_outage_ends_on_its_own(client: TestClient, monkeypatch) -> None:
    from flatline.ingest import app as app_module

    monkeypatch.setattr(app_module, "OUTAGE_SECONDS", 0)
    res = client.post(
        "/api/chaos",
        headers={"X-Passcode": "demo-judge", "X-Inject-Token": "test-inject"},
        json={"chaos": {"mock_response": "INSTRUMENT_DECLINED"}},
    )
    assert res.status_code == 200
    cfg = client.get("/api/shop/config").json()
    assert "mock_response" not in cfg["chaos"]
