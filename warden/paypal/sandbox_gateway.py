"""Real PayPal sandbox gateway.

Read methods prefer the read-scoped MCP server and fall back to REST.
Write methods go through write-scoped MCP where it exists, otherwise REST
(subscription suspend / activate / capture — not in @paypal/mcp).

This module never talks to live PayPal hosts.
"""

from __future__ import annotations

from typing import Any

import httpx

from warden.config import Settings, settings
from warden.paypal.mcp_pool import McpPool, get_pool
from warden.paypal.token import TokenManager


class SandboxGateway:
    def __init__(
        self,
        cfg: Settings | None = None,
        token_manager: TokenManager | None = None,
        pool: McpPool | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.cfg = cfg or settings()
        if self.cfg.is_mock_paypal:
            raise RuntimeError("SandboxGateway requires PAYPAL_ENVIRONMENT=SANDBOX")
        if not self.cfg.paypal_api_base or "sandbox" not in self.cfg.paypal_api_base:
            raise RuntimeError("SandboxGateway refused: sandbox host is not configured")
        self.tokens = token_manager or TokenManager(self.cfg)
        self.pool = pool or get_pool()
        self._client = client

    async def _auth_headers(self) -> dict[str, str]:
        token = await self.tokens.get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _rest(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=30)
            close = True
        try:
            resp = await client.request(
                method,
                f"{self.cfg.paypal_api_base}{path}",
                headers=await self._auth_headers(),
                json=json,
            )
            resp.raise_for_status()
            if not resp.content:
                return {"status": "NO_CONTENT"}
            return resp.json()
        finally:
            if close:
                await client.aclose()

    async def _read_mcp_or_rest(
        self, tool: str, arguments: dict[str, Any], rest_path: str
    ) -> dict[str, Any]:
        try:
            await self.pool.ensure()
            return await self.pool.call_read(tool, arguments)
        except Exception:
            return await self._rest("GET", rest_path)

    async def list_transactions(self, **filters: Any) -> list[dict[str, Any]]:
        try:
            await self.pool.ensure()
            data = await self.pool.call_read("list_transactions", filters)
            if isinstance(data, list):
                return data
            return list(data.get("transaction_details") or data.get("items") or [])
        except Exception:
            data = await self._rest("GET", "/v1/reporting/transactions")
            return list(data.get("transaction_details") or [])

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self._read_mcp_or_rest(
            "get_order", {"id": order_id}, f"/v2/checkout/orders/{order_id}"
        )

    async def get_refund(self, refund_id: str) -> dict[str, Any]:
        return await self._read_mcp_or_rest(
            "get_refund", {"refund_id": refund_id}, f"/v2/payments/refunds/{refund_id}"
        )

    async def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await self._read_mcp_or_rest(
            "show_subscription_details",
            {"subscription_id": subscription_id},
            f"/v1/billing/subscriptions/{subscription_id}",
        )

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        return await self._read_mcp_or_rest(
            "show_subscription_plan_details",
            {"plan_id": plan_id},
            f"/v1/billing/plans/{plan_id}",
        )

    async def list_disputes(self, **filters: Any) -> list[dict[str, Any]]:
        try:
            await self.pool.ensure()
            data = await self.pool.call_read("list_disputes", filters)
            if isinstance(data, list):
                return data
            return list(data.get("items") or [])
        except Exception:
            data = await self._rest("GET", "/v1/customer/disputes")
            return list(data.get("items") or [])

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return await self._read_mcp_or_rest(
            "get_dispute", {"dispute_id": dispute_id}, f"/v1/customer/disputes/{dispute_id}"
        )

    async def get_merchant_insights(self, **filters: Any) -> dict[str, Any]:
        # Not in @paypal/mcp 1.8.1. REST merchant insights is partner-only; return a stub.
        del filters
        return {"available": False, "reason": "merchant_insights_not_in_mcp"}

    async def create_refund(self, capture_id: str, amount: str, currency: str) -> dict[str, Any]:
        payload = {"amount": {"value": amount, "currency_code": currency}}
        try:
            await self.pool.ensure()
            return await self.pool.call_write(
                "create_refund", {"capture_id": capture_id, **payload}
            )
        except Exception:
            return await self._rest("POST", f"/v2/payments/captures/{capture_id}/refund", json=payload)

    async def suspend_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]:
        return await self._rest(
            "POST",
            f"/v1/billing/subscriptions/{subscription_id}/suspend",
            json={"reason": reason},
        )

    async def activate_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]:
        return await self._rest(
            "POST",
            f"/v1/billing/subscriptions/{subscription_id}/activate",
            json={"reason": reason},
        )

    async def capture_subscription_outstanding(
        self, subscription_id: str, note: str = ""
    ) -> dict[str, Any]:
        return await self._rest(
            "POST",
            f"/v1/billing/subscriptions/{subscription_id}/capture",
            json={"note": note or "Warden outstanding balance capture", "capture_type": "OUTSTANDING_BALANCE"},
        )

    async def send_invoice_reminder(self, invoice_id: str) -> dict[str, Any]:
        try:
            await self.pool.ensure()
            return await self.pool.call_write("send_invoice_reminder", {"invoice_id": invoice_id})
        except Exception:
            return await self._rest("POST", f"/v2/invoicing/invoices/{invoice_id}/remind")

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            await self.pool.ensure()
            return await self.pool.call_write("create_invoice", payload)
        except Exception:
            return await self._rest("POST", "/v2/invoicing/invoices", json=payload)

    async def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        try:
            await self.pool.ensure()
            return await self.pool.call_write("send_invoice", {"invoice_id": invoice_id})
        except Exception:
            return await self._rest("POST", f"/v2/invoicing/invoices/{invoice_id}/send")
