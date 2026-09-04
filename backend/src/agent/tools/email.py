"""
DEMO TOOL - sends the email through the `simulation-api` service
(`/simulate/email`) instead of a real transactional email provider (e.g.
SendGrid, Postmark, SES). It records the attempt and pushes it to the demo
dashboard (`frontend-demo`) for the frontend to display; no real email is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools._simulation_client import call_simulation_api


@tool
async def send_email(
    email_address: str,
    subject: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> str:
    """Send an email to the customer.

    Best for a detailed, documented follow-up (e.g. an invoice recap, a formal
    payment-failure notice with a retry link) - less time-sensitive than
    SMS/WhatsApp/call, but leaves a durable record for the customer.

    Args:
        email_address: Customer's email address.
        subject: Email subject line.
        message: Email body (plain text).
    """
    result = await call_simulation_api(
        "/simulate/email",
        {
            "case_id": str(case_id),
            "customer_id": email_address,
            "email_address": email_address,
            "subject": subject,
            "message": message,
        },
    )
    if result is None:
        return (
            f"Could not reach the demo simulation service to email {email_address}; "
            "nothing was recorded. No real email was sent either way."
        )
    return f"Simulated email to {email_address} - visible on the demo dashboard now. No real email was sent."
