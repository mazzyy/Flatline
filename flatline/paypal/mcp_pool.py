"""Run the two PayPal MCP servers (read scope and write scope) and call their tools.

Each scope is its own `npx @paypal/mcp` process with an MCP client session over
stdio. The read server only gets read tools; the write server only gets write
tools and is used by the executor alone. Sessions restart when the OAuth token
refreshes.

@paypal/mcp 1.8.1 takes dotted names on the command line (`--tools=orders.get`)
and exposes snake_case tool names over MCP (`get_order`). See docs/decisions.md D-016.

Only this module and the executor may touch the write instance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from flatline.config import Settings, settings
from flatline.paypal.token import TokenManager

log = logging.getLogger("flatline.paypal.mcp")

# MCP tool name -> the name @paypal/mcp accepts in --tools.
READ_TOOL_FLAGS = {
    "list_transactions": "transactions.list",
    "get_order": "orders.get",
    "get_refund": "payments.getRefunds",
    "show_subscription_details": "subscriptions.show",
    "show_subscription_plan_details": "subscriptionPlans.show",
    "list_subscription_plans": "subscriptionPlans.list",
    "list_disputes": "disputes.list",
    "get_dispute": "disputes.get",
    "list_invoices": "invoices.list",
    "get_invoice": "invoices.get",
}
WRITE_TOOL_FLAGS = {
    "create_refund": "payments.createRefund",
    "send_invoice_reminder": "invoices.sendReminder",
    # Recovery: a payment link is a PayPal invoice, created and then sent.
    "create_invoice": "invoices.create",
    "send_invoice": "invoices.send",
}
READ_TOOLS = tuple(READ_TOOL_FLAGS)
WRITE_TOOLS = tuple(WRITE_TOOL_FLAGS)

PAYPAL_MCP_PACKAGE = "@paypal/mcp@1.8.1"  # tool flag names are version specific
START_TIMEOUT_S = 90  # the first `npx` run downloads the package
CALL_TIMEOUT_S = 30


class McpUnavailable(RuntimeError):
    """The MCP server is not running. Nothing was sent to PayPal."""


class McpRejected(RuntimeError):
    """The MCP server refused the call before running it (invalid arguments)."""


class McpToolError(RuntimeError):
    """The tool ran and PayPal answered with an error."""


@dataclass
class McpProcess:
    name: str
    tools: tuple[str, ...]
    flags: tuple[str, ...]
    token: str = ""
    session: Any = None
    task: asyncio.Task[None] | None = None
    stop: asyncio.Event | None = None

    @property
    def running(self) -> bool:
        return self.session is not None and self.task is not None and not self.task.done()


def _result_payload(result: Any) -> tuple[bool, str, Any]:
    """(is_error, first text block, structured content) for MCP SDK 1.x and 2.x."""
    is_error = bool(getattr(result, "is_error", getattr(result, "isError", False)))
    text = ""
    for block in getattr(result, "content", None) or []:
        if getattr(block, "text", None):
            text = block.text
            break
    structured = getattr(result, "structured_content", getattr(result, "structuredContent", None))
    return is_error, text, structured


@dataclass
class McpPool:
    """Two @paypal/mcp sessions, one per scope."""

    cfg: Settings = field(default_factory=settings)
    token_manager: TokenManager | None = None
    read: McpProcess = field(
        default_factory=lambda: McpProcess("read", READ_TOOLS, tuple(READ_TOOL_FLAGS.values()))
    )
    write: McpProcess = field(
        default_factory=lambda: McpProcess("write", WRITE_TOOLS, tuple(WRITE_TOOL_FLAGS.values()))
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _cmd(self, slot: McpProcess) -> list[str]:
        return ["npx", "-y", PAYPAL_MCP_PACKAGE, f"--tools={','.join(slot.flags)}"]

    async def ensure(self) -> None:
        """Start or restart both sessions for the current token. Raises McpUnavailable."""
        if self.cfg.is_mock_paypal:
            raise McpUnavailable("MOCK mode has no PayPal MCP server")
        tm = self.token_manager or TokenManager(self.cfg)
        token = await tm.get_token()
        async with self._lock:
            await self._ensure_one(self.read, token)
            await self._ensure_one(self.write, token)

    async def _ensure_one(self, slot: McpProcess, token: str) -> None:
        if slot.running and slot.token == token:
            return
        await self._stop(slot)
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise McpUnavailable("pip install -r requirements-live.txt for MCP") from exc

        cmd = self._cmd(slot)
        params = StdioServerParameters(
            command=cmd[0],
            args=cmd[1:],
            env={**os.environ, "PAYPAL_ENVIRONMENT": "SANDBOX", "PAYPAL_ACCESS_TOKEN": token},
        )
        ready: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        stop = asyncio.Event()

        async def run() -> None:
            # The stdio and session contexts must open and close in this one task.
            try:
                async with (
                    stdio_client(params) as (reader, writer),
                    ClientSession(reader, writer) as session,
                ):
                    await session.initialize()
                    slot.session = session
                    ready.set_result(None)
                    await stop.wait()
            except asyncio.CancelledError:
                # The event loop is closing (the agent loop runs one asyncio.run per job).
                # The next ensure() starts a fresh session.
                if not ready.done():
                    ready.set_exception(McpUnavailable(f"{slot.name} MCP start was cancelled"))
            except BaseException as exc:
                if not ready.done():
                    ready.set_exception(McpUnavailable(f"{slot.name} MCP did not start: {exc}"))
                else:
                    log.warning("%s MCP session ended: %s", slot.name, exc)
            finally:
                slot.session = None

        log.info("starting %s MCP with tools=%s", slot.name, ",".join(slot.flags))
        slot.stop, slot.token = stop, token
        slot.task = asyncio.create_task(run(), name=f"paypal-mcp-{slot.name}")
        try:
            await asyncio.wait_for(ready, timeout=START_TIMEOUT_S)
        except TimeoutError as exc:
            await self._stop(slot)
            raise McpUnavailable(f"{slot.name} MCP did not start in {START_TIMEOUT_S}s") from exc

    async def _stop(self, slot: McpProcess) -> None:
        if slot.stop is not None:
            slot.stop.set()
        if slot.task is not None:
            try:
                await asyncio.wait_for(slot.task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                slot.task.cancel()
        slot.task, slot.stop, slot.session = None, None, None

    async def close(self) -> None:
        await self._stop(self.read)
        await self._stop(self.write)

    async def call_read(self, tool: str, arguments: dict[str, Any]) -> Any:
        if tool not in READ_TOOLS:
            raise ValueError(f"{tool} is not a read-scoped PayPal MCP tool")
        return await self._call(self.read, tool, arguments)

    async def call_write(self, tool: str, arguments: dict[str, Any]) -> Any:
        if tool not in WRITE_TOOLS:
            raise ValueError(f"{tool} is not a write-scoped PayPal MCP tool")
        return await self._call(self.write, tool, arguments)

    async def _call(self, slot: McpProcess, tool: str, arguments: dict[str, Any]) -> Any:
        if not slot.running:
            raise McpUnavailable(f"{slot.name} MCP session is not running")
        result = await asyncio.wait_for(
            slot.session.call_tool(tool, arguments), timeout=CALL_TIMEOUT_S
        )
        is_error, text, structured = _result_payload(result)
        if is_error:
            # -32602: the server validated the arguments and did not call PayPal.
            if "-32602" in text or "Input validation error" in text:
                raise McpRejected(f"{tool}: {text}")
            raise McpToolError(f"{tool}: {text}")
        data: Any
        if isinstance(structured, dict) and structured:
            data = structured
        else:
            try:
                data = json.loads(text)
            except ValueError:
                data = {"text": text}
        # @paypal/mcp reports PayPal API errors as a normal result with ok: false.
        if isinstance(data, dict) and data.get("ok") is False:
            raise McpToolError(
                f"{tool}: PayPal answered {data.get('status')} {data.get('code')}: "
                f"{data.get('message')}"
            )
        return data


_POOL: McpPool | None = None


def get_pool() -> McpPool:
    global _POOL
    if _POOL is None:
        _POOL = McpPool()
    return _POOL
