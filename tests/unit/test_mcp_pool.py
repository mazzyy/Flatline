"""PayPal MCP client: result handling and the write-retry rule, without npx."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from flatline.config import Settings
from flatline.paypal.mcp_pool import (
    READ_TOOL_FLAGS,
    WRITE_TOOL_FLAGS,
    McpPool,
    McpRejected,
    McpToolError,
    McpUnavailable,
)
from flatline.paypal.sandbox_gateway import SandboxGateway

CFG = Settings(PAYPAL_ENVIRONMENT="SANDBOX", PAYPAL_CLIENT_ID="id", PAYPAL_CLIENT_SECRET="s")


def _result(text: str, is_error: bool = False) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text)], is_error=is_error)


class FakeSession:
    def __init__(self, result: SimpleNamespace) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> SimpleNamespace:
        self.calls.append((name, arguments))
        return self.result


def _pool_with(result: SimpleNamespace) -> McpPool:
    pool = McpPool(cfg=CFG)

    class Done:
        def done(self) -> bool:
            return False

    for slot in (pool.read, pool.write):
        slot.session, slot.task = FakeSession(result), Done()  # type: ignore[assignment]
    return pool


def test_cli_flags_are_the_dotted_names_paypal_mcp_accepts() -> None:
    assert READ_TOOL_FLAGS["get_order"] == "orders.get"
    assert WRITE_TOOL_FLAGS["create_refund"] == "payments.createRefund"
    assert set(READ_TOOL_FLAGS).isdisjoint(WRITE_TOOL_FLAGS)
    assert all("." in flag for flag in [*READ_TOOL_FLAGS.values(), *WRITE_TOOL_FLAGS.values()])


@pytest.mark.asyncio
async def test_json_result_is_parsed() -> None:
    pool = _pool_with(_result(json.dumps({"id": "O-1", "status": "COMPLETED"})))
    assert await pool.call_read("get_order", {"id": "O-1"}) == {"id": "O-1", "status": "COMPLETED"}


@pytest.mark.asyncio
async def test_invalid_arguments_are_rejected_not_run() -> None:
    pool = _pool_with(_result("MCP error -32602: Input validation error: bad id", is_error=True))
    with pytest.raises(McpRejected):
        await pool.call_write("create_refund", {})


@pytest.mark.asyncio
async def test_paypal_error_inside_a_normal_result_is_a_tool_error() -> None:
    body = {"ok": False, "status": 422, "code": "PAYPAL_API_HTTP_ERROR", "message": "nope"}
    pool = _pool_with(_result(json.dumps(body)))
    with pytest.raises(McpToolError, match="422"):
        await pool.call_read("get_order", {"id": "O-1"})


@pytest.mark.asyncio
async def test_stopped_session_is_unavailable() -> None:
    with pytest.raises(McpUnavailable):
        await McpPool(cfg=CFG).call_read("get_order", {"id": "O-1"})


class FakePool:
    """Stands in for McpPool inside SandboxGateway."""

    def __init__(self, error: Exception | None = None, data: Any = None) -> None:
        self.error, self.data = error, data

    async def ensure(self) -> None:
        return None

    async def call_read(self, tool: str, arguments: dict[str, Any]) -> Any:
        if self.error:
            raise self.error
        return self.data

    call_write = call_read


class RestSpy(SandboxGateway):
    def __init__(self, pool: FakePool) -> None:
        super().__init__(CFG, pool=pool)  # type: ignore[arg-type]
        self.rest_calls: list[tuple[str, str]] = []

    async def _rest(self, method: str, path: str, *, json: Any = None) -> dict[str, Any]:
        self.rest_calls.append((method, path))
        return {"status": "COMPLETED", "via": "rest"}


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [McpUnavailable("down"), McpRejected("bad args")])
async def test_refund_falls_back_to_rest_only_when_nothing_was_sent(error: Exception) -> None:
    gw = RestSpy(FakePool(error=error))
    out = await gw.create_refund("CAP-1", "5.00", "USD")
    assert out["via"] == "rest"
    assert gw.rest_calls == [("POST", "/v2/payments/captures/CAP-1/refund")]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [McpToolError("PayPal said no"), TimeoutError("no answer")])
async def test_refund_is_never_retried_after_mcp_may_have_sent_it(error: Exception) -> None:
    gw = RestSpy(FakePool(error=error))
    with pytest.raises(type(error)):
        await gw.create_refund("CAP-1", "5.00", "USD")
    assert gw.rest_calls == []


@pytest.mark.asyncio
async def test_reads_record_how_they_were_served() -> None:
    gw = RestSpy(FakePool(data={"id": "P-1"}))
    await gw.get_plan("P-1")
    failing = RestSpy(FakePool(error=McpToolError("403")))
    await failing.get_plan("P-1")
    assert gw.read_log == [{"tool": "paypal.show_subscription_plan_details", "via": "mcp"}]
    assert failing.read_log[0]["via"] == "rest"
    assert "McpToolError" in failing.read_log[0]["mcp_error"]
