"""Recovery planner and money ledger: who is asked back, for how much, and what counts."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import Event, Incident
from flatline.db.session import create_schema, ensure_default_config, get_sessionmaker, reset_engine
from flatline.playbooks.loader import load_playbooks
from flatline.recovery import ledger, planner


@pytest.fixture
def db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/recovery.db")
    reset_engine()
    create_schema()
    session = get_sessionmaker()()
    ensure_default_config(session)
    yield session
    session.close()
    reset_engine()


def _incident(db: Session, playbook: str, metric: str, **scope: str) -> Incident:
    now = utcnow()
    row = Incident(
        playbook=playbook,
        status="resolved",
        metric=metric,
        window_start=now - timedelta(minutes=30),
        window_end=now,
        scope_key=next(iter(scope), "none"),
        scope_value=next(iter(scope.values()), None),
    )
    db.add(row)
    db.flush()
    return row


def _event(db: Session, minutes_ago: float = 5, **fields: Any) -> Event:
    row = Event(
        source="synthetic",
        occurred_at=utcnow() - timedelta(minutes=minutes_ago),
        payload={},
        synthetic=True,
        **fields,
    )
    db.add(row)
    db.flush()
    return row


def _failed_capture(db: Session, buyer: str, order: str, **more: Any) -> Event:
    fields = {
        "event_type": "checkout.capture",
        "error_code": "CURRENCY_MISMATCH",
        "amount": Decimal("18.00"),
        "currency": "EUR",
        "buyer_ref": buyer,
        "resource_id": order,
        "product_id": "house-blend",
        **more,
    }
    return _event(db, **fields)


def test_one_payment_link_per_customer_in_the_shop_currency(db: Session) -> None:
    incident = _incident(db, "checkout_failure_spike", "capture_failures")
    _failed_capture(db, "B1", "ORD-1")
    _failed_capture(db, "B1", "ORD-1b", minutes_ago=4)  # the same buyer tried again
    _failed_capture(db, "B2", "ORD-2")
    found = planner.plan(db, incident, load_playbooks()["checkout_failure_spike"])
    assert found.action == planner.PAYMENT_LINKS
    assert [i["order_id"] for i in found.items] == ["ORD-1", "ORD-2"]
    assert found.total == Decimal("36.00")
    # The failures were logged in EUR by the broken config; the shop bills in USD.
    assert {i["currency"] for i in found.items} == {"USD"}
    assert (found.affected, found.impact) == (2, Decimal("36.00"))


def test_left_alone_declined_cards_returning_buyers_and_unknown_amounts(db: Session) -> None:
    incident = _incident(db, "checkout_failure_spike", "capture_failures")
    _failed_capture(db, "B1", "ORD-1")
    _failed_capture(db, "B2", "ORD-2", error_code="INSTRUMENT_DECLINED", currency="USD")
    _failed_capture(db, "B3", "ORD-3")
    _event(db, 1, event_type="checkout.capture", buyer_ref="B3", resource_id="ORD-3b")  # paid
    _failed_capture(db, "B4", "ORD-4", amount=None)
    found = planner.plan(db, incident, load_playbooks()["checkout_failure_spike"])
    assert [i["order_id"] for i in found.items] == ["ORD-1"]
    reasons = {s["ref"]: s["reason"] for s in found.skipped}
    assert "INSTRUMENT_DECLINED" in reasons["ORD-2"]
    assert reasons["ORD-3"] == "has paid since"
    assert "no amount" in reasons["ORD-4"]
    # All four still count as lost; the one without an amount at the playbook's price.
    assert (found.affected, found.estimated, found.impact) == (4, 1, Decimal("72.00"))


def test_renewals_are_retried_once_per_subscriber(db: Session) -> None:
    incident = _incident(db, "subscription_renewal_failures", "renewal_failures", plan_id="P-1")
    for sub in ("I-1", "I-1", "I-2"):
        _event(
            db,
            event_type="BILLING.SUBSCRIPTION.PAYMENT.FAILED",
            plan_id="P-1",
            subscription_id=sub,
            amount=Decimal("14.00"),
        )
    _event(db, event_type="BILLING.SUBSCRIPTION.PAYMENT.FAILED", plan_id="P-OTHER", amount=14)
    found = planner.plan(db, incident, load_playbooks()["subscription_renewal_failures"])
    assert found.action == planner.RENEWAL_RETRY
    assert [i["subscription_id"] for i in found.items] == ["I-1", "I-2"]
    assert found.total == Decimal("28.00")


def test_a_refund_wave_has_an_impact_and_nothing_to_ask_back(db: Session) -> None:
    incident = _incident(db, "refund_wave", "refunds", product_id="ethiopia-yirgacheffe")
    for i in range(3):
        _event(
            db,
            event_type="PAYMENT.CAPTURE.REFUNDED",
            product_id="ethiopia-yirgacheffe",
            buyer_ref=f"R{i}",
            amount=Decimal("22.00"),
        )
    found = planner.plan(db, incident, load_playbooks()["refund_wave"])
    assert found.action is None and found.items == []
    assert (found.affected, found.impact) == (3, Decimal("66.00"))


def test_ledger_totals_and_payment_confirmation(db: Session) -> None:
    incident = _incident(db, "checkout_failure_spike", "capture_failures")
    ledger.record(
        db, kind=ledger.IMPACT, amount="54", incident_id=incident.id, details={"count": 3}
    )
    for ref in ("INV2-A", "INV2-B"):
        ledger.record(db, kind=ledger.REQUESTED, amount="18", incident_id=incident.id, ref=ref)
    assert ledger.confirm_from_event(db, _event(db, event_type="PAYMENT.CAPTURE.COMPLETED")) is None

    paid = _event(db, event_type="INVOICING.INVOICE.PAID")
    paid.payload = {"resource": {"invoice": {"id": "INV2-A"}}}
    row = ledger.confirm_from_event(db, paid)
    assert row is not None and row.kind == ledger.RECOVERED and row.simulated  # synthetic event
    assert ledger.confirm_from_event(db, paid) is None  # paid once, counted once

    totals = ledger.summary(db, incident.id)
    assert (totals["impact"], totals["requested"], totals["recovered"]) == (
        "54.00",
        "36.00",
        "18.00",
    )
    assert totals["outstanding"] == "18.00"
    assert totals["counts"] == {"impact": 3, "requested": 2, "recovered": 1, "refunded": 0}
    assert [r.ref for r in ledger.open_requests(db)] == ["INV2-B"]


def test_refund_budget_counts_only_the_last_24_hours(db: Session) -> None:
    old = ledger.record(db, kind=ledger.REFUNDED, amount="100")
    old.created_at = utcnow() - timedelta(hours=30)
    ledger.record(db, kind=ledger.REFUNDED, amount="40")
    ledger.record(db, kind=ledger.REQUESTED, amount="500")  # not a refund
    db.flush()
    assert ledger.refunded_last_24h(db) == 40.0
