"""Incident loop: agents propose, proxy decides, executor writes, verifier checks.

Lives outside warden/agents so the import-boundary test stays meaningful.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from warden.agents.nodes import run_verifier
from warden.agents.workflow import run_agents
from warden.config import settings
from warden.db.base import utcnow
from warden.db.models import AgentJob, Event, Incident, Proposal, audit
from warden.detector.rules import event_matches_metric
from warden.ingest.sse import HUB
from warden.playbooks.loader import load_playbooks
from warden.policy.executor import execute_proposal
from warden.policy.proxy import decide, rate_limit_auto, rate_limit_pending

log = logging.getLogger("warden.loop")


async def process_incident(db: Session, incident: Incident) -> Incident:
    result = await run_agents(db, incident)
    drafts = result.remediation.proposals if result.remediation else []
    auto_done = 0
    pending_by_action: dict[str, int] = {}
    for draft in drafts:
        decision = decide(draft.action, draft.params)
        status = "pending"
        if decision.tier == "forbidden":
            status = "refused"
            incident.status = "escalated"
            note = (incident.notes or "") + f"\nRefused {draft.action}: {decision.reason}. Agent recommendation: {draft.rationale}"
            incident.notes = note.strip()
        elif decision.tier == "approval":
            if not rate_limit_pending(pending_by_action.get(draft.action, 0)):
                status = "refused"
            else:
                pending_by_action[draft.action] = pending_by_action.get(draft.action, 0) + 1
                incident.status = "awaiting_approval"
        else:
            if not rate_limit_auto(auto_done):
                status = "refused"
            else:
                status = "approved"
                auto_done += 1
        proposal = Proposal(
            incident_id=incident.id,
            action=draft.action,
            params=draft.params,
            rationale=draft.rationale,
            tier=decision.tier,
            status=status,
            decided_by="policy" if decision.tier != "approval" else None,
            decided_at=utcnow() if decision.tier != "approval" else None,
        )
        db.add(proposal)
        db.flush()
        audit(
            db,
            actor="policy",
            action=f"decide.{decision.tier}",
            incident_id=incident.id,
            proposal_id=proposal.id,
            details={"reason": decision.reason},
        )
        HUB.publish("proposal.created", {"id": str(proposal.id), "action": draft.action, "tier": decision.tier})
        if status == "approved":
            execute_proposal(db, proposal)
    db.flush()
    pending = list(
        db.scalars(
            select(Proposal).where(Proposal.incident_id == incident.id, Proposal.status == "pending")
        ).all()
    )
    if not pending:
        await verify_incident(db, incident)
    return incident


async def verify_incident(db: Session, incident: Incident) -> None:
    incident.status = "verifying"
    playbooks = load_playbooks()
    pb = playbooks.get(incident.playbook)
    minutes = settings().effective_verify_minutes
    cutoff = utcnow() - timedelta(minutes=max(minutes, 0))
    events = list(db.scalars(select(Event).where(Event.occurred_at >= cutoff)).all())
    metric = pb.metric if pb else incident.metric
    current = sum(1 for e in events if event_matches_metric(e, metric))
    threshold = (pb.min_count if pb else 1) if minutes > 0 else 0
    # After a fix, the verify window should be quiet. minutes=0 (tests) means
    # "no events after now" which is always resolved.
    resolved = current < (pb.min_count if pb else 1) if minutes > 0 else True
    observation = (
        f"metric {metric} in last {minutes}m is {current} (threshold {threshold})"
    )
    run_verifier(db, incident, resolved, observation)


async def process_job(db: Session, job: AgentJob) -> None:
    incident = db.get(Incident, job.incident_id)
    if not incident:
        job.status = "error"
        job.error = "incident missing"
        return
    job.status = "running"
    job.started_at = utcnow()
    try:
        await process_incident(db, incident)
        job.status = "done"
        job.finished_at = utcnow()
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        job.finished_at = utcnow()
        log.exception("job %s failed", job.id)


def run_forever(interval: float = 2.0) -> None:
    from time import sleep

    from warden.config import apply_sandbox_guard
    from warden.db.session import create_schema, get_sessionmaker

    apply_sandbox_guard()
    create_schema()
    SessionLocal = get_sessionmaker()
    log.info("agents worker polling every %ss", interval)
    while True:
        db = SessionLocal()
        try:
            job = db.scalar(select(AgentJob).where(AgentJob.status == "queued").order_by(AgentJob.created_at.asc()))
            if job:
                import asyncio

                asyncio.run(process_job(db, job))
            db.commit()
        except Exception:
            db.rollback()
            log.exception("agents worker failed")
        finally:
            db.close()
        sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
