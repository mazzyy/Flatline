"""Deterministic PayPal gateway backed by fixtures and an in-memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "paypal"


def _load(name: str) -> Any:
    path = FIXTURE_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


class MockGateway:
    def __init__(self, store: dict[str, Any] | None = None) -> None:
        self.store = store if store is not None else {}
        self.store.setdefault("orders", _load("orders.json") or {})
        self.store.setdefault("refunds", _load("refunds.json") or {})
        self.store.setdefault("subscriptions", _load("subscriptions.json") or {})
        self.store.setdefault("plans", _load("plans.json") or {})
        self.store.setdefault("disputes", _load("disputes.json") or {})
        self.store.setdefault("transactions", _load("transactions.json") or [])
        self.store.setdefault("invoices", {})
        self.store.setdefault("insights", _load("insights.json") or {"available": False})
        self.writes: list[dict[str, Any]] = []

    async def list_transactions(self, **filters: Any) -> list[dict[str, Any]]:
        rows = list(self.store.get("transactions") or [])
        product_id = filters.get("product_id")
        if product_id:
            rows = [r for r in rows if r.get("product_id") == product_id]
        return rows

    async def get_order(self, order_id: str) -> dict[str, Any]:
        order = (self.store.get("orders") or {}).get(order_id)
        if not order:
            raise KeyError(f"order not found: {order_id}")
        return order

    async def get_refund(self, refund_id: str) -> dict[str, Any]:
        refund = (self.store.get("refunds") or {}).get(refund_id)
        if not refund:
            raise KeyError(f"refund not found: {refund_id}")
        return refund

    async def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        sub = (self.store.get("subscriptions") or {}).get(subscription_id)
        if not sub:
            raise KeyError(f"subscription not found: {subscription_id}")
        return sub

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        plan = (self.store.get("plans") or {}).get(plan_id)
        if not plan:
            raise KeyError(f"plan not found: {plan_id}")
        return plan

    async def list_disputes(self, **filters: Any) -> list[dict[str, Any]]:
        del filters
        return list((self.store.get("disputes") or {}).values())

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        dispute = (self.store.get("disputes") or {}).get(dispute_id)
        if not dispute:
            raise KeyError(f"dispute not found: {dispute_id}")
        return dispute

    async def get_merchant_insights(self, **filters: Any) -> dict[str, Any]:
        del filters
        return dict(self.store.get("insights") or {"available": False})

    async def create_refund(self, capture_id: str, amount: str, currency: str) -> dict[str, Any]:
        refund_id = f"REF-{uuid4().hex[:10]}"
        body = {
            "id": refund_id,
            "capture_id": capture_id,
            "amount": {"value": amount, "currency_code": currency},
            "status": "COMPLETED",
        }
        self.store.setdefault("refunds", {})[refund_id] = body
        self.writes.append({"op": "create_refund", **body})
        return body

    async def suspend_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]:
        sub = await self.get_subscription(subscription_id)
        sub["status"] = "SUSPENDED"
        sub["status_reason"] = reason
        self.writes.append({"op": "suspend_subscription", "id": subscription_id, "reason": reason})
        return sub

    async def activate_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]:
        sub = await self.get_subscription(subscription_id)
        sub["status"] = "ACTIVE"
        sub["status_reason"] = reason
        self.writes.append({"op": "activate_subscription", "id": subscription_id, "reason": reason})
        return sub

    async def capture_subscription_outstanding(
        self, subscription_id: str, note: str = ""
    ) -> dict[str, Any]:
        sub = await self.get_subscription(subscription_id)
        capture = {
            "id": f"CAP-{uuid4().hex[:10]}",
            "subscription_id": subscription_id,
            "status": "COMPLETED",
            "note": note,
        }
        self.writes.append({"op": "capture_subscription_outstanding", **capture})
        sub["outstanding_balance"] = {"value": "0.00", "currency_code": "USD"}
        return capture

    async def send_invoice_reminder(self, invoice_id: str) -> dict[str, Any]:
        rec = {"id": invoice_id, "status": "REMINDED"}
        self.writes.append({"op": "send_invoice_reminder", **rec})
        return rec

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        invoice_id = f"INV-{uuid4().hex[:10]}"
        body = {"id": invoice_id, "status": "DRAFT", **payload}
        self.store.setdefault("invoices", {})[invoice_id] = body
        self.writes.append({"op": "create_invoice", **body})
        return body

    async def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        inv = (self.store.get("invoices") or {}).get(invoice_id, {"id": invoice_id})
        inv["status"] = "SENT"
        self.writes.append({"op": "send_invoice", "id": invoice_id})
        return inv
