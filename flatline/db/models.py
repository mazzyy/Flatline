"""SQLAlchemy models matching docs/spec.md Section 8."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from flatline.db.base import Base, IdMixin, utcnow


class Event(IdMixin, Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("paypal_event_id", name="uq_events_paypal_event_id"),)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    product_id: Mapped[str | None] = mapped_column(String(80))
    plan_id: Mapped[str | None] = mapped_column(String(80))
    subscription_id: Mapped[str | None] = mapped_column(String(80))
    buyer_ref: Mapped[str | None] = mapped_column(String(80))
    error_code: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paypal_event_id: Mapped[str | None] = mapped_column(String(80))


class ShopConfigVersion(IdMixin, Base):
    __tablename__ = "shop_config_versions"

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    author: Mapped[str] = mapped_column(String(16), nullable=False)  # human | flatline
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Incident(IdMixin, Base):
    __tablename__ = "incidents"

    playbook: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String(16), default="med")
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_value: Mapped[float] = mapped_column(default=0.0)
    baseline_value: Mapped[float] = mapped_column(default=0.0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revenue_at_risk_per_hour: Mapped[float] = mapped_column(default=0.0)
    title: Mapped[str] = mapped_column(String(240), default="")
    root_cause: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope_key: Mapped[str] = mapped_column(String(80), default="none")
    scope_value: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)

    steps: Mapped[list[AgentStep]] = relationship(back_populates="incident")
    proposals: Mapped[list[Proposal]] = relationship(back_populates="incident")


class AgentStep(IdMixin, Base):
    __tablename__ = "agent_steps"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    node: Mapped[str] = mapped_column(String(32), nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model: Mapped[str] = mapped_column(String(80), default="mock")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[list[Any]] = mapped_column(JSON, default=list)

    incident: Mapped[Incident] = relationship(back_populates="steps")


class Proposal(IdMixin, Base):
    __tablename__ = "proposals"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    decided_by: Mapped[str | None] = mapped_column(String(32))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    incident: Mapped[Incident] = relationship(back_populates="proposals")
    executions: Mapped[list[Execution]] = relationship(back_populates="proposal")


class Execution(IdMixin, Base):
    __tablename__ = "executions"

    proposal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proposals.id"), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)

    proposal: Mapped[Proposal] = relationship(back_populates="executions")


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_log"

    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"))
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proposals.id"))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class LedgerEntry(IdMixin, Base):
    """One line of an incident's money: what it cost, what was asked back, what came back.

    kind is one of: impact (sales lost or refunded while the incident ran),
    requested (a payment link sent or a renewal retried), recovered (PayPal confirmed
    the payment), refunded (a refund the executor sent).
    """

    __tablename__ = "money_ledger"

    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"))
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proposals.id"))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    # Invoice id, subscription id or capture id.
    ref: Mapped[str | None] = mapped_column(String(120))
    # Buyer or subscriber reference. Never an email address.
    counterparty: Mapped[str | None] = mapped_column(String(80))
    simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentJob(IdMixin, Base):
    """Postgres-backed queue so the agents worker can pick up incidents."""

    __tablename__ = "agent_jobs"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|error
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


DEFAULT_SHOP_CONFIG: dict[str, Any] = {
    "currency": "USD",
    "paused_products": [],
    "plan_signups_paused": False,
    "banner": "",
    "chaos": {},
}


def audit(
    session: Any,
    *,
    actor: str,
    action: str,
    incident_id: uuid.UUID | None = None,
    proposal_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        actor=actor,
        action=action,
        incident_id=incident_id,
        proposal_id=proposal_id,
        details=details or {},
        created_at=utcnow(),
    )
    session.add(row)
    return row
