import hashlib
import hmac
import json
import pathlib

import pytest

from src.integrations.razorpay.helpers.normalizer import build_dedupe_key, normalize_event
from src.integrations.razorpay.webhooks import razorpay_webhook_client

_SAMPLES_DIR = pathlib.Path(__file__).parents[2].parent / "docs" / "webhooks" / "recovery_webhooks"
_SAMPLE_FILES = sorted(_SAMPLES_DIR.rglob("*.json"))


def test_verify_signature_roundtrip() -> None:
    body = b'{"event":"payment.failed"}'
    secret = "top-secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert razorpay_webhook_client.verify_signature(raw_body=body, signature=sig, secret=secret) is True
    assert razorpay_webhook_client.verify_signature(raw_body=body, signature="deadbeef", secret=secret) is False
    assert razorpay_webhook_client.verify_signature(raw_body=body, signature=None, secret=secret) is False
    assert razorpay_webhook_client.verify_signature(raw_body=body, signature=sig, secret="") is False


def test_build_dedupe_key_prefers_event_id() -> None:
    assert build_dedupe_key(event_id="evt_123", raw_body=b"{}") == "evt_123"
    assert build_dedupe_key(event_id=None, raw_body=b"{}").startswith("sha256:")


@pytest.mark.parametrize("path", _SAMPLE_FILES, ids=lambda p: p.name)
def test_every_sample_event_normalizes(path: pathlib.Path) -> None:
    body = json.loads(path.read_text())
    values = normalize_event(body, dedupe_key="k", signature_verified=True, business_id=1)

    assert values["event_type"] and values["event_type"] != "unknown"
    assert values["entity_type"]
    assert values["entity_id"]
    assert values["razorpay_account_id"]
    assert values["payload"] == body
