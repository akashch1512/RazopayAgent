import json
import pathlib

import pytest

from src.integrations.razorpay.normalization import normalize_event
from src.services.recovery.grouping import is_resolving_event, resolve_case_key

_SAMPLES_DIR = pathlib.Path(__file__).parents[2].parent / "docs" / "webhooks" / "recovery_webhooks"
_SAMPLE_FILES = sorted(_SAMPLES_DIR.rglob("*.json"))


def test_same_order_retries_collapse_to_one_case_key() -> None:
    """The exact scenario this feature exists for: a customer retries a failing
    payment against the same order several times over different payment ids."""
    attempt_1 = resolve_case_key(order_id="order_ABC123", entity_id="pay_one", dedupe_key="d1")
    attempt_2 = resolve_case_key(order_id="order_ABC123", entity_id="pay_two", dedupe_key="d2")
    attempt_3 = resolve_case_key(order_id="order_ABC123", entity_id="pay_three", dedupe_key="d3")

    assert attempt_1 == attempt_2 == attempt_3


def test_different_orders_never_collapse() -> None:
    a = resolve_case_key(order_id="order_A", entity_id="pay_1", dedupe_key="d1")
    b = resolve_case_key(order_id="order_B", entity_id="pay_2", dedupe_key="d2")
    assert a != b


def test_falls_back_to_entity_id_without_an_order() -> None:
    first = resolve_case_key(order_id=None, entity_id="sub_XYZ", dedupe_key="d1")
    second = resolve_case_key(order_id=None, entity_id="sub_XYZ", dedupe_key="d2")
    assert first == second == "entity:sub_XYZ"


def test_falls_back_to_dedupe_key_when_nothing_else_ties_events_together() -> None:
    a = resolve_case_key(order_id=None, entity_id=None, dedupe_key="evt_1")
    b = resolve_case_key(order_id=None, entity_id=None, dedupe_key="evt_2")
    assert a != b  # nothing to merge on - each gets its own case, not silently dropped


def test_resolving_events_close_the_case() -> None:
    assert is_resolving_event("payment.captured") is True
    assert is_resolving_event("order.paid") is True
    assert is_resolving_event("payment.failed") is False


@pytest.mark.parametrize("path", _SAMPLE_FILES, ids=lambda p: p.name)
def test_every_sample_event_yields_a_stable_case_key(path: pathlib.Path) -> None:
    body = json.loads(path.read_text())
    values = normalize_event(body, dedupe_key="k", signature_verified=True, business_id=1)

    key = resolve_case_key(
        order_id=values.get("order_id"), entity_id=values.get("entity_id"), dedupe_key=values["dedupe_key"]
    )
    assert key
    key_again = resolve_case_key(
        order_id=values.get("order_id"), entity_id=values.get("entity_id"), dedupe_key=values["dedupe_key"]
    )
    assert key == key_again
