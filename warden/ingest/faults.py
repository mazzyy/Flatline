"""Synthetic fault payloads used by the chaos panel and inject script."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


def checkout_failures(code: str, n: int = 6) -> list[dict[str, Any]]:
    at = _now()
    return [
        {
            "id": f"WH-INJ-{uuid4().hex[:10]}",
            "event_type": "checkout.capture",
            "create_time": at,
            "error_code": code,
            "product_id": "house-blend",
            "amount": "18.00",
            "currency": "EUR" if code == "CURRENCY_MISMATCH" else "USD",
            "buyer_ref": f"B{i}",
            "resource_id": f"ORD-INJ-{i}",
        }
        for i in range(n)
    ]


def refund_wave(n: int = 5) -> list[dict[str, Any]]:
    at = _now()
    return [
        {
            "id": f"WH-INJ-R-{uuid4().hex[:10]}",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "create_time": at,
            "product_id": "ethiopia-yirgacheffe",
            "resource": {
                "id": f"REF-INJ-{i}",
                "amount": {"currency_code": "USD", "value": "22.00"},
                "custom_id": "ethiopia-yirgacheffe",
            },
        }
        for i in range(n)
    ]


def renewal_failures(n: int = 4) -> list[dict[str, Any]]:
    at = _now()
    return [
        {
            "id": f"WH-INJ-S-{uuid4().hex[:10]}",
            "event_type": "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
            "create_time": at,
            "plan_id": "P-COFFEECLUB",
            "resource": {
                "id": f"I-INJ-{i}",
                "plan_id": "P-COFFEECLUB",
                "billing_info": {
                    "last_failed_payment": {"amount": {"currency_code": "USD", "value": "14.00"}}
                },
            },
        }
        for i in range(n)
    ]
