"""
DEMO TOOL - sends the push notification through the `simulation-api` service
(`/simulate/app-notification`) instead of a real provider (e.g. Firebase Cloud
Messaging, OneSignal) or the business' own notification service. It records
the attempt and pushes it to the demo dashboard (`frontend-demo`) for the
frontend to display; no real notification is sent.
"""

import typing

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.tools.outreach._scheduler import schedule_outreach


@tool
async def send_app_notification(
    customer_id: str,
    title: str,
    message: str,
    case_id: typing.Annotated[int, InjectedState("case_id")],
    scheduled_for: str | None = None,
) -> str:
    """Send an in-app / push notification to the customer's device.

    Use this when the customer is a known app user (e.g. via `customer_id`
    from the Razorpay entity) and a low-friction, in-context nudge is enough -
    cheaper than SMS/WhatsApp and doesn't require a phone number.

    Args:
        customer_id: The customer's Razorpay `customer_id` (or the business'
            own user id), used to look up their device/push token.
        title: Short notification title.
        message: Notification body text.
        scheduled_for: Optional ISO-8601 time. Omit for immediate delivery.
    """
    return await schedule_outreach(
        case_id=case_id,
        channel="app_notification",
        recipient=customer_id,
        payload={
            "customer_id": customer_id,
            "title": title,
            "message": message,
        },
        scheduled_for=scheduled_for,
    )
