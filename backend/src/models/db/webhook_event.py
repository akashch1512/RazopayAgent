import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class WebhookEvent(Base):  # type: ignore
    """
    One Razorpay webhook delivery, verbatim history.

    Dispatch, priority and retries all live on `RecoveryCase` - this table is an
    append-only log: every delivery is stored (and merged into a case via
    `case_id`), but only the *case* is ever handed to the agent worker. A
    customer retrying a failing payment five times yields five rows here and
    one `recovery_case`.
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

    # The merged case this delivery belongs to. See `RecoveryCase`.
    case_id: SQLAlchemyMapped[int | None] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("recovery_case.id", ondelete="SET NULL"), nullable=True, index=True
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
    # Present on payment/invoice-shaped entities - the grouping signal for cases.
    order_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True, index=True
    )

    signature_verified: SQLAlchemyMapped[bool] = sqlalchemy_mapped_column(
        sqlalchemy.Boolean, nullable=False, server_default=sqlalchemy.sql.expression.false()
    )

    payload: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False)

    # Razorpay's own event timestamp (top-level `created_at`, epoch seconds).
    event_created_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True, index=True
    )
    received_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    __mapper_args__ = {"eager_defaults": True}
