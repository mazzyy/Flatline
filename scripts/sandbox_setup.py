#!/usr/bin/env python3
"""Create the Coffee Club product and monthly plan in the PayPal sandbox.

Run once, after the sandbox app's Client ID and Secret are in .env and
PAYPAL_ENVIRONMENT=SANDBOX:

    python scripts/sandbox_setup.py

It prints PAYPAL_SANDBOX_PRODUCT_ID and PAYPAL_SANDBOX_PLAN_ID to paste into
.env. When PAYPAL_SANDBOX_PLAN_ID is already set and that plan exists, it
creates nothing and prints the existing IDs. Sandbox host only.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

import httpx

from flatline.config import Settings, apply_sandbox_guard
from flatline.paypal.token import TokenManager

# Matches the "coffee-club" item in demo-shop/products.js.
PRODUCT: dict[str, Any] = {
    "name": "Coffee Club",
    "description": "A bag a month, roasted the week it ships.",
    "type": "PHYSICAL",
}
MONTHLY_PRICE = "14.00"
CURRENCY = "USD"


def plan_body(product_id: str) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "name": "Coffee Club monthly",
        "description": "Lumen Coffee Co. subscription, one bag a month.",
        "status": "ACTIVE",
        "billing_cycles": [
            {
                "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {"value": MONTHLY_PRICE, "currency_code": CURRENCY}
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }


async def setup(cfg: Settings, client: httpx.AsyncClient) -> tuple[str, str, bool]:
    """Return (product_id, plan_id, created)."""
    base = cfg.paypal_api_base
    if not base:
        raise RuntimeError("PAYPAL_ENVIRONMENT must be SANDBOX")
    token = await TokenManager(cfg, client=client).get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if cfg.paypal_sandbox_plan_id:
        resp = await client.get(
            f"{base}/v1/billing/plans/{cfg.paypal_sandbox_plan_id}", headers=headers
        )
        if resp.status_code == 200:
            plan = resp.json()
            return str(plan["product_id"]), str(plan["id"]), False

    product_id = cfg.paypal_sandbox_product_id
    if not product_id:
        resp = await client.post(f"{base}/v1/catalogs/products", json=PRODUCT, headers=headers)
        resp.raise_for_status()
        product_id = str(resp.json()["id"])

    resp = await client.post(
        f"{base}/v1/billing/plans",
        json=plan_body(product_id),
        headers={**headers, "Prefer": "return=representation"},
    )
    resp.raise_for_status()
    return product_id, str(resp.json()["id"]), True


async def main() -> int:
    cfg = apply_sandbox_guard()
    if cfg.paypal_environment != "SANDBOX":
        print("Set PAYPAL_ENVIRONMENT=SANDBOX in .env first.", file=sys.stderr)
        return 1
    if not cfg.paypal_client_id or not cfg.paypal_client_secret:
        print("Put the sandbox app's Client ID and Secret in .env first.", file=sys.stderr)
        return 1
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            product_id, plan_id, created = await setup(cfg, client)
        except httpx.HTTPStatusError as exc:
            print(
                f"PayPal answered {exc.response.status_code}: {exc.response.text}",
                file=sys.stderr,
            )
            return 1
    print("Created in the sandbox:" if created else "Already set up in the sandbox:")
    print(f"PAYPAL_SANDBOX_PRODUCT_ID={product_id}")
    print(f"PAYPAL_SANDBOX_PLAN_ID={plan_id}")
    if created:
        print("Paste both lines into .env, then restart the stack.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
