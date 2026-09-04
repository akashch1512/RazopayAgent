import json

import fastapi
import loguru

from src.api.dependencies.repository import get_repository
from src.config.manager import settings
from src.integrations.razorpay.normalizer import build_dedupe_key, normalize_event
from src.integrations.razorpay.priority import compute_priority
from src.integrations.razorpay.recovery_case import is_resolving_event, resolve_case_key
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.db.recovery_case import RecoveryCase
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.utilities.retry import transient_db_retry
from src.workers import names
from src.workers.enqueue import enqueue

router = fastapi.APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _upsert_case(
    *, case_repo: RecoveryCaseCRUDRepository, values: dict
) -> tuple[RecoveryCase, bool, bool]:
    """
    Merge this delivery into its recovery case. Returns `(case, is_new, is_resolving)`.

    This runs *before* the event is stored so the row can be written with its
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


async def _dispatch_if_needed(
    *, case_repo: RecoveryCaseCRUDRepository, case: RecoveryCase, is_new: bool, is_resolving: bool
) -> str:
    """
    Enqueue the case for the agent worker unless it is already in flight or was
    just resolved. A case with 5 merged retries still triggers exactly one
    dispatch, not five - repeat deliveries just enrich its history.
    """
    if not RecoveryCaseCRUDRepository.needs_dispatch(case, is_resolving=is_resolving):
        return "resolved" if is_resolving else "merged"

    try:
        task_id = enqueue(
            names.RECOVERY_CASE_PROCESS_TASK,
            priority=case.priority,
            kwargs={"case_id": case.id},
        )
        await case_repo.mark_queued(
            case_id=case.id,
            celery_task_id=task_id,
            priority=case.priority,
            priority_reason=case.priority_reason or "",
        )
        return "queued" if is_new else "requeued"
    except Exception as exc:  # noqa: BLE001 - never fail the request over dispatch
        loguru.logger.warning(
            f"recovery_case id={case.id} stored but not enqueued ({exc!r}); reconciler will retry"
        )
        return "stored"


@router.post(
    path="/razorpay",
    name="webhooks:razorpay",
    status_code=fastapi.status.HTTP_200_OK,
)
async def receive_razorpay_webhook(
    request: fastapi.Request,
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
) -> dict[str, str]:
    """
    Single ingress for every onboarded business' Razorpay webhooks.

    Fast path: verify signature, normalize the envelope, merge it into its
    recovery case (same order / same entity -> same case, so a customer
    retrying a failing payment N times is one unit of agent work, not N),
    persist the delivery as history, dispatch the case by priority, return 200.
    """
    raw_body = await request.body()

    try:
        body = json.loads(raw_body)
        if not isinstance(body, dict):
            raise ValueError("payload is not a JSON object")
    except ValueError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON body: {exc}"
        ) from exc

    signature = request.headers.get("X-Razorpay-Signature")
    account_id = body.get("account_id")

    business_id, secret = await webhook_repo.resolve_business(account_id=account_id)
    if business_id is None:
        loguru.logger.warning(
            f"Razorpay webhook for unknown account_id={account_id} event={body.get('event')}"
        )
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_200_OK, detail="Unauthorized Business: account_id not onboarded"
        )
    secret = secret or settings.RAZORPAY_WEBHOOK_SECRET

    verified = razorpay_webhook_client.verify_signature(
        raw_body=raw_body, signature=signature, secret=secret or ""
    )
    if not verified:
        loguru.logger.warning(
            f"Unverified Razorpay webhook: event={body.get('event')} account_id={account_id}"
        )
        if settings.RAZORPAY_WEBHOOK_REJECT_UNVERIFIED:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_200_OK, detail="Signature verification failed"
            )

    values = normalize_event(
        body,
        dedupe_key=build_dedupe_key(
            event_id=request.headers.get("X-Razorpay-Event-Id"), raw_body=raw_body
        ),
        signature_verified=verified,
        business_id=business_id,
    )

    try:
        # NOTE: `_upsert_case` and `store_event` commit independently, so a
        # transient failure landing *between* them (rare - both are on the same
        # connection) can retry the case merge alone and double count one
        # delivery in `event_count`. Not worth a shared transaction for a
        # heuristic retry counter; the dedupe_key still makes the actual event
        # row idempotent.
        async for attempt in transient_db_retry():
            with attempt:
                case, is_new, resolving = await _upsert_case(case_repo=case_repo, values=values)
                event_values = {
                    key: value
                    for key, value in values.items()
                    if key not in ("customer_email", "customer_contact")
                }
                event_values["case_id"] = case.id
                event = await webhook_repo.store_event(values=event_values)
    except Exception as exc:  # noqa: BLE001
        # Persistence genuinely failed: ask Razorpay to redeliver rather than
        # acking an event we dropped. It retries webhooks with backoff.
        loguru.logger.exception(f"Failed to persist Razorpay webhook: {exc}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist event, please redeliver",
        ) from exc

    if event is None:
        return {"status": "duplicate"}

    status = await _dispatch_if_needed(
        case_repo=case_repo, case=case, is_new=is_new, is_resolving=resolving
    )
    return {"status": status, "case_id": str(case.id)}
