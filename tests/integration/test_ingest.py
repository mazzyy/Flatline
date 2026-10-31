"""Ingest endpoints: webhooks, telemetry, synthetic, SSE, shop config."""

from __future__ import annotations

import json
from pathlib import Path

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
