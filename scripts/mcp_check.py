#!/usr/bin/env python3
"""Check the PayPal MCP servers against your sandbox app.

    python scripts/mcp_check.py

Starts the read and write @paypal/mcp sessions with the token from .env, lists
each scope's tools and runs one read (list_transactions). Needs Node (npx) and
`pip install -r requirements-live.txt`. Writes nothing to PayPal.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

from flatline.config import settings
from flatline.paypal.mcp_pool import McpPool, McpToolError
from flatline.paypal.sandbox_gateway import SandboxGateway


async def main() -> int:
    cfg = settings()
    if cfg.paypal_environment != "SANDBOX":
        print("Set PAYPAL_ENVIRONMENT=SANDBOX in .env first.", file=sys.stderr)
        return 1
    pool = McpPool(cfg=cfg)
    try:
        await pool.ensure()
        for slot in (pool.read, pool.write):
            listed = await slot.session.list_tools()
            names = ", ".join(sorted(t.name for t in listed.tools))
            print(f"{slot.name} MCP is up with {len(listed.tools)} tools: {names}")
        gateway = SandboxGateway(cfg, pool=pool)
        txs = await gateway.list_transactions()
        print(f"list_transactions returned {len(txs)} transactions; {gateway.read_log[-1]}")
        if gateway.read_log[-1]["via"] != "mcp":
            print("The read fell back to REST. If it mentions permission, Transaction Search")
            print("may still be activating for your app (PayPal says up to 9 hours).")
    except McpToolError as exc:
        print(f"MCP is up but PayPal refused the read: {exc}")
    except Exception as exc:
        print(f"MCP check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        await pool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
