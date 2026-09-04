"""
In-memory demo store.

This whole service is a decoupled stand-in for real communication providers
(Twilio, SendGrid, WhatsApp Business API, ...) - it exists purely to give the
demo dashboard (`frontend-demo`) something real to poll. It has no database and
resets whenever the process restarts; that's intentional, not a shortcut we
forgot to fix.

One "case" here is keyed by whatever `case_id` the caller (the backend agent's
tools) sends - it does not talk to the real backend's database at all.
"""

import datetime
import itertools
import typing

_id_counter = itertools.count(1)

# The order outreach channels escalate through in the demo, purely to make
# `next_action` look like a coherent plan rather than a random label.
_CHANNEL_LADDER: tuple[str, ...] = ("whatsapp", "sms", "call", "email", "app_notification")


class Communication(typing.TypedDict):
    event_id: str
    channel: str
    message: str | None
    customer_response: str | None
    status: str
    created_at: str


class RecoveryCase(typing.TypedDict):
    case_id: str
    customer_id: str
    payment_id: str | None
    status: str
    trigger_type: str
    attempt_count: int
    next_action: str
    priority_score: int
    decision: str
    decision_reason: str
    current_step: str
    context: dict[str, typing.Any]
    communications: list[Communication]


_cases: dict[str, RecoveryCase] = {}


def _now() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()


def _next_event_id() -> str:
    return f"evt_{next(_id_counter)}"


def _next_channel_label(current: str) -> str:
    if current not in _CHANNEL_LADDER:
        return "follow_up"
    next_channel = _CHANNEL_LADDER[(_CHANNEL_LADDER.index(current) + 1) % len(_CHANNEL_LADDER)]
    return f"follow_up_via_{next_channel}"


def _new_case(case_id: str, customer_id: str) -> RecoveryCase:
    return {
        "case_id": case_id,
        "customer_id": customer_id,
        "payment_id": None,
        "status": "processing",
        "trigger_type": "payment_failed",
        "attempt_count": 0,
        "next_action": "contact_customer",
        "priority_score": 40,
        "decision": "",
        "decision_reason": "",
        "current_step": "new",
        "context": {},
        "communications": [],
    }


def record_action(
    *,
    case_id: str,
    channel: str,
    customer_id: str,
    message: str,
    payment_id: str | None = None,
    context: dict[str, typing.Any] | None = None,
) -> Communication:
    """The agent took an outreach action - record it and fold it into the
    case's demo "decision" narrative for the dashboard's right-hand panel."""
    case = _cases.setdefault(case_id, _new_case(case_id, customer_id))

    if customer_id:
        case["customer_id"] = customer_id
    if payment_id:
        case["payment_id"] = payment_id
    if context:
        case["context"].update(context)

    case["attempt_count"] += 1
    case["status"] = "processing"
    case["current_step"] = f"contacted_via_{channel}"
    case["decision"] = f"Reach out via {channel}"
    case["decision_reason"] = f'Attempt #{case["attempt_count"]}: sending a {channel} nudge - "{message[:80]}"'
    case["priority_score"] = min(100, 40 + case["attempt_count"] * 15)
    case["next_action"] = _next_channel_label(channel)

    communication: Communication = {
        "event_id": _next_event_id(),
        "channel": channel,
        "message": message,
        "customer_response": None,
        "status": "delivered",
        "created_at": _now(),
    }
    case["communications"].insert(0, communication)
    return communication


def record_customer_reply(*, case_id: str, channel: str, message: str) -> Communication | None:
    """Simulates the customer replying - matched onto the most recent
    still-unanswered communication on that channel, or a fresh entry if none."""
    case = _cases.get(case_id)
    if case is None:
        return None

    for communication in case["communications"]:
        if communication["channel"] == channel and communication["customer_response"] is None:
            communication["customer_response"] = message
            _mark_customer_engaged(case, channel=channel, message=message)
            return communication

    communication = Communication(
        event_id=_next_event_id(),
        channel=channel,
        message=None,
        customer_response=message,
        status="delivered",
        created_at=_now(),
    )
    case["communications"].insert(0, communication)
    _mark_customer_engaged(case, channel=channel, message=message)
    return communication


def _mark_customer_engaged(case: RecoveryCase, *, channel: str, message: str) -> None:
    case["status"] = "active"
    case["current_step"] = f"customer_replied_via_{channel}"
    case["decision"] = "Customer responded"
    case["decision_reason"] = f'Customer replied via {channel}: "{message[:80]}"'


def mark_paid(*, case_id: str) -> RecoveryCase | None:
    case = _cases.get(case_id)
    if case is None:
        return None

    case["status"] = "active"
    case["next_action"] = "none"
    case["decision"] = "Payment recovered"
    case["decision_reason"] = "Customer completed the payment."
    case["current_step"] = "payment_recovered"
    return case


def get_case(case_id: str) -> RecoveryCase | None:
    return _cases.get(case_id)


def metrics() -> dict[str, int]:
    total = len(_cases)
    active = sum(1 for case in _cases.values() if case["status"] == "active")
    processing = sum(1 for case in _cases.values() if case["status"] == "processing")
    return {
        "handled_today": active,
        "in_progress": processing,
        # Real queue depth lives in the main backend's Redis/Celery, not here.
        "queued_cases": 0,
        "recovery_rate": round((active / total) * 100) if total else 0,
    }
