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
    """Returned by `POST /onboard-business/` - redirect the business owner here to grant access."""

    business_id: int
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
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class WebhookConfigResponse(pydantic.BaseModel):
    """The live config of a business' registered Razorpay webhook (not cached)."""

    id: str
    url: str
    active: bool
    events: list[str]
    alert_email: str | None = None
    secret_exists: bool | None = None
    created_at: int | None = None


class RazorpayTokenResponse(pydantic.BaseModel):
    """Shape of the Razorpay `POST /token` response."""

    access_token: str
    refresh_token: str | None = None
    public_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    razorpay_account_id: str | None = None
    scope: str | None = None
