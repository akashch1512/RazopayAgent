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

from src.agent.tools._simulation_client import call_simulation_api


@tool
async def send_whatsapp_message(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> str:
    """Send a WhatsApp message to the customer.

    Often the highest-engagement channel for payment recovery - use it for the
    primary nudge, with rich context (amount, reason, a retry link) since it
    isn't length-constrained like SMS.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: The message body to send.
    """
    result = await call_simulation_api(
        "/simulate/whatsapp",
        {
            "case_id": str(case_id),
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
    )
    if result is None:
        return (
            f"Could not reach the demo simulation service to WhatsApp {phone_number}; "
            "nothing was recorded. No real message was sent either way."
        )
    return (
        f"Simulated WhatsApp message to {phone_number} - visible on the demo dashboard now. "
        "No real message was sent."
    )
