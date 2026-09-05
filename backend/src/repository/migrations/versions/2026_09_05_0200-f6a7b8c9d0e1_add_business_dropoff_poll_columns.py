"""add business drop-off poll rotation columns

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-05 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business", sa.Column("next_dropoff_poll_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("business", sa.Column("last_dropoff_poll_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_business_next_dropoff_poll_at", "business", ["next_dropoff_poll_at"])


def downgrade() -> None:
    op.drop_index("ix_business_next_dropoff_poll_at", table_name="business")
    op.drop_column("business", "last_dropoff_poll_at")
    op.drop_column("business", "next_dropoff_poll_at")
