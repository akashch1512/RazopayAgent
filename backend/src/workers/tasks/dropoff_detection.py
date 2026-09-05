"""
Detects payment drop-off: a customer who started checkout (an order got
created) but never completed payment. Razorpay fires no webhook for this - no
`order.created`, nothing - so it can only be discovered by polling
`GET /v1/orders` per business and looking for orders that are still not
`status=paid` after a "should've paid by now" threshold.

Businesses are polled one at a time on a rotation, not all at once:
`Business.next_dropoff_poll_at` is the DB's stand-in for a circular queue -
`list_due_for_dropoff_poll` always returns whoever is due soonest, and
`mark_dropoff_polled` pushes them to the back (+interval, +jitter to avoid
every business lining back up at the same instant). A newly onboarded business
joins the rotation immediately (`store_webhook` seeds `next_dropoff_poll_at`).

Each drop-off order is fed through the exact same merge/priority/dispatch
pipeline as a real webhook (`src.integrations.razorpay.ingestion`), tagged
with a synthetic `event_type="order.dropoff"` - everything downstream (case
merging, priority, the agent) treats it identically to a real event.
"""

import datetime
import random
import typing

import loguru

from src.config.manager import settings
from src.integrations.razorpay.auth import build_auth_header
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.ingestion import (
    dispatch_case_if_needed,
    store_event_for_case,
    upsert_case_from_event,
)
from src.integrations.razorpay.normalizer import normalize_event
from src.integrations.razorpay.orders import razorpay_orders_client
from src.models.db.business import Business
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.workers import names
from src.workers.celery_app import celery_app
from src.workers.runtime import run_async, worker_session
from src.workers.tasks.base import DBTask


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def _next_poll_at(now: datetime.datetime) -> datetime.datetime:
    jitter = random.uniform(0, settings.DROPOFF_POLL_JITTER_SECONDS)  # noqa: S311 - scheduling jitter, not security
    return now + datetime.timedelta(seconds=settings.DROPOFF_POLL_INTERVAL_SECONDS + jitter)


def _is_dropped_off(order: dict[str, typing.Any], *, now: datetime.datetime) -> bool:
    if order.get("status") == "paid":
        return False
    created_at = order.get("created_at")
    if not isinstance(created_at, int | float):
        return False
    age_seconds = now.timestamp() - created_at
    return age_seconds >= settings.DROPOFF_THRESHOLD_SECONDS


def _build_dropoff_envelope(order: dict[str, typing.Any], *, account_id: str) -> dict[str, typing.Any]:
    """Wraps a raw Orders-API order in the same envelope shape a real Razorpay
    webhook body has, so `normalize_event` (and `compute_priority`, which reads
    the same shape) work unmodified."""
    return {
        "entity": "event",
        "account_id": account_id,
        "event": "order.dropoff",
        "contains": ["order"],
        "payload": {"order": {"entity": order}},
        "created_at": order.get("created_at"),
    }


async def _poll_one_business(
    business: Business,
    *,
    case_repo: RecoveryCaseCRUDRepository,
    webhook_repo: WebhookEventCRUDRepository,
    now: datetime.datetime,
) -> int:
    headers, is_demo = build_auth_header(business)
    if headers is None:
        loguru.logger.warning(f"business id={business.id}: no Razorpay auth available, skipping drop-off poll.")
        return 0
    if is_demo:
        loguru.logger.warning(
            f"business id={business.id}: using the DEMO Razorpay Key ID/Secret fallback for the "
            "Orders API - this is for demo purposes only, never use it in production."
        )

    from_ts = int((now - datetime.timedelta(seconds=settings.DROPOFF_LOOKBACK_SECONDS)).timestamp())
    to_ts = int(now.timestamp())

    try:
        orders = await razorpay_orders_client.fetch_orders(
            account_id=business.razorpay_account_id,  # type: ignore[arg-type]
            auth_header=headers,
            from_ts=from_ts,
            to_ts=to_ts,
            max_orders=settings.DROPOFF_MAX_ORDERS_PER_BUSINESS,
        )
    except RazorpayIntegrationError as exc:
        loguru.logger.error(f"business id={business.id}: drop-off poll failed: {exc!r}")
        return 0

    detected = 0
    for order in orders:
        if not _is_dropped_off(order, now=now):
            continue

        body = _build_dropoff_envelope(order, account_id=business.razorpay_account_id)  # type: ignore[arg-type]
        values = normalize_event(
            body,
            dedupe_key=f"order_dropoff:{order.get('id')}",
            signature_verified=True,
            business_id=business.id,
        )
        # An order has no `order_id` field of its own (it *is* the order) - a
        # real `payment.failed`/`invoice.expired` webhook for this same order
        # keys its case on `order_id`, so this must match or the two would
        # never merge into one case.
        values["order_id"] = order.get("id")

        case, is_new, resolving = await upsert_case_from_event(case_repo=case_repo, values=values)
        event = await store_event_for_case(webhook_repo=webhook_repo, values=values, case_id=case.id)
        if event is not None:
            await dispatch_case_if_needed(case_repo=case_repo, case=case, is_new=is_new, is_resolving=resolving)
            detected += 1

    return detected


async def _poll_due_businesses() -> dict[str, int]:
    now = _utcnow()
    polled = 0
    dropoffs_found = 0

    async with worker_session() as session:
        business_repo = BusinessCRUDRepository(async_session=session)
        case_repo = RecoveryCaseCRUDRepository(async_session=session)
        webhook_repo = WebhookEventCRUDRepository(async_session=session)

        businesses = await business_repo.list_due_for_dropoff_poll(
            now=now, limit=settings.DROPOFF_POLL_BATCH_SIZE
        )

        for business in businesses:
            dropoffs_found += await _poll_one_business(
                business, case_repo=case_repo, webhook_repo=webhook_repo, now=now
            )
            await business_repo.mark_dropoff_polled(
                business_id=business.id, polled_at=now, next_poll_at=_next_poll_at(now)
            )
            polled += 1

    if polled:
        loguru.logger.info(f"drop-off poll: businesses_polled={polled} dropoffs_found={dropoffs_found}")
    return {"businesses_polled": polled, "dropoffs_found": dropoffs_found}


@celery_app.task(base=DBTask, name=names.DROPOFF_POLL_BUSINESSES_TASK, ignore_result=True)
def poll_businesses_for_dropoffs() -> dict[str, int]:
    return run_async(_poll_due_businesses())
