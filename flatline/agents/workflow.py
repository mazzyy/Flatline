"""Sequential agent workflow: Triage → Diagnostician → Remediator.

Orchestration is plain Python (same reason as original Flatline: inspectable
handoffs). Live nodes can use ADK + LiteLLM; mock mode never imports them.
This module must not import the executor or any write-side PayPal client.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatline.agents import tools
from flatline.agents.nodes import run_diagnostician, run_remediator, run_triage
from flatline.agents.schemas import DiagnosisOutput, RemediatorOutput, TriageOutput
from flatline.db.models import Event, Incident
from flatline.paypal.factory import build_read_gateway


class WorkflowResult:
    def __init__(self, incident: Incident) -> None:
        self.incident = incident
        self.triage: TriageOutput | None = None
        self.diagnosis: DiagnosisOutput | None = None
        self.remediation: RemediatorOutput | None = None


def _event_dicts(rows: list[Event]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            "resource_id": r.resource_id,
            "error_code": r.error_code,
            "product_id": r.product_id,
            "plan_id": r.plan_id,
            "buyer_ref": r.buyer_ref,
            "currency": r.currency,
            "amount": str(r.amount) if r.amount is not None else None,
            "synthetic": r.synthetic,
        }
        for r in rows
    ]


async def run_agents(db: Session, incident: Incident) -> WorkflowResult:
    events = list(db.scalars(select(Event).order_by(Event.occurred_at.desc()).limit(50)).all())
    event_dicts = _event_dicts(events)
    result = WorkflowResult(incident)
    result.triage = run_triage(db, incident, event_dicts)
    history = tools.config_history(db)
    grouped = tools.events_by_group(db, incident.id, incident.playbook)
    gateway = build_read_gateway()
    paypal = await tools.paypal_snapshot(
        gateway, plan_id=incident.scope_value, product_hint=incident.scope_value
    )
    result.diagnosis = run_diagnostician(
        db, incident, event_dicts, history, {"events": grouped, "paypal": paypal}
    )
    result.remediation = run_remediator(db, incident, result.diagnosis)
    return result
