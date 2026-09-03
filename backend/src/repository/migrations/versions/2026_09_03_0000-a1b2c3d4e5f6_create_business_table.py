"""create business table

Revision ID: a1b2c3d4e5f6
Revises: 60d1844cb5d3
Create Date: 2026-09-03 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "60d1844cb5d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("oauth_state", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("razorpay_account_id", sa.String(length=255), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("encrypted_public_token", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=32), nullable=True),
        sa.Column("token_scope", sa.String(length=255), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_id", sa.String(length=255), nullable=True),
        sa.Column("encrypted_webhook_secret", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_id"),
        sa.UniqueConstraint("oauth_state"),
        sa.UniqueConstraint("razorpay_account_id"),
    )
    op.create_index(op.f("ix_business_oauth_state"), "business", ["oauth_state"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_business_oauth_state"), table_name="business")
    op.drop_table("business")
