"""create webhook_event table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-04 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("razorpay_account_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("entity_status", sa.String(length=50), nullable=True),
        sa.Column("signature_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("processing_status", sa.String(length=20), server_default="RECEIVED", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("event_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["business.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(op.f("ix_webhook_event_business_id"), "webhook_event", ["business_id"])
    op.create_index(op.f("ix_webhook_event_razorpay_account_id"), "webhook_event", ["razorpay_account_id"])
    op.create_index(op.f("ix_webhook_event_event_type"), "webhook_event", ["event_type"])
    op.create_index(op.f("ix_webhook_event_entity_id"), "webhook_event", ["entity_id"])
    op.create_index(op.f("ix_webhook_event_processing_status"), "webhook_event", ["processing_status"])
    op.create_index(op.f("ix_webhook_event_event_created_at"), "webhook_event", ["event_created_at"])


def downgrade() -> None:
    op.drop_table("webhook_event")
