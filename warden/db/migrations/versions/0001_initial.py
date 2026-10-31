"""Initial schema (SPEC.md Section 8).

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_id", sa.String(80)),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(8)),
        sa.Column("product_id", sa.String(80)),
        sa.Column("plan_id", sa.String(80)),
        sa.Column("subscription_id", sa.String(80)),
        sa.Column("buyer_ref", sa.String(80)),
        sa.Column("error_code", sa.String(80)),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("paypal_event_id", sa.String(80)),
        sa.UniqueConstraint("paypal_event_id", name="uq_events_paypal_event_id"),
    )
    op.create_table(
        "shop_config_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON()),
        sa.Column("author", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text()),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("playbook", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16)),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("observed_value", sa.Float()),
        sa.Column("baseline_value", sa.Float()),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revenue_at_risk_per_hour", sa.Float()),
        sa.Column("title", sa.String(240)),
        sa.Column("root_cause", sa.Text()),
        sa.Column("evidence", sa.JSON()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("scope_key", sa.String(80)),
        sa.Column("scope_value", sa.String(80)),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("node", sa.String(32), nullable=False),
        sa.Column("input", sa.JSON()),
        sa.Column("output", sa.JSON()),
        sa.Column("model", sa.String(80)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("tool_calls", sa.JSON()),
    )
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("params", sa.JSON()),
        sa.Column("rationale", sa.Text()),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16)),
        sa.Column("decided_by", sa.String(32)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id"), nullable=False),
        sa.Column("request", sa.JSON()),
        sa.Column("response", sa.JSON()),
        sa.Column("success", sa.Boolean()),
        sa.Column("error", sa.Text()),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id")),
        sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id")),
        sa.Column("details", sa.JSON()),
    )
    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("status", sa.String(16)),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in (
        "agent_jobs",
        "audit_log",
        "executions",
        "proposals",
        "agent_steps",
        "incidents",
        "shop_config_versions",
        "events",
    ):
        op.drop_table(table)
