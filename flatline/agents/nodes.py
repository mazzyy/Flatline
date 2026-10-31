"""Run one agent node, persist the step, emit SSE. Agents never import the executor."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from flatline.agents.schemas import DiagnosisOutput, RemediatorOutput, TriageOutput, VerifierOutput
from flatline.config import settings
from flatline.db.base import utcnow
from flatline.db.models import AgentStep, Incident, audit
from flatline.ingest.sse import HUB
from flatline.llm import mock_llm

PROMPTS = Path(__file__).resolve().parent / "prompts"


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
    audit(db, actor=f"agent:{node}", action=f"{node}.completed", incident_id=incident.id, details={"model": model})
    db.flush()
    HUB.publish("step.added", {"incident_id": str(incident.id), "node": node, "id": str(step.id)})
    return step


def _live_or_mock(node: str, model_kind: str, fallback: Any) -> Any:
    cfg = settings()
    if cfg.is_mock_llm:
        return fallback
    from flatline.llm.models import live_complete, resolve_model

    raw = live_complete(resolve_model(model_kind, cfg), _prompt(node) + "\n\n" + json.dumps(fallback))
    return raw


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
    out = mock_llm.triage(body, events)
    if not settings().is_mock_llm:
        try:
            raw = _live_or_mock("triage", "fast", out.model_dump())
            if isinstance(raw, str):
                out = TriageOutput.model_validate_json(raw)
        except (ValidationError, Exception):
            pass
    incident.severity = out.severity
    incident.status = "diagnosing"
    _persist(db, incident, "triage", body, out.model_dump(), model="mock" if settings().is_mock_llm else settings().model_fast, latency_ms=int((time.perf_counter() - started) * 1000))
    return out


def run_diagnostician(
    db: Session,
    incident: Incident,
    events: list[dict[str, Any]],
    config_history: list[dict[str, Any]],
    tool_bundle: dict[str, Any],
) -> DiagnosisOutput:
    started = time.perf_counter()
    body = {
        "id": str(incident.id),
        "playbook": incident.playbook,
        "scope_value": incident.scope_value,
        "events": events[:50],
        "config_history": config_history,
        "tools": tool_bundle,
    }
    out = mock_llm.diagnose(body, events, config_history, tool_bundle)
    if not settings().is_mock_llm:
        try:
            raw = _live_or_mock("diagnostician", "reasoning", out.model_dump())
            if isinstance(raw, str):
                out = DiagnosisOutput.model_validate_json(raw)
        except ValidationError:
            out = mock_llm.diagnose(body, events, config_history, tool_bundle)
    incident.root_cause = out.root_cause
    incident.evidence = {"claims": [c.model_dump() for c in out.evidence], "tools": tool_bundle}
    _persist(
        db,
        incident,
        "diagnostician",
        {"event_count": len(events), "tools": tool_bundle},
        out.model_dump(),
        model="mock" if settings().is_mock_llm else settings().model_reasoning,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=[{"tool": "events_by_group"}, {"tool": "config_history"}],
    )
    return out


def run_remediator(db: Session, incident: Incident, diagnosis: DiagnosisOutput) -> RemediatorOutput:
    started = time.perf_counter()
    body = {"id": str(incident.id), "playbook": incident.playbook, "scope_value": incident.scope_value}
    out = mock_llm.remediate(body, diagnosis)
    if not settings().is_mock_llm:
        try:
            raw = _live_or_mock("remediator", "reasoning", out.model_dump())
            if isinstance(raw, str):
                out = RemediatorOutput.model_validate_json(raw)
        except ValidationError:
            out = mock_llm.remediate(body, diagnosis)
    incident.status = "awaiting_approval"
    _persist(
        db,
        incident,
        "remediator",
        body,
        out.model_dump(),
        model="mock" if settings().is_mock_llm else settings().model_reasoning,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return out


def run_verifier(db: Session, incident: Incident, resolved: bool, observation: str) -> VerifierOutput:
    started = time.perf_counter()
    out = mock_llm.verify(resolved, observation)
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
        model="mock" if settings().is_mock_llm else settings().model_fast,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    HUB.publish("incident.updated", {"id": str(incident.id), "status": incident.status})
    return out
