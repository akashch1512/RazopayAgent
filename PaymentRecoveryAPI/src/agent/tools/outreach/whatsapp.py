"""
DEMO TOOL - sends the WhatsApp message through the `simulation-api` service
(`/simulate/whatsapp`) instead of a real provider (WhatsApp Business/Cloud API
or a BSP like Gupshup/Twilio). It records the attempt and pushes it to the
demo dashboard (`frontend-demo`) for the frontend to display; no real message
is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools.outreach._scheduler import schedule_outreach


@tool
async def send_whatsapp_message(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
    scheduled_for: str | None = None,
) -> str:
    """Send a WhatsApp message to the customer.

    Often the highest-engagement channel for payment recovery - use it for the
    primary nudge, with rich context (amount, reason, a retry link) since it
    isn't length-constrained like SMS.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: The message body to send.
        scheduled_for: Optional ISO-8601 time. Omit for immediate delivery.
    """
    return await schedule_outreach(
        case_id=case_id,
        channel="whatsapp",
        recipient=phone_number,
        payload={
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
        scheduled_for=scheduled_for,
    )
