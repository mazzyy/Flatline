"""Read-only tools for the Diagnostician. No write methods."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import Event, Incident, ShopConfigVersion
from flatline.detector.rules import event_matches_metric, scope_of
from flatline.paypal.gateway import ReadOnlyGateway


def incident_events(
    db: Session, incident: Incident, limit: int = 50
) -> tuple[list[Event], Counter[str]]:
    """The events behind this incident, and a count of everything else in its window.

    Signal events match the incident's metric and scope (product, plan) inside the
    detection window. Other traffic is summarised by type only, so one incident's
    evidence never leaks into the next one's diagnosis.
    """
    since = incident.window_start or (utcnow() - timedelta(hours=1))
    rows = list(
        db.scalars(
            select(Event)
            .where(Event.occurred_at >= since)
            .order_by(Event.occurred_at.desc())
            .limit(1000)
        ).all()
    )
    scoped = incident.scope_key not in (None, "", "none") and bool(incident.scope_value)
    signal: list[Event] = []
    background: Counter[str] = Counter()
    for row in rows:
        matches = event_matches_metric(row, incident.metric or "") and (
            not scoped or scope_of(row, str(incident.scope_key)) == incident.scope_value
        )
        if matches:
            signal.append(row)
        elif scoped and scope_of(row, str(incident.scope_key)) == incident.scope_value:
            # Healthy traffic on the same plan or product: is the scope itself broken?
            background[f"{row.event_type} on this {incident.scope_key}"] += 1
        else:
            background[row.event_type] += 1
    return signal[:limit], background


def events_by_group(rows: list[Event], background: Counter[str]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "error_code_breakdown": dict(Counter(r.error_code or "none" for r in rows)),
        "by_product": dict(Counter(r.product_id or "none" for r in rows)),
        "by_plan": dict(Counter(r.plan_id or "none" for r in rows)),
        "by_currency": dict(Counter(r.currency or "none" for r in rows)),
        "by_buyer": dict(Counter(r.buyer_ref or "none" for r in rows)),
        "sample_ids": [str(r.id) for r in rows[:8]],
        "other_traffic_in_window": dict(background),
    }


def config_history(db: Session) -> list[dict[str, Any]]:
    """The shop's config versions as a merchant would see them.

    The Chaos panel keeps its test flags under `chaos` and writes a version even
    when only those flags change. The agents see the real settings only: `chaos`
    is removed and versions identical to the one before are folded into it, so a
    diagnosis has to come from the settings that actually changed.
    """
    rows = list(
        db.scalars(select(ShopConfigVersion).order_by(ShopConfigVersion.version.asc())).all()
    )
    history: list[dict[str, Any]] = []
    for r in rows:
        settings = {k: v for k, v in (r.config or {}).items() if k != "chaos"}
        if history and history[-1]["config"] == settings:
            history[-1]["active"] = history[-1]["active"] or r.active
            continue
        history.append(
            {
                "version": r.version,
                "active": r.active,
                "author": r.author,
                "note": r.note,
                "config": settings,
                "id": str(r.id),
            }
        )
    return history


async def paypal_snapshot(
    gateway: ReadOnlyGateway, *, plan_id: str | None, product_hint: str | None
) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    try:
        snap["transactions"] = await gateway.list_transactions(product_id=product_hint)
    except Exception as exc:
        snap["transactions_error"] = str(exc)
    if plan_id:
        try:
            snap["plan"] = await gateway.get_plan(plan_id)
        except Exception as exc:
            snap["plan_error"] = str(exc)
    # Which PayPal reads ran, and whether each went through MCP or REST.
    snap["calls"] = list(getattr(gateway, "read_log", []))
    return snap
