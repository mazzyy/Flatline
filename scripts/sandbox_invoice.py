#!/usr/bin/env python3
"""Send one real invoice in the PayPal sandbox, through the gateway the recovery step uses.

    python scripts/sandbox_invoice.py sb-buyer123@personal.example.com
    python scripts/sandbox_invoice.py <sandbox buyer email> --amount 18.00 --order ORDER-123

Needs PAYPAL_ENVIRONMENT=SANDBOX and the sandbox client id and secret in .env.
The recipient should be a sandbox personal account from developer.paypal.com
(Testing Tools, Sandbox Accounts). It prints the invoice id, its status and the
link the buyer opens to pay. Sandbox only: no real money moves, and the gateway
refuses to run in any other environment.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

from flatline.config import settings
from flatline.paypal.sandbox_gateway import SandboxGateway
from flatline.policy.executor import INVOICE_NOTE


async def send(email: str, amount: str, order: str) -> int:
    cfg = settings()
    if cfg.is_mock_paypal:
        print("PAYPAL_ENVIRONMENT is MOCK. Set it to SANDBOX in .env to send a sandbox invoice.")
        return 1
    gateway = SandboxGateway(cfg)
    invoice = await gateway.create_invoice(
        recipient_email=email,
        amount=amount,
        currency="USD",
        item_name=f"Order {order}: house-blend",
        note=INVOICE_NOTE,
        reference=order,
    )
    invoice_id = str(invoice["id"])
    print(f"created  {invoice_id}")
    await gateway.send_invoice(invoice_id)
    details = await gateway._rest("GET", f"/v2/invoicing/invoices/{invoice_id}")
    link = (details.get("detail") or {}).get("metadata", {}).get("recipient_view_url", "")
    print(f"status   {details.get('status')}")
    print(f"amount   {amount} USD to {email}")
    print(f"pay link {link or '(open the invoice from the sandbox buyer account)'}")
    await gateway.pool.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email", help="email of a sandbox personal (buyer) account")
    parser.add_argument("--amount", default="18.00")
    parser.add_argument("--order", default="DEMO-RECOVERY-1")
    args = parser.parse_args()
    return asyncio.run(send(args.email, args.amount, args.order))


if __name__ == "__main__":
    raise SystemExit(main())
