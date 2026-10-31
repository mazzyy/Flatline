"""Deterministic policy proxy. No LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flatline.config import settings
from flatline.policy.catalog import ACTIONS, get


@dataclass(frozen=True)
class Decision:
    tier: str
    reason: str


def decide(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    refund_max: float | None = None,
    auto_enabled: bool | None = None,
) -> Decision:
    params = params or {}
    spec = get(action)
    if spec is None:
        return Decision("forbidden", f"{action!r} is not in the action catalog")
    cfg = settings()
    refund_max = cfg.refund_approval_max if refund_max is None else refund_max
    auto_enabled = cfg.auto_actions_enabled if auto_enabled is None else auto_enabled
    if spec.tier == "forbidden":
        return Decision("forbidden", f"{action} is explicitly forbidden")
    if action == "refund.single":
        try:
            amount = float(params.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0
        if amount > refund_max:
            return Decision(
                "forbidden",
                f"refund {amount} exceeds REFUND_APPROVAL_MAX={refund_max}",
            )
    if spec.tier == "auto" and not auto_enabled:
        return Decision("approval", "AUTO_ACTIONS_ENABLED is false")
    return Decision(spec.tier, f"{action} is {spec.tier}")


def rate_limit_auto(existing_auto_count: int, limit: int = 5) -> bool:
    return existing_auto_count < limit


def rate_limit_pending(existing_pending_for_action: int, limit: int = 1) -> bool:
    return existing_pending_for_action < limit


# Imported by the dashboard catalog view.
CATALOG_KEYS = tuple(ACTIONS)
