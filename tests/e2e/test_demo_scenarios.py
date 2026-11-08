"""Three demo playbooks end to end against an in-process mock stack."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import DEFAULT_SHOP_CONFIG, Event, Proposal, ShopConfigVersion
from flatline.db.session import create_schema, ensure_default_config, get_sessionmaker, reset_engine
from flatline.detector.worker import scan_once
from flatline.loop import process_incident
from flatline.policy.executor import execute_proposal

pytestmark = pytest.mark.e2e


@pytest.fixture
def db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/e2e.db")
    monkeypatch.setenv("VERIFY_MINUTES", "1")
    monkeypatch.setenv("DEMO_MODE", "true")
    reset_engine()
    create_schema()
    session = get_sessionmaker()()
    ensure_default_config(session)
    yield session
    session.close()
    reset_engine()


def _add_config(db: Session, config: dict[str, Any], version: int, active: bool = True) -> None:
    if active:
        for row in db.query(ShopConfigVersion).all():
            row.active = False
    db.add(
        ShopConfigVersion(
            version=version,
            config=config,
            author="human",
            active=active,
            note=f"v{version}",
        )
    )
    db.commit()


def _event(db: Session, **kwargs: Any) -> None:
    now = utcnow()
    occurred = kwargs.pop("occurred_at", now - timedelta(seconds=90))
    db.add(
        Event(
            source=kwargs.pop("source", "synthetic"),
            event_type=kwargs.pop("event_type"),
            occurred_at=occurred,
            payload=kwargs.pop("payload", {}),
            synthetic=True,
            **kwargs,
        )
    )


@pytest.mark.asyncio
async def test_checkout_spike_bad_currency(db: Session) -> None:
    _add_config(db, dict(DEFAULT_SHOP_CONFIG), 1, active=False)
    bad = dict(DEFAULT_SHOP_CONFIG)
    bad["currency"] = "EUR"
    bad["chaos"] = {"bad_currency": True}
    _add_config(db, bad, 2, active=True)
    now = utcnow()
    db.add(
        Event(
            source="shop_telemetry",
            event_type="checkout.capture",
            occurred_at=now - timedelta(minutes=20),
            error_code="INSTRUMENT_DECLINED",
            payload={},
        )
    )
    for i in range(6):
        _event(
            db,
            event_type="checkout.capture",
            error_code="CURRENCY_MISMATCH",
            currency="EUR",
            product_id="house-blend",
            buyer_ref=f"B{i}",
            resource_id=f"ORD-{i}",
        )
    db.commit()
    incidents = scan_once(db)
    db.commit()
    assert incidents
    incident = incidents[0]
    await process_incident(db, incident)
    db.commit()
    db.refresh(incident)
    assert incident.playbook == "checkout_failure_spike"
    assert incident.root_cause and "config version" in incident.root_cause.lower()
    proposals = list(db.query(Proposal).filter(Proposal.incident_id == incident.id).all())
    actions = {p.action: p for p in proposals}
    assert actions["shop.banner.set"].tier == "auto"
    assert actions["shop.banner.set"].status == "executed"
    assert actions["shop.config.rollback"].tier == "approval"
    assert actions["shop.config.rollback"].status == "pending"
    execute_proposal(db, actions["shop.config.rollback"])
    from flatline.loop import verify_incident

    await verify_incident(db, incident)
    db.commit()
    db.refresh(incident)
    assert incident.status == "resolved"
    active = db.query(ShopConfigVersion).filter(ShopConfigVersion.active.is_(True)).one()
    assert active.config.get("currency") == "USD"


@pytest.mark.asyncio
async def test_refund_wave_refuses_bulk(db: Session) -> None:
    for i in range(5):
        _event(
            db,
            event_type="PAYMENT.CAPTURE.REFUNDED",
            product_id="ethiopia-yirgacheffe",
            amount=22,
            currency="USD",
            resource_id=f"REF-{i}",
        )
    db.commit()
    incidents = scan_once(db)
    db.commit()
    wave = next(i for i in incidents if i.playbook == "refund_wave")
    await process_incident(db, wave)
    db.commit()
    assert wave.root_cause and "ethiopia" in wave.root_cause
    proposals = list(db.query(Proposal).filter(Proposal.incident_id == wave.id).all())
    by = {p.action: p for p in proposals}
    assert by["refund.bulk"].tier == "forbidden"
    assert by["refund.bulk"].status == "refused"
    assert by["shop.product.pause_sales"].tier == "approval"
    assert wave.status == "escalated" or wave.notes


@pytest.mark.asyncio
async def test_renewal_failures(db: Session) -> None:
    for i in range(4):
        _event(
            db,
            event_type="BILLING.SUBSCRIPTION.PAYMENT.FAILED",
            plan_id="P-COFFEECLUB",
            subscription_id=f"I-{i}",
            amount=14,
            currency="USD",
        )
    db.commit()
    incidents = scan_once(db)
    db.commit()
    inc = next(i for i in incidents if i.playbook == "subscription_renewal_failures")
    await process_incident(db, inc)
    db.commit()
    proposals = list(db.query(Proposal).filter(Proposal.incident_id == inc.id).all())
    by = {p.action: p for p in proposals}
    assert by["invoice.send_reminder"].tier == "auto"
    assert by["invoice.send_reminder"].status == "executed"
    assert by["subscription.capture_outstanding"].tier == "approval"
    assert by["subscription.capture_outstanding"].status == "pending"


@pytest.mark.asyncio
@pytest.mark.parametrize("injected", [True, False])
async def test_sandbox_writes_for_injected_incidents_are_simulated(
    db: Session, monkeypatch: pytest.MonkeyPatch, injected: bool
) -> None:
    from flatline.config import reset_settings
    from flatline.db.models import Event as EventRow
    from flatline.policy import executor

    await test_renewal_failures(db)
    if not injected:
        for row in db.query(EventRow).all():
            row.synthetic = False
        db.commit()
    capture = db.query(Proposal).filter(Proposal.action == "subscription.capture_outstanding").one()

    sent: list[str] = []

    class Gateway:
        async def capture_subscription_outstanding(self, sub: str, note: str) -> dict[str, Any]:
            sent.append(sub)
            return {"ok": True}

    monkeypatch.setattr(executor, "build_gateway", Gateway)
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    reset_settings()
    row = execute_proposal(db, capture)
    assert row.success
    if injected:
        assert row.response["simulated"] is True
        assert sent == []  # fake ids never reach PayPal
    else:
        assert sent and "simulated" not in row.response


@pytest.mark.parametrize("version", [2, "2", "v2", "version 2", "the last good version", None])
def test_rollback_understands_how_models_write_the_version(db: Session, version: Any) -> None:
    _add_config(db, dict(DEFAULT_SHOP_CONFIG), 2, active=False)
    bad = dict(DEFAULT_SHOP_CONFIG)
    bad["currency"] = "EUR"
    _add_config(db, bad, 3, active=True)
    from flatline.db.models import Incident

    now = utcnow()
    incident = Incident(
        playbook="checkout_failure_spike",
        status="awaiting_approval",
        metric="capture_failures",
        window_start=now - timedelta(minutes=5),
        window_end=now,
    )
    db.add(incident)
    db.commit()
    proposal = Proposal(
        incident_id=incident.id,
        action="shop.config.rollback",
        params={"version": version},
        rationale="r",
        tier="approval",
        status="approved",
    )
    db.add(proposal)
    db.flush()
    row = execute_proposal(db, proposal)
    assert row.success, row.error
    active = db.query(ShopConfigVersion).filter(ShopConfigVersion.active.is_(True)).one()
    assert active.config["currency"] == "USD"
