import datetime
import enum

import sqlalchemy
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class RecoveryCaseStatus(enum.StrEnum):
    """
    Lifecycle of a merged recovery case - this, not the individual webhook
    event, is what the agent worker actually claims and processes.

        RECEIVED   - case created, not yet handed to the broker
        QUEUED     - dispatched, waiting for the agent worker
        PROCESSING - claimed by the worker, agent run in flight
        PROCESSED  - the agent finished a run (case may reopen on a new failure)
        FAILED     - transient failure, will be retried
        DEAD       - retries exhausted, needs a human
        RESOLVED   - a resolving event arrived (payment eventually succeeded, ...)
    """

    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DEAD = "DEAD"
    RESOLVED = "RESOLVED"


RECLAIMABLE_CASE_STATUSES: tuple[str, ...] = (
    RecoveryCaseStatus.RECEIVED.value,
    RecoveryCaseStatus.QUEUED.value,
    RecoveryCaseStatus.PROCESSING.value,
    RecoveryCaseStatus.FAILED.value,
)
# A case in one of these is currently "spoken for" - a new event should merge
# into its history without triggering a second dispatch.
IN_FLIGHT_CASE_STATUSES: tuple[str, ...] = (
    RecoveryCaseStatus.QUEUED.value,
    RecoveryCaseStatus.PROCESSING.value,
)


class RecoveryCase(Base):  # type: ignore
    """
    One case = one underlying problem (an order a customer keeps failing to
    pay, a halted subscription, ...), merged from N `webhook_event` deliveries.
    See `src.integrations.razorpay.recovery_case` for the grouping rule.
    """

    __tablename__ = "recovery_case"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.BigInteger, primary_key=True, autoincrement="auto"
    )

    business_id: SQLAlchemyMapped[int | None] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("business.id", ondelete="SET NULL"), nullable=True, index=True
    )
    razorpay_account_id: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=False
    )
    # `order:<id>` / `entity:<id>` / `event:<dedupe_key>` - see recovery_case.py.
    case_key: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=191), nullable=False)

    entity_type: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=50), nullable=True
    )
    # The order/entity id the case is keyed on, kept flat for cheap filtering.
    primary_entity_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True
    )
    customer_email: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True
    )
    customer_contact: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=32), nullable=True
    )

    latest_event_type: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=100), nullable=False
    )
    latest_entity_status: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=50), nullable=True
    )
    # How many webhook deliveries have been merged into this case, e.g. "customer
    # retried payment 4 times" - the whole point of this table.
    event_count: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.Integer, nullable=False, server_default="1"
    )

    processing_status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=20), nullable=False, server_default=RecoveryCaseStatus.RECEIVED.value
    )
    priority: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.SmallInteger, nullable=False, server_default="5"
    )
    priority_reason: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=160), nullable=True
    )
    processing_attempts: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.SmallInteger, nullable=False, server_default="0"
    )
    next_visible_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )
    queued_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )
    celery_task_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True
    )
    last_error: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(sqlalchemy.Text, nullable=True)

    first_event_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    last_event_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    resolved_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        sqlalchemy.UniqueConstraint("razorpay_account_id", "case_key", name="uq_recovery_case_account_key"),
        sqlalchemy.Index(
            "ix_recovery_case_dispatch_queue",
            "processing_status",
            "priority",
            "first_event_at",
        ),
        sqlalchemy.Index("ix_recovery_case_next_visible_at", "next_visible_at"),
    )

    __mapper_args__ = {"eager_defaults": True}
