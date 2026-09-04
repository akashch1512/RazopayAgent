import datetime
import json
import pathlib

import pytest

from src.agent.context import _summarize_case, _summarize_event
from src.integrations.razorpay.normalizer import build_dedupe_key, normalize_event
from src.models.db.webhook_event import WebhookEvent

_SAMPLES_DIR = pathlib.Path(__file__).parents[2].parent / "docs" / "webhooks" / "recovery_webhooks"
_SAMPLE_FILES = sorted(_SAMPLES_DIR.rglob("*.json"))


def _event_from_sample(path: pathlib.Path) -> WebhookEvent:
    body = json.loads(path.read_text())
    values = normalize_event(
        body,
        dedupe_key=build_dedupe_key(event_id=None, raw_body=path.read_bytes()),
        signature_verified=True,
        business_id=1,
    )
    return WebhookEvent(
        id=1,
        received_at=datetime.datetime.now(tz=datetime.UTC),
        **{k: v for k, v in values.items() if k not in ("customer_email", "customer_contact")},
    )


@pytest.mark.parametrize("path", _SAMPLE_FILES, ids=lambda p: p.name)
def test_every_sample_event_summarizes_without_error(path: pathlib.Path) -> None:
    """The context builder must handle every event type generically - no
    per-type branches, so every sample in the recovery-webhooks corpus should
    summarize cleanly."""
    event = _event_from_sample(path)
    summary = _summarize_event(event)

    assert summary.startswith("- [")
    assert event.event_type in summary
    assert str(event.entity_id) in summary


def test_case_summary_includes_full_history_in_order() -> None:
    events = [_event_from_sample(path) for path in _SAMPLE_FILES[:3]]

    class _FakeCase:
        id = 42
        case_key = "order:test"
        processing_status = "PROCESSING"
        priority = 3
        priority_reason = "high-event:test"
        event_count = len(events)
        latest_event_type = events[-1].event_type
        latest_entity_status = events[-1].entity_status
        customer_email = "customer@example.com"
        customer_contact = "+919876543210"

    summary = _summarize_case(_FakeCase(), events)  # type: ignore[arg-type]

    assert f"Retries merged into this case: {len(events)}" in summary
    for event in events:
        assert event.event_type in summary
