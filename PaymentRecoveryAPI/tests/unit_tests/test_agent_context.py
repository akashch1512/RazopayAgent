"""
Offline checks of the agent's memory/context construction
(`src.agent.orchestration.context`): the first-customer-message extraction and
the way a prior run's memory is folded back into state + prompt. No LLM, no DB.
"""

import datetime

from src.agent.orchestration.context import (
    _first_customer_message,
    build_case_context,
    build_system_prompt_context,
)
from src.models.db.business import Business
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent

_NOW = datetime.datetime(2026, 9, 5, 12, 0, tzinfo=datetime.UTC)


def _feedback_event(message: str, *, event_id: int) -> WebhookEvent:
    return WebhookEvent(
        id=event_id,
        case_id=1,
        received_at=_NOW,
        dedupe_key=f"fb-{event_id}",
        event_type="customer.feedback",
        entity_type="customer_feedback",
        entity_id=f"feedback_{event_id}",
        entity_status="received",
        signature_verified=True,
        payload={
            "event": "customer.feedback",
            "contains": ["customer_feedback"],
            "payload": {"customer_feedback": {"entity": {"id": f"feedback_{event_id}", "message": message}}},
        },
    )


def _failure_event(event_id: int) -> WebhookEvent:
    return WebhookEvent(
        id=event_id,
        case_id=1,
        received_at=_NOW,
        dedupe_key=f"pf-{event_id}",
        event_type="payment.failed",
        entity_type="payment",
        entity_id=f"pay_{event_id}",
        entity_status="failed",
        signature_verified=True,
        payload={"event": "payment.failed", "contains": ["payment"], "payload": {"payment": {"entity": {}}}},
    )


def _case() -> RecoveryCase:
    return RecoveryCase(
        id=1,
        business_id=1,
        razorpay_account_id="acc_test",
        case_key="order:order_test",
        entity_type="payment",
        primary_entity_id="order_test",
        customer_email="c@example.com",
        customer_contact="+919876543210",
        latest_event_type="payment.failed",
        latest_entity_status="failed",
        event_count=3,
        processing_status="PROCESSING",
        priority=3,
        priority_reason="critical-event:payment.failed",
        first_event_at=_NOW,
        last_event_at=_NOW,
    )


def test_first_customer_message_is_the_earliest_feedback() -> None:
    history = [
        _failure_event(1),
        _feedback_event("my card keeps getting declined", event_id=2),
        _feedback_event("any update?", event_id=3),
    ]
    assert _first_customer_message(history) == "my card keeps getting declined"


def test_first_customer_message_none_when_no_feedback() -> None:
    assert _first_customer_message([_failure_event(1)]) is None


def test_build_case_context_carries_prior_memory_forward() -> None:
    prior = {
        "customer_summary": "disputing the amount",
        "commitments": ["will pay by 2026-09-10"],
        "payment_verified": False,
        "resolution": None,
    }
    state = build_case_context(
        case=_case(),
        history=[_feedback_event("hello", event_id=1)],
        business=Business(name="Acme", reference_id="ref"),
        prior_memory=prior,
    )
    assert state["case_id"] == 1
    assert state["customer_first_message"] == "hello"
    assert state["customer_summary"] == "disputing the amount"
    assert state["commitments"] == ["will pay by 2026-09-10"]
    assert state["payment_verified"] is False


def test_system_prompt_renders_memory_and_first_message() -> None:
    prior = {"customer_summary": "card declined repeatedly", "payment_verified": True}
    prompt = build_system_prompt_context(
        case=_case(),
        history=[_feedback_event("the card won't work", event_id=1)],
        business=Business(name="Acme", reference_id="ref"),
        prior_memory=prior,
    )
    assert "card declined repeatedly" in prompt.content
    assert "the card won't work" in prompt.content
    assert "CONFIRMED this payment is settled" in prompt.content
