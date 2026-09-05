"""
Cheap, pure priority scoring for an incoming Razorpay webhook.

Runs on the hot path (a flooded route), so it must stay allocation-light: a
couple of dict lookups and one set membership test - no I/O, no regex, no
parsing beyond what `normalize_event` already did.

Convention: **0 = most urgent, 9 = least urgent** (matches Celery's Redis
priority ordering). The reconciler can hand the broker an even lower number as a
case ages; this function only decides the *base* band.
"""

import typing

# Recovery-critical events: money already moved the wrong way or a customer is
# actively blocked. Handle these first.
_CRITICAL_EVENTS: frozenset[str] = frozenset(
    {
        "payment.failed",
        "payment.dispute.created",
        "payment.dispute.lost",
        "payout.failed",
        "payout.rejected",
        "refund.failed",
        "subscription.halted",
        # A customer replying is the moment they're most engaged - strike
        # while the iron is hot rather than letting it sit in the queue.
        "customer.feedback",
        # A human explicitly asked for this - see
        # src.integrations.razorpay.ingestion.start_manual_case.
        "manual.recovery",
        "invoice.b2b_chase",
    }
)

# Important but not bleeding: recoverable soon, or a heads-up before failure.
_HIGH_EVENTS: frozenset[str] = frozenset(
    {
        "subscription.pending",
        "subscription.cancelled",
        "payment_link.expired",
        "invoice.expired",
        "order.paid",
        "refund.created",
        # Synthesized by the drop-off poller, not a real Razorpay webhook -
        # see src.workers.tasks.dropoff_detection.
        "order.dropoff",
    }
)

_BASE_CRITICAL = 2
_BASE_HIGH = 4
_BASE_DEFAULT = 6

# Amount thresholds in the smallest currency unit (paise for INR).
_AMOUNT_TIERS: tuple[tuple[int, int], ...] = (
    (10_00_00_000, 2),  # >= ₹10,00,000 -> bump priority by 2
    (1_00_00_000, 1),  # >= ₹1,00,000  -> bump priority by 1
)

_MIN_PRIORITY = 0
_MAX_PRIORITY = 9


def _extract_amount(payload: dict[str, typing.Any]) -> int | None:
    """Pull the primary entity's `amount` (paise) from the normalized envelope."""
    contains = payload.get("contains") or []
    node = payload.get("payload")
    if not isinstance(node, dict):
        return None
    for key in contains:
        entity = node.get(key)
        if isinstance(entity, dict) and isinstance(entity.get("entity"), dict):
            amount = entity["entity"].get("amount")
            if isinstance(amount, int | float) and amount > 0:
                return int(amount)
    return None


def compute_priority(payload: dict[str, typing.Any]) -> tuple[int, str]:
    """
    Return ``(priority, reason)`` for a raw Razorpay event body.

    `reason` is a short human string kept on the row for observability
    ("why did this jump the queue?").
    """
    event = payload.get("event") or "unknown"

    if event in _CRITICAL_EVENTS:
        base, band = _BASE_CRITICAL, "critical-event"
    elif event in _HIGH_EVENTS:
        base, band = _BASE_HIGH, "high-event"
    else:
        base, band = _BASE_DEFAULT, "default"

    reason = f"{band}:{event}"

    amount = _extract_amount(payload)
    if amount is not None:
        for threshold, bump in _AMOUNT_TIERS:
            if amount >= threshold:
                base -= bump
                reason = f"{reason}|amount>={threshold}"
                break

    priority = max(_MIN_PRIORITY, min(_MAX_PRIORITY, base))
    return priority, reason[:120]
