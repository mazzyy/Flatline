"""Synthetic fault payloads used by the chaos panel and inject script."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


def _at(offset_seconds: float) -> str:
    """Event times spread like real traffic instead of one shared timestamp."""
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


def _pp_id(n: int = 17) -> str:
    """An id shaped like PayPal's. Injected events carry synthetic=True in the store;
    the agents are not told which events were injected, like any fault injection test."""
    return uuid4().hex.upper()[:n]


def checkout_failures(code: str, n: int = 6) -> list[dict[str, Any]]:
    return [
        {
            "id": f"WH-{_pp_id()}-{_pp_id()}",
            "event_type": "checkout.capture",
            "create_time": _at(0),
            "error_code": code,
            "product_id": "house-blend",
            "amount": "18.00",
            "currency": "EUR" if code == "CURRENCY_MISMATCH" else "USD",
            "buyer_ref": f"B{i}",
            "resource_id": _pp_id(),
        }
        for i in range(n)
    ]


def refund_wave(n: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": f"WH-{_pp_id()}-{_pp_id()}",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "create_time": _at(-60 * (2 + 9 * i)),  # over the last 40 minutes
            "product_id": "ethiopia-yirgacheffe",
            "resource": {
                "id": _pp_id(),
                "amount": {"currency_code": "USD", "value": "22.00"},
                "custom_id": "ethiopia-yirgacheffe",
            },
        }
        for i in range(n)
    ]


def renewal_failures(n: int = 4) -> list[dict[str, Any]]:
    from flatline.config import settings

    # The real sandbox Coffee Club plan when it exists, so the Diagnostician reads it.
    plan = settings().paypal_sandbox_plan_id or "P-COFFEECLUB"
    return [
        {
            "id": f"WH-{_pp_id()}-{_pp_id()}",
            "event_type": "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
            "create_time": _at(-60 * (3 + 13 * i)),  # over the last 45 minutes
            "plan_id": plan,
            "resource": {
                "id": f"I-{_pp_id(12)}",
                "plan_id": plan,
                "billing_info": {
                    "last_failed_payment": {"amount": {"currency_code": "USD", "value": "14.00"}}
                },
            },
        }
        for i in range(n)
    ]
