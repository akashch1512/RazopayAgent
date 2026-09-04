"""
DEMO TOOL - places the call through the `simulation-api` service
(`/simulate/call`) instead of a real voice provider (e.g. Twilio Voice,
Exotel). It records the attempt and pushes it to the demo dashboard
(`frontend-demo`) for the frontend to display; no real call is placed.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools._simulation_client import call_simulation_api


@tool
async def make_call(
    phone_number: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> str:
    """Place an automated voice call to the customer to help recover a payment.

    Use this for high-priority or high-value cases, or after other channels
    (SMS/WhatsApp/email) went unanswered. Respect the customer's local time -
    do not call outside reasonable daytime hours.

    Args:
        phone_number: Customer's phone number in E.164 format, e.g. "+919876543210".
        message: A short, clear script describing what the call should communicate.
    """
    result = await call_simulation_api(
        "/simulate/call",
        {
            "case_id": str(case_id),
            "customer_id": phone_number,
            "phone_number": phone_number,
            "message": message,
        },
    )
    if result is None:
        return (
            f"Could not reach the demo simulation service to place a call to {phone_number}; "
            "nothing was recorded. No real call was placed either way."
        )
    return f"Simulated call to {phone_number} - visible on the demo dashboard now. No real call was placed."
