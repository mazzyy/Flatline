"""Plain dict serializers for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from flatline.db.models import (
    AgentStep,
    AuditLog,
    Event,
    Execution,
    Incident,
    Proposal,
    ShopConfigVersion,
)


def _v(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def event_out(row: Event) -> dict[str, Any]:
    return {
        "id": _v(row.id),
        "created_at": _v(row.created_at),
        "source": row.source,
        "event_type": row.event_type,
        "occurred_at": _v(row.occurred_at),
        "resource_id": row.resource_id,
        "amount": _v(row.amount),
        "currency": row.currency,
        "product_id": row.product_id,
        "plan_id": row.plan_id,
        "subscription_id": row.subscription_id,
        "buyer_ref": row.buyer_ref,
        "error_code": row.error_code,
        "synthetic": row.synthetic,
        "verified": row.verified,
        "paypal_event_id": row.paypal_event_id,
    }


def incident_out(row: Incident, *, extra: bool = False) -> dict[str, Any]:
    body = {
        "id": _v(row.id),
        "created_at": _v(row.created_at),
        "playbook": row.playbook,
        "status": row.status,
        "severity": row.severity,
        "metric": row.metric,
        "observed_value": row.observed_value,
        "baseline_value": row.baseline_value,
        "window_start": _v(row.window_start),
        "window_end": _v(row.window_end),
        "revenue_at_risk_per_hour": row.revenue_at_risk_per_hour,
        "title": row.title,
        "root_cause": row.root_cause,
        "evidence": row.evidence,
        "resolved_at": _v(row.resolved_at),
        "scope_key": row.scope_key,
        "scope_value": row.scope_value,
        "notes": row.notes,
    }
    if extra:
        body["steps"] = [step_out(s) for s in row.steps]
        body["proposals"] = [proposal_out(p, extra=True) for p in row.proposals]
    return body


def step_out(row: AgentStep) -> dict[str, Any]:
    return {
        "id": _v(row.id),
        "incident_id": _v(row.incident_id),
        "node": row.node,
        "input": row.input,
        "output": row.output,
        "model": row.model,
        "latency_ms": row.latency_ms,
        "tool_calls": row.tool_calls,
        "created_at": _v(row.created_at),
    }


def proposal_out(row: Proposal, *, extra: bool = False) -> dict[str, Any]:
    body = {
        "id": _v(row.id),
        "incident_id": _v(row.incident_id),
        "action": row.action,
        "params": row.params,
        "rationale": row.rationale,
        "tier": row.tier,
        "status": row.status,
        "decided_by": row.decided_by,
        "decided_at": _v(row.decided_at),
        "created_at": _v(row.created_at),
    }
    if extra:
        body["executions"] = [execution_out(e) for e in row.executions]
    return body


def execution_out(row: Execution) -> dict[str, Any]:
    return {
        "id": _v(row.id),
        "proposal_id": _v(row.proposal_id),
        "request": row.request,
        "response": row.response,
        "success": row.success,
        "error": row.error,
        "created_at": _v(row.created_at),
    }


def audit_out(row: AuditLog) -> dict[str, Any]:
    return {
        "id": _v(row.id),
        "created_at": _v(row.created_at),
        "actor": row.actor,
        "action": row.action,
        "incident_id": _v(row.incident_id),
        "proposal_id": _v(row.proposal_id),
        "details": row.details,
    }


def config_out(row: ShopConfigVersion) -> dict[str, Any]:
    return {
        "version": row.version,
        "config": row.config,
        "author": row.author,
        "active": row.active,
        "note": row.note,
        "id": _v(row.id),
    }
