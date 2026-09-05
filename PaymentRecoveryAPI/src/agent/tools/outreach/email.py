"""
DEMO TOOL - sends the email through the `simulation-api` service
(`/simulate/email`) instead of a real transactional email provider (e.g.
SendGrid, Postmark, SES). It records the attempt and pushes it to the demo
dashboard (`frontend-demo`) for the frontend to display; no real email is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools.outreach._scheduler import schedule_outreach


@tool
async def send_email(
    email_address: str,
    subject: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
    scheduled_for: str | None = None,
) -> str:
    """Send an email to the customer.

    Best for a detailed, documented follow-up (e.g. an invoice recap, a formal
    payment-failure notice with a retry link) - less time-sensitive than
    SMS/WhatsApp/call, but leaves a durable record for the customer.

    Args:
        email_address: Customer's email address.
        subject: Email subject line.
        message: Email body (plain text).
        scheduled_for: Optional ISO-8601 time. Omit for immediate delivery.
    """
    return await schedule_outreach(
        case_id=case_id,
        channel="email",
        recipient=email_address,
        payload={
            "customer_id": email_address,
            "email_address": email_address,
            "subject": subject,
            "message": message,
        },
        scheduled_for=scheduled_for,
    )
