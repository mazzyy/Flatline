"""Write-side executor. The only module allowed to call PayPal write methods."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warden.db.base import utcnow
from warden.db.models import (
    DEFAULT_SHOP_CONFIG,
    Event,
    Execution,
    Incident,
    Proposal,
    ShopConfigVersion,
    audit,
)
from warden.ingest.sse import HUB
from warden.notify.sinks import send_alert
from warden.paypal.factory import build_gateway

log = logging.getLogger("warden.executor")

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
    row = ShopConfigVersion(version=1, config=dict(DEFAULT_SHOP_CONFIG), author="human", active=True)
    db.add(row)
    db.flush()
    return row


def _write_config(db: Session, config: dict[str, Any], *, author: str, note: str) -> ShopConfigVersion:
    current = db.scalar(select(func.max(ShopConfigVersion.version))) or 0
    for row in db.scalars(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True))):
        row.active = False
    nxt = ShopConfigVersion(version=int(current) + 1, config=config, author=author, active=True, note=note)
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
        return send_alert(str(params.get("message") or "Warden alert"), params)
    if action == "report.create":
        incident = db.get(Incident, proposal.incident_id)
        if incident is not None:
            evidence = dict(incident.evidence or {})
            evidence["report"] = params.get("markdown") or ""
            incident.evidence = evidence
        return {"attached": True}
    if action in CONFIG_ACTIONS:
        return _shop_action(db, action, params)
    return _run(_paypal_write(action, params))


async def _paypal_write(action: str, params: dict[str, Any]) -> dict[str, Any]:
    gateway = build_gateway()
    if action == "invoice.send_reminder":
        return await gateway.send_invoice_reminder(str(params.get("invoice_id") or "INV-1"))
    if action == "subscription.capture_outstanding":
        return await gateway.capture_subscription_outstanding(
            str(params.get("subscription_id")), str(params.get("note") or "warden")
        )
    if action == "subscription.suspend":
        return await gateway.suspend_subscription(
            str(params.get("subscription_id")), str(params.get("reason") or "warden")
        )
    if action == "subscription.activate":
        return await gateway.activate_subscription(
            str(params.get("subscription_id")), str(params.get("reason") or "warden")
        )
    if action == "refund.single":
        return await gateway.create_refund(
            str(params.get("capture_id")),
            str(params.get("amount")),
            str(params.get("currency") or "USD"),
        )
    raise RuntimeError(f"no executor handler for {action}")


def _shop_action(db: Session, action: str, params: dict[str, Any]) -> dict[str, Any]:
    current = _active_config(db)
    cfg = dict(current.config or DEFAULT_SHOP_CONFIG)
    if action == "shop.banner.set":
        cfg["banner"] = str(params.get("text") or params.get("banner") or "")
        row = _write_config(db, cfg, author="warden", note="banner.set")
        return {"version": row.version, "banner": cfg["banner"]}
    if action == "shop.banner.clear":
        cfg["banner"] = ""
        row = _write_config(db, cfg, author="warden", note="banner.clear")
        return {"version": row.version}
    if action == "shop.product.pause_sales":
        paused = list(cfg.get("paused_products") or [])
        pid = str(params.get("product_id"))
        if pid not in paused:
            paused.append(pid)
        cfg["paused_products"] = paused
        row = _write_config(db, cfg, author="warden", note=f"pause {pid}")
        return {"version": row.version, "paused_products": paused}
    if action == "shop.product.resume_sales":
        pid = str(params.get("product_id"))
        cfg["paused_products"] = [p for p in (cfg.get("paused_products") or []) if p != pid]
        row = _write_config(db, cfg, author="warden", note=f"resume {pid}")
        return {"version": row.version}
    if action == "shop.plan.pause_signups":
        cfg["plan_signups_paused"] = True
        row = _write_config(db, cfg, author="warden", note="pause signups")
        return {"version": row.version}
    if action == "shop.plan.resume_signups":
        cfg["plan_signups_paused"] = False
        row = _write_config(db, cfg, author="warden", note="resume signups")
        return {"version": row.version}
    if action == "shop.config.rollback":
        target_version = params.get("version")
        if target_version:
            prev = db.scalar(select(ShopConfigVersion).where(ShopConfigVersion.version == int(target_version)))
        else:
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
        row = _write_config(db, restored, author="warden", note=f"rollback to v{prev.version}")
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
    from warden.config import settings as get_settings

    cfg = get_settings()
    if not cfg.github_token:
        return
    log.info("GITHUB_TOKEN set; would open a rollback PR on %s (%s)", cfg.github_repo, note)
