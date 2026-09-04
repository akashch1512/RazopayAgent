"""
DEMO TOOL - sends the SMS through the `simulation-api` service
(`/simulate/sms`) instead of a real provider (e.g. Twilio, MSG91, Plivo). It
records the attempt and pushes it to the demo dashboard (`frontend-demo`) for
the frontend to display; no real SMS is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools._simulation_client import call_simulation_api


@tool
async def send_sms(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> str:
    """Send a short SMS text message to the customer.

    Good for a quick nudge (e.g. "your payment failed, retry here: <link>") -
    cheap, fast, and works on any phone. Keep the message under ~160 characters.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: The SMS body to send.
    """
    result = await call_simulation_api(
        "/simulate/sms",
        {
            "case_id": str(case_id),
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
    )
    if result is None:
        return (
            f"Could not reach the demo simulation service to SMS {phone_number}; "
            "nothing was recorded. No real SMS was sent either way."
        )
    return f"Simulated SMS to {phone_number} - visible on the demo dashboard now. No real SMS was sent."
