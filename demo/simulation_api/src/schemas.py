"""Request/response shapes. Kept close to the raw store dicts on purpose -
`frontend-demo` reads these fields directly (see `dashboardUtils.js`)."""

import typing

import pydantic


class ActionRequest(pydantic.BaseModel):
    """Common fields every "simulate an outreach action" endpoint takes."""

    case_id: str
    customer_id: str
    message: str
    payment_id: str | None = None
    context: dict[str, typing.Any] = pydantic.Field(default_factory=dict)


class CallActionRequest(ActionRequest):
    phone_number: str


class SmsActionRequest(ActionRequest):
    phone_number: str


class WhatsappActionRequest(ActionRequest):
    phone_number: str


class EmailActionRequest(ActionRequest):
    email_address: str
    subject: str


class AppNotificationActionRequest(ActionRequest):
    title: str


class ActionResponse(pydantic.BaseModel):
    status: typing.Literal["simulated"] = "simulated"
    channel: str
    event_id: str
    detail: str


class ReplyRequest(pydantic.BaseModel):
    case_id: str
    channel: str
    message: str


class PayRequest(pydantic.BaseModel):
    case_id: str


class DashboardMetrics(pydantic.BaseModel):
    handled_today: int
    in_progress: int
    queued_cases: int
    recovery_rate: int


class DashboardResponse(pydantic.BaseModel):
    recovery_case: dict[str, typing.Any]
    metrics: DashboardMetrics
