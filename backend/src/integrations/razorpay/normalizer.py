"""
Turn any Razorpay webhook event body into a flat dict ready for
`WebhookEvent`. Razorpay events share a common envelope::

    {
      "entity": "event",
      "account_id": "acc_XXX",
      "event": "payment.failed",
      "contains": ["payment"],
      "payload": { "<entity>": { "entity": { ... } } },
      "created_at": 1567675356
    }

so a single normalizer covers every event type in
``docs/webhooks/recovery_webhooks``.
"""

import datetime
import hashlib
import typing


def _epoch_to_dt(value: typing.Any) -> datetime.datetime | None:
    if not isinstance(value, int | float) or value <= 0:
        return None
    try:
        return datetime.datetime.fromtimestamp(int(value), tz=datetime.UTC)
    except (OverflowError, OSError, ValueError):
        return None


def build_dedupe_key(*, event_id: str | None, raw_body: bytes) -> str:
    if event_id:
        return event_id.strip()[:128]
    return "sha256:" + hashlib.sha256(raw_body).hexdigest()


def normalize_event(
    body: dict[str, typing.Any],
    *,
    dedupe_key: str,
    signature_verified: bool,
    business_id: int | None,
) -> dict[str, typing.Any]:
    contains = body.get("contains") or []
    entity_type: str | None = contains[0] if contains else None

    entity: dict[str, typing.Any] = {}
    payload = body.get("payload")
    if entity_type and isinstance(payload, dict):
        node = payload.get(entity_type)
        if isinstance(node, dict) and isinstance(node.get("entity"), dict):
            entity = node["entity"]

    return {
        "dedupe_key": dedupe_key,
        "business_id": business_id,
        "razorpay_account_id": body.get("account_id"),
        "event_type": body.get("event") or "unknown",
        "entity_type": entity_type,
        "entity_id": entity.get("id"),
        "entity_status": entity.get("status"),
        "signature_verified": signature_verified,
        "payload": body,
        "event_created_at": _epoch_to_dt(body.get("created_at")),
    }
