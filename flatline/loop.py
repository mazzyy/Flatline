"""Incident loop: agents propose, proxy decides, executor writes, verifier checks,
and once the incident is resolved the recovery planner asks the lost sales back.

Lives outside flatline/agents so the import-boundary test stays meaningful.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.agents.nodes import run_verifier
from flatline.agents.schemas import ProposalDraft
from flatline.agents.workflow import run_agents
from flatline.config import settings
from flatline.db.base import utcnow
from flatline.db.models import AgentJob, AgentStep, Event, Incident, Proposal, audit
from flatline.detector.rules import event_matches_metric
from flatline.ingest.sse import HUB
from flatline.playbooks.loader import load_playbooks
from flatline.policy.executor import _active_config as active_config
from flatline.policy.executor import execute_proposal
from flatline.policy.proxy import AGENT, PLANNER, decide, rate_limit_auto, rate_limit_pending
from flatline.recovery import ledger, planner

log = logging.getLogger("flatline.loop")


def red_team_probe(incident: Incident) -> ProposalDraft | None:
    """The playbook's forbidden test action, labelled so nobody mistakes it for the model's."""
    playbook = load_playbooks().get(incident.playbook)
    if playbook is None or not playbook.red_team_probe:
        return None
    params = {incident.scope_key: incident.scope_value} if incident.scope_value else {}
    return ProposalDraft(
        action=playbook.red_team_probe,
        params=params,
        rationale=(
            "Red-team probe added by the playbook, not by the model: a forbidden action "
            "sent on purpose to prove the policy proxy refuses it."
        ),
        expected_effect="refused by policy",
    )


async def process_incident(db: Session, incident: Incident) -> Incident:
    result = await run_agents(db, incident)
    drafts = list(result.remediation.proposals) if result.remediation else []
    probe = red_team_probe(incident)
    if probe is not None:
        drafts.append(probe)
    file_proposals(db, incident, drafts, source=AGENT)
    db.flush()
    pending = list(
        db.scalars(
            select(Proposal).where(
                Proposal.incident_id == incident.id, Proposal.status == "pending"
            )
        ).all()
    )
    if not pending:
        await verify_incident(db, incident)
    return incident


def file_proposals(
    db: Session, incident: Incident, drafts: list[ProposalDraft], *, source: str
) -> list[Proposal]:
    """Put each draft through the policy proxy, store it, and run what may run on its own.

    Agent drafts move the incident along (awaiting approval, escalated). The
    recovery planner files its drafts after the incident is resolved, so those
    leave the incident's status alone.
    """
    from_agent = source == AGENT
    filed: list[Proposal] = []
    auto_done = 0
    pending_by_action: dict[str, int] = {}
    for draft in drafts:
        decision = decide(
            draft.action,
            draft.params,
            refunded_today=ledger.refunded_last_24h(db),
            source=source,
        )
        status = "pending"
        if decision.tier == "forbidden":
            status = "refused"
            who = "Agent recommendation" if from_agent else "Recovery plan"
            if from_agent:
                incident.status = "escalated"
            note = (
                incident.notes or ""
            ) + f"\nRefused {draft.action}: {decision.reason}. {who}: {draft.rationale}"
            incident.notes = note.strip()
        elif decision.tier == "approval":
            if not rate_limit_pending(pending_by_action.get(draft.action, 0)):
                status = "refused"
            else:
                pending_by_action[draft.action] = pending_by_action.get(draft.action, 0) + 1
                if from_agent:
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
            details={"reason": decision.reason, "source": source},
        )
        HUB.publish(
            "proposal.created",
            {"id": str(proposal.id), "action": draft.action, "tier": decision.tier},
        )
        if status == "approved":
            execute_proposal(db, proposal)
        filed.append(proposal)
    return filed


def settle_incident(db: Session, incident: Incident) -> Proposal | None:
    """Once an incident is resolved: write down what it cost and ask the lost sales back.

    No model takes part. The planner reads the failed events, the ledger gets
    one impact line, and what is worth recovering becomes one proposal that
    goes through the same policy proxy as everything else. Returns that
    proposal, or None when there is nothing to ask back.
    """
    playbook = load_playbooks().get(incident.playbook)
    found = planner.plan(db, incident, playbook)
    if found.affected == 0:
        return None
    started = utcnow()
    ledger.record(
        db,
        kind=ledger.IMPACT,
        amount=found.impact,
        currency=found.currency,
        incident_id=incident.id,
        details={"count": found.affected, "estimated": found.estimated},
    )
    summary = {
        "affected": found.affected,
        "impact": f"{found.impact} {found.currency}",
        "recoverable": f"{found.total} {found.currency}",
        "to_contact": len(found.items),
        "left_alone": found.skipped,
        "action": found.action,
    }
    db.add(
        AgentStep(
            incident_id=incident.id,
            node="recovery",
            input={"playbook": incident.playbook, "events_since": str(incident.window_start)},
            output=summary,
            model="code, no model",
            latency_ms=int((utcnow() - started).total_seconds() * 1000),
            tool_calls=[{"tool": "events_since_incident"}],
            created_at=utcnow(),
        )
    )
    audit(
        db,
        actor="recovery",
        action="recovery.planned",
        incident_id=incident.id,
        details={k: v for k, v in summary.items() if k != "left_alone"},
    )
    db.flush()
    HUB.publish("step.added", {"incident_id": str(incident.id), "node": "recovery"})
    if not (settings().recovery_enabled and found.action and found.items):
        return None
    draft = ProposalDraft(
        action=found.action,
        params={"items": found.items, "total": str(found.total), "currency": found.currency},
        rationale=planner.rationale(found, incident),
        expected_effect="customers can complete the purchase they tried to make",
    )
    filed = file_proposals(db, incident, [draft], source=PLANNER)
    return filed[0] if filed else None


async def verify_incident(db: Session, incident: Incident, *, record_pending: bool = True) -> bool:
    """Check whether the metric has been quiet for the verify window.

    Returns True once the incident is resolved. With ``record_pending=False``
    a still-noisy window is not written as a verifier step (used by the
    periodic re-check so the timeline is not flooded).
    """
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
    observation = f"metric {metric} in last {minutes}m is {current} (threshold {threshold})"
    if resolved or record_pending:
        run_verifier(db, incident, resolved, observation)
    if resolved:
        clear_banner(db, incident)
        settle_incident(db, incident)
    return resolved


def clear_banner(db: Session, incident: Incident) -> Proposal | None:
    """Take the warning banner down once the incident that put it up is resolved.

    Plain code, through the same policy proxy as everything else. Nothing
    happens when this incident never set a banner, when it is already down,
    or while another incident is still open.
    """
    last = db.scalar(
        select(Proposal)
        .where(
            Proposal.incident_id == incident.id,
            Proposal.action.in_(("shop.banner.set", "shop.banner.clear")),
            Proposal.status == "executed",
        )
        .order_by(Proposal.decided_at.desc())
    )
    if not last or last.action != "shop.banner.set":
        return None
    if not (active_config(db).config or {}).get("banner"):
        return None  # a rollback already took it down
    still_open = db.scalar(
        select(Incident).where(Incident.id != incident.id, Incident.status != "resolved")
    )
    if still_open:
        return None
    draft = ProposalDraft(
        action="shop.banner.clear",
        params={},
        rationale="The incident is resolved and checkout has been quiet for the whole verify window, so the warning no longer applies.",
        expected_effect="customers stop seeing a warning about a problem that is over",
    )
    filed = file_proposals(db, incident, [draft], source=PLANNER)
    return filed[0] if filed else None


async def reverify_pending(db: Session) -> list[Incident]:
    """Re-check every incident still in ``verifying``; resolve the quiet ones."""
    resolved: list[Incident] = []
    for incident in db.scalars(select(Incident).where(Incident.status == "verifying")).all():
        if await verify_incident(db, incident, record_pending=False):
            resolved.append(incident)
    return resolved


REVERIFY_SECONDS = 15.0


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

    from flatline.config import apply_sandbox_guard
    from flatline.db.session import create_schema, get_sessionmaker

    apply_sandbox_guard()
    create_schema()
    SessionLocal = get_sessionmaker()
    log.info("agents worker polling every %ss", interval)
    last_reverify = 0.0
    while True:
        db = SessionLocal()
        try:
            import asyncio
            from time import monotonic

            job = db.scalar(
                select(AgentJob)
                .where(AgentJob.status == "queued")
                .order_by(AgentJob.created_at.asc())
            )
            if job:
                asyncio.run(process_job(db, job))
            if monotonic() - last_reverify >= REVERIFY_SECONDS:
                last_reverify = monotonic()
                for inc in asyncio.run(reverify_pending(db)):
                    log.info("incident %s resolved by verifier", inc.id)
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
