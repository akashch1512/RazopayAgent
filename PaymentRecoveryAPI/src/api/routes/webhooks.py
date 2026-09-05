import json
import logging

import fastapi

from src.api.dependencies import get_repository
from src.config.manager import settings
from src.integrations.razorpay.normalization import build_dedupe_key, normalize_event
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.schemas.recovery_case import WebhookEventResponse
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.services.recovery.ingestion import (
    dispatch_case_if_needed,
    store_event_for_case,
    upsert_case_from_event,
)
from src.utilities.exceptions import EntityDoesNotExist
from src.utilities.retry import transient_db_retry

router = fastapi.APIRouter(prefix="/webhooks", tags=["webhooks"])


logger = logging.getLogger(__name__)


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

    The merge/dispatch logic itself lives in `src.services.recovery.ingestion`
    - shared with the drop-off poller (`src.workers.tasks.dropoff_detection`),
    which synthesizes the same shape of event from the Orders API since
    Razorpay has no drop-off webhook.
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
        logger.warning(
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
        logger.warning(
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
        # NOTE: `upsert_case_from_event` and `store_event_for_case` commit
        # independently, so a transient failure landing *between* them (rare -
        # both are on the same connection) can retry the case merge alone and
        # double count one delivery in `event_count`. Not worth a shared
        # transaction for a heuristic retry counter; the dedupe_key still
        # makes the actual event row idempotent.
        async for attempt in transient_db_retry():
            with attempt:
                case, is_new, resolving = await upsert_case_from_event(case_repo=case_repo, values=values)
                event = await store_event_for_case(webhook_repo=webhook_repo, values=values, case_id=case.id)
    except Exception as exc:  # noqa: BLE001
        # Persistence genuinely failed: ask Razorpay to redeliver rather than
        # acking an event we dropped. It retries webhooks with backoff.
        logger.exception(f"Failed to persist Razorpay webhook: {exc}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist event, please redeliver",
        ) from exc

    if event is None:
        logger.info(f"Razorpay webhook {values['event_type']} account_id={account_id} deduplicated")
        return {"status": "duplicate"}

    status = await dispatch_case_if_needed(
        case_repo=case_repo,
        case=case,
        is_new=is_new,
        is_resolving=resolving,
        delay_seconds=settings.RECOVERY_GRACE_PERIOD_SECONDS,
    )
    logger.info(
        f"Razorpay webhook {values['event_type']} account_id={account_id} "
        f"-> case id={case.id} ({status})"
    )
    return {"status": status, "case_id": str(case.id)}


@router.get(
    path="/events/{event_id}",
    name="webhook-events:get-by-id",
    response_model=WebhookEventResponse,
)
async def get_webhook_event(
    event_id: int,
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
) -> WebhookEventResponse:
    """One raw delivery (full verbatim `payload` included) - for debugging a
    specific webhook outside the context of its merged recovery case."""
    try:
        event = await webhook_repo.read_event_by_id(event_id=event_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return WebhookEventResponse.model_validate(event)
