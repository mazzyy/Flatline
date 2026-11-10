"""The money ledger: what incidents cost, what was asked back, and what came back."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.db.base import utcnow
from flatline.db.models import Event, LedgerEntry, audit
from flatline.ingest.sse import HUB

IMPACT, REQUESTED, RECOVERED, REFUNDED = "impact", "requested", "recovered", "refunded"
KINDS = (IMPACT, REQUESTED, RECOVERED, REFUNDED)

PAID_INVOICE = "INVOICING.INVOICE.PAID"
SUBSCRIPTION_PAYMENT = "PAYMENT.SALE.COMPLETED"


def money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def record(
    db: Session,
    *,
    kind: str,
    amount: Any,
    currency: str = "USD",
    incident_id: uuid.UUID | None = None,
    proposal_id: uuid.UUID | None = None,
    ref: str | None = None,
    counterparty: str | None = None,
    simulated: bool = False,
    details: dict[str, Any] | None = None,
) -> LedgerEntry:
    row = LedgerEntry(
        incident_id=incident_id,
        proposal_id=proposal_id,
        kind=kind,
        amount=money(amount),
        currency=currency or "USD",
        ref=ref,
        counterparty=counterparty,
        simulated=simulated,
        details=details or {},
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def refunded_last_24h(db: Session) -> float:
    """What the executor has refunded in the last 24 hours, for the daily budget."""
    since = utcnow() - timedelta(hours=24)
    rows = db.scalars(
        select(LedgerEntry).where(LedgerEntry.kind == REFUNDED, LedgerEntry.created_at >= since)
    ).all()
    return float(sum((r.amount for r in rows), Decimal("0.00")))


def summary(db: Session, incident_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Totals per kind, for one incident or for everything."""
    stmt = select(LedgerEntry)
    if incident_id is not None:
        stmt = stmt.where(LedgerEntry.incident_id == incident_id)
    rows = list(db.scalars(stmt).all())
    currencies = Counter(r.currency or "USD" for r in rows)
    currency = currencies.most_common(1)[0][0] if currencies else "USD"
    totals = {kind: Decimal("0.00") for kind in KINDS}
    counts = {kind: 0 for kind in KINDS}
    for row in rows:
        if row.kind not in totals or (row.currency or "USD") != currency:
            continue
        totals[row.kind] += row.amount
        # An impact line covers several lost sales; the other kinds are one line each.
        counts[row.kind] += int((row.details or {}).get("count") or 1)
    out: dict[str, Any] = {kind: str(total) for kind, total in totals.items()}
    out["counts"] = counts
    out["currency"] = currency
    # Asked back, and PayPal has not confirmed a payment yet.
    out["outstanding"] = str(max(totals[REQUESTED] - totals[RECOVERED], Decimal("0.00")))
    out["simulated"] = any(r.simulated for r in rows if r.kind != IMPACT)
    return out


def open_requests(db: Session) -> list[LedgerEntry]:
    """Requests with no payment confirmed yet, oldest first."""
    rows = list(db.scalars(select(LedgerEntry).order_by(LedgerEntry.created_at.asc())).all())
    paid = Counter(r.ref for r in rows if r.kind == RECOVERED)
    still_open: list[LedgerEntry] = []
    for row in rows:
        if row.kind != REQUESTED or not row.ref:
            continue
        if paid[row.ref] > 0:
            paid[row.ref] -= 1  # this request was paid; a later one for the same ref is new
        else:
            still_open.append(row)
    return still_open


def _invoice_id(event: Event) -> str | None:
    payload = event.payload or {}
    raw = payload.get("resource")
    resource: dict[str, Any] = raw if isinstance(raw, dict) else {}
    nested = resource.get("invoice")
    invoice: dict[str, Any] = nested if isinstance(nested, dict) else {}
    found = invoice.get("id") or resource.get("id") or event.resource_id
    return str(found) if found else None


def confirm_from_event(db: Session, event: Event) -> LedgerEntry | None:
    """Mark a request as recovered when PayPal reports the payment.

    A paid invoice confirms a payment link; a completed subscription payment
    confirms a renewal retry. Anything else is ignored.
    """
    if event.event_type == PAID_INVOICE:
        ref = _invoice_id(event)
    elif event.event_type == SUBSCRIPTION_PAYMENT:
        ref = event.subscription_id
    else:
        return None
    if not ref:
        return None
    request = next((r for r in open_requests(db) if r.ref == ref), None)
    if request is None:
        return None
    row = record(
        db,
        kind=RECOVERED,
        amount=request.amount,
        currency=request.currency,
        incident_id=request.incident_id,
        proposal_id=request.proposal_id,
        ref=ref,
        counterparty=request.counterparty,
        simulated=request.simulated or event.synthetic,
        details={"confirmed_by": event.event_type, "event_id": str(event.id)},
    )
    audit(
        db,
        actor="ingest",
        action="recovery.confirmed",
        incident_id=request.incident_id,
        proposal_id=request.proposal_id,
        details={"ref": ref, "amount": str(request.amount), "event_type": event.event_type},
    )
    HUB.publish("incident.updated", {"id": str(request.incident_id), "reason": "recovered"})
    return row
