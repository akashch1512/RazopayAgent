"""
Groups repeated webhook deliveries about the same underlying problem into one
`recovery_case`, so a customer retrying a failing payment five times produces
five `webhook_event` history rows but exactly one unit of agent work.

Grouping key, in priority order:
  1. `order_id`   - every retry against the same order shares it (payments,
                    invoices). This is the common "customer keeps retrying" case.
  2. `entity_id`  - events without an order (subscriptions, payouts, payment
                    links) repeat about the same entity id; grouping on it still
                    collapses duplicate status pings into one case.
  3. the event's own `dedupe_key` - no real grouping signal, so it gets its own
                    case rather than being silently dropped.

Events that signal the problem is already solved (`payment.captured`, ...)
close the case instead of creating agent work.
"""

# Deliveries that mean "this order/case is no longer a recovery problem".
RESOLVING_EVENTS: frozenset[str] = frozenset(
    {
        "payment.captured",
        "order.paid",
        "invoice.paid",
        "subscription.charged",
        "subscription.activated",
        "refund.processed",
    }
)


def is_resolving_event(event_type: str) -> bool:
    return event_type in RESOLVING_EVENTS


def resolve_case_key(
    *,
    order_id: str | None,
    entity_id: str | None,
    dedupe_key: str,
) -> str:
    """Pure, cheap - safe to call on the request hot path."""
    if order_id:
        return f"order:{order_id}"
    if entity_id:
        return f"entity:{entity_id}"
    return f"event:{dedupe_key}"
