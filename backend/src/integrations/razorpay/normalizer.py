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


def extract_primary_entity(body: dict[str, typing.Any]) -> tuple[str | None, dict[str, typing.Any]]:
    """
    Pull `(entity_type, entity_dict)` out of a raw Razorpay event body - the one
    piece of type-specific unwrapping every event shares. Reused by the agent's
    context builder so it never needs per-event-type branches either.
    """
    contains = body.get("contains") or []
    entity_type: str | None = contains[0] if contains else None

    entity: dict[str, typing.Any] = {}
    payload = body.get("payload")
    if entity_type and isinstance(payload, dict):
        node = payload.get(entity_type)
        if isinstance(node, dict) and isinstance(node.get("entity"), dict):
            entity = node["entity"]

    return entity_type, entity


def normalize_event(
    body: dict[str, typing.Any],
    *,
    dedupe_key: str,
    signature_verified: bool,
    business_id: int | None,
) -> dict[str, typing.Any]:
    entity_type, entity = extract_primary_entity(body)

    return {
        "dedupe_key": dedupe_key,
        "business_id": business_id,
        "razorpay_account_id": body.get("account_id"),
        "event_type": body.get("event") or "unknown",
        "entity_type": entity_type,
        "entity_id": entity.get("id"),
        "entity_status": entity.get("status"),
        # Present on payment/invoice-shaped entities; the single strongest signal
        # that two deliveries are "the same case" (a customer retrying one order).
        "order_id": entity.get("order_id"),
        "customer_email": entity.get("email") or _dig(entity, "customer_details", "email"),
        "customer_contact": entity.get("contact") or _dig(entity, "customer_details", "contact"),
        "signature_verified": signature_verified,
        "payload": body,
        "event_created_at": _epoch_to_dt(body.get("created_at")),
    }


def _dig(entity: dict[str, typing.Any], *path: str) -> str | None:
    node: typing.Any = entity
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, str) else None
