"""
Turns a `RecoveryCase` + its merged `WebhookEvent` history into the agent's
initial state (system prompt + a human-readable case brief).

Works for every Razorpay event type without per-type branches: it leans on the
same flat fields (`event_type`, `entity_type`, `entity_status`, ...) every
`WebhookEvent` already carries via `normalize_event`, plus a small set of
*generic* payload fields (amount, currency, error reason, method, ...) that
happen to exist across most Razorpay entities and are simply absent - not
special-cased - when an event type doesn't have them.
"""

import datetime
import typing
import zoneinfo

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import RecoveryAgentState
from src.agent.timezone_lookup import resolve_timezone
from src.integrations.razorpay.normalizer import extract_primary_entity
from src.models.db.business import Business
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent

# Common, non-sensitive fields worth surfacing generically from any entity
# payload - present on some event types, absent (and silently skipped) on
# others. Deliberately not an exhaustive per-entity schema.
_GENERIC_ENTITY_FIELDS: tuple[str, ...] = (
    "amount",
    "currency",
    "method",
    "description",
    "error_code",
    "error_description",
    "error_reason",
    # Present on synthetic `customer.feedback` events (see
    # `src.integrations.razorpay.ingestion`) - what the customer actually said.
    "channel",
    "message",
    # Present on synthetic `manual.recovery`/`invoice.b2b_chase` events - why a
    # human asked for this case specifically.
    "reason",
)

_SYSTEM_PROMPT_TEMPLATE = """\
You are a payment-recovery assistant working on behalf of "{business_name}", a \
business using Razorpay. Your job is to study one recovery case (a payment, \
subscription, payout, or similar problem a customer is having) and take the \
best action(s) to recover it - or to confirm none are needed.
{business_customization}
You have tools to reach the customer directly ({available_channels}) and tools \
to inspect/act on Razorpay itself (via the Razorpay MCP server, if connected \
for this business). Some tools are still placeholders that log what they \
*would* do instead of really doing it - treat their result as a plan, not a \
confirmed action, when they say so explicitly.

The customer's local time right now is {local_time} ({timezone}). Do not \
suggest or place calls/notifications outside a reasonable local daytime window \
(roughly 9am-8pm) unless the case is urgent enough to justify it.

Guidelines:
- Check the case history below before acting - if the customer already \
  resolved this or you already reached out recently, don't repeat yourself. A \
  `customer.feedback` entry is the customer's own reply - read it carefully \
  and respond to what they actually said (a question, an objection, a "yes") \
  rather than repeating your last message.
- Prefer the least intrusive effective channel first (e.g. WhatsApp/SMS before \
  a phone call), escalating only if warranted by priority or repeated failures.
- If a payment link would make it easier for the customer to actually pay \
  (rather than just being told about the problem again), use the \
  `send_payment_link` tool to send one - it writes and sends the whole \
  message itself, real link included. Never write a message yourself that \
  mentions "the payment link" or a placeholder like "[Payment Link]" - you \
  don't know its URL, only that tool does; a message you write yourself would \
  reach the customer with no working link at all.
- Be concise and factual when drafting messages to the customer; no invented \
  details (amounts, dates, reasons) beyond what the case data provides.
- If nothing useful can be done right now, say so plainly instead of taking a \
  low-value action just to do something.
"""


# Tool function name -> how to describe it to the LLM in prose. Kept here
# (not imported from `src.agent.tools`) so a channel can be described even if
# disabled and therefore not in the bound tool list.
_CHANNEL_DESCRIPTIONS: dict[str, str] = {
    "make_call": "call",
    "send_sms": "SMS",
    "send_whatsapp_message": "WhatsApp",
    "send_app_notification": "app notification",
    "send_email": "email",
    "send_payment_link": "a one-click payment link",
}


def _describe_available_channels(business: Business) -> str:
    enabled = (business.agent_settings or {}).get("enabled_channels")
    names = enabled if enabled else list(_CHANNEL_DESCRIPTIONS)
    return ", ".join(_CHANNEL_DESCRIPTIONS.get(name, name) for name in names)


def _business_customization_block(business: Business) -> str:
    """Folds a business' `agent_settings` (see `src.models.schemas.business.
    AgentSettings`) into the prompt - the dashboard's "customize agent" form
    actually changes agent behaviour, not just cosmetic settings."""
    settings = business.agent_settings or {}
    tone = settings.get("tone") or "friendly and professional"
    lines = [f"\nRespond to the customer in a {tone} tone."]

    description = settings.get("business_description")
    if description:
        lines.append(f"About this business: {description}")

    custom_instructions = settings.get("custom_instructions")
    if custom_instructions:
        lines.append(f"Business-specific instructions - follow these: {custom_instructions}")

    return "\n".join(lines) + "\n"


def _local_time_string(timezone_name: str) -> str:
    try:
        tz = zoneinfo.ZoneInfo(timezone_name)
    except zoneinfo.ZoneInfoNotFoundError:
        tz = zoneinfo.ZoneInfo("UTC")
    return datetime.datetime.now(tz=tz).strftime("%A, %Y-%m-%d %H:%M %Z")


def _summarize_entity_fields(payload: dict[str, typing.Any]) -> str:
    _entity_type, entity = extract_primary_entity(payload)
    facts = {field: entity[field] for field in _GENERIC_ENTITY_FIELDS if entity.get(field) not in (None, "")}
    if not facts:
        return ""
    return " (" + ", ".join(f"{key}={value}" for key, value in facts.items()) + ")"


def _summarize_event(event: WebhookEvent) -> str:
    when = (event.event_created_at or event.received_at).strftime("%Y-%m-%d %H:%M UTC")
    extra = _summarize_entity_fields(event.payload)
    entity = f"{event.entity_type}:{event.entity_id}"
    return f"- [{when}] {event.event_type} -> {entity} status={event.entity_status}{extra}"


def _summarize_case(case: RecoveryCase, history: typing.Sequence[WebhookEvent]) -> str:
    lines = [
        f"Recovery case #{case.id} (key={case.case_key})",
        f"Status: {case.processing_status} | Priority: {case.priority} ({case.priority_reason or 'n/a'})",
        f"Retries merged into this case: {case.event_count}",
        f"Latest event: {case.latest_event_type} -> status={case.latest_entity_status}",
        f"Customer contact: email={case.customer_email or 'unknown'} phone={case.customer_contact or 'unknown'}",
        "",
        f"Delivery history ({len(history)} events, oldest first):",
        *[_summarize_event(event) for event in history],
    ]
    return "\n".join(lines)


def build_case_context(
    *, case: RecoveryCase, history: typing.Sequence[WebhookEvent], business: Business
) -> RecoveryAgentState:
    """The initial state handed to `create_react_agent(...).ainvoke(...)`."""
    timezone_name = resolve_timezone(case.customer_contact)

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        business_name=business.name,
        business_customization=_business_customization_block(business),
        available_channels=_describe_available_channels(business),
        local_time=_local_time_string(timezone_name),
        timezone=timezone_name,
    )
    case_brief = _summarize_case(case, history)

    return RecoveryAgentState(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=case_brief),
        ],
        case_id=case.id,
        business_id=case.business_id,
        razorpay_account_id=case.razorpay_account_id,
        customer_timezone=timezone_name,
    )
