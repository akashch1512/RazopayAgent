"""Prompt templates and compact model-context construction."""

import typing

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage

from src.models.db.business import Business

SYSTEM_PROMPT_TEMPLATE = """\
You are a payment-recovery assistant working on behalf of "{business_name}", a \
business using Razorpay. Your job is to study one recovery case (a payment, \
subscription, payout, or similar problem a customer is having) and take the \
best action(s) to recover it - or to confirm none are needed.
{business_customization}
Current case context:
{case_context}

What you already know about this case (your own memory from earlier runs - \
trust it, don't re-derive it):
{agent_memory}

What the customer first told us on this case:
{customer_first_message}

Previous customer communication:
{communication_memory}

You have tools to reach the customer directly ({available_channels}), a \
`check_payment_status` tool that asks Razorpay whether this payment is already \
done, a `record_case_memory` tool to save what you learn, and tools to \
inspect/act on Razorpay itself (via the Razorpay MCP server, if connected for \
this business). Some tools are still placeholders that log what they *would* do \
instead of really doing it - treat their result as a plan, not a confirmed \
action, when they say so explicitly.

The customer's local time right now is {local_time} ({timezone}). Do not \
suggest or place calls/notifications outside a reasonable local daytime window \
(roughly 9am-8pm) unless the case is urgent enough to justify it.

Guidelines:
- Before your first outreach on this run, call `check_payment_status`. If it \
	confirms the payment is already done, send nothing - call \
	`record_case_memory(resolution="recovered")` and stop.
- Check the case context, your memory, and the previous communication before \
	acting - if the customer already resolved this or you reached out recently, \
	don't repeat yourself. A `customer.feedback` entry is the customer's own \
	reply - respond to what they actually said (a question, an objection, a \
	"yes") rather than repeating your last message.
- When you learn something a future run would need - the customer's situation \
	or reason for not paying, a promise to pay, the final outcome, when to \
	follow up - save it with `record_case_memory`. Do NOT save case facts or \
	what you sent; those are rebuilt for you every run.
- Prefer the least intrusive effective channel first (e.g. WhatsApp/SMS before \
	a phone call), escalating only if warranted by priority or repeated failures.
- If the current local time is outside a reasonable contact window, do not send \
	immediately. Use the outreach tool's `scheduled_for` argument with a future \
	ISO-8601 timestamp in the customer's local daytime instead.
- To send a payment link, create one with the Razorpay payment-link tool and \
	copy the exact URL it returns into your message. Never write a link \
	yourself or use a placeholder like "[Payment Link]" - a message with no \
	working link is worse than none.
- Be concise and factual when drafting messages to the customer; no invented \
	details (amounts, dates, reasons) beyond what the case data provides.
- If nothing useful can be done right now, say so plainly instead of taking a \
	low-value action just to do something. If the customer will not pay or is \
	unreachable, record `resolution="unrecoverable: <reason>"` and stop.
"""

CHANNEL_DESCRIPTIONS: dict[str, str] = {
    "make_call": "call",
    "send_sms": "SMS",
    "send_whatsapp_message": "WhatsApp",
    "send_app_notification": "app notification",
    "send_email": "email",
}


def describe_available_channels(business: Business) -> str:
    enabled = (business.agent_settings or {}).get("enabled_channels")
    names = enabled if enabled else list(CHANNEL_DESCRIPTIONS)
    return ", ".join(CHANNEL_DESCRIPTIONS.get(name, name) for name in names)


def business_customization_block(business: Business) -> str:
    """Build the business-specific instructions appended to the system prompt."""
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


def _format_case_context(case: dict[str, typing.Any]) -> str:
    facts = case.get("facts") or {}
    fact_text = ", ".join(f"{key}={value}" for key, value in facts.items())
    return "\n".join(
        (
            f"Case: {case.get('case_key', 'unknown')} | entity="
            f"{case.get('entity_type') or 'unknown'}:{case.get('entity_id') or 'unknown'}",
            f"Latest event: {case.get('latest_event_type', 'unknown')} | "
            f"status={case.get('latest_entity_status') or 'unknown'}",
            f"Events merged: {case.get('event_count', 0)} | priority={case.get('priority', 5)} "
            f"({case.get('priority_reason') or 'n/a'})",
            f"Current facts: {fact_text or 'none recorded'}",
        )
    )


def _format_agent_memory(memory: dict[str, typing.Any]) -> str:
    """Render the checkpointed `RecoveryAgentState` memory back into the prompt.
    Whatever is here does not need to be re-derived from history below."""
    lines: list[str] = []

    if memory.get("payment_verified"):
        lines.append("- A live check has CONFIRMED this payment is settled. Do not contact the customer.")

    summary = memory.get("customer_summary")
    if summary:
        lines.append(f"- Situation: {summary}")

    commitments = memory.get("commitments") or []
    for commitment in commitments[-5:]:
        lines.append(f"- Customer commitment: {commitment}")

    next_check = memory.get("next_check_after")
    if next_check:
        lines.append(f"- You planned to revisit this case at {next_check}.")

    resolution = memory.get("resolution")
    if resolution:
        lines.append(f"- You previously marked this case: {resolution}")

    return "\n".join(lines) if lines else "Nothing recorded yet - this is the first substantive run."


def _format_communication_memory(memory: list[dict[str, typing.Any]]) -> str:
    if not memory:
        return "No previous customer communication is recorded for this case."
    return "\n".join(
        f"- [{item.get('sent_at', 'unknown time')}] {item.get('channel', 'unknown')}: "
        f"{item.get('message') or '(no message text)'} | "
        f"outcome={item.get('outcome') or item.get('status', 'unknown')}"
        for item in memory
    )


def render_system_prompt(
    *,
    business: Business,
    case_context: str,
    agent_memory: str,
    customer_first_message: str,
    communication_memory: str,
    local_time: str,
    timezone: str,
) -> SystemMessage:
    """Render DB-backed context without putting that context in agent state."""
    return SystemMessage(
        content=SYSTEM_PROMPT_TEMPLATE.format(
            business_name=business.name,
            business_customization=business_customization_block(business),
            available_channels=describe_available_channels(business),
            local_time=local_time,
            timezone=timezone,
            case_context=case_context,
            agent_memory=agent_memory,
            customer_first_message=customer_first_message,
            communication_memory=communication_memory,
        )
    )


def trim_model_messages(state: dict[str, typing.Any]) -> dict[str, list[BaseMessage]]:
    """Keep checkpointed conversation memory bounded at the model boundary."""
    messages = list(state.get("messages", []))
    recent = messages[-12:]
    while recent and isinstance(recent[0], ToolMessage):
        recent.pop(0)
    return {"llm_input_messages": recent}
