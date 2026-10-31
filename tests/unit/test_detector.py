"""Baseline / breach math and detector scan."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import Event, Incident
from flatline.db.session import create_schema, get_sessionmaker, reset_engine
from flatline.detector.rules import baseline, is_breach
from flatline.detector.worker import scan_once
from flatline.playbooks.loader import load_playbooks


def test_baseline_floored() -> None:
    assert baseline([0, 0, 0], floor=1) == 1
    assert baseline([2, 4, 6], floor=1) == 4


def test_breach_requires_multiplier_and_min_count() -> None:
    assert is_breach(5, 1, 3, 5) is True
    assert is_breach(4, 1, 3, 5) is False
    assert is_breach(5, 2, 3, 5) is False


def test_playbooks_load() -> None:
    pbs = load_playbooks()
    assert "checkout_failure_spike" in pbs
    assert "subscription_renewal_failures" in pbs
    assert "refund_wave" in pbs
    assert pbs["webhook_gap"].enabled is False


def _session(tmp_path, monkeypatch) -> Session:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/det.db")
    reset_engine()
    create_schema()
    return get_sessionmaker()()


def test_checkout_spike_creates_incident(tmp_path, monkeypatch) -> None:
    db = _session(tmp_path, monkeypatch)
    now = utcnow()
    # Quiet baseline: one failure an hour ago (outside the 5-min window, inside prior windows).
    db.add(
        Event(
            source="shop_telemetry",
            event_type="checkout.capture",
            occurred_at=now - timedelta(minutes=20),
            error_code="INSTRUMENT_DECLINED",
            product_id="house-blend",
            amount=18,
            currency="USD",
            payload={},
        )
    )
    for i in range(6):
        db.add(
            Event(
                source="shop_telemetry",
                event_type="checkout.capture",
                occurred_at=now - timedelta(seconds=30 * i),
                error_code="CURRENCY_MISMATCH",
                product_id="house-blend",
                buyer_ref=f"B{i}",
                amount=18,
                currency="EUR",
                payload={},
            )
        )
    db.commit()
    incidents = scan_once(db)
    db.commit()
    assert incidents
    assert incidents[0].playbook == "checkout_failure_spike"
    assert incidents[0].observed_value >= 5
    # Dedupe: second scan updates, does not create.
    again = scan_once(db)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Incident)) == 1
    assert again[0].id == incidents[0].id

    # Resolved incident + the same stale events: no duplicate, no reopen.
    incidents[0].status = "resolved"
    incidents[0].resolved_at = utcnow()
    db.commit()
    assert scan_once(db) == []
    db.commit()
    assert db.scalar(select(func.count()).select_from(Incident)) == 1
    assert db.get(Incident, incidents[0].id).status == "resolved"

    # Fresh failures after the fix reopen the same incident and queue agents.
    for i in range(5):
        db.add(
            Event(
                source="shop_telemetry",
                event_type="checkout.capture",
                occurred_at=utcnow() + timedelta(seconds=1 + i),
                error_code="CURRENCY_MISMATCH",
                product_id="house-blend",
                buyer_ref=f"R{i}",
                amount=18,
                currency="EUR",
                payload={},
            )
        )
    db.commit()
    reopened = scan_once(db)
    db.commit()
    assert reopened and reopened[0].id == incidents[0].id
    assert reopened[0].status == "reopened"
    assert db.scalar(select(func.count()).select_from(Incident)) == 1
    db.close()
    reset_engine()


def test_reverify_resolves_quiet_incident(tmp_path, monkeypatch) -> None:
    import asyncio

    from flatline.config import settings
    from flatline.loop import reverify_pending

    monkeypatch.setenv("VERIFY_MINUTES", "1")
    settings.cache_clear()
    db = _session(tmp_path, monkeypatch)
    inc = Incident(
        playbook="checkout_failure_spike",
        status="verifying",
        severity="high",
        metric="checkout_failures",
        observed_value=6,
        baseline_value=1,
        window_start=utcnow(),
        window_end=utcnow(),
        revenue_at_risk_per_hour=108,
        title="t",
        evidence={},
        scope_key="none",
        scope_value=None,
    )
    db.add(inc)
    # Failures still inside the 1-minute window: stays verifying, no step written.
    for i in range(6):
        db.add(
            Event(
                source="shop_telemetry",
                event_type="checkout.capture",
                occurred_at=utcnow() - timedelta(seconds=10 + i),
                error_code="CURRENCY_MISMATCH",
                amount=18,
                currency="USD",
                payload={},
            )
        )
    db.commit()
    assert asyncio.run(reverify_pending(db)) == []
    assert inc.status == "verifying"
    # Window goes quiet: resolved.
    for e in db.scalars(select(Event)).all():
        e.occurred_at = utcnow() - timedelta(minutes=5)
    db.commit()
    assert asyncio.run(reverify_pending(db)) == [inc]
    assert inc.status == "resolved"
    db.close()
    reset_engine()
    settings.cache_clear()
