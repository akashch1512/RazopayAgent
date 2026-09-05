import datetime

import pydantic

from src.models.schemas.base import BaseSchemaModel


class WebhookEventResponse(BaseSchemaModel):
    """One delivery merged into a case - the agent's (and now the API's) history."""

    id: int
    event_type: str
    entity_type: str | None
    entity_id: str | None
    entity_status: str | None
    order_id: str | None
    signature_verified: bool
    payload: dict
    event_created_at: datetime.datetime | None
    received_at: datetime.datetime


class RecoveryCaseResponse(BaseSchemaModel):
    id: int
    business_id: int | None
    razorpay_account_id: str
    case_key: str
    entity_type: str | None
    primary_entity_id: str | None
    customer_email: str | None
    customer_contact: str | None
    latest_event_type: str
    latest_entity_status: str | None
    event_count: int
    processing_status: str
    priority: int
    priority_reason: str | None
    processing_attempts: int
    last_error: str | None
    first_event_at: datetime.datetime
    last_event_at: datetime.datetime
    resolved_at: datetime.datetime | None


class CaseActionResponse(BaseSchemaModel):
    """One audit-trail entry: a tool the agent called, what it sent, and what
    came back (if anything) - the outbound counterpart to `WebhookEventResponse`."""

    id: int
    tool_name: str
    status: str
    tool_input: dict
    tool_output: str | None
    created_at: datetime.datetime


class CustomerFeedbackRequest(BaseSchemaModel):
    """A customer's reply on some channel - from the demo dashboard today, a
    real inbound channel eventually. See `POST /recovery-cases/{id}/feedback`."""

    channel: str
    message: str = pydantic.Field(..., min_length=1)


class ManualRecoveryRequest(BaseSchemaModel):
    """A human explicitly asking the agent to chase a specific order/invoice -
    "start custom recovery" on the dashboard. See
    `POST /onboard-business/{id}/recovery-cases/start`."""

    order_reference: str = pydantic.Field(..., min_length=1, max_length=191)
    customer_email: pydantic.EmailStr | None = None
    customer_contact: str | None = pydantic.Field(default=None, max_length=32)
    amount: int | None = pydantic.Field(default=None, ge=0)
    currency: str = pydantic.Field(default="INR", max_length=10)
    reason: str = pydantic.Field(..., min_length=1, max_length=500)


class RecoveryCaseDetailResponse(RecoveryCaseResponse):
    """Case + its full merged delivery history (inbound, from Razorpay) and its
    audit trail of agent actions (outbound), both oldest first."""

    history: list[WebhookEventResponse]
    actions: list[CaseActionResponse]
