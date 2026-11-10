"""Work out who lost a sale during an incident and what to ask back.

Plain code over the event store. No model takes part, so no amount, order or
customer in a recovery proposal can be invented: every item points at the
failed event it came from, and the executor reads that event again before it
sends anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.db.models import DEFAULT_SHOP_CONFIG, Event, Incident, LedgerEntry, ShopConfigVersion
from flatline.detector.rules import event_matches_metric, scope_of
from flatline.playbooks.loader import Playbook
from flatline.recovery.ledger import IMPACT, money

PAYMENT_LINKS = "recovery.payment_links.send"
RENEWAL_RETRY = "recovery.renewals.retry"

SUCCESS_TYPES = frozenset({"PAYMENT.CAPTURE.COMPLETED", "PAYMENT.SALE.COMPLETED"})


@dataclass
class RecoveryPlan:
    action: str | None  # None: this kind of incident has nothing to ask back
    currency: str
    impact: Decimal = Decimal("0.00")  # every lost or refunded sale, recoverable or not
    affected: int = 0
    estimated: int = 0  # lost sales with no amount on the event, counted at the playbook price
    items: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((money(i["amount"]) for i in self.items), Decimal("0.00"))


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes for timezone columns; compare in UTC."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def shop_currency(db: Session) -> str:
    row = db.scalar(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True)))
    config = (row.config if row else None) or DEFAULT_SHOP_CONFIG
    return str(config.get("currency") or "USD")


def _since(db: Session, incident: Incident) -> datetime:
    """Start of the events to settle: the detection window, or the last settlement."""
    last = db.scalar(
        select(LedgerEntry)
        .where(LedgerEntry.incident_id == incident.id, LedgerEntry.kind == IMPACT)
        .order_by(LedgerEntry.created_at.desc())
    )
    return last.created_at if last is not None else incident.window_start


def _events_since(db: Session, since: datetime) -> list[Event]:
    return list(
        db.scalars(
            select(Event).where(Event.occurred_at >= since).order_by(Event.occurred_at.asc())
        ).all()
    )


def _is_success(event: Event) -> bool:
    if event.event_type in SUCCESS_TYPES:
        return True
    return event.event_type == "checkout.capture" and not event.error_code


def _paid_later(event: Event, key: str, successes: list[Event]) -> bool:
    """The same buyer, order or subscription paid after this failure."""
    at = _aware(event.occurred_at)
    for ok in successes:
        if key not in (ok.buyer_ref, ok.resource_id, ok.subscription_id):
            continue
        ok_at = _aware(ok.occurred_at)
        if at is None or ok_at is None or ok_at >= at:
            return True
    return False


def plan(db: Session, incident: Incident, playbook: Playbook | None) -> RecoveryPlan:
    """The incident's lost sales, and the ones worth asking back.

    One lost sale per buyer (or per order, or per subscription): somebody who
    tried three times is asked once. Left alone: anyone who has paid since,
    failures the playbook says a customer cannot fix by paying again (a
    declined card), and events with no amount.
    """
    recovery = dict(playbook.recovery) if playbook else {}
    action = str(recovery.get("action") or "") or None
    skip_codes = {str(c) for c in (recovery.get("skip_error_codes") or [])}
    currency = shop_currency(db)
    out = RecoveryPlan(action=action, currency=currency)

    events = _events_since(db, _since(db, incident))
    scoped = incident.scope_key not in (None, "", "none") and bool(incident.scope_value)
    failures = [
        e
        for e in events
        if event_matches_metric(e, incident.metric or "")
        and (not scoped or scope_of(e, str(incident.scope_key)) == incident.scope_value)
    ]
    successes = [e for e in events if _is_success(e)]
    renewals = action == RENEWAL_RETRY
    fallback = money(
        (playbook.plan_price if renewals else playbook.average_order_value) if playbook else 0
    )

    seen: set[str] = set()
    for event in failures:
        key = (
            event.subscription_id if renewals else (event.buyer_ref or event.resource_id)
        ) or str(event.id)
        if key in seen:
            continue
        seen.add(key)
        out.affected += 1
        if event.amount is None:
            out.estimated += 1
        out.impact += money(event.amount) if event.amount is not None else fallback
        if action is None:
            continue
        ref = str(event.subscription_id if renewals else event.resource_id or "")
        if _paid_later(event, key, successes):
            out.skipped.append({"ref": ref or key, "reason": "has paid since"})
        elif event.error_code and event.error_code in skip_codes:
            out.skipped.append(
                {"ref": ref or key, "reason": f"{event.error_code}: paying again would not help"}
            )
        elif event.amount is None:
            out.skipped.append({"ref": ref or key, "reason": "the event carries no amount"})
        elif not ref:
            out.skipped.append({"ref": key, "reason": "no order or subscription id to bill"})
        else:
            item: dict[str, Any] = {
                "event_id": str(event.id),
                "amount": str(money(event.amount)),
                "currency": currency,
                "buyer_ref": event.buyer_ref,
            }
            if renewals:
                item["subscription_id"] = ref
            else:
                item["order_id"] = ref
                item["product_id"] = event.product_id
            out.items.append(item)
    return out


def rationale(found: RecoveryPlan, incident: Incident) -> str:
    n, total = len(found.items), f"{found.total} {found.currency}"
    left = (
        f" {len(found.skipped)} more were left alone (see the recovery step)."
        if found.skipped
        else ""
    )
    source = "Orders and amounts come from the failed events themselves, not from a model."
    if found.action == RENEWAL_RETRY:
        return (
            f"{n} subscribers on plan {incident.scope_value} still owe a renewal that failed "
            f"during this incident. Retry each outstanding balance through PayPal: {total} "
            f"in total.{left} {source}"
        )
    return (
        f"Checkout is healthy again. {n} customers tried to pay during the incident and "
        f"could not. Send each of them a PayPal invoice for the order they tried to place: "
        f"{total} in total.{left} {source}"
    )
