"""FastAPI ingest, dashboard API, and SSE."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flatline.config import apply_sandbox_guard, settings
from flatline.db.base import utcnow
from flatline.db.models import (
    DEFAULT_SHOP_CONFIG,
    AuditLog,
    Event,
    Incident,
    Proposal,
    ShopConfigVersion,
    audit,
)
from flatline.db.session import create_schema, ensure_default_config, get_sessionmaker, session_dep
from flatline.ingest.auth import require_inject_token, require_passcode
from flatline.ingest.serializers import (
    audit_out,
    config_out,
    event_out,
    incident_out,
    proposal_out,
)
from flatline.ingest.sse import HUB
from flatline.paypal.webhooks import normalize_event, verify_signature

log = logging.getLogger("flatline.ingest")

SORTABLE_EVENTS = {
    "occurred_at": Event.occurred_at,
    "event_type": Event.event_type,
    "amount": Event.amount,
    "source": Event.source,
    "created_at": Event.created_at,
}


def create_app() -> FastAPI:
    apply_sandbox_guard()
    app = FastAPI(title="Flatline", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        create_schema()
        db = get_sessionmaker()()
        try:
            ensure_default_config(db)
        finally:
            db.close()
        if settings().run_workers:
            _start_workers()

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        cfg = settings()
        return {
            "ok": True,
            "paypal_environment": cfg.paypal_environment,
            "llm_mode": cfg.llm_mode,
        }

    @app.post("/webhooks/paypal")
    async def paypal_webhook(
        request: Request,
        db: Session = Depends(session_dep),
    ) -> dict[str, Any]:
        if _chaos_flag(db, "webhook_broken"):
            raise HTTPException(status_code=500, detail="chaos: webhook endpoint broken")
        raw = await request.json()
        headers = {k: v for k, v in request.headers.items()}
        cfg = settings()
        verified = False
        if not cfg.is_mock_paypal:
            try:
                from flatline.paypal.token import TokenManager

                token = await TokenManager(cfg).get_token()
                verified = await verify_signature(headers, raw, cfg=cfg, access_token=token)
            except Exception as exc:
                log.warning("webhook verify failed: %s", exc)
                raise HTTPException(status_code=400, detail="webhook verification failed") from exc
        row = _store_normalized(db, normalize_event(raw, verified=verified), emit=True)
        return {"id": str(row.id), "duplicate": getattr(row, "_duplicate", False)}

    @app.post("/api/telemetry")
    def telemetry(body: dict[str, Any], db: Session = Depends(session_dep)) -> dict[str, Any]:
        occurred = body.get("at") or body.get("occurred_at")
        try:
            occurred_at = (
                datetime.fromisoformat(str(occurred).replace("Z", "+00:00"))
                if occurred
                else utcnow()
            )
        except ValueError:
            occurred_at = utcnow()
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        ok = bool(body.get("ok", True))
        event_type = str(body.get("type") or "checkout.capture")
        error_code = body.get("error_code")
        if not ok and not error_code:
            error_code = "CAPTURE_FAILED"
        row = Event(
            source="shop_telemetry",
            event_type=event_type,
            occurred_at=occurred_at,
            resource_id=body.get("order_id"),
            amount=_decimal(body.get("amount")),
            currency=body.get("currency"),
            product_id=body.get("product_id"),
            plan_id=body.get("plan_id"),
            error_code=error_code,
            payload=body,
            # The shop's "pay without a PayPal login" checkout: no PayPal order behind it.
            synthetic=bool(body.get("simulated")),
            verified=True,
        )
        db.add(row)
        db.flush()
        audit(db, actor="ingest", action="telemetry", details={"type": event_type, "ok": ok})
        HUB.publish("event.ingested", event_out(row))
        return {"id": str(row.id)}

    @app.post("/api/synthetic/events", dependencies=[Depends(require_inject_token)])
    def synthetic_events(
        body: dict[str, Any], db: Session = Depends(session_dep)
    ) -> dict[str, Any]:
        raw_items = body.get("events")
        items: list[Any] = raw_items if isinstance(raw_items, list) else [body]
        stored: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            norm = normalize_event(item, synthetic=True, verified=False)
            if item.get("source"):
                norm["source"] = str(item["source"])
            if item.get("event_type"):
                norm["event_type"] = str(item["event_type"])
            if item.get("product_id"):
                norm["product_id"] = item["product_id"]
            if item.get("plan_id"):
                norm["plan_id"] = item["plan_id"]
            if item.get("error_code"):
                norm["error_code"] = item["error_code"]
            if item.get("amount") is not None:
                norm["amount"] = _decimal(item["amount"])
            row = _store_normalized(db, norm, emit=True)
            stored.append(str(row.id))
        incidents = _run_scan(db)
        return {"ids": stored, "incidents": incidents}

    @app.post(
        "/api/synthetic/recovery-payments",
        dependencies=[Depends(require_passcode), Depends(require_inject_token)],
    )
    def synthetic_recovery_payments(db: Session = Depends(session_dep)) -> dict[str, Any]:
        """Customers pay their recovery requests: inject the events PayPal would send.

        Sandbox buyers do not pay invoices on their own, so the demo plays their
        part. The events are stored as synthetic and the ledger lines they
        confirm are marked simulated.
        """
        from flatline.ingest.faults import recovery_payments
        from flatline.recovery import ledger

        stored = _ingest_payloads(db, recovery_payments(ledger.open_requests(db)))
        audit(
            db,
            actor="human",
            action="chaos.inject",
            details={"inject": "recovery_payments", "synthetic_events": len(stored)},
        )
        return {"injected": stored, "money": ledger.summary(db)}

    @app.get("/api/site")
    def site() -> dict[str, Any]:
        """What the landing page needs to send a visitor to the right places."""
        cfg = settings()
        return {
            "shop_url": cfg.shop_public_url,
            "paypal_environment": cfg.paypal_environment,
            "llm_mode": cfg.llm_mode,
        }

    @app.api_route("/shop", methods=["GET", "POST"])
    @app.api_route("/shop/{path:path}", methods=["GET", "POST"])
    async def shop_proxy(request: Request, path: str = "") -> Response:
        """One-container hosting: pass /shop on to the demo shop process.

        Only active when SHOP_INTERNAL_URL is set. The address is fixed by the
        operator; nothing in the request can change where this goes.
        """
        import httpx

        upstream = settings().shop_internal_url.rstrip("/")
        if not upstream:
            raise HTTPException(status_code=404, detail="the demo shop is not served from here")
        headers = {
            k: v for k, v in request.headers.items() if k.lower() in ("content-type", "accept")
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                answer = await client.request(
                    request.method,
                    f"{upstream}{request.url.path}",
                    params=dict(request.query_params),
                    content=await request.body(),
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="the demo shop is not answering") from exc
        return Response(
            content=answer.content,
            status_code=answer.status_code,
            media_type=answer.headers.get("content-type"),
        )

    @app.get("/api/shop/config")
    def shop_config(db: Session = Depends(session_dep)) -> dict[str, Any]:
        row = _active_config(db)
        cfg = dict(row.config or DEFAULT_SHOP_CONFIG)
        cfg["chaos"] = _live_chaos(cfg.get("chaos"))
        return {"version": row.version, **cfg}

    @app.get("/api/incidents")
    def list_incidents(
        db: Session = Depends(session_dep),
        status: str | None = None,
        playbook: str | None = None,
    ) -> dict[str, Any]:
        stmt = select(Incident).order_by(Incident.created_at.desc())
        if status:
            stmt = stmt.where(Incident.status == status)
        if playbook:
            stmt = stmt.where(Incident.playbook == playbook)
        rows = list(db.scalars(stmt).all())
        return {"items": [incident_out(r) for r in rows]}

    @app.get("/api/incidents/{incident_id}")
    def get_incident(incident_id: UUID, db: Session = Depends(session_dep)) -> dict[str, Any]:
        row = db.get(Incident, incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="incident not found")
        db.refresh(row, attribute_names=["steps", "proposals"])
        for proposal in row.proposals:
            db.refresh(proposal, attribute_names=["executions"])
        from flatline.recovery import ledger

        body = incident_out(row, extra=True)
        body["money"] = ledger.summary(db, row.id)
        return body

    @app.get("/api/money")
    def money_summary(db: Session = Depends(session_dep)) -> dict[str, Any]:
        """What incidents cost, what was asked back and what came back, over everything."""
        from flatline.recovery import ledger

        return ledger.summary(db)

    @app.post("/api/proposals/{proposal_id}/approve", dependencies=[Depends(require_passcode)])
    def approve_proposal(proposal_id: UUID, db: Session = Depends(session_dep)) -> dict[str, Any]:
        return _decide_proposal(db, proposal_id, approved=True)

    @app.post("/api/proposals/{proposal_id}/reject", dependencies=[Depends(require_passcode)])
    def reject_proposal(proposal_id: UUID, db: Session = Depends(session_dep)) -> dict[str, Any]:
        return _decide_proposal(db, proposal_id, approved=False)

    @app.get("/api/events")
    def list_events(
        db: Session = Depends(session_dep),
        start_row: int = Query(default=0, ge=0),
        end_row: int = Query(default=100, ge=0),
        sort_field: str = "occurred_at",
        sort_dir: str = "desc",
        filter_event_type: str | None = None,
        filter_source: str | None = None,
        quick_filter: str | None = None,
        synthetic: bool | None = None,
    ) -> dict[str, Any]:
        stmt = select(Event)
        if filter_event_type:
            stmt = stmt.where(Event.event_type == filter_event_type)
        if filter_source:
            stmt = stmt.where(Event.source == filter_source)
        if synthetic is not None:
            stmt = stmt.where(Event.synthetic.is_(synthetic))
        if quick_filter:
            like = f"%{quick_filter}%"
            stmt = stmt.where(
                Event.event_type.ilike(like)
                | Event.resource_id.ilike(like)
                | Event.product_id.ilike(like)
                | Event.buyer_ref.ilike(like)
                | Event.error_code.ilike(like)
            )
        col = SORTABLE_EVENTS.get(sort_field, Event.occurred_at)
        stmt = stmt.order_by(col.desc() if sort_dir.lower() == "desc" else col.asc())
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(db.scalars(stmt.offset(start_row).limit(max(0, end_row - start_row))).all())
        return {"rows": [event_out(r) for r in rows], "lastRow": total}

    @app.get("/api/metrics/health")
    def metrics_health(db: Session = Depends(session_dep)) -> dict[str, Any]:
        from flatline.detector.worker import health_snapshot

        return health_snapshot(db)

    @app.get("/api/audit")
    def list_audit(
        db: Session = Depends(session_dep),
        incident_id: UUID | None = None,
        actor: str | None = None,
        start_row: int = 0,
        end_row: int = 200,
    ) -> dict[str, Any]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if incident_id:
            stmt = stmt.where(AuditLog.incident_id == incident_id)
        if actor:
            stmt = stmt.where(AuditLog.actor == actor)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(db.scalars(stmt.offset(start_row).limit(max(0, end_row - start_row))).all())
        return {"rows": [audit_out(r) for r in rows], "lastRow": total}

    @app.post("/api/chaos", dependencies=[Depends(require_passcode), Depends(require_inject_token)])
    def set_chaos(body: dict[str, Any], db: Session = Depends(session_dep)) -> dict[str, Any]:
        current = _active_config(db)
        cfg = dict(current.config or DEFAULT_SHOP_CONFIG)
        chaos = dict(cfg.get("chaos") or {})
        injected: list[str] = []
        if body.get("reset"):
            chaos = {}
            cfg["banner"] = ""
            cfg["paused_products"] = []
            cfg["plan_signups_paused"] = False
            cfg["currency"] = "USD"
        else:
            incoming = dict(body.get("chaos") or body)
            incoming.pop("note", None)
            incoming.pop("reset", None)
            chaos.update(incoming)
            if incoming.get("mock_response"):
                # A wave of declines or PayPal errors is not ours to fix, and in
                # real life it passes. The simulated one passes after a minute.
                until = utcnow() + timedelta(seconds=OUTAGE_SECONDS)
                chaos["mock_until"] = until.isoformat()
            if incoming.get("bad_currency"):
                cfg["currency"] = "EUR"
            injected = _inject_from_chaos(db, incoming)
        cfg["chaos"] = chaos
        # Notes read like a merchant's change log; the test intent stays in the audit log.
        if body.get("reset"):
            note = "Restore default storefront settings"
        elif (body.get("chaos") or body).get("bad_currency"):
            note = "Storefront currency set to EUR"
        else:
            note = str(body.get("note") or "chaos update")
        row = _new_config(db, cfg, author="human", note=note)
        audit(
            db,
            actor="human",
            action="chaos.reset" if body.get("reset") else "chaos.inject",
            details={
                "chaos": body.get("chaos") or {},
                "note": body.get("note"),
                "config_version": row.version,
                "synthetic_events": len(injected),
            },
        )
        incidents = _run_scan(db)
        HUB.publish("incident.updated", {"reason": "chaos", "version": row.version})
        out = config_out(row)
        out["injected"] = injected
        out["incidents"] = incidents
        return out

    @app.get("/api/stream")
    async def stream() -> StreamingResponse:
        return StreamingResponse(HUB.stream(), media_type="text/event-stream")

    @app.get("/api/policy/catalog")
    def policy_catalog() -> dict[str, Any]:
        from flatline.policy.catalog import catalog_public
        from flatline.policy.proxy import limits_public

        return {"items": catalog_public(), "limits": limits_public()}

    dashboard_dist = Path(__file__).resolve().parents[2] / "dashboard" / "dist"
    if dashboard_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dashboard_dist / "assets"), name="assets")

        @app.get("/")
        def _index() -> FileResponse:
            # Hashed assets are immutable; the entry document must never be stale.
            return FileResponse(
                dashboard_dist / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    return app


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _active_config(db: Session) -> ShopConfigVersion:
    row = db.scalar(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True)))
    if row:
        return row
    return ensure_default_config(db)


def _new_config(
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


def _store_normalized(db: Session, norm: dict[str, Any], *, emit: bool) -> Event:
    paypal_id = norm.get("paypal_event_id")
    if paypal_id:
        existing = db.scalar(select(Event).where(Event.paypal_event_id == paypal_id))
        if existing:
            existing._duplicate = True  # type: ignore[attr-defined]
            return existing
    row = Event(
        source=str(norm.get("source") or "paypal_webhook"),
        event_type=str(norm.get("event_type") or "UNKNOWN"),
        occurred_at=norm.get("occurred_at") or utcnow(),
        resource_id=norm.get("resource_id"),
        amount=norm.get("amount"),
        currency=norm.get("currency"),
        product_id=norm.get("product_id"),
        plan_id=norm.get("plan_id"),
        subscription_id=norm.get("subscription_id"),
        buyer_ref=norm.get("buyer_ref"),
        error_code=norm.get("error_code"),
        payload=norm.get("payload") or {},
        synthetic=bool(norm.get("synthetic")),
        verified=bool(norm.get("verified")),
        paypal_event_id=paypal_id,
    )
    db.add(row)
    db.flush()
    audit(
        db,
        actor="ingest",
        action="event.ingested",
        details={"event_type": row.event_type, "synthetic": row.synthetic},
    )
    if emit:
        HUB.publish("event.ingested", event_out(row))
    row._duplicate = False  # type: ignore[attr-defined]
    # A paid invoice or a completed subscription payment may settle a recovery request.
    from flatline.recovery import ledger

    ledger.confirm_from_event(db, row)
    return row


def _decide_proposal(db: Session, proposal_id: UUID, *, approved: bool) -> dict[str, Any]:
    row = db.get(Proposal, proposal_id)
    if not row:
        raise HTTPException(status_code=404, detail="proposal not found")
    if row.status not in {"pending"}:
        raise HTTPException(status_code=409, detail=f"proposal is {row.status}")
    row.status = "approved" if approved else "rejected"
    row.decided_by = "human"
    row.decided_at = utcnow()
    audit(
        db,
        actor="human",
        action="proposal.approved" if approved else "proposal.rejected",
        incident_id=row.incident_id,
        proposal_id=row.id,
    )
    # Commit before telling the dashboard, so the refresh it triggers sees the
    # decision, then again after the executor, before the (slower) verifier.
    db.commit()
    HUB.publish("proposal.updated", proposal_out(row))
    if approved:
        try:
            from flatline.policy.executor import execute_proposal

            execute_proposal(db, row)
            db.commit()
            HUB.publish("proposal.updated", proposal_out(row))
        except ImportError:
            pass
        except Exception as exc:
            log.warning("executor after approve failed: %s", exc)
        try:
            from flatline.loop import verify_incident

            incident = db.get(Incident, row.incident_id)
            # A recovery proposal is approved after the incident is resolved; the fix
            # has been verified already, so there is nothing to check again.
            if incident is not None and incident.status != "resolved":
                pending = list(
                    db.scalars(
                        select(Proposal).where(
                            Proposal.incident_id == incident.id, Proposal.status == "pending"
                        )
                    ).all()
                )
                if not pending:
                    import asyncio

                    asyncio.run(verify_incident(db, incident))
        except Exception as exc:
            log.warning("verify after approve failed: %s", exc)
    return proposal_out(row)


OUTAGE_SECONDS = 60


def _live_chaos(chaos: Any) -> dict[str, Any]:
    """The chaos settings the shop should act on: a simulated outage that has run its time is over."""
    out = dict(chaos or {})
    until = out.get("mock_until")
    if not until:
        return out
    try:
        ends = datetime.fromisoformat(str(until))
    except ValueError:
        return out
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=UTC)
    if datetime.now(UTC) >= ends:
        out.pop("mock_response", None)
        out.pop("mock_until", None)
    return out


def _chaos_flag(db: Session, key: str) -> bool:
    cfg = _active_config(db).config or {}
    chaos = cfg.get("chaos") or {}
    return bool(chaos.get(key))


def _ingest_payloads(db: Session, items: list[dict[str, Any]]) -> list[str]:
    stored: list[str] = []
    for item in items:
        norm = normalize_event(item, synthetic=True, verified=False)
        if item.get("event_type"):
            norm["event_type"] = str(item["event_type"])
        if item.get("product_id"):
            norm["product_id"] = item["product_id"]
        if item.get("plan_id"):
            norm["plan_id"] = item["plan_id"]
        if item.get("error_code"):
            norm["error_code"] = item["error_code"]
        if item.get("amount") is not None:
            norm["amount"] = _decimal(item["amount"])
        row = _store_normalized(db, norm, emit=True)
        stored.append(str(row.id))
    return stored


def _inject_from_chaos(db: Session, chaos: dict[str, Any]) -> list[str]:
    from flatline.ingest.faults import checkout_failures, refund_wave, renewal_failures

    kind = str(chaos.get("inject") or "")
    if chaos.get("bad_currency"):
        return _ingest_payloads(db, checkout_failures("CURRENCY_MISMATCH"))
    if chaos.get("mock_response") == "INSTRUMENT_DECLINED" or kind == "checkout_declines":
        return _ingest_payloads(db, checkout_failures("INSTRUMENT_DECLINED"))
    if chaos.get("mock_response") == "INTERNAL_SERVER_ERROR" or kind == "checkout_errors":
        return _ingest_payloads(db, checkout_failures("INTERNAL_SERVER_ERROR"))
    if kind == "refund_wave":
        return _ingest_payloads(db, refund_wave())
    if kind in {"renewal_failures", "renewals"}:
        return _ingest_payloads(db, renewal_failures())
    return []


def _start_workers() -> None:
    """Detector and agent loops as daemon threads, for a single hosted service."""
    import threading

    from flatline.detector.worker import run_forever as detector_forever
    from flatline.loop import run_forever as agents_forever

    for name, target in (("detector", detector_forever), ("agents", agents_forever)):
        threading.Thread(target=target, name=f"flatline-{name}", daemon=True).start()
    log.info("detector and agent loops running in the API process")


def _run_scan(db: Session) -> list[str]:
    from flatline.detector.worker import scan_once

    rows = scan_once(db)
    db.flush()
    return [str(r.id) for r in rows]


app = create_app()
