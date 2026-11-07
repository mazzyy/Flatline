"""PayPalGateway protocol.

Read methods are safe for agents. Write methods exist only for the Executor.
Agents must receive a ReadOnlyGateway, never a full gateway.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PayPalGateway(Protocol):
    """Read + write surface. Only the executor may call write methods."""

    async def list_transactions(self, **filters: Any) -> list[dict[str, Any]]: ...
    async def get_order(self, order_id: str) -> dict[str, Any]: ...
    async def get_refund(self, refund_id: str) -> dict[str, Any]: ...
    async def get_subscription(self, subscription_id: str) -> dict[str, Any]: ...
    async def get_plan(self, plan_id: str) -> dict[str, Any]: ...
    async def list_disputes(self, **filters: Any) -> list[dict[str, Any]]: ...
    async def get_dispute(self, dispute_id: str) -> dict[str, Any]: ...
    async def get_merchant_insights(self, **filters: Any) -> dict[str, Any]: ...

    async def create_refund(
        self, capture_id: str, amount: str, currency: str
    ) -> dict[str, Any]: ...
    async def suspend_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]: ...
    async def activate_subscription(self, subscription_id: str, reason: str) -> dict[str, Any]: ...
    async def capture_subscription_outstanding(
        self, subscription_id: str, note: str = ""
    ) -> dict[str, Any]: ...
    async def send_invoice_reminder(self, invoice_id: str) -> dict[str, Any]: ...
    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def send_invoice(self, invoice_id: str) -> dict[str, Any]: ...


WRITE_METHODS = frozenset(
    {
        "create_refund",
        "suspend_subscription",
        "activate_subscription",
        "capture_subscription_outstanding",
        "send_invoice_reminder",
        "create_invoice",
        "send_invoice",
    }
)

READ_METHODS = frozenset(
    {
        "list_transactions",
        "get_order",
        "get_refund",
        "get_subscription",
        "get_plan",
        "list_disputes",
        "get_dispute",
        "get_merchant_insights",
    }
)


class WriteAccessError(PermissionError):
    """Raised when a read-only wrapper is asked to write."""


class ReadOnlyGateway:
    """Agents get this. Write methods raise WriteAccessError."""

    def __init__(self, inner: PayPalGateway) -> None:
        self._inner = inner

    async def list_transactions(self, **filters: Any) -> list[dict[str, Any]]:
        return await self._inner.list_transactions(**filters)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self._inner.get_order(order_id)

    async def get_refund(self, refund_id: str) -> dict[str, Any]:
        return await self._inner.get_refund(refund_id)

    async def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await self._inner.get_subscription(subscription_id)

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        return await self._inner.get_plan(plan_id)

    async def list_disputes(self, **filters: Any) -> list[dict[str, Any]]:
        return await self._inner.list_disputes(**filters)

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return await self._inner.get_dispute(dispute_id)

    async def get_merchant_insights(self, **filters: Any) -> dict[str, Any]:
        return await self._inner.get_merchant_insights(**filters)

    def __getattr__(self, name: str) -> Any:
        if name in WRITE_METHODS:
            raise WriteAccessError(
                f"read-only gateway: {name} is a write method; only the executor may call it"
            )
        return getattr(self._inner, name)
