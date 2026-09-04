"""
PLACEHOLDER TOOL - not wired to a real status source yet.

Intended integration: a simple REST call to Razorpay's Payments/Orders API (or
an internal tracker) to check the *current* state of a payment/order, since the
recovery case's stored `entity_status` is a snapshot from the last webhook and
may be stale by the time the agent acts. The Razorpay MCP tools (see
`src.agent.mcp`) may end up covering this same need with live data - this tool
stays as an explicit, cheap fallback / first check.
"""

import loguru
from langchain_core.tools import tool


@tool
async def track_payment_status(order_id: str | None = None, payment_id: str | None = None) -> str:
    """Look up the current status of a payment or order before acting on it.

    Call this before nudging the customer again, to avoid recovery actions on a
    payment that has already succeeded, been refunded, or otherwise moved on.

    Args:
        order_id: Razorpay order id, e.g. "order_XXXXXXXXXXXXXX", if known.
        payment_id: Razorpay payment id, e.g. "pay_XXXXXXXXXXXXXX", if known.
    """
    loguru.logger.warning(
        f"[tool-stub] track_payment_status({order_id=}, {payment_id=}) is not "
        "implemented yet - status was not actually checked. Wire this to the "
        "Razorpay Payments/Orders API."
    )
    return (
        f"PLACEHOLDER: would check live status for order_id={order_id!r} "
        f"payment_id={payment_id!r}. No lookup was actually performed - fall "
        "back to the case's last known `entity_status` from its history."
    )
