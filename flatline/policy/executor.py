"""Write-side executor. The only module allowed to call PayPal write methods."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flatline.config import settings
from flatline.db.base import utcnow
from flatline.db.models import (
    DEFAULT_SHOP_CONFIG,
    Event,
    Execution,
    Incident,
    Proposal,
    ShopConfigVersion,
    audit,
)
from flatline.detector.rules import event_matches_metric
from flatline.ingest.sse import HUB
from flatline.notify.sinks import send_alert
from flatline.paypal.factory import build_gateway
from flatline.recovery import ledger
from flatline.recovery.planner import PAYMENT_LINKS, RENEWAL_RETRY, shop_currency

log = logging.getLogger("flatline.executor")

RECOVERY_ACTIONS = {PAYMENT_LINKS, RENEWAL_RETRY}

INVOICE_NOTE = (
    "Your checkout did not go through because of a problem on our side, and you were not "
    "charged. If you would still like your order, you can pay for it with this invoice."
)

CONFIG_ACTIONS = {
    "shop.banner.set",
    "shop.banner.clear",
    "shop.config.rollback",
    "shop.product.pause_sales",
    "shop.product.resume_sales",
    "shop.plan.pause_signups",
    "shop.plan.resume_signups",
    "events.replay",
}


def _active_config(db: Session) -> ShopConfigVersion:
    row = db.scalar(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True)))
    if row:
        return row
    row = ShopConfigVersion(
        version=1, config=dict(DEFAULT_SHOP_CONFIG), author="human", active=True
    )
    db.add(row)
    db.flush()
    return row


def _write_config(
    db: Session, config: dict[str, Any], *, author: str, note: str
) -> ShopConfigVersion:
    current = db.scalar(select(func.max(ShopConfigVersion.version))) or 0
    for row in db.scalars(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True))):
        row.active = False
    nxt = ShopConfigVersion(
        version=int(current) + 1, config=config, author=author, active=True, note=note
    )
    db.add(nxt)
    db.flush()
    return nxt


def _run(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def _thread() -> None:
        result["value"] = asyncio.run(coro)

    import threading

    t = threading.Thread(target=_thread)
    t.start()
    t.join()
    return result["value"]


def execute_proposal(db: Session, proposal: Proposal) -> Execution:
    request = {"action": proposal.action, "params": proposal.params}
    try:
        response = _perform(db, proposal)
        success, error = True, None
    except Exception as exc:
        log.exception("execute %s failed", proposal.action)
        response, success, error = {"error": str(exc)}, False, str(exc)
    row = Execution(
        proposal_id=proposal.id,
        request=request,
        response=response,
        success=success,
        error=error,
        created_at=utcnow(),
    )
    db.add(row)
    proposal.status = "executed" if success else "failed"
    proposal.decided_at = proposal.decided_at or utcnow()
    audit(
        db,
        actor="executor",
        action=proposal.action,
        incident_id=proposal.incident_id,
        proposal_id=proposal.id,
        details={"success": success, "error": error},
    )
    db.flush()
    HUB.publish("proposal.updated", {"id": str(proposal.id), "status": proposal.status})
    return row


def _perform(db: Session, proposal: Proposal) -> dict[str, Any]:
    action = proposal.action
    params = proposal.params or {}
    if action == "notify.alert":
        return send_alert(str(params.get("message") or "Flatline alert"), params)
    if action == "report.create":
        incident = db.get(Incident, proposal.incident_id)
        if incident is not None:
            evidence = dict(incident.evidence or {})
            evidence["report"] = params.get("markdown") or ""
            incident.evidence = evidence
        return {"attached": True}
    if action in CONFIG_ACTIONS:
        return _shop_action(db, action, params)
    if action in RECOVERY_ACTIONS:
        return _recover(db, proposal)
    if action == "refund.single":
        _check_refund_budget(db, params)
    if _from_injected_events(db, proposal):
        return {
            "simulated": True,
            "reason": "This incident was built from injected test events, so its PayPal ids "
            "are not real objects. Nothing was sent to PayPal.",
        }
    response: dict[str, Any] = _run(_paypal_write(action, params))
    if action == "refund.single":
        ledger.record(
            db,
            kind=ledger.REFUNDED,
            amount=params.get("amount"),
            currency=str(params.get("currency") or "USD"),
            incident_id=proposal.incident_id,
            proposal_id=proposal.id,
            ref=str(response.get("id") or params.get("capture_id") or ""),
            simulated=settings().is_mock_paypal,
        )
    return response


def _check_refund_budget(db: Session, params: dict[str, Any]) -> None:
    """The daily budget again, at the moment of sending.

    The proxy checked it when the refund was proposed, but several refunds can
    wait for approval at once, each inside the budget on its own.
    """
    cfg = settings()
    amount = float(ledger.money(params.get("amount")))
    spent = ledger.refunded_last_24h(db)
    if spent + amount > cfg.daily_refund_budget:
        raise RuntimeError(
            f"refund {amount:.2f} would pass DAILY_REFUND_BUDGET={cfg.daily_refund_budget:.2f} "
            f"({spent:.2f} already refunded in the last 24 hours); nothing was sent"
        )


def _version_number(value: Any) -> int | None:
    match = re.search(r"\d+", str(value)) if value is not None else None
    return int(match.group()) if match else None


def _from_injected_events(db: Session, proposal: Proposal) -> bool:
    """True when every event behind the incident came from the Chaos panel (sandbox only)."""
    if settings().is_mock_paypal:
        return False  # the mock gateway answers every id
    incident = db.get(Incident, proposal.incident_id)
    if incident is None or incident.window_start is None:
        return False
    stmt = select(Event).where(Event.occurred_at >= incident.window_start)
    if incident.window_end is not None:
        stmt = stmt.where(Event.occurred_at <= incident.window_end)
    behind = [e for e in db.scalars(stmt).all() if event_matches_metric(e, incident.metric or "")]
    return bool(behind) and all(e.synthetic for e in behind)


async def _paypal_write(action: str, params: dict[str, Any]) -> dict[str, Any]:
    gateway = build_gateway()
    if action == "invoice.send_reminder":
        return await gateway.send_invoice_reminder(str(params.get("invoice_id") or "INV-1"))
    if action == "subscription.capture_outstanding":
        return await gateway.capture_subscription_outstanding(
            str(params.get("subscription_id")), str(params.get("note") or "flatline")
        )
    if action == "subscription.suspend":
        return await gateway.suspend_subscription(
            str(params.get("subscription_id")), str(params.get("reason") or "flatline")
        )
    if action == "subscription.activate":
        return await gateway.activate_subscription(
            str(params.get("subscription_id")), str(params.get("reason") or "flatline")
        )
    if action == "refund.single":
        return await gateway.create_refund(
            str(params.get("capture_id")),
            str(params.get("amount")),
            str(params.get("currency") or "USD"),
        )
    raise RuntimeError(f"no executor handler for {action}")


def _recover(db: Session, proposal: Proposal) -> dict[str, Any]:
    """Send the payment links, or retry the renewals, of an approved recovery proposal.

    Each item is read again from its failed event: the amount, the order and the
    subscription come from the event store, not from the proposal's parameters.
    Items are independent; one that fails is reported and never retried.
    """
    cfg = settings()
    incident = db.get(Incident, proposal.incident_id)
    metric = (incident.metric if incident else "") or ""
    renewals = proposal.action == RENEWAL_RETRY
    currency = shop_currency(db)
    work: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for item in (proposal.params or {}).get("items") or []:
        event = _event_of(db, item)
        ref = (event.subscription_id if renewals else event.resource_id) if event else None
        if event is None or not event_matches_metric(event, metric) or event.amount is None:
            results.append(
                {
                    "ref": str(item.get("event_id")),
                    "status": "skipped",
                    "reason": "no failed event with an amount behind this item",
                }
            )
        elif not ref:
            results.append(
                {
                    "ref": str(event.id),
                    "status": "skipped",
                    "reason": "the event has no order or subscription id",
                }
            )
        else:
            work.append(
                {
                    "ref": str(ref),
                    "amount": str(ledger.money(event.amount)),
                    "currency": currency,
                    "buyer_ref": event.buyer_ref,
                    "product_id": event.product_id,
                    # In the sandbox an injected event's ids are not real PayPal objects.
                    "simulate": event.synthetic and not cfg.is_mock_paypal,
                }
            )
    results += _run(_recover_writes(work, renewals=renewals))
    asked = Decimal("0.00")
    for done in results:
        if done["status"] not in ("sent", "retried", "simulated"):
            continue
        asked += ledger.money(done["amount"])
        shared: dict[str, Any] = {
            "amount": done["amount"],
            "currency": currency,
            "incident_id": proposal.incident_id,
            "proposal_id": proposal.id,
            "ref": done.get("paypal_ref") or done["ref"],
            "counterparty": done.get("buyer_ref"),
            "simulated": cfg.is_mock_paypal or done["status"] == "simulated",
            "details": {"action": proposal.action, "source_ref": done["ref"]},
        }
        ledger.record(db, kind=ledger.REQUESTED, **shared)
        if done.get("paid"):  # PayPal captured the balance in the same call
            ledger.record(db, kind=ledger.RECOVERED, **shared)
    acted = [r for r in results if r["status"] in ("sent", "retried", "simulated")]
    if not acted:
        raise RuntimeError(
            "nothing could be recovered: "
            + "; ".join(f"{r['ref']}: {r.get('reason') or r['status']}" for r in results[:5])
        )
    out: dict[str, Any] = {
        "asked": str(asked),
        "currency": currency,
        "customers": len(acted),
        "items": [{k: v for k, v in r.items() if k not in ("buyer_ref", "paid")} for r in results],
    }
    if all(r["status"] == "simulated" for r in acted):
        out["simulated"] = True
        out["reason"] = (
            "These customers come from injected test events, so their PayPal ids are not "
            "real objects. Nothing was sent to PayPal."
        )
    return out


def _event_of(db: Session, item: Any) -> Event | None:
    try:
        return db.get(Event, uuid.UUID(str(item.get("event_id"))))
    except (AttributeError, ValueError):
        return None


async def _recover_writes(work: list[dict[str, Any]], *, renewals: bool) -> list[dict[str, Any]]:
    gateway = build_gateway()
    done: list[dict[str, Any]] = []
    for item in work:
        row = {k: item[k] for k in ("ref", "amount", "buyer_ref")}
        if item["simulate"]:
            done.append({**row, "status": "simulated", "paypal_ref": f"SIM-{item['ref']}"})
            continue
        try:
            if renewals:
                answer = await gateway.capture_subscription_outstanding(
                    item["ref"], "Flatline: retry of a renewal that failed during an incident"
                )
                paid = str(answer.get("status") or "").upper() == "COMPLETED"
                done.append({**row, "status": "retried", "paid": paid})
            else:
                email = await _payer_email(gateway, item["ref"])
                invoice = await gateway.create_invoice(
                    recipient_email=email,
                    amount=item["amount"],
                    currency=item["currency"],
                    item_name=f"Order {item['ref']}: {item['product_id'] or 'your order'}",
                    note=INVOICE_NOTE,
                    reference=item["ref"],
                )
                await gateway.send_invoice(str(invoice["id"]))
                done.append({**row, "status": "sent", "paypal_ref": str(invoice["id"])})
        except Exception as exc:
            log.warning("recovery item %s failed: %s", item["ref"], exc)
            done.append({**row, "status": "failed", "reason": str(exc)[:200]})
    return done


async def _payer_email(gateway: Any, order_id: str) -> str | None:
    """The payer's email from the PayPal order. Read here, at send time, and nowhere else:
    no agent and no proposal ever holds a customer's email address."""
    try:
        order = await gateway.get_order(order_id)
    except Exception:
        return None
    payer = order.get("payer") or {}
    source = (order.get("payment_source") or {}).get("paypal") or {}
    return payer.get("email_address") or source.get("email_address")


def _shop_action(db: Session, action: str, params: dict[str, Any]) -> dict[str, Any]:
    current = _active_config(db)
    cfg = dict(current.config or DEFAULT_SHOP_CONFIG)
    if action == "shop.banner.set":
        cfg["banner"] = str(params.get("text") or params.get("banner") or "")
        row = _write_config(db, cfg, author="flatline", note="banner.set")
        return {"version": row.version, "banner": cfg["banner"]}
    if action == "shop.banner.clear":
        cfg["banner"] = ""
        row = _write_config(db, cfg, author="flatline", note="banner.clear")
        return {"version": row.version}
    if action == "shop.product.pause_sales":
        paused = list(cfg.get("paused_products") or [])
        pid = str(params.get("product_id"))
        if pid not in paused:
            paused.append(pid)
        cfg["paused_products"] = paused
        row = _write_config(db, cfg, author="flatline", note=f"pause {pid}")
        return {"version": row.version, "paused_products": paused}
    if action == "shop.product.resume_sales":
        pid = str(params.get("product_id"))
        cfg["paused_products"] = [p for p in (cfg.get("paused_products") or []) if p != pid]
        row = _write_config(db, cfg, author="flatline", note=f"resume {pid}")
        return {"version": row.version}
    if action == "shop.plan.pause_signups":
        cfg["plan_signups_paused"] = True
        row = _write_config(db, cfg, author="flatline", note="pause signups")
        return {"version": row.version}
    if action == "shop.plan.resume_signups":
        cfg["plan_signups_paused"] = False
        row = _write_config(db, cfg, author="flatline", note="resume signups")
        return {"version": row.version}
    if action == "shop.config.rollback":
        # Models write the version as 2, "2", "v2" or "version 2"; anything else, or a
        # version that is not an earlier inactive one, falls back to the last inactive.
        prev = None
        wanted = _version_number(params.get("version"))
        if wanted is not None:
            prev = db.scalar(
                select(ShopConfigVersion).where(
                    ShopConfigVersion.version == wanted, ShopConfigVersion.active.is_(False)
                )
            )
        if prev is None:
            prev = db.scalar(
                select(ShopConfigVersion)
                .where(ShopConfigVersion.active.is_(False))
                .order_by(ShopConfigVersion.version.desc())
            )
        if not prev:
            raise RuntimeError("no previous config version to restore")
        restored = dict(prev.config or DEFAULT_SHOP_CONFIG)
        chaos = dict(restored.get("chaos") or {})
        chaos["bad_currency"] = False
        restored["chaos"] = chaos
        restored["currency"] = "USD"
        row = _write_config(db, restored, author="flatline", note=f"rollback to v{prev.version}")
        maybe_github_pr(row.note or "")
        return {"version": row.version, "restored_from": prev.version}
    if action == "events.replay":
        n = 0
        for eid in params.get("event_ids") or []:
            if db.get(Event, eid):
                n += 1
        return {"replayed": n}
    raise RuntimeError(action)


def maybe_github_pr(note: str) -> None:
    from flatline.config import settings as get_settings

    cfg = get_settings()
    if not cfg.github_token:
        return
    log.info("GITHUB_TOKEN set; would open a rollback PR on %s (%s)", cfg.github_repo, note)
