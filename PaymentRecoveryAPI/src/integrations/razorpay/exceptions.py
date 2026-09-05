class RazorpayIntegrationError(Exception):
    """Base error for any failed Razorpay Partner API interaction."""


class RazorpayOAuthError(RazorpayIntegrationError):
    """Raised when the OAuth authorization / token exchange fails."""


class RazorpayWebhookError(RazorpayIntegrationError):
    """Raised when creating a webhook on a sub-merchant account fails."""
