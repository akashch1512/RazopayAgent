import datetime
import enum

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.model_base import Base


class ScheduledActionStatus(enum.StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ScheduledAction(Base):  # type: ignore
    """Durable queue for immediate and future customer outreach."""

    __tablename__ = "scheduled_action"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.BigInteger, primary_key=True, autoincrement="auto"
    )
    case_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=32), nullable=False)
    recipient: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=255), nullable=False)
    payload: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False)
    scheduled_for: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, index=True
    )
    status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=20), nullable=False, server_default=ScheduledActionStatus.PENDING.value, index=True
    )
    attempts: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.SmallInteger, nullable=False, server_default="0"
    )
    celery_task_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=True
    )
    last_error: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(sqlalchemy.Text, nullable=True)
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    updated_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    __table_args__ = (
        sqlalchemy.Index("ix_scheduled_action_due", "status", "scheduled_for"),
    )

    __mapper_args__ = {"eager_defaults": True}
