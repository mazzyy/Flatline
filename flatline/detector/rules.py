"""Pure baseline / breach math. No I/O."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from flatline.playbooks.loader import Playbook

REFUND_TYPES = frozenset({"PAYMENT.CAPTURE.REFUNDED"})
RENEWAL_FAIL_TYPES = frozenset({"BILLING.SUBSCRIPTION.PAYMENT.FAILED"})


def baseline(window_values: Iterable[float], floor: float) -> float:
    values = list(window_values)
    if not values:
        return floor
    return max(floor, sum(values) / len(values))


def is_breach(current: float, baseline_value: float, multiplier: float, min_count: int) -> bool:
    return current >= multiplier * baseline_value and current >= min_count


def event_matches_metric(event: Any, metric: str) -> bool:
    event_type = getattr(event, "event_type", None) or (
        event.get("event_type") if isinstance(event, dict) else ""
    )
    error = (
        getattr(event, "error_code", None)
        if not isinstance(event, dict)
        else event.get("error_code")
    )
    if metric == "capture_failures":
        if event_type == "PAYMENT.CAPTURE.DENIED":
            return True
        return event_type == "checkout.capture" and bool(error)
    if metric == "renewal_failures":
        return event_type in RENEWAL_FAIL_TYPES
    if metric == "refunds":
        return event_type in REFUND_TYPES
    if metric == "missing_webhooks":
        return event_type == "webhook.missing"
    return False


def scope_of(event: Any, scope_key: str) -> str | None:
    if scope_key in {"none", "", None}:
        return None
    if isinstance(event, dict):
        return event.get(scope_key)
    return getattr(event, scope_key, None)


def windows(now: datetime, window_minutes: int, n: int = 13) -> list[tuple[datetime, datetime]]:
    """Current window plus n-1 previous windows, newest first."""
    delta = timedelta(minutes=window_minutes)
    out: list[tuple[datetime, datetime]] = []
    end = now
    for _ in range(n):
        start = end - delta
        out.append((start, end))
        end = start
    return out


def counts_by_window(
    events: list[Any],
    playbook: Playbook,
    now: datetime,
    scope_value: str | None = None,
) -> list[float]:
    buckets = windows(now, playbook.window_minutes, 13)
    counts = [0.0] * 13
    for event in events:
        if not event_matches_metric(event, playbook.metric):
            continue
        if scope_value and scope_of(event, playbook.scope_key) != scope_value:
            continue
        occurred = event.occurred_at if not isinstance(event, dict) else event["occurred_at"]
        if isinstance(occurred, datetime) and occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=UTC)
        for i, (start, end) in enumerate(buckets):
            if start <= occurred < end:
                counts[i] += 1
                break
    return counts
