#!/usr/bin/env python3
"""Inject a playbook fault (chaos flags + synthetic events)."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from flatline.config import apply_sandbox_guard, settings


def events_for(playbook: str) -> list[dict]:
    now = datetime.now(UTC).isoformat()
    if playbook == "checkout_failure_spike":
        return [
            {
                "id": f"WH-INJ-{uuid4().hex[:8]}",
                "event_type": "checkout.capture",
                "create_time": now,
                "error_code": "CURRENCY_MISMATCH",
                "product_id": "house-blend",
                "amount": "18.00",
                "currency": "EUR",
                "buyer_ref": f"B{i}",
            }
            for i in range(6)
        ]
    if playbook == "refund_wave":
        return [
            {
                "id": f"WH-INJ-R-{uuid4().hex[:8]}",
                "event_type": "PAYMENT.CAPTURE.REFUNDED",
                "create_time": now,
                "product_id": "ethiopia-yirgacheffe",
                "resource": {
                    "id": f"REF-{i}",
                    "amount": {"currency_code": "USD", "value": "22.00"},
                    "custom_id": "ethiopia-yirgacheffe",
                },
            }
            for i in range(5)
        ]
    if playbook == "subscription_renewal_failures":
        return [
            {
                "id": f"WH-INJ-S-{uuid4().hex[:8]}",
                "event_type": "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
                "create_time": now,
                "plan_id": "P-COFFEECLUB",
                "resource": {
                    "id": f"I-{i}",
                    "plan_id": "P-COFFEECLUB",
                    "billing_info": {
                        "last_failed_payment": {"amount": {"currency_code": "USD", "value": "14.00"}}
                    },
                },
            }
            for i in range(4)
        ]
    raise SystemExit(f"unknown playbook {playbook}")


def main() -> None:
    apply_sandbox_guard()
    p = argparse.ArgumentParser()
    p.add_argument("playbook")
    args = p.parse_args()
    cfg = settings()
    base = os.environ.get("FLATLINE_API_URL", cfg.app_base_url)
    headers = {
        "X-Inject-Token": cfg.inject_token,
        "X-Passcode": cfg.dashboard_passcode,
        "Content-Type": "application/json",
    }
    chaos = {
        "checkout_failure_spike": {"bad_currency": True},
        "refund_wave": {"inject": "refund_wave"},
        "subscription_renewal_failures": {"inject": "renewals"},
    }.get(args.playbook, {})
    with httpx.Client(timeout=20) as client:
        client.post(f"{base}/api/chaos", headers=headers, json={"chaos": chaos}).raise_for_status()
        client.post(
            f"{base}/api/synthetic/events",
            headers=headers,
            json={"events": events_for(args.playbook)},
        ).raise_for_status()
    print(f"injected {args.playbook}")


if __name__ == "__main__":
    main()
