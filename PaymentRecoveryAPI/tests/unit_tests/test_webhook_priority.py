import json
import pathlib

import pytest

from src.services.recovery.priority import compute_priority

_SAMPLES_DIR = pathlib.Path(__file__).parents[2].parent / "docs" / "webhooks" / "recovery_webhooks"
_SAMPLE_FILES = sorted(_SAMPLES_DIR.rglob("*.json"))


def _event(name: str, *, amount: int | None = None, contains: list[str] | None = None) -> dict:
    keys = contains or ["payment"]
    body: dict = {"event": name, "contains": keys, "payload": {}}
    if amount is not None:
        body["payload"][keys[0]] = {"entity": {"amount": amount, "id": "x_1", "status": "failed"}}
    return body


def test_critical_event_outranks_default_event() -> None:
    crit, _ = compute_priority(_event("payment.failed"))
    dflt, _ = compute_priority(_event("some.unknown.event"))
    assert crit < dflt


def test_large_amount_bumps_priority() -> None:
    small, _ = compute_priority(_event("payment.failed", amount=10_000))
    large, _ = compute_priority(_event("payment.failed", amount=20_00_00_000))
    assert large < small


def test_priority_is_clamped_to_band() -> None:
    for name in ("payment.failed", "unknown", "subscription.pending"):
        p, _ = compute_priority(_event(name, amount=99_99_99_999))
        assert 0 <= p <= 9


def test_reason_is_populated_and_bounded() -> None:
    p, reason = compute_priority(_event("payment.failed", amount=5_00_00_000))
    assert reason and len(reason) <= 120
    assert "payment.failed" in reason


@pytest.mark.parametrize("path", _SAMPLE_FILES, ids=lambda p: p.name)
def test_every_sample_event_scores_within_band(path: pathlib.Path) -> None:
    body = json.loads(path.read_text())
    priority, reason = compute_priority(body)
    assert 0 <= priority <= 9
    assert isinstance(reason, str) and reason
