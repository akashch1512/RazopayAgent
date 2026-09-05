"""create durable scheduled outreach actions

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-06 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_action",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_case.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_action_case_id", "scheduled_action", ["case_id"])
    op.create_index("ix_scheduled_action_scheduled_for", "scheduled_action", ["scheduled_for"])
    op.create_index("ix_scheduled_action_status", "scheduled_action", ["status"])
    op.create_index(
        "ix_scheduled_action_due",
        "scheduled_action",
        ["status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_action_due", table_name="scheduled_action")
    op.drop_index("ix_scheduled_action_status", table_name="scheduled_action")
    op.drop_index("ix_scheduled_action_scheduled_for", table_name="scheduled_action")
    op.drop_index("ix_scheduled_action_case_id", table_name="scheduled_action")
    op.drop_table("scheduled_action")
