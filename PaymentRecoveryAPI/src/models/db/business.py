import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.model_base import Base


class Business(Base):  # type: ignore
    """
    A sub-merchant business onboarded through the Razorpay Partner OAuth flow.

    All Razorpay tokens/secrets are stored encrypted (Fernet) - never in plaintext.
    """

    __tablename__ = "business"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    name: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=255), nullable=False)
    # Caller-supplied identifier to correlate this business with your own system.
    reference_id: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=False, unique=True
    )
    contact_email: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True
    )

    # OAuth handshake bookkeeping.
    oauth_state: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True, unique=True, index=True
    )
    status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=32), nullable=False, server_default="PENDING"
    )

    # Razorpay identifiers + encrypted credentials.
    razorpay_account_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True, unique=True
    )
    encrypted_access_token: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.Text, nullable=True
    )
    encrypted_refresh_token: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.Text, nullable=True
    )
    encrypted_public_token: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.Text, nullable=True
    )
    token_type: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=32), nullable=True
    )
    token_scope: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True
    )
    token_expires_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )

    # Webhook registered on the sub-merchant account.
    webhook_id: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=255), nullable=True
    )
    encrypted_webhook_secret: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(
        sqlalchemy.Text, nullable=True
    )

    # Drop-off poll rotation (Razorpay has no drop-off webhook - see
    # src.workers.tasks.dropoff_detection). Acts as a circular queue: whichever
    # ACTIVE business has the oldest/earliest `next_dropoff_poll_at` goes next.
    next_dropoff_poll_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True, index=True
    )
    last_dropoff_poll_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )

    # Business-customized agent behaviour - see `src.models.schemas.business.AgentSettings`.
    # Read directly by `src.agent.orchestration.context` / `src.agent.application.runner`; an empty dict
    # means "use the defaults", not "unconfigured".
    agent_settings: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False, server_default="{}")

    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    updated_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True),
        nullable=True,
        server_onupdate=sqlalchemy.schema.FetchedValue(for_update=True),
    )

    __mapper_args__ = {"eager_defaults": True}
