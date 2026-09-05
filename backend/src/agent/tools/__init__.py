"""
Static tools available to every recovery agent run, in addition to the
per-business Razorpay MCP tools (see `src.agent.mcp`).

Every tool here is a placeholder (see each module's docstring) - simple,
single-purpose functions that will become real API calls later without
changing how the agent uses them.
"""

from src.agent.tools.app_notification import send_app_notification
from src.agent.tools.call import make_call
from src.agent.tools.email import send_email
from src.agent.tools.payment_link import send_payment_link
from src.agent.tools.payment_tracker import track_payment_status
from src.agent.tools.sms import send_sms
from src.agent.tools.whatsapp import send_whatsapp_message

STATIC_TOOLS = [
    make_call,
    send_sms,
    send_whatsapp_message,
    send_app_notification,
    send_email,
    send_payment_link,
    track_payment_status,
]

__all__ = [
    "STATIC_TOOLS",
    "make_call",
    "send_sms",
    "send_whatsapp_message",
    "send_app_notification",
    "send_email",
    "send_payment_link",
    "track_payment_status",
]
