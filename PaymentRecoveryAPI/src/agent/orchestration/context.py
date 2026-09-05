"""
Turns a `RecoveryCase` + its merged `WebhookEvent` history into the agent's
initial memory (`RecoveryAgentState`) and its per-run system prompt.

Works for every Razorpay event type without per-type branches: it leans on the
same flat fields (`event_type`, `entity_type`, `entity_status`, ...) every
`WebhookEvent` already carries via `normalize_event`, plus a small set of
*generic* payload fields (amount, currency, error reason, method, ...) that
happen to exist across most Razorpay entities and are simply absent - not
special-cased - when an event type doesn't have them.

On a re-run, `prior_memory` (the checkpointed `RecoveryAgentState` from the last
run) is passed in: what the agent already remembers is rendered straight back
into the prompt and the rebuilt-from-DB context is trimmed accordingly.
"""

import typing

from src.agent.orchestration.prompts import (
    _format_agent_memory,
    _format_case_context,
    _format_communication_memory,
    render_system_prompt,
)
from src.agent.policies.contact_policy import local_time_string
from src.agent.state.recovery import RecoveryAgentState
from src.agent.utilities.timezone import resolve_timezone
from src.integrations.razorpay.helpers.normalizer import extract_primary_entity
from src.models.db.business import Business
from src.models.db.case_action import CaseAction
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent

# `RecoveryAgentState` keys that are the agent's own durable memory - carried
# forward from a prior run's checkpoint so a re-run does not start cold.
# (`case_id` is rebuilt; `messages` is reduced by the checkpointer.)
MEMORY_KEYS: tuple[str, ...] = (
    "customer_first_message",
    "customer_summary",
    "commitments",
    "payment_verified",
    "resolution",
    "next_check_after",
)

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
    # `src.services.recovery.ingestion`) - what the customer actually said.
    "channel",
    "message",
    # Present on synthetic `manual.recovery`/`invoice.b2b_chase` events - why a
    # human asked for this case specifically.
    "reason",
)


def _extract_entity_facts(payload: dict[str, typing.Any]) -> dict[str, typing.Any]:
    _entity_type, entity = extract_primary_entity(payload)
    return {field: entity[field] for field in _GENERIC_ENTITY_FIELDS if entity.get(field) not in (None, "")}


def _first_customer_message(history: typing.Sequence[WebhookEvent]) -> str | None:
    """Verbatim text of the earliest `customer.feedback` event - the first thing
    the customer actually told us on this case. Lost from the model context once
    messages are trimmed, so it is pinned into state instead."""
    for event in history:  # oldest-first
        if event.event_type == "customer.feedback":
            _entity_type, entity = extract_primary_entity(event.payload)
            message = entity.get("message")
            if message:
                return str(message)[:1000]
    return None


def _build_communication_memory(
    actions: typing.Sequence[CaseAction], *, limit: int
) -> list[dict[str, typing.Any]]:
    """Keep only the recent, customer-relevant part of the outbound audit trail."""
    memory: list[dict[str, typing.Any]] = []
    for action in actions[-limit:]:
        tool_input = action.tool_input or {}
        message = tool_input.get("message")
        output = action.tool_output or ""
        memory.append(
            {
                "channel": action.tool_name,
                "sent_at": action.created_at.isoformat() if action.created_at else "unknown",
                "message": str(message)[:500] if message else "",
                "outcome": output[:300],
                "status": action.status,
            }
        )
    return memory


def build_case_context(
    *,
    case: RecoveryCase,
    history: typing.Sequence[WebhookEvent],
    business: Business,
    actions: typing.Sequence[CaseAction] = (),
    prior_memory: dict[str, typing.Any] | None = None,
) -> RecoveryAgentState:
    """
    The agent's initial memory for one run. `case_id` and `customer_first_message`
    are (re)derived from the DB; the agent-written fields start empty and then a
    prior run's checkpointed values are layered back on so nothing is lost.
    """
    state = RecoveryAgentState(
        messages=[],
        case_id=case.id,
        customer_first_message=_first_customer_message(history),
        customer_summary=None,
        commitments=[],
        payment_verified=False,
        resolution=None,
        next_check_after=None,
    )
    for key in MEMORY_KEYS:
        value = (prior_memory or {}).get(key)
        if value not in (None, [], ""):
            state[key] = value  # type: ignore[literal-required]
    return state


def build_system_prompt_context(
    *,
    case: RecoveryCase,
    history: typing.Sequence[WebhookEvent],
    business: Business,
    actions: typing.Sequence[CaseAction] = (),
    prior_memory: dict[str, typing.Any] | None = None,
):
    """Build the per-run system prompt from DB-backed context + prior memory."""
    memory = prior_memory or {}
    timezone_name = resolve_timezone(case.customer_contact)
    latest_event = history[-1] if history else None
    facts = _extract_entity_facts(latest_event.payload) if latest_event else {}

    case_context = _format_case_context(
        {
            "case_key": case.case_key,
            "entity_type": case.entity_type,
            "entity_id": case.primary_entity_id,
            "latest_event_type": case.latest_event_type,
            "latest_entity_status": case.latest_entity_status,
            "event_count": case.event_count,
            "priority": case.priority,
            "priority_reason": case.priority_reason,
            "facts": facts,
        }
    )

    # Once the agent has its own summary, the full outbound trail is redundant
    # detail - a short tail is enough to avoid an immediate repeat message.
    comm_limit = 4 if memory.get("customer_summary") else 12
    first_message = memory.get("customer_first_message") or _first_customer_message(history)

    return render_system_prompt(
        business=business,
        case_context=case_context,
        agent_memory=_format_agent_memory(memory),
        customer_first_message=first_message or "The customer has not replied to us on this case yet.",
        communication_memory=_format_communication_memory(
            _build_communication_memory(actions, limit=comm_limit)
        ),
        local_time=local_time_string(timezone_name),
        timezone=timezone_name,
    )
