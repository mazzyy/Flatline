"""Detector entrypoints: health snapshot and the 30s scan loop."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import AgentJob, Event, Incident, audit
from flatline.detector.rules import (
    baseline,
    counts_by_window,
    event_matches_metric,
    is_breach,
    scope_of,
    windows,
)
from flatline.ingest.sse import HUB
from flatline.playbooks.loader import Playbook, load_playbooks

log = logging.getLogger("flatline.detector")

DEDUPE_MINUTES = 30


def _aware(value: Any) -> datetime | None:
    """SQLite returns naive datetimes for timezone columns; compare in UTC."""
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def health_snapshot(db: Session) -> dict[str, Any]:
    """Revenue health score plus per-playbook current-vs-baseline tiles."""
    captures = (
        db.scalar(
            select(func.count()).where(
                Event.event_type.in_(("checkout.capture", "PAYMENT.CAPTURE.COMPLETED"))
            )
        )
        or 0
    )
    failures = (
        db.scalar(
            select(func.count()).where(
                Event.event_type.in_(("checkout.capture", "PAYMENT.CAPTURE.DENIED"))
                & (Event.error_code.is_not(None))
            )
        )
        or 0
    )
    open_incidents = db.scalar(select(func.count()).where(Incident.status.notin_(("resolved",)))) or 0
    fail_rate = (failures / captures) if captures else 0.0
    score = max(0, min(100, int(100 - fail_rate * 80 - open_incidents * 10)))
    metrics = {}
    now = utcnow()
    events = list(db.scalars(select(Event)).all())
    for pb in load_playbooks().values():
        if not pb.enabled:
            continue
        counts = counts_by_window(events, pb, now)
        current = counts[0]
        base = baseline(counts[1:], pb.baseline_floor)
        metrics[pb.name] = {
            "metric": pb.metric,
            "current": current,
            "baseline": base,
            "breached": is_breach(current, base, pb.multiplier, pb.min_count),
        }
    return {
        "score": score,
        "captures": captures,
        "failures": failures,
        "open_incidents": open_incidents,
        "metrics": metrics,
    }


def _scopes(events: list[Event], playbook: Playbook) -> list[str | None]:
    if playbook.scope_key in {"none", ""}:
        return [None]
    values = {scope_of(e, playbook.scope_key) for e in events if event_matches_metric(e, playbook.metric)}
    values.discard(None)
    if playbook.name == "refund_wave":
        matching = [e for e in events if event_matches_metric(e, playbook.metric)]
        if matching:
            counted = Counter(scope_of(e, "product_id") for e in matching)
            total = sum(counted.values())
            for product, n in counted.items():
                if product and total and n / total >= playbook.concentration_ratio:
                    values.add(product)
    return list(values) or [None]


def _revenue_at_risk(playbook: Playbook, current: float) -> float:
    if playbook.metric == "renewal_failures":
        return current * playbook.plan_price
    return current * playbook.average_order_value


def scan_once(db: Session, playbooks: dict[str, Playbook] | None = None) -> list[Incident]:
    playbooks = playbooks or load_playbooks()
    now = utcnow()
    lookback = now - timedelta(hours=8)
    events = list(db.scalars(select(Event).where(Event.occurred_at >= lookback)).all())
    created: list[Incident] = []
    for pb in playbooks.values():
        if not pb.enabled:
            continue
        for scope in _scopes(events, pb):
            counts = counts_by_window(events, pb, now, scope)
            current = counts[0]
            base = baseline(counts[1:], pb.baseline_floor)
            if not is_breach(current, base, pb.multiplier, pb.min_count):
                continue
            window_start, window_end = windows(now, pb.window_minutes, 1)[0]
            incident = _upsert_incident(
                db,
                playbook=pb,
                scope_value=scope,
                current=current,
                base=base,
                window_start=window_start,
                window_end=window_end,
                events=events,
            )
            if incident is not None:
                created.append(incident)
    return created


def _upsert_incident(
    db: Session,
    *,
    playbook: Playbook,
    scope_value: str | None,
    current: float,
    base: float,
    window_start: Any,
    window_end: Any,
    events: list[Event] | None = None,
) -> Incident | None:
    cutoff = utcnow() - timedelta(minutes=DEDUPE_MINUTES)
    existing = db.scalar(
        select(Incident)
        .where(
            Incident.playbook == playbook.name,
            Incident.scope_key == playbook.scope_key,
            Incident.scope_value == scope_value,
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.created_at.desc())
    )
    rar = _revenue_at_risk(playbook, current)
    if existing:
        if existing.status == "resolved":
            # The breach window still contains the events that caused the
            # resolved incident. Only reopen when the metric fires again
            # *after* the fix was verified; otherwise the breach is stale.
            since = _aware(existing.resolved_at)
            fresh = [
                e
                for e in (events or [])
                if event_matches_metric(e, playbook.metric)
                and (scope_value is None or scope_of(e, playbook.scope_key) == scope_value)
                and (since is None or (_aware(e.occurred_at) or since) > since)
            ]
            if len(fresh) < playbook.min_count:
                return None
            existing.status = "reopened"
            existing.resolved_at = None
            db.add(AgentJob(incident_id=existing.id, status="queued"))
        existing.observed_value = current
        existing.baseline_value = base
        existing.window_start = window_start
        existing.window_end = window_end
        existing.revenue_at_risk_per_hour = rar
        audit(
            db,
            actor="detector",
            action="incident.updated",
            incident_id=existing.id,
            details={"observed": current, "baseline": base},
        )
        HUB.publish("incident.updated", {"id": str(existing.id), "playbook": playbook.name})
        return existing
    incident = Incident(
        playbook=playbook.name,
        status="open",
        severity="high" if current >= playbook.min_count * 2 else "med",
        metric=playbook.metric,
        observed_value=current,
        baseline_value=base,
        window_start=window_start,
        window_end=window_end,
        revenue_at_risk_per_hour=rar,
        title=f"{playbook.name.replace('_', ' ')} ({int(current)} vs baseline {base:.1f})",
        evidence={"scope": scope_value},
        scope_key=playbook.scope_key,
        scope_value=scope_value,
    )
    db.add(incident)
    db.flush()
    db.add(AgentJob(incident_id=incident.id, status="queued"))
    audit(
        db,
        actor="detector",
        action="incident.created",
        incident_id=incident.id,
        details={"observed": current, "baseline": base, "scope": scope_value},
    )
    HUB.publish(
        "incident.created",
        {"id": str(incident.id), "playbook": playbook.name, "title": incident.title},
    )
    log.info("incident %s created for %s", incident.id, playbook.name)
    return incident


def run_forever(interval: float = 30.0) -> None:
    from time import sleep

    from flatline.config import apply_sandbox_guard
    from flatline.db.session import create_schema, get_sessionmaker

    apply_sandbox_guard()
    create_schema()
    SessionLocal = get_sessionmaker()
    log.info("detector loop every %ss", interval)
    while True:
        db = SessionLocal()
        try:
            scan_once(db)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("detector scan failed")
        finally:
            db.close()
        sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
