"""Agents must never import write-side PayPal access."""

from __future__ import annotations

import ast
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[2] / "warden" / "agents"

FORBIDDEN_IMPORTS = {
    "warden.paypal.sandbox_gateway",
    "warden.policy.executor",
}
FORBIDDEN_NAMES = {
    "SandboxGateway",
    "write_instance",
    "call_write",
    "WRITE_TOOLS",
    "create_refund",
    "suspend_subscription",
    "activate_subscription",
    "capture_subscription_outstanding",
    "send_invoice",
    "create_invoice",
}


def _iter_py() -> list[Path]:
    return [p for p in AGENTS.rglob("*.py") if p.name != "__pycache__"]


def test_agents_package_does_not_import_write_surface() -> None:
    hits: list[str] = []
    for path in _iter_py():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in FORBIDDEN_IMPORTS:
                    hits.append(f"{path.name}: import {mod}")
                for alias in node.names:
                    if alias.name in FORBIDDEN_NAMES:
                        hits.append(f"{path.name}: from {mod} import {alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORTS:
                        hits.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.attr in {"write_instance", "call_write"}:
                    hits.append(f"{path.name}: .{node.attr}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {
                    "create_refund",
                    "suspend_subscription",
                    "activate_subscription",
                    "capture_subscription_outstanding",
                    "send_invoice",
                    "create_invoice",
                    "call_write",
                    "write_instance",
                }:
                    hits.append(f"{path.name}: call {node.func.attr}()")
    assert hits == []


def test_mcp_pool_keeps_read_and_write_tool_sets_disjoint() -> None:
    from warden.paypal.mcp_pool import READ_TOOLS, WRITE_TOOLS

    assert not set(READ_TOOLS) & set(WRITE_TOOLS)
    # Official @paypal/mcp names, not the dotted SPEC draft names.
    assert "list_transactions" in READ_TOOLS
    assert "create_refund" in WRITE_TOOLS
    assert "transactions.list" not in READ_TOOLS
    assert "payments.createRefund" not in WRITE_TOOLS
