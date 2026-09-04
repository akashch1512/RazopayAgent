import datetime

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


class RecoveryCaseDetailResponse(RecoveryCaseResponse):
    """Case + its full merged delivery history (inbound, from Razorpay) and its
    audit trail of agent actions (outbound), both oldest first."""

    history: list[WebhookEventResponse]
    actions: list[CaseActionResponse]
