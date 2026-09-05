import datetime

import pydantic

from src.models.schemas.base import BaseSchemaModel


class BusinessOnboardRequest(BaseSchemaModel):
    """Payload to kick off onboarding of a new sub-merchant business."""

    name: str = pydantic.Field(..., min_length=1, max_length=255)
    reference_id: str = pydantic.Field(..., min_length=1, max_length=255)
    contact_email: pydantic.EmailStr | None = None
    # Optional override of the configured default scope.
    scope: str | None = pydantic.Field(default=None, max_length=255)


class BusinessOnboardInitResponse(BaseSchemaModel):
    """
    Returned by `POST /businesses/` - redirect the business owner here to grant
    access. No `Business` row exists yet at this point - `business_id` is only
    populated once the OAuth callback completes and creates one.
    """

    business_id: int | None = None
    reference_id: str
    status: str
    authorization_url: str
    state: str


class BusinessResponse(BaseSchemaModel):
    id: int
    name: str
    reference_id: str
    contact_email: str | None
    status: str
    razorpay_account_id: str | None
    token_scope: str | None
    token_expires_at: datetime.datetime | None
    webhook_id: str | None
    agent_settings: dict
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


# Every channel tool name the agent could be restricted to - kept here (not
# imported from `src.agent.tools`) so this schema module has no dependency on
# the agent package.
AGENT_CHANNELS: tuple[str, ...] = (
    "make_call",
    "send_sms",
    "send_whatsapp_message",
    "send_app_notification",
    "send_email",
)


class AgentSettings(BaseSchemaModel):
    """
    A business' customization of how its agent behaves - read directly by
    `src.agent.context` (folded into the system prompt) and `src.agent.runner`
    (which tools it's allowed to use). An empty/default instance means "use
    the built-in defaults", not "nothing is allowed".
    """

    business_description: str | None = pydantic.Field(default=None, max_length=1000)
    tone: str = pydantic.Field(default="friendly and professional", max_length=200)
    custom_instructions: str | None = pydantic.Field(default=None, max_length=2000)
    # `None` = every channel tool is allowed (the default). An empty list
    # would disable all outreach, which is almost certainly a mistake, so it's
    # only reachable by explicitly listing zero channels, not by omission.
    enabled_channels: list[str] | None = None

    @pydantic.field_validator("enabled_channels")
    @classmethod
    def _validate_channels(cls, value: list[str] | None) -> list[str] | None:
        """Drop unknown channel names rather than rejecting - stored settings
        may reference a channel that has since been removed (e.g. the retired
        `send_payment_link`), and a stale value must not 500 the read path.
        Returns `None` if nothing recognizable remains, so the agent falls back
        to "all channels allowed" instead of "no outreach at all"."""
        if value is None:
            return None
        known = [channel for channel in value if channel in AGENT_CHANNELS]
        return known or None


class WebhookConfigResponse(pydantic.BaseModel):
    """The live config of a business' registered Razorpay webhook (not cached)."""

    id: str
    url: str
    active: bool
    events: list[str]
    alert_email: str | None = None
    secret_exists: bool | None = None
    created_at: int | None = None


class InvoiceCustomerDetails(pydantic.BaseModel):
    name: str | None = None
    email: str | None = None
    contact: str | None = None


class InvoiceResponse(pydantic.BaseModel):
    """A subset of Razorpay's invoice object - just what the dashboard needs
    to list invoices and let a human start a B2B chase on one."""

    id: str
    status: str
    invoice_number: str | None = None
    amount: int
    amount_paid: int = 0
    amount_due: int = 0
    currency: str = "INR"
    short_url: str | None = None
    customer_details: InvoiceCustomerDetails = pydantic.Field(default_factory=InvoiceCustomerDetails)
    created_at: int | None = None


class StartInvoiceChaseRequest(BaseSchemaModel):
    """Optional overrides when a human kicks off a B2B chase for one invoice."""

    reason: str | None = pydantic.Field(default=None, max_length=500)


class RazorpayTokenResponse(pydantic.BaseModel):
    """Shape of the Razorpay `POST /token` response."""

    access_token: str
    refresh_token: str | None = None
    public_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    razorpay_account_id: str | None = None
    scope: str | None = None
