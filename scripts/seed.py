#!/usr/bin/env python3
"""Generate steady baseline traffic. MOCK: synthetic events. SANDBOX: telemetry + synthetic.

Server-side capture without a buyer approval is not possible on PayPal Checkout,
so SANDBOX seed does not create real captured orders. See docs/decisions.md D-008.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from flatline.config import apply_sandbox_guard, settings


def main() -> None:
    apply_sandbox_guard()
    p = argparse.ArgumentParser()
    p.add_argument("--minutes", type=int, default=5)
    p.add_argument("--rate", type=float, default=4, help="successful captures per minute")
    args = p.parse_args()
    cfg = settings()
    base = os.environ.get("FLATLINE_API_URL", cfg.app_base_url)
    token = cfg.inject_token
    now = datetime.now(UTC)
    events = []
    n = max(1, int(args.minutes * args.rate))
    for i in range(n):
        at = now - timedelta(seconds=(n - i) * (60 / args.rate))
        events.append(
            {
                "id": f"WH-SEED-{uuid4().hex[:10]}",
                "event_type": "PAYMENT.CAPTURE.COMPLETED",
                "create_time": at.isoformat(),
                "source": "synthetic",
                "product_id": "house-blend",
                "resource": {
                    "id": f"CAP-SEED-{i}",
                    "amount": {"currency_code": "USD", "value": "18.00"},
                    "custom_id": "house-blend",
                },
            }
        )
    last_error: Exception | None = None
    with httpx.Client(timeout=20) as client:
        for attempt in range(1, 16):
            try:
                res = client.post(
                    f"{base}/api/synthetic/events",
                    headers={"X-Inject-Token": token, "Content-Type": "application/json"},
                    json={"events": events},
                )
                res.raise_for_status()
                print(f"seeded {n} captures via {base} ({cfg.paypal_environment})")
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(f"seed attempt {attempt}/15 failed: {exc}")
                time.sleep(2)
    if last_error is not None:
        raise last_error
    if cfg.is_mock_paypal:
        return
    print("SANDBOX seed used synthetic+telemetry events; live captures need a buyer.")


if __name__ == "__main__":
    main()
