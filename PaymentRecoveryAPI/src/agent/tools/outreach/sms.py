"""
DEMO TOOL - sends the SMS through the `simulation-api` service
(`/simulate/sms`) instead of a real provider (e.g. Twilio, MSG91, Plivo). It
records the attempt and pushes it to the demo dashboard (`frontend-demo`) for
the frontend to display; no real SMS is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools.outreach._scheduler import schedule_outreach


@tool
async def send_sms(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
    scheduled_for: str | None = None,
) -> str:
    """Send a short SMS text message to the customer.

    Good for a quick nudge (e.g. "your payment failed, retry here: <link>") -
    cheap, fast, and works on any phone. Keep the message under ~160 characters.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: The SMS body to send.
        scheduled_for: Optional ISO-8601 time. Omit for immediate delivery.
    """
    return await schedule_outreach(
        case_id=case_id,
        channel="sms",
        recipient=phone_number,
        payload={
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
        scheduled_for=scheduled_for,
    )
