"""merge webhook events into recovery_case

Revision ID: d4e5f6a7b8c9
Revises: 6cd1faa7ccb1
Create Date: 2026-09-06 00:00:00.000000

Adds `recovery_case` - one row per underlying problem (order/entity), merging
repeated webhook deliveries about the same case. `webhook_event` becomes a pure
history log: dispatch/priority/retry columns move to `recovery_case`.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "6cd1faa7ccb1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_case",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("razorpay_account_id", sa.String(length=64), nullable=False),
        sa.Column("case_key", sa.String(length=191), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("primary_entity_id", sa.String(length=64), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_contact", sa.String(length=32), nullable=True),
        sa.Column("latest_event_type", sa.String(length=100), nullable=False),
        sa.Column("latest_entity_status", sa.String(length=50), nullable=True),
        sa.Column("event_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("processing_status", sa.String(length=20), server_default="RECEIVED", nullable=False),
        sa.Column("priority", sa.SmallInteger(), server_default="5", nullable=False),
        sa.Column("priority_reason", sa.String(length=160), nullable=True),
        sa.Column("processing_attempts", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("next_visible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("first_event_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["business.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_account_id", "case_key", name="uq_recovery_case_account_key"),
    )
    op.create_index("ix_recovery_case_business_id", "recovery_case", ["business_id"])
    op.create_index(
        "ix_recovery_case_dispatch_queue", "recovery_case", ["processing_status", "priority", "first_event_at"]
    )
    op.create_index("ix_recovery_case_next_visible_at", "recovery_case", ["next_visible_at"])

    op.add_column("webhook_event", sa.Column("order_id", sa.String(length=64), nullable=True))
    op.add_column("webhook_event", sa.Column("case_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_webhook_event_order_id", "webhook_event", ["order_id"])
    op.create_index("ix_webhook_event_case_id", "webhook_event", ["case_id"])
    op.create_foreign_key(
        "fk_webhook_event_case_id", "webhook_event", "recovery_case", ["case_id"], ["id"], ondelete="SET NULL"
    )

    # Per-event processing state is superseded by recovery_case's dispatch lifecycle.
    op.drop_index("ix_webhook_event_processing_status", table_name="webhook_event")
    op.drop_column("webhook_event", "processing_status")
    op.drop_column("webhook_event", "processed_at")


def downgrade() -> None:
    op.add_column(
        "webhook_event",
        sa.Column("processing_status", sa.String(length=20), server_default="RECEIVED", nullable=False),
    )
    op.add_column("webhook_event", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_webhook_event_processing_status", "webhook_event", ["processing_status"])

    op.drop_constraint("fk_webhook_event_case_id", "webhook_event", type_="foreignkey")
    op.drop_index("ix_webhook_event_case_id", table_name="webhook_event")
    op.drop_index("ix_webhook_event_order_id", table_name="webhook_event")
    op.drop_column("webhook_event", "case_id")
    op.drop_column("webhook_event", "order_id")

    op.drop_table("recovery_case")
