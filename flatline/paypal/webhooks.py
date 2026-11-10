"""PayPal webhook signature verification and event normalization."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from flatline.config import Settings, settings

VERIFY_PATH = "/v1/notifications/verify-webhook-signature"

KNOWN_EVENT_TYPES = frozenset(
    {
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.REFUNDED",
        "CHECKOUT.ORDER.APPROVED",
        "BILLING.SUBSCRIPTION.ACTIVATED",
        "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
        "BILLING.SUBSCRIPTION.SUSPENDED",
        "BILLING.SUBSCRIPTION.CANCELLED",
        "CUSTOMER.DISPUTE.CREATED",
        # Confirm a recovery: a paid payment link, a renewal that went through.
        "INVOICING.INVOICE.PAID",
        "PAYMENT.SALE.COMPLETED",
    }
)

HEADER_MAP = {
    "paypal-auth-algo": "auth_algo",
    "paypal-cert-url": "cert_url",
    "paypal-transmission-id": "transmission_id",
    "paypal-transmission-sig": "transmission_sig",
    "paypal-transmission-time": "transmission_time",
}


def _header(headers: dict[str, str], name: str) -> str:
    lower = {k.lower(): v for k, v in headers.items()}
    return lower.get(name, "")


def verification_payload(
    headers: dict[str, str], event: dict[str, Any], webhook_id: str
) -> dict[str, Any]:
    body: dict[str, Any] = {"webhook_id": webhook_id, "webhook_event": event}
    for header_name, field in HEADER_MAP.items():
        value = _header(headers, header_name)
        if value:
            body[field] = value
    return body


async def verify_signature(
    headers: dict[str, str],
    event: dict[str, Any],
    *,
    cfg: Settings | None = None,
    client: httpx.AsyncClient | None = None,
    access_token: str = "",
) -> bool:
    """Verify via PayPal's sandbox verify-webhook-signature API.

    In MOCK mode verification is skipped and the event is treated as unverified
    unless the caller marks it synthetic.
    """
    cfg = cfg or settings()
    if cfg.is_mock_paypal:
        return False
    if not cfg.paypal_webhook_id:
        raise RuntimeError("PAYPAL_WEBHOOK_ID is required to verify sandbox webhooks")
    if not cfg.paypal_api_base:
        raise RuntimeError("sandbox host missing")
    payload = verification_payload(headers, event, cfg.paypal_webhook_id)
    close = False
    http = client
    if http is None:
        http = httpx.AsyncClient(timeout=20)
        close = True
    try:
        resp = await http.post(
            f"{cfg.paypal_api_base}{VERIFY_PATH}",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    finally:
        if close:
            await http.aclose()
    return str(data.get("verification_status", "")).upper() == "SUCCESS"


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _amount_from(resource: dict[str, Any]) -> tuple[Decimal | None, str | None]:
    for key in ("amount", "amount_with_breakdown", "gross_amount"):
        block = resource.get(key)
        if isinstance(block, dict):
            raw = block.get("value") or block.get("total")
            currency = block.get("currency_code") or block.get("currency")
            if raw is not None:
                try:
                    return Decimal(str(raw)), str(currency) if currency else None
                except Exception:
                    return None, str(currency) if currency else None
    billing = resource.get("billing_info") or {}
    last_fail = billing.get("last_failed_payment") or {}
    if last_fail.get("amount"):
        return _amount_from(last_fail)
    return None, None


def normalize_event(
    raw: dict[str, Any], *, synthetic: bool = False, verified: bool = False
) -> dict[str, Any]:
    """Flatten a PayPal webhook (or similar) into the events-table shape."""
    raw_resource = raw.get("resource")
    resource: dict[str, Any] = raw_resource if isinstance(raw_resource, dict) else {}
    event_type = str(raw.get("event_type") or raw.get("type") or "UNKNOWN")
    amount, currency = _amount_from(resource)

    supplementary = resource.get("supplementary_data") or {}
    related = supplementary.get("related_ids") or {}

    product_id = (
        resource.get("custom_id")
        or resource.get("custom")
        or (resource.get("purchase_units") or [{}])[0].get("custom_id")
        if isinstance(resource.get("purchase_units"), list) and resource.get("purchase_units")
        else resource.get("custom_id")
    )
    if isinstance(raw.get("product_id"), str):
        product_id = raw["product_id"]

    plan_id = resource.get("plan_id") or raw.get("plan_id")
    subscription_id = None
    if event_type.startswith("BILLING.SUBSCRIPTION"):
        subscription_id = resource.get("id") or raw.get("subscription_id")
    else:
        subscription_id = resource.get("billing_agreement_id") or raw.get("subscription_id")

    resource_id = str(
        resource.get("id")
        or related.get("order_id")
        or raw.get("resource_id")
        or raw.get("id")
        or ""
    )
    buyer = (
        (resource.get("payer") or {}).get("payer_id")
        or (resource.get("subscriber") or {}).get("payer_id")
        or raw.get("buyer_ref")
    )
    error_code = (
        resource.get("status_details", {}).get("reason")
        if isinstance(resource.get("status_details"), dict)
        else None
    ) or raw.get("error_code")

    paypal_event_id = raw.get("id")

    return {
        "source": "synthetic" if synthetic else "paypal_webhook",
        "event_type": event_type,
        "occurred_at": _parse_time(raw.get("create_time") or raw.get("occurred_at")),
        "resource_id": resource_id or None,
        "amount": amount,
        "currency": currency or raw.get("currency"),
        "product_id": product_id,
        "plan_id": plan_id,
        "subscription_id": subscription_id,
        "buyer_ref": buyer,
        "error_code": error_code,
        "payload": raw,
        "synthetic": synthetic,
        "verified": verified,
        "paypal_event_id": paypal_event_id,
        "known": event_type in KNOWN_EVENT_TYPES,
    }
