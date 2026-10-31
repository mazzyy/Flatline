"""Spawn and respawn the two PayPal MCP servers (read scope and write scope).

Tool identifiers are the official @paypal/mcp names (snake_case), not the
dotted names in SPEC.md Section 9.4. See DECISIONS.md D-004.

Only this module and the executor may touch the write instance.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from warden.config import Settings, settings
from warden.paypal.token import TokenManager

log = logging.getLogger("warden.paypal.mcp")

# Official tool names from https://www.npmjs.com/package/@paypal/mcp (v1.8.1).
READ_TOOLS = (
    "list_transactions",
    "get_order",
    "get_refund",
    "show_subscription_details",
    "show_subscription_plan_details",
    "list_subscription_plans",
    "list_disputes",
    "get_dispute",
    "list_invoices",
    "get_invoice",
)

WRITE_TOOLS = (
    "create_refund",
    "create_invoice",
    "send_invoice",
    "send_invoice_reminder",
)


@dataclass
class McpProcess:
    name: str
    tools: tuple[str, ...]
    proc: asyncio.subprocess.Process | None = None
    token: str = ""

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.returncode is None


@dataclass
class McpPool:
    """Two npx @paypal/mcp processes. Respawned when the OAuth token refreshes."""

    cfg: Settings = field(default_factory=settings)
    token_manager: TokenManager | None = None
    read: McpProcess = field(default_factory=lambda: McpProcess("read", READ_TOOLS))
    write: McpProcess = field(default_factory=lambda: McpProcess("write", WRITE_TOOLS))
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _cmd(self, tools: tuple[str, ...]) -> list[str]:
        return ["npx", "-y", "@paypal/mcp", f"--tools={','.join(tools)}"]

    async def ensure(self) -> None:
        if self.cfg.is_mock_paypal:
            return
        tm = self.token_manager or TokenManager(self.cfg)
        token = await tm.get_token()
        async with self._lock:
            await self._ensure_one(self.read, token)
            await self._ensure_one(self.write, token)

    async def _ensure_one(self, slot: McpProcess, token: str) -> None:
        if slot.running and slot.token == token:
            return
        await self._stop(slot)
        env = {
            "PAYPAL_ENVIRONMENT": "SANDBOX",
            "PAYPAL_ACCESS_TOKEN": token,
        }
        log.info("spawning %s MCP with tools=%s", slot.name, ",".join(slot.tools))
        slot.proc = await asyncio.create_subprocess_exec(
            *self._cmd(slot.tools),
            env={**dict(__import__("os").environ), **env},
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        slot.token = token

    async def _stop(self, slot: McpProcess) -> None:
        if slot.proc and slot.proc.returncode is None:
            slot.proc.terminate()
            try:
                await asyncio.wait_for(slot.proc.wait(), timeout=5)
            except TimeoutError:
                slot.proc.kill()
        slot.proc = None

    async def close(self) -> None:
        await self._stop(self.read)
        await self._stop(self.write)

    def read_instance(self) -> McpProcess:
        return self.read

    def write_instance(self) -> McpProcess:
        """Executor-only. Agents must not call this."""
        return self.write

    async def call_read(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool not in READ_TOOLS:
            raise ValueError(f"{tool} is not a read-scoped PayPal MCP tool")
        return await self._call(self.read, tool, arguments)

    async def call_write(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool not in WRITE_TOOLS:
            raise ValueError(f"{tool} is not a write-scoped PayPal MCP tool")
        return await self._call(self.write, tool, arguments)

    async def _call(self, slot: McpProcess, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Placeholder stdio call. Real JSON-RPC is wired when a session is open.

        Tests never exercise this against a live process. SandboxGateway uses
        REST for the same operations so the stack works without a live MCP
        handshake; MCP is still spawned for tool discovery / judge demo.
        """
        del slot, arguments
        raise RuntimeError(
            f"MCP stdio call for {tool} is only available when a live session is attached"
        )


_POOL: McpPool | None = None


def get_pool() -> McpPool:
    global _POOL
    if _POOL is None:
        _POOL = McpPool()
    return _POOL
