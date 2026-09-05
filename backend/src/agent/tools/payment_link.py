"""
DEMO TOOL - generates a payment link and sends it to the customer over an
existing channel (WhatsApp/SMS/email), instead of Razorpay's real Payment
Links API (https://razorpay.com/docs/api/payments/payment-links/create).

Deliberately does NOT expose the link as a separate "channel" - it composes
the full, correctly-formatted customer-facing message itself (the real link
included) and sends it via `/simulate/<channel>`, the exact same demo
endpoints `send_whatsapp_message`/`send_sms`/`send_email` use. That's the
point: the LLM never sees the link, so it can't paraphrase it, drop it, or
write a placeholder like "[Payment Link]" instead of a real URL - it only
ever gets to say a payment link was sent, in a plain past-tense report.
"""

import secrets
import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools._simulation_client import call_simulation_api

# channel -> (simulate endpoint, the contact field that endpoint expects)
_CHANNEL_ENDPOINTS: dict[str, tuple[str, str]] = {
    "whatsapp": ("/simulate/whatsapp", "phone_number"),
    "sms": ("/simulate/sms", "phone_number"),
    "email": ("/simulate/email", "email_address"),
}


def _compose_message(amount_hint: str, link: str) -> str:
    return (
        f"Hi! Here's a secure link to complete your payment ({amount_hint}): {link}\n\n"
        "It's valid for 24 hours. Reply here if you'd rather pay a different way or need help."
    )


@tool
async def send_payment_link(
    channel: str,
    contact: str,
    amount_hint: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> str:
    """Generate a payment link and send it to the customer in one message, so
    they can complete their payment in one click instead of just being told
    about the problem again.

    This tool writes and sends the entire customer-facing message itself,
    with a real clickable link - do not also send a separate WhatsApp/SMS/
    email message claiming to include "the payment link"; you don't know its
    URL, only this tool does, so a message you write yourself would either
    have no real link or a made-up placeholder like "[Payment Link]".

    Args:
        channel: Which channel to send it over - "whatsapp", "sms", or "email".
        contact: The customer's phone number (E.164, for whatsapp/sms) or
            email address (for email) to send the link to.
        amount_hint: A short human description of what's being paid (e.g.
            "order #1234, ₹420") - used only to label the link, not a real
            transaction amount.
    """
    if channel not in _CHANNEL_ENDPOINTS:
        return f"Unsupported channel {channel!r} for a payment link - use 'whatsapp', 'sms', or 'email'."

    path, contact_field = _CHANNEL_ENDPOINTS[channel]
    link = f"https://rzp.io/l/demo{secrets.token_urlsafe(6)}"
    message = _compose_message(amount_hint, link)

    payload: dict[str, typing.Any] = {
        "case_id": str(case_id),
        "customer_id": contact,
        contact_field: contact,
        "message": message,
    }
    if channel == "email":
        payload["subject"] = "Complete your payment"

    result = await call_simulation_api(path, payload)
    if result is None:
        return f"Could not reach the demo simulation service to send a payment link to {contact}; nothing was sent."

    return (
        f"Sent a payment link to {contact} via {channel} - visible on the demo dashboard now. "
        "This is a DEMO link, not a real Razorpay payment link - no real payment can be made through it."
    )
