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


# --- Recovery: after the fix, ask the lost sales back -------------------------------


def _failed_checkouts(db: Session, n: int = 6, **overrides: Any) -> None:
    for i in range(n):
        fields = {
            "event_type": "checkout.capture",
            "error_code": "CURRENCY_MISMATCH",
            "currency": "EUR",
            "amount": 18,
            "product_id": "house-blend",
            "buyer_ref": f"B{i}",
            "resource_id": f"ORD-{i}",
            **overrides,
        }
        _event(db, **fields)


async def _resolved_checkout_incident(db: Session) -> Any:
    """The bad currency scenario up to the verified rollback."""
    from flatline.loop import verify_incident

    _add_config(db, dict(DEFAULT_SHOP_CONFIG), 1, active=False)
    bad = dict(DEFAULT_SHOP_CONFIG)
    bad["currency"] = "EUR"
    _add_config(db, bad, 2, active=True)
    _failed_checkouts(db)
    db.commit()
    incident = scan_once(db)[0]
    await process_incident(db, incident)
    rollback = (
        db.query(Proposal)
        .filter(Proposal.incident_id == incident.id, Proposal.action == "shop.config.rollback")
        .one()
    )
    execute_proposal(db, rollback)
    assert await verify_incident(db, incident)
    db.commit()
    return incident


def _recovery_proposal(db: Session, incident: Any, action: str) -> Proposal:
    return (
        db.query(Proposal)
        .filter(Proposal.incident_id == incident.id, Proposal.action == action)
        .one()
    )


@pytest.mark.asyncio
async def test_recovery_sends_payment_links_only_after_approval(db: Session) -> None:
    from flatline.db.models import AgentStep
    from flatline.recovery import ledger

    incident = await _resolved_checkout_incident(db)
    assert incident.status == "resolved"  # a recovery proposal does not reopen the incident
    proposal = _recovery_proposal(db, incident, "recovery.payment_links.send")
    assert (proposal.tier, proposal.status) == ("approval", "pending")
    assert len(proposal.params["items"]) == 6
    assert {i["currency"] for i in proposal.params["items"]} == {"USD"}  # the restored currency
    step = db.query(AgentStep).filter(AgentStep.node == "recovery").one()
    assert step.model == "code, no model" and step.output["recoverable"] == "108.00 USD"

    # Planned is not sent: until a person approves, the ledger holds the impact only.
    before = ledger.summary(db, incident.id)
    assert (before["impact"], before["requested"]) == ("108.00", "0.00")

    row = execute_proposal(db, proposal)
    assert row.success, row.error
    assert row.response["customers"] == 6 and row.response["asked"] == "108.00"
    assert all(i["paypal_ref"].startswith("INV2-MOCK-") for i in row.response["items"])
    assert ledger.summary(db, incident.id)["requested"] == "108.00"

    # Four of the six customers pay: PayPal reports each paid invoice.
    from flatline.ingest.faults import recovery_payments
    from flatline.paypal.webhooks import normalize_event

    for raw in recovery_payments(ledger.open_requests(db)):
        norm = normalize_event(raw, synthetic=True)
        paid = Event(
            source="synthetic",
            event_type=norm["event_type"],
            occurred_at=norm["occurred_at"],
            payload=raw,
            synthetic=True,
        )
        db.add(paid)
        db.flush()
        assert ledger.confirm_from_event(db, paid) is not None
    after = ledger.summary(db, incident.id)
    assert (after["recovered"], after["outstanding"]) == ("72.00", "36.00")
    assert incident.status == "resolved"


@pytest.mark.asyncio
async def test_recovery_leaves_declined_cards_alone(db: Session) -> None:
    from flatline.loop import verify_incident

    _failed_checkouts(db, error_code="INSTRUMENT_DECLINED", currency="USD")
    db.commit()
    incident = scan_once(db)[0]
    await process_incident(db, incident)
    await verify_incident(db, incident)
    assert incident.status == "resolved"
    actions = {p.action for p in db.query(Proposal).filter(Proposal.incident_id == incident.id)}
    assert "shop.config.rollback" not in actions
    assert not any(a.startswith("recovery.") for a in actions)


@pytest.mark.asyncio
async def test_recovery_retries_failed_renewals(db: Session) -> None:
    from flatline.loop import verify_incident
    from flatline.recovery import ledger

    await test_renewal_failures(db)
    incident = db.query(Proposal).filter(Proposal.action == "invoice.send_reminder").one().incident
    capture = _recovery_proposal(db, incident, "subscription.capture_outstanding")
    execute_proposal(db, capture)
    assert await verify_incident(db, incident)
    retry = _recovery_proposal(db, incident, "recovery.renewals.retry")
    assert (retry.tier, retry.status) == ("approval", "pending")
    assert sorted(i["subscription_id"] for i in retry.params["items"]) == [
        "I-0",
        "I-1",
        "I-2",
        "I-3",
    ]
    row = execute_proposal(db, retry)
    assert row.success, row.error
    totals = ledger.summary(db, incident.id)
    # The mock captures each balance at once, so asked and recovered agree.
    assert (totals["impact"], totals["requested"], totals["recovered"]) == (
        "56.00",
        "56.00",
        "56.00",
    )


@pytest.mark.asyncio
async def test_sandbox_recovery_of_injected_customers_is_simulated(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from flatline.config import reset_settings
    from flatline.policy import executor
    from flatline.recovery import ledger

    incident = await _resolved_checkout_incident(db)
    proposal = _recovery_proposal(db, incident, "recovery.payment_links.send")

    class Gateway:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"PayPal was called: {name}")

    monkeypatch.setattr(executor, "build_gateway", Gateway)
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    reset_settings()
    row = execute_proposal(db, proposal)
    assert row.success, row.error
    assert row.response["simulated"] is True and "Nothing was sent" in row.response["reason"]
    totals = ledger.summary(db, incident.id)
    assert totals["requested"] == "108.00" and totals["simulated"] is True


@pytest.mark.asyncio
async def test_the_executor_bills_what_the_event_says_not_what_the_proposal_says(
    db: Session,
) -> None:
    incident = await _resolved_checkout_incident(db)
    proposal = _recovery_proposal(db, incident, "recovery.payment_links.send")
    items = [dict(i, amount="999.00") for i in proposal.params["items"][:1]]
    items.append({"event_id": "not-an-event", "amount": "50.00", "order_id": "ORD-X"})
    proposal.params = {"items": items}
    row = execute_proposal(db, proposal)
    assert row.success, row.error
    assert row.response["asked"] == "18.00"  # the failed event's amount
    assert [i["status"] for i in row.response["items"]] == ["skipped", "sent"]


@pytest.mark.asyncio
async def test_a_recovery_action_proposed_by_an_agent_is_refused(db: Session) -> None:
    from flatline.agents.schemas import ProposalDraft
    from flatline.loop import file_proposals

    incident = await _resolved_checkout_incident(db)
    draft = ProposalDraft(
        action="recovery.payment_links.send",
        params={"items": [{"event_id": "x", "amount": "500.00"}]},
        rationale="invented by a model",
    )
    filed = file_proposals(db, incident, [draft], source="agent")
    assert (filed[0].tier, filed[0].status) == ("forbidden", "refused")


def test_refund_budget_is_checked_again_when_the_refund_is_sent(db: Session) -> None:
    from flatline.db.models import Incident
    from flatline.recovery import ledger

    now = utcnow()
    incident = Incident(
        playbook="refund_wave",
        status="awaiting_approval",
        metric="refunds",
        window_start=now - timedelta(minutes=5),
        window_end=now,
    )
    db.add(incident)
    db.flush()

    def refund(amount: str) -> Proposal:
        row = Proposal(
            incident_id=incident.id,
            action="refund.single",
            params={"capture_id": "CAP-OK-1", "amount": amount, "currency": "USD"},
            rationale="r",
            tier="approval",
            status="approved",
        )
        db.add(row)
        db.flush()
        return row

    # Five refunds of 45 each waited for approval; each alone fits the 200 budget.
    results = [execute_proposal(db, refund("45.00")) for _ in range(5)]
    assert [r.success for r in results] == [True, True, True, True, False]
    assert "DAILY_REFUND_BUDGET" in (results[-1].error or "")
    assert ledger.refunded_last_24h(db) == 180.0
