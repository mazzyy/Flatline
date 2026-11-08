"""Run one agent node, persist the step, emit SSE. Agents never import the executor."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from flatline.agents.schemas import DiagnosisOutput, RemediatorOutput, TriageOutput, VerifierOutput
from flatline.config import settings
from flatline.db.base import utcnow
from flatline.db.models import AgentStep, Incident, audit
from flatline.ingest.sse import HUB
from flatline.llm import mock_llm

PROMPTS = Path(__file__).resolve().parent / "prompts"
log = logging.getLogger(__name__)


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def _persist(
    db: Session,
    incident: Incident,
    node: str,
    payload_in: dict[str, Any],
    payload_out: dict[str, Any],
    *,
    model: str,
    latency_ms: int,
    tool_calls: list[Any] | None = None,
) -> AgentStep:
    step = AgentStep(
        incident_id=incident.id,
        node=node,
        input=payload_in,
        output=payload_out,
        model=model,
        latency_ms=latency_ms,
        tool_calls=tool_calls or [],
        created_at=utcnow(),
    )
    db.add(step)
    audit(
        db,
        actor=f"agent:{node}",
        action=f"{node}.completed",
        incident_id=incident.id,
        details={"model": model},
    )
    db.flush()
    HUB.publish("step.added", {"incident_id": str(incident.id), "node": node, "id": str(step.id)})
    return step


def _ask_model[T: BaseModel](
    node: str, model_kind: str, node_input: Any, draft: T
) -> tuple[T, str]:
    """Return this node's answer and the label to record for it.

    The model answers from the input and the output schema alone. The playbook answer
    (`draft`) is the fallback: any failure (network, auth, quota, invalid JSON) keeps it
    and the label says so, so the timeline never credits a model with an answer it did
    not give.
    """
    cfg = settings()
    if cfg.is_mock_llm:
        return draft, "mock"
    from flatline.llm.models import live_complete, resolve_model

    primary = resolve_model(model_kind, cfg)
    chain = [primary] + [
        m.strip() for m in cfg.model_fallbacks.split(",") if m.strip() and m.strip() != primary
    ]
    # The model gets the evidence and the output schema. The playbook's own answer
    # (`draft`) is never shown to it; it is only the labelled fallback below.
    prompt = (
        _prompt(node)
        + "\n\nInput:\n"
        + json.dumps(node_input, default=str)
        + "\n\nReply with one JSON object that matches this JSON Schema, and nothing else:\n"
        + json.dumps(type(draft).model_json_schema())
    )
    for model in chain:
        try:
            raw = live_complete(model, prompt)
            return type(draft).model_validate_json(_json_object(raw)), model
        except Exception as exc:
            log.warning("%s: live call to %s failed: %s", node, model, str(exc)[:500])
    log.warning("%s: every model failed, keeping the playbook answer", node)
    return draft, f"{primary} (failed, playbook fallback)"


def _json_object(raw: str) -> str:
    """The JSON object in a reply, without Markdown fences or chatter around it."""
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start : end + 1] if start != -1 and end > start else raw


def run_triage(db: Session, incident: Incident, events: list[dict[str, Any]]) -> TriageOutput:
    started = time.perf_counter()
    body = {
        "id": str(incident.id),
        "playbook": incident.playbook,
        "observed_value": incident.observed_value,
        "baseline_value": incident.baseline_value,
        "revenue_at_risk_per_hour": incident.revenue_at_risk_per_hour,
        "scope_key": incident.scope_key,
        "scope_value": incident.scope_value,
    }
    out, model = _ask_model(
        "triage", "fast", {"incident": body, "events": events[:50]}, mock_llm.triage(body, events)
    )
    incident.severity = out.severity
    incident.status = "diagnosing"
    _persist(
        db,
        incident,
        "triage",
        body,
        out.model_dump(),
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return out


def run_diagnostician(
    db: Session,
    incident: Incident,
    events: list[dict[str, Any]],
    config_history: list[dict[str, Any]],
    tool_bundle: dict[str, Any],
) -> DiagnosisOutput:
    started = time.perf_counter()
    from flatline.playbooks.loader import load_playbooks

    playbook = load_playbooks().get(incident.playbook)
    body = {
        "id": str(incident.id),
        "playbook": incident.playbook,
        "scope_value": incident.scope_value,
        "evidence_to_check": playbook.evidence if playbook else [],
        "events": events[:50],
        "config_history": config_history,
        "tools": tool_bundle,
    }
    out, model = _ask_model(
        "diagnostician",
        "reasoning",
        body,
        mock_llm.diagnose(body, events, config_history, tool_bundle),
    )
    incident.root_cause = out.root_cause
    incident.evidence = {"claims": [c.model_dump() for c in out.evidence], "tools": tool_bundle}
    _persist(
        db,
        incident,
        "diagnostician",
        {"event_count": len(events), "tools": tool_bundle},
        out.model_dump(),
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=[
            {"tool": "events_by_group"},
            {"tool": "config_history"},
            *tool_bundle.get("paypal", {}).get("calls", []),
        ],
    )
    return out


def run_remediator(db: Session, incident: Incident, diagnosis: DiagnosisOutput) -> RemediatorOutput:
    started = time.perf_counter()
    from flatline.playbooks.loader import load_playbooks

    playbook = load_playbooks().get(incident.playbook)
    body = {
        "id": str(incident.id),
        "playbook": incident.playbook,
        "scope_value": incident.scope_value,
    }
    from flatline.policy.catalog import get as catalog_action

    allowed = {
        "allowed_actions": [
            {"action": spec.key, "description": spec.description, "params": spec.params}
            for spec in (catalog_action(a) for a in (playbook.allowed_actions if playbook else []))
            if spec is not None
        ]
    }
    out, model = _ask_model(
        "remediator",
        "reasoning",
        {**body, **allowed, "diagnosis": diagnosis.model_dump()},
        mock_llm.remediate(body, diagnosis),
    )
    incident.status = "awaiting_approval"
    _persist(
        db,
        incident,
        "remediator",
        body,
        out.model_dump(),
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return out


def run_verifier(
    db: Session, incident: Incident, resolved: bool, observation: str
) -> VerifierOutput:
    started = time.perf_counter()
    out, model = _ask_model(
        "verifier",
        "fast",
        {"resolved": resolved, "observation": observation},
        mock_llm.verify(resolved, observation),
    )
    # The metric check decides; the model only writes the words.
    out = out.model_copy(update={"resolved": resolved})
    if resolved:
        incident.status = "resolved"
        incident.resolved_at = utcnow()
    else:
        incident.status = "verifying"
    _persist(
        db,
        incident,
        "verifier",
        {"resolved": resolved, "observation": observation},
        out.model_dump(),
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    HUB.publish("incident.updated", {"id": str(incident.id), "status": incident.status})
    return out
