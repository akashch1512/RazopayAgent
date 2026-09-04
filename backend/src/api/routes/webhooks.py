import json

import fastapi
import loguru

from src.api.dependencies.repository import get_repository
from src.config.manager import settings
from src.integrations.razorpay.normalizer import build_dedupe_key, normalize_event
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.repository.crud.webhook_event import WebhookEventCRUDRepository

router = fastapi.APIRouter(prefix="/webhooks", tags=["webhooks"])


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
) -> dict[str, str]:
    """
    Single ingress for every onboarded business' Razorpay webhooks.

    Fast path only: verify signature, normalize the envelope, upsert one row,
    return 200. Anything heavier (agent context building) happens out of band
    off the stored `webhook_event` rows.
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
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Signature verification failed"
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
        created = await webhook_repo.store_event(values=values)
    except Exception as exc:  # noqa: BLE001 - never 500 back to Razorpay; it would retry-storm.
        loguru.logger.exception(f"Failed to persist Razorpay webhook: {exc}")
        return {"status": "error"}

    return {"status": "stored" if created else "duplicate"}
