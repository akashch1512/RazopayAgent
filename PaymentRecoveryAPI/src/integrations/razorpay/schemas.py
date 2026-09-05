import pydantic


class RazorpayTokenResponse(pydantic.BaseModel):
    """Shape of the Razorpay `POST /token` response."""

    access_token: str
    refresh_token: str | None = None
    public_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    razorpay_account_id: str | None = None
    scope: str | None = None
