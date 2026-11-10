"""Money ledger: what an incident cost, what was asked back, what came back.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "money_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id")),
        sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id")),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8)),
        sa.Column("ref", sa.String(120)),
        sa.Column("counterparty", sa.String(80)),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON()),
    )


def downgrade() -> None:
    op.drop_table("money_ledger")
