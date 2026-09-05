"""create case_action table (audit trail)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-05 01:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_action",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("tool_name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tool_input", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("tool_output", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_case.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_action_case_id", "case_action", ["case_id"])
    op.create_index("ix_case_action_tool_name", "case_action", ["tool_name"])
    op.create_index("ix_case_action_created_at", "case_action", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_case_action_created_at", table_name="case_action")
    op.drop_index("ix_case_action_tool_name", table_name="case_action")
    op.drop_index("ix_case_action_case_id", table_name="case_action")
    op.drop_table("case_action")
