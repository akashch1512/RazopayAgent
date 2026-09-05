"""
DEMO TOOL - places the call through the `simulation-api` service
(`/simulate/call`) instead of a real voice provider (e.g. Twilio Voice,
Exotel). It records the attempt and pushes it to the demo dashboard
(`frontend-demo`) for the frontend to display; no real call is placed.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools.outreach.scheduling import schedule_outreach


@tool
async def make_call(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
    scheduled_for: str | None = None,
) -> str:
    """Place an automated voice call to the customer to help recover a payment.

    Use this for high-priority or high-value cases, or after other channels
    (SMS/WhatsApp/email) went unanswered. Respect the customer's local time -
    do not call outside reasonable daytime hours.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: A short, clear script describing what the call should communicate.
        scheduled_for: Optional ISO-8601 time. Omit for immediate delivery.
    """
    return await schedule_outreach(
        case_id=case_id,
        channel="call",
        recipient=phone_number,
        payload={
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
        scheduled_for=scheduled_for,
    )
