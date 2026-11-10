"""Deterministic policy proxy. No LLM, no database: every input is passed in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flatline.config import settings
from flatline.policy.catalog import ACTIONS, get

# Who filed the proposal. Agents are the default; the recovery planner is plain code.
AGENT = "agent"
PLANNER = "planner"


@dataclass(frozen=True)
class Decision:
    tier: str
    reason: str


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def items_total(params: dict[str, Any] | None) -> tuple[int, float]:
    """How many items a recovery proposal holds and what they add up to.

    The proxy adds the items up itself; it never trusts a `total` field.
    """
    items = [i for i in ((params or {}).get("items") or []) if isinstance(i, dict)]
    return len(items), round(sum(_number(i.get("amount")) for i in items), 2)


def decide(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    refund_max: float | None = None,
    auto_enabled: bool | None = None,
    auto_refund_max: float | None = None,
    daily_refund_budget: float | None = None,
    refunded_today: float = 0.0,
    source: str = AGENT,
) -> Decision:
    params = params or {}
    spec = get(action)
    if spec is None:
        return Decision("forbidden", f"{action!r} is not in the action catalog")
    cfg = settings()
    refund_max = cfg.refund_approval_max if refund_max is None else refund_max
    auto_enabled = cfg.auto_actions_enabled if auto_enabled is None else auto_enabled
    auto_refund_max = cfg.auto_refund_max if auto_refund_max is None else auto_refund_max
    budget = cfg.daily_refund_budget if daily_refund_budget is None else daily_refund_budget
    if spec.tier == "forbidden":
        return Decision("forbidden", f"{action} is explicitly forbidden")
    if spec.planner_only and source != PLANNER:
        return Decision(
            "forbidden",
            f"{action} is planned by code from the event store; an agent may not propose it",
        )
    if action == "refund.single":
        amount = _number(params.get("amount"))
        if amount > refund_max:
            return Decision(
                "forbidden",
                f"refund {amount} exceeds REFUND_APPROVAL_MAX={refund_max}",
            )
        if refunded_today + amount > budget:
            return Decision(
                "forbidden",
                f"refund {amount:.2f} would pass DAILY_REFUND_BUDGET={budget:.2f} "
                f"({refunded_today:.2f} already refunded in the last 24 hours)",
            )
        if auto_enabled and 0 < amount <= min(auto_refund_max, refund_max):
            return Decision(
                "auto", f"refund {amount:.2f} is within AUTO_REFUND_MAX={auto_refund_max:.2f}"
            )
    if spec.planner_only:
        count, total = items_total(params)
        if count == 0:
            return Decision("forbidden", f"{action} has no items")
        if count > cfg.recovery_max_links:
            return Decision(
                "forbidden",
                f"{count} customers is more than RECOVERY_MAX_LINKS={cfg.recovery_max_links}",
            )
        if total > cfg.recovery_max_total:
            return Decision(
                "forbidden",
                f"{total:.2f} is more than RECOVERY_MAX_TOTAL={cfg.recovery_max_total:.2f}",
            )
    if spec.tier == "auto" and not auto_enabled:
        return Decision("approval", "AUTO_ACTIONS_ENABLED is false")
    return Decision(spec.tier, f"{action} is {spec.tier}")


def limits_public() -> list[dict[str, Any]]:
    """The money limits the proxy enforces, for the dashboard's Policy page."""
    cfg = settings()
    return [
        {
            "key": "AUTO_REFUND_MAX",
            "value": cfg.auto_refund_max,
            "meaning": "A single refund at or under this runs on its own. 0 means every "
            "refund waits for a person.",
        },
        {
            "key": "REFUND_APPROVAL_MAX",
            "value": cfg.refund_approval_max,
            "meaning": "A single refund up to this waits for approval. Above it, refused.",
        },
        {
            "key": "DAILY_REFUND_BUDGET",
            "value": cfg.daily_refund_budget,
            "meaning": "Everything the agents refund in 24 hours has to fit in this. "
            "Checked when a refund is proposed and again when it is executed.",
        },
        {
            "key": "RECOVERY_MAX_LINKS",
            "value": cfg.recovery_max_links,
            "meaning": "The most customers one recovery proposal may contact.",
        },
        {
            "key": "RECOVERY_MAX_TOTAL",
            "value": cfg.recovery_max_total,
            "meaning": "The most one recovery proposal may ask back in total.",
        },
    ]


def rate_limit_auto(existing_auto_count: int, limit: int = 5) -> bool:
    return existing_auto_count < limit


def rate_limit_pending(existing_pending_for_action: int, limit: int = 1) -> bool:
    return existing_pending_for_action < limit


# Imported by the dashboard catalog view.
CATALOG_KEYS = tuple(ACTIONS)
