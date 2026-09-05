"""
End-to-end (but fully offline) check of the real pipeline's non-agent half:

    raw webhook JSON -> normalize_event -> case/event construction -> build_case_context

using the exact templates in `docs/webhooks/recovery_webhooks` for every event
type this app actually subscribes to (`WEBHOOK_EVENTS` in
`src.integrations.razorpay.constants`) - i.e. the webhooks that will really
arrive in production.

No LLM/network calls anywhere in this path: `build_case_context` only builds
text (system prompt + case brief) from local data, and this test never touches
`src.agent.llm`, `src.agent.graph`, `src.agent.runner`, or the Celery task that
runs the actual agent. Do NOT import those here - that's what would start
spending OpenAI credits.
"""

import datetime
import json
import pathlib
import typing

import pytest

from src.agent.orchestration.context import build_case_context, build_system_prompt_context
from src.integrations.razorpay.constants import WEBHOOK_EVENTS
from src.integrations.razorpay.normalization import build_dedupe_key, normalize_event
from src.models.db.business import Business
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent
from src.services.recovery.grouping import is_resolving_event, resolve_case_key
from src.services.recovery.priority import compute_priority

_SAMPLES_DIR = pathlib.Path(__file__).parents[2].parent / "docs" / "webhooks" / "recovery_webhooks"
_ALL_SAMPLE_FILES = sorted(_SAMPLES_DIR.rglob("*.json"))


def _sample_event_type(path: pathlib.Path) -> str | None:
    body = json.loads(path.read_text())
    return body.get("event")


# event_type -> every template file that delivers it. Built once at collection
# time so a missing template fails the test below loudly, at parametrize time,
# rather than being silently skipped.
_SAMPLES_BY_EVENT_TYPE: dict[str, list[pathlib.Path]] = {}
for _path in _ALL_SAMPLE_FILES:
    _event_type = _sample_event_type(_path)
    if _event_type:
        _SAMPLES_BY_EVENT_TYPE.setdefault(_event_type, []).append(_path)

# (event_type, sample_path) for every configured WEBHOOK_EVENTS entry that has
# at least one template - see `test_every_configured_webhook_event_has_a_sample_template`
# for the "at least one" part itself.
_CONFIGURED_EVENT_SAMPLES: list[tuple[str, pathlib.Path]] = [
    (event_type, path)
    for event_type in WEBHOOK_EVENTS
    for path in _SAMPLES_BY_EVENT_TYPE.get(event_type, [])
]


def test_every_configured_webhook_event_has_a_sample_template() -> None:
    """Guards the test below: if `WEBHOOK_EVENTS` grows an event type with no
    template under `docs/webhooks/recovery_webhooks`, that's a gap in this
    suite's coverage of what production will actually receive - fail loudly
    instead of silently testing nothing for it."""
    missing = [event_type for event_type in WEBHOOK_EVENTS if event_type not in _SAMPLES_BY_EVENT_TYPE]
    assert not missing, f"No docs/webhooks/recovery_webhooks template for configured event(s): {missing}"


def _build_case_and_event(
    *, event_type: str, path: pathlib.Path
) -> tuple[RecoveryCase, WebhookEvent, Business]:
    """Mirrors what `_upsert_case` + `store_event` do in the real webhook route
    (`src.api.routes.webhooks`), just against unpersisted ORM objects instead
    of a database."""
    body = json.loads(path.read_text())
    assert body.get("event") == event_type, f"{path} does not actually deliver {event_type}"

    dedupe_key = build_dedupe_key(event_id=None, raw_body=path.read_bytes())
    values = normalize_event(body, dedupe_key=dedupe_key, signature_verified=True, business_id=1)

    resolving = is_resolving_event(values["event_type"])
    case_key = resolve_case_key(
        order_id=values.get("order_id"), entity_id=values.get("entity_id"), dedupe_key=dedupe_key
    )
    priority, priority_reason = compute_priority(values["payload"])
    now = datetime.datetime.now(tz=datetime.UTC)

    case = RecoveryCase(
        id=1,
        business_id=1,
        razorpay_account_id=values["razorpay_account_id"] or "unknown",
        case_key=case_key,
        entity_type=values.get("entity_type"),
        primary_entity_id=values.get("order_id") or values.get("entity_id"),
        customer_email=values.get("customer_email"),
        customer_contact=values.get("customer_contact"),
        latest_event_type=values["event_type"],
        latest_entity_status=values.get("entity_status"),
        event_count=1,
        processing_status="RESOLVED" if resolving else "RECEIVED",
        priority=priority,
        priority_reason=priority_reason,
        first_event_at=now,
        last_event_at=now,
    )

    event_values: dict[str, typing.Any] = {
        key: value for key, value in values.items() if key not in ("customer_email", "customer_contact")
    }
    event = WebhookEvent(id=1, case_id=1, received_at=now, **event_values)

    business = Business(id=1, name="Test Business Pvt Ltd", reference_id="ref-test-business")

    return case, event, business


@pytest.mark.parametrize(
    ("event_type", "path"), _CONFIGURED_EVENT_SAMPLES, ids=[p.name for _, p in _CONFIGURED_EVENT_SAMPLES]
)
def test_context_builder_handles_every_configured_webhook_event(event_type: str, path: pathlib.Path) -> None:
    """The real path a production webhook takes, minus the DB and the agent
    itself: raw JSON -> normalize -> case/event -> `build_case_context`, for
    every event type actually subscribed to via `WEBHOOK_EVENTS`."""
    case, event, business = _build_case_and_event(event_type=event_type, path=path)

    state = build_case_context(case=case, history=[event], business=business)

    system_message = build_system_prompt_context(case=case, history=[event], business=business)
    assert system_message.content and business.name in system_message.content
    assert event_type in system_message.content

    assert state["case_id"] == case.id
    assert state["payment_verified"] is False
    assert state["commitments"] == []
    assert "customer_first_message" in state
