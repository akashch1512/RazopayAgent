import datetime

from src.integrations.razorpay.normalization import normalize_event
from src.services.recovery.grouping import is_resolving_event, resolve_case_key
from src.services.recovery.priority import compute_priority
from src.workers.tasks.dropoff_detection import (
    _build_dropoff_envelope,
    _is_dropped_off,
    _next_poll_at,
)


def _order(*, status: str = "created", created_at: int, amount: int = 50000) -> dict:
    return {
        "id": "order_DROPTEST001",
        "entity": "order",
        "amount": amount,
        "currency": "INR",
        "status": status,
        "attempts": 1,
        "created_at": created_at,
    }


def test_paid_order_is_never_a_dropoff() -> None:
    now = datetime.datetime.now(tz=datetime.UTC)
    old_created_at = int(now.timestamp()) - 10_000
    assert _is_dropped_off(_order(status="paid", created_at=old_created_at), now=now) is False


def test_fresh_order_is_not_yet_a_dropoff() -> None:
    now = datetime.datetime.now(tz=datetime.UTC)
    just_created = int(now.timestamp())
    assert _is_dropped_off(_order(status="created", created_at=just_created), now=now) is False


def test_stale_unpaid_order_is_a_dropoff() -> None:
    now = datetime.datetime.now(tz=datetime.UTC)
    stale_created_at = int(now.timestamp()) - 100_000
    assert _is_dropped_off(_order(status="created", created_at=stale_created_at), now=now) is True
    assert _is_dropped_off(_order(status="attempted", created_at=stale_created_at), now=now) is True


def test_next_poll_at_is_strictly_in_the_future_and_bounded() -> None:
    now = datetime.datetime.now(tz=datetime.UTC)
    next_poll = _next_poll_at(now)
    assert next_poll > now

    from src.config.manager import settings

    max_gap = datetime.timedelta(
        seconds=settings.DROPOFF_POLL_INTERVAL_SECONDS + settings.DROPOFF_POLL_JITTER_SECONDS
    )
    assert next_poll <= now + max_gap


def test_dropoff_envelope_normalizes_like_a_real_webhook() -> None:
    """The synthetic order.dropoff envelope must survive the same
    `normalize_event` every real webhook goes through, unmodified."""
    now = datetime.datetime.now(tz=datetime.UTC)
    order = _order(status="created", created_at=int(now.timestamp()) - 100_000)
    body = _build_dropoff_envelope(order, account_id="acc_TESTACCOUNT01")

    values = normalize_event(
        body, dedupe_key=f"order_dropoff:{order['id']}", signature_verified=True, business_id=1
    )

    assert values["event_type"] == "order.dropoff"
    assert values["entity_type"] == "order"
    assert values["entity_id"] == order["id"]
    assert values["entity_status"] == "created"
    assert values["razorpay_account_id"] == "acc_TESTACCOUNT01"
    assert is_resolving_event(values["event_type"]) is False

    priority, reason = compute_priority(values["payload"])
    assert 0 <= priority <= 9
    assert "order.dropoff" in reason


def test_dropoff_case_key_matches_a_later_real_webhook_for_the_same_order() -> None:
    """The whole point of overriding `values['order_id']` on a dropoff event:
    a later real `payment.failed` webhook for the same order must merge into
    the same case, not create a second one."""
    now = datetime.datetime.now(tz=datetime.UTC)
    order_id = "order_SHARED0001"
    order = {**_order(created_at=int(now.timestamp()) - 100_000), "id": order_id}
    body = _build_dropoff_envelope(order, account_id="acc_TESTACCOUNT01")

    dropoff_values = normalize_event(
        body, dedupe_key=f"order_dropoff:{order_id}", signature_verified=True, business_id=1
    )
    # Mirrors what the task itself does after calling normalize_event.
    dropoff_values["order_id"] = order_id
    dropoff_case_key = resolve_case_key(
        order_id=dropoff_values.get("order_id"),
        entity_id=dropoff_values.get("entity_id"),
        dedupe_key=dropoff_values["dedupe_key"],
    )

    payment_failed_body = {
        "entity": "event",
        "account_id": "acc_TESTACCOUNT01",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {"payment": {"entity": {"id": "pay_LATER0001", "order_id": order_id, "status": "failed"}}},
        "created_at": int(now.timestamp()),
    }
    payment_values = normalize_event(
        payment_failed_body, dedupe_key="evt_later_1", signature_verified=True, business_id=1
    )
    payment_case_key = resolve_case_key(
        order_id=payment_values.get("order_id"),
        entity_id=payment_values.get("entity_id"),
        dedupe_key=payment_values["dedupe_key"],
    )

    assert dropoff_case_key == payment_case_key == f"order:{order_id}"
