"""Webhook verification + normalization."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from flatline.config import Settings
from flatline.paypal.webhooks import (
    KNOWN_EVENT_TYPES,
    normalize_event,
    verification_payload,
    verify_signature,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "paypal" / "webhooks.json"


def _webhooks() -> dict:
    return json.loads(FIXTURES.read_text())


def test_normalize_capture_completed() -> None:
    event = normalize_event(_webhooks()["PAYMENT.CAPTURE.COMPLETED"], verified=True)
    assert event["event_type"] == "PAYMENT.CAPTURE.COMPLETED"
    assert event["known"] is True
    assert event["product_id"] == "house-blend"
    assert str(event["amount"]) == "18.00"
    assert event["currency"] == "USD"
    assert event["resource_id"] == "CAP-OK-1"
    assert event["buyer_ref"] == "BUYER-1"
    assert event["paypal_event_id"] == "WH-CAPTURE-OK-1"
    assert event["verified"] is True
    assert event["synthetic"] is False


def test_normalize_denied_extracts_error_code() -> None:
    event = normalize_event(_webhooks()["PAYMENT.CAPTURE.DENIED"])
    assert event["error_code"] == "INSTRUMENT_DECLINED"


def test_normalize_refund_and_renewal() -> None:
    refund = normalize_event(_webhooks()["PAYMENT.CAPTURE.REFUNDED"])
    assert refund["product_id"] == "ethiopia-yirgacheffe"
    fail = normalize_event(_webhooks()["BILLING.SUBSCRIPTION.PAYMENT.FAILED"])
    assert fail["plan_id"] == "P-COFFEECLUB"
    assert fail["subscription_id"] == "I-COFFEECLUB-1"
    assert str(fail["amount"]) == "14.00"


def test_unknown_event_is_stored_but_marked_unknown() -> None:
    event = normalize_event({"id": "WH-X", "event_type": "SOME.NEW.TYPE", "resource": {}})
    assert event["known"] is False
    assert event["event_type"] == "SOME.NEW.TYPE"


def test_synthetic_flag() -> None:
    event = normalize_event(_webhooks()["PAYMENT.CAPTURE.COMPLETED"], synthetic=True)
    assert event["source"] == "synthetic"
    assert event["synthetic"] is True


def test_verification_payload_maps_headers() -> None:
    payload = verification_payload(
        {
            "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            "PAYPAL-CERT-URL": "https://api.sandbox.paypal.com/cert.pem",
            "PAYPAL-TRANSMISSION-ID": "tid",
            "PAYPAL-TRANSMISSION-SIG": "sig",
            "PAYPAL-TRANSMISSION-TIME": "2026-10-31T16:00:00Z",
        },
        {"id": "WH-1"},
        "WHID-1",
    )
    assert payload["auth_algo"] == "SHA256withRSA"
    assert payload["webhook_id"] == "WHID-1"
    assert payload["transmission_id"] == "tid"


@pytest.mark.asyncio
async def test_verify_skipped_in_mock() -> None:
    cfg = Settings(PAYPAL_ENVIRONMENT="MOCK")
    ok = await verify_signature({}, {"id": "WH-1"}, cfg=cfg)
    assert ok is False


@pytest.mark.asyncio
async def test_verify_calls_sandbox_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "WHID-1")
    cfg = Settings()

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api-m.sandbox.paypal.com" in str(request.url)
        assert str(request.url).endswith("/v1/notifications/verify-webhook-signature")
        assert "paypal.com/v1" in str(request.url) or "sandbox" in str(request.url)
        assert "api-m.paypal.com" not in str(request.url).replace("api-m.sandbox.paypal.com", "")
        return httpx.Response(200, json={"verification_status": "SUCCESS"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await verify_signature(
            {"paypal-transmission-id": "tid"},
            {"id": "WH-1"},
            cfg=cfg,
            client=client,
            access_token="tok",
        )
    assert ok is True


def test_known_types_match_spec() -> None:
    expected = {
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.REFUNDED",
        "CHECKOUT.ORDER.APPROVED",
        "BILLING.SUBSCRIPTION.ACTIVATED",
        "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
        "BILLING.SUBSCRIPTION.SUSPENDED",
        "BILLING.SUBSCRIPTION.CANCELLED",
        "CUSTOMER.DISPUTE.CREATED",
    }
    assert expected <= KNOWN_EVENT_TYPES
