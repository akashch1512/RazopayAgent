"""Static tools made available to every recovery-agent run."""

from src.agent.tools.management.case_memory import record_case_memory
from src.agent.tools.management.payment_status import check_payment_status
from src.agent.tools.management.skills import load_skill
from src.agent.tools.outreach.app_notification import send_app_notification
from src.agent.tools.outreach.call import make_call
from src.agent.tools.outreach.email import send_email
from src.agent.tools.outreach.sms import send_sms
from src.agent.tools.outreach.whatsapp import send_whatsapp_message

STATIC_TOOLS = [
    load_skill,
    check_payment_status,
    make_call,
    send_sms,
    send_whatsapp_message,
    send_app_notification,
    send_email,
    record_case_memory,
]

__all__ = ["STATIC_TOOLS"]
