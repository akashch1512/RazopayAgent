import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class WebhookEvent(Base):  # type: ignore
    """
    A single Razorpay webhook delivery, normalized into a shape that is uniform
    across every event type (payments, payouts, subscriptions, invoices,
    disputes, payment links, bill payments, ...).

    The full verbatim event is kept in `payload` (JSONB) for the agent to mine;
    the flat columns are extracted for cheap filtering / indexing / context
    windows.
    """

    __tablename__ = "webhook_event"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.BigInteger, primary_key=True, autoincrement="auto"
    )

    # Idempotency key. Prefer Razorpay's `X-Razorpay-Event-Id` header; fall back
    # to a sha256 of the raw body. A unique index makes redelivery a no-op.
    dedupe_key: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=128), nullable=False, unique=True
    )

    # Owning business (resolved from `account_id`). Nullable: we never drop an
    # event just because the account is unknown - it is still agent context.
    business_id: SQLAlchemyMapped[int | None] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("business.id", ondelete="SET NULL"), nullable=True, index=True
    )
    razorpay_account_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True, index=True
    )

    # e.g. "payment.failed", "subscription.halted", "payout.rejected".
    event_type: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=100), nullable=False, index=True
    )
    # Primary entity carried by the event: "payment", "payout", "subscription", ...
    entity_type: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=50), nullable=True
    )
    # Id of that entity: "pay_XXX", "pout_XXX", "sub_XXX", ...
    entity_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True, index=True
    )
    # Status of that entity at delivery time: "failed", "halted", "expired", ...
    entity_status: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=50), nullable=True
    )

    signature_verified: SQLAlchemyMapped[bool] = sqlalchemy_mapped_column(
        sqlalchemy.Boolean, nullable=False, server_default=sqlalchemy.sql.expression.false()
    )

    # Downstream processing state (consumed later by the LangGraph agent).
    # RECEIVED -> PROCESSED / FAILED
    processing_status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=20), nullable=False, server_default="RECEIVED", index=True
    )

    payload: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False)

    # Razorpay's own event timestamp (top-level `created_at`, epoch seconds).
    event_created_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True, index=True
    )
    received_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    processed_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )

    __mapper_args__ = {"eager_defaults": True}
