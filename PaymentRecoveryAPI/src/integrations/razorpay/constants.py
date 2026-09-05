"""
Configuration constants for the Razorpay Partner integration.

`WEBHOOK_EVENTS` is the list of event triggers subscribed to when a webhook is
created on a newly onboarded sub-merchant account. These are placeholder values -
replace / extend this list with the final set of events you want to listen to.
See: https://razorpay.com/docs/webhooks/supported-events/
"""

WEBHOOK_EVENTS: list[str] = [
    "payment.dispute.lost",
    "payment_link.expired",
    "invoice.expired",
    "subscription.paused", 
    "subscription.cancelled", 
    "subscription.pending", 
    "subscription.halted", 
    "payment.failed",

    
]

# Razorpay OAuth endpoints (paths are joined onto the configured base URLs).
AUTHORIZE_PATH: str = "/authorize"
TOKEN_PATH: str = "/token"

# Create-webhook endpoint template: /v2/accounts/{account_id}/webhooks
WEBHOOKS_PATH_TEMPLATE: str = "/v2/accounts/{account_id}/webhooks"
