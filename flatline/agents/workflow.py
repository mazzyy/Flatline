"""Sequential agent workflow: Triage → Diagnostician → Remediator.

Orchestration is plain Python (same reason as original Flatline: inspectable
handoffs). Live nodes call LiteLLM; mock mode never imports it.
This module must not import the executor or any write-side PayPal client.
"""

from __future__ import annotations

from typing import Any

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
        }
        for r in rows
    ]


async def run_agents(db: Session, incident: Incident) -> WorkflowResult:
    events, background = tools.incident_events(db, incident)
    event_dicts = _event_dicts(events)
    result = WorkflowResult(incident)
    result.triage = run_triage(db, incident, event_dicts)
    # Config history is evidence only where the playbook says so (a config diff);
    # elsewhere it only invites the model to blame an unrelated earlier change.
    from flatline.playbooks.loader import load_playbooks

    playbook = load_playbooks().get(incident.playbook)
    history = (
        tools.config_history(db)
        if playbook is not None and "active_config_diff" in playbook.evidence
        else []
    )
    grouped = tools.events_by_group(events, background)
    gateway = build_read_gateway()
    paypal = await tools.paypal_snapshot(
        gateway,
        plan_id=incident.scope_value if incident.scope_key == "plan_id" else None,
        product_hint=incident.scope_value,
    )
    result.diagnosis = run_diagnostician(
        db, incident, event_dicts, history, {"events": grouped, "paypal": paypal}
    )
    result.remediation = run_remediator(db, incident, result.diagnosis)
    return result
