import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped
from sqlalchemy.orm import mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.model_base import Base


class CaseAction(Base):  # type: ignore
    """
    The audit trail: one row per tool call the agent made on a recovery case -
    what was attempted, what was sent (`tool_input`), and what came back
    (`tool_output`), if anything.

    Complements `WebhookEvent` (the inbound side - what Razorpay told us) with
    the outbound side - what the agent actually did about it. Covers both our
    own static tools and the dynamically-loaded Razorpay MCP tools, recorded
    generically via `src.agent.infrastructure.audit.CaseActionAuditHandler` rather than
    per-tool code.
    """

    __tablename__ = "case_action"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.BigInteger, primary_key=True, autoincrement="auto"
    )
    case_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # e.g. "make_call", "send_sms", "send_whatsapp_message", "send_email",
    # "send_app_notification", "check_payment_status", "record_case_memory", or a
    # Razorpay MCP tool name such as "razorpay__fetch_payment".
    tool_name: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=150), nullable=False, index=True
    )
    status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=20), nullable=False)
    tool_input: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False, server_default="{}")
    tool_output: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(sqlalchemy.Text, nullable=True)

    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now(), index=True
    )

    __mapper_args__ = {"eager_defaults": True}
