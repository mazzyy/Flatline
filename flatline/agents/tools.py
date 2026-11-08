"""Read-only tools for the Diagnostician. No write methods."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.db.models import Event, ShopConfigVersion
from flatline.paypal.gateway import ReadOnlyGateway


def events_by_group(
    db: Session, incident_id: UUID | None = None, playbook: str | None = None
) -> dict[str, Any]:
    rows = list(db.scalars(select(Event).order_by(Event.occurred_at.desc()).limit(200)).all())
    by_error = Counter(r.error_code or "none" for r in rows)
    by_product = Counter(r.product_id or "none" for r in rows)
    by_buyer = Counter(r.buyer_ref or "none" for r in rows)
    return {
        "count": len(rows),
        "error_code_breakdown": dict(by_error),
        "by_product": dict(by_product),
        "by_buyer": dict(by_buyer),
        "sample_ids": [str(r.id) for r in rows[:8]],
        "incident_id": str(incident_id) if incident_id else None,
        "playbook": playbook,
    }


def config_history(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(select(ShopConfigVersion).order_by(ShopConfigVersion.version.asc())).all()
    )
    return [
        {
            "version": r.version,
            "active": r.active,
            "author": r.author,
            "note": r.note,
            "config": r.config,
            "id": str(r.id),
        }
        for r in rows
    ]


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
