"""
The shared "merge one normalized event into its case, store it, maybe
dispatch" pipeline - used by the webhook route (real-time deliveries from
Razorpay), the drop-off poller (synthesized from the Orders API, since
Razorpay has no drop-off webhook), and customer feedback from the demo
dashboard (synthesized the same way, since a customer's reply isn't a Razorpay
webhook either). Keeping this in one place means every producer gets identical
merge/priority/dispatch behaviour for free.
"""

import datetime
import typing
import uuid

import loguru

from src.integrations.razorpay.priority import compute_priority
from src.integrations.razorpay.recovery_case import is_resolving_event, resolve_case_key
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.workers import names
from src.workers.enqueue import enqueue


async def upsert_case_from_event(
    *, case_repo: RecoveryCaseCRUDRepository, values: dict[str, typing.Any]
) -> tuple[RecoveryCase, bool, bool]:
    """
    Merge one normalized event dict (the shape `normalize_event` produces) into
    its recovery case. Returns `(case, is_new, is_resolving)`.

    Runs *before* the event is stored so the row can be written with its
    `case_id` already set - one insert, no follow-up UPDATE.
    """
    event_type = values["event_type"]
    resolving = is_resolving_event(event_type)
    case_key = resolve_case_key(
        order_id=values.get("order_id"), entity_id=values.get("entity_id"), dedupe_key=values["dedupe_key"]
    )
    priority, priority_reason = compute_priority(values["payload"])

    case, is_new = await case_repo.upsert_case(
        business_id=values.get("business_id"),
        razorpay_account_id=values["razorpay_account_id"] or "unknown",
        case_key=case_key,
        entity_type=values.get("entity_type"),
        primary_entity_id=values.get("order_id") or values.get("entity_id"),
        event_type=event_type,
        entity_status=values.get("entity_status"),
        customer_email=values.get("customer_email"),
        customer_contact=values.get("customer_contact"),
        priority=priority,
        priority_reason=priority_reason,
        is_resolving=resolving,
    )
    return case, is_new, resolving


async def store_event_for_case(
    *, webhook_repo: WebhookEventCRUDRepository, values: dict[str, typing.Any], case_id: int
) -> WebhookEvent | None:
    """Insert the delivery tagged with its `case_id`. `None` if it was a
    duplicate (idempotent via `dedupe_key`)."""
    event_values = {key: value for key, value in values.items() if key not in ("customer_email", "customer_contact")}
    event_values["case_id"] = case_id
    return await webhook_repo.store_event(values=event_values)


def build_customer_feedback_values(
    *, case: RecoveryCase, channel: str, message: str
) -> dict[str, typing.Any]:
    """
    Shapes a customer's reply (from the demo dashboard today; a real inbound
    channel eventually) into the same normalized-event shape webhooks and
    drop-offs use, so it flows through the identical merge -> history -> agent
    pipeline and shows up in the case brief `src.agent.context` builds.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    entity_id = f"feedback_{case.id}_{uuid.uuid4().hex[:8]}"
    return {
        # Every reply is a genuinely new signal, never a redelivery - no
        # dedup key collision wanted here.
        "dedupe_key": f"customer_feedback:{case.id}:{uuid.uuid4()}",
        "business_id": case.business_id,
        "razorpay_account_id": case.razorpay_account_id,
        "event_type": "customer.feedback",
        "entity_type": "customer_feedback",
        "entity_id": entity_id,
        "entity_status": "received",
        "order_id": None,
        "customer_email": case.customer_email,
        "customer_contact": case.customer_contact,
        "signature_verified": True,
        "payload": {
            "entity": "event",
            "account_id": case.razorpay_account_id,
            "event": "customer.feedback",
            "contains": ["customer_feedback"],
            "payload": {
                "customer_feedback": {
                    "entity": {
                        "id": entity_id,
                        "channel": channel,
                        "message": message,
                        "status": "received",
                    }
                }
            },
            "created_at": int(now.timestamp()),
        },
        "event_created_at": now,
    }


async def record_customer_feedback(
    *,
    case_repo: RecoveryCaseCRUDRepository,
    webhook_repo: WebhookEventCRUDRepository,
    case: RecoveryCase,
    channel: str,
    message: str,
) -> tuple[RecoveryCase, WebhookEvent | None]:
    """
    Merge a customer's reply into its (already-known) case and store it as
    history. Reuses the case's own `case_key`/`razorpay_account_id` so this
    always lands on the same row - unlike a webhook, we already know exactly
    which case this belongs to, so there's no order/entity matching to do.
    """
    values = build_customer_feedback_values(case=case, channel=channel, message=message)
    priority, priority_reason = compute_priority(values["payload"])

    updated_case, _is_new = await case_repo.upsert_case(
        business_id=case.business_id,
        razorpay_account_id=case.razorpay_account_id,
        case_key=case.case_key,
        entity_type=values["entity_type"],
        primary_entity_id=case.primary_entity_id,
        event_type=values["event_type"],
        entity_status=values["entity_status"],
        customer_email=case.customer_email,
        customer_contact=case.customer_contact,
        priority=priority,
        priority_reason=priority_reason,
        is_resolving=False,
    )
    event = await store_event_for_case(webhook_repo=webhook_repo, values=values, case_id=updated_case.id)
    return updated_case, event


def build_manual_case_values(
    *,
    business_id: int,
    razorpay_account_id: str,
    event_type: str,
    order_reference: str,
    customer_email: str | None,
    customer_contact: str | None,
    amount: int | None,
    currency: str,
    reason: str,
) -> dict[str, typing.Any]:
    """
    Shapes a human-initiated request - "start custom recovery" or "start a B2B
    chase" on the dashboard - into the same normalized-event shape webhooks
    use. Keyed on `order_reference` as the `order_id`, so this merges with any
    webhook event (past or future) for the same order/invoice.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    entity: dict[str, typing.Any] = {
        "id": order_reference,
        "order_id": order_reference,
        "status": "requested",
        "reason": reason,
    }
    if amount is not None:
        entity["amount"] = amount
        entity["currency"] = currency

    return {
        "dedupe_key": f"{event_type}:{order_reference}:{uuid.uuid4()}",
        "business_id": business_id,
        "razorpay_account_id": razorpay_account_id,
        "event_type": event_type,
        "entity_type": "manual_case",
        "entity_id": order_reference,
        "entity_status": "requested",
        "order_id": order_reference,
        "customer_email": customer_email,
        "customer_contact": customer_contact,
        "signature_verified": True,
        "payload": {
            "entity": "event",
            "account_id": razorpay_account_id,
            "event": event_type,
            "contains": ["manual_case"],
            "payload": {"manual_case": {"entity": entity}},
            "created_at": int(now.timestamp()),
        },
        "event_created_at": now,
    }


async def start_manual_case(
    *,
    case_repo: RecoveryCaseCRUDRepository,
    webhook_repo: WebhookEventCRUDRepository,
    business_id: int,
    razorpay_account_id: str,
    event_type: str,
    order_reference: str,
    customer_email: str | None,
    customer_contact: str | None,
    amount: int | None,
    currency: str,
    reason: str,
) -> tuple[RecoveryCase, bool, bool, WebhookEvent | None]:
    """A human explicitly asking the agent to chase a specific order/invoice
    (manual recovery, or a B2B invoice chase) - the exact same merge/priority/
    dispatch pipeline as a real webhook, just a different origin."""
    values = build_manual_case_values(
        business_id=business_id,
        razorpay_account_id=razorpay_account_id,
        event_type=event_type,
        order_reference=order_reference,
        customer_email=customer_email,
        customer_contact=customer_contact,
        amount=amount,
        currency=currency,
        reason=reason,
    )
    case, is_new, resolving = await upsert_case_from_event(case_repo=case_repo, values=values)
    event = await store_event_for_case(webhook_repo=webhook_repo, values=values, case_id=case.id)
    return case, is_new, resolving, event


async def dispatch_case_if_needed(
    *, case_repo: RecoveryCaseCRUDRepository, case: RecoveryCase, is_new: bool, is_resolving: bool
) -> str:
    """
    Enqueue the case for the agent worker unless it is already in flight or
    was just resolved. A case with N merged retries still triggers exactly one
    dispatch, not N - repeat deliveries just enrich its history.
    """
    if not RecoveryCaseCRUDRepository.needs_dispatch(case, is_resolving=is_resolving):
        return "resolved" if is_resolving else "merged"

    try:
        task_id = enqueue(names.RECOVERY_CASE_PROCESS_TASK, priority=case.priority, kwargs={"case_id": case.id})
        await case_repo.mark_queued(
            case_id=case.id,
            celery_task_id=task_id,
            priority=case.priority,
            priority_reason=case.priority_reason or "",
        )
        return "queued" if is_new else "requeued"
    except Exception as exc:  # noqa: BLE001 - never fail the caller over dispatch
        loguru.logger.warning(
            f"recovery_case id={case.id} stored but not enqueued ({exc!r}); reconciler will retry"
        )
        return "stored"
