import logging
import urllib.parse

import fastapi
from jose import JWTError

from src.api.dependencies import get_repository
from src.api.onboarding_state import decode_onboarding_state
from src.config.manager import settings
from src.integrations.razorpay.constants import WEBHOOK_EVENTS
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.oauth import razorpay_oauth_client
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.schemas.business import BusinessResponse
from src.repository.crud.business import BusinessCRUDRepository
from src.utilities.exceptions import EntityAlreadyExists, EntityDoesNotExist

router = fastapi.APIRouter(prefix="/integrations/razorpay", tags=["onboarding"])

logger = logging.getLogger(__name__)


def _onboarding_complete_url(**params: str) -> str:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/business/onboard/complete?{query}"


@router.get(path="/callback", name="razorpay:callback")
async def onboarding_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> fastapi.responses.RedirectResponse:
    """
    Step 2 of onboarding (Razorpay OAuth redirect target).

    Decodes the signed `state` token from step 1 (no DB lookup - nothing was
    persisted yet), exchanges `code` for tokens, and only then creates the
    `Business` row. If the grant is denied or anything fails before the code
    exchange succeeds, no row is ever written. Redirects the browser back to the
    dashboard (`FRONTEND_BASE_URL`) instead of dead-ending in raw JSON.
    """
    try:
        onboarding_data = decode_onboarding_state(state)
    except JWTError as exc:
        return fastapi.responses.RedirectResponse(
            _onboarding_complete_url(error=f"Onboarding session is invalid or expired: {exc}")
        )

    if error or not code:
        return fastapi.responses.RedirectResponse(
            _onboarding_complete_url(
                error=f"Authorization was not granted: {error or 'missing authorization code'}",
            )
        )

    try:
        token = await razorpay_oauth_client.exchange_code_for_token(code=code)
    except RazorpayIntegrationError as exc:
        logger.error(f"Onboarding failed for reference_id {onboarding_data['reference_id']}: {exc}")
        return fastapi.responses.RedirectResponse(_onboarding_complete_url(error=str(exc)))

    try:
        business = await business_repo.create_authorized_business(
            name=onboarding_data["name"],
            reference_id=onboarding_data["reference_id"],
            contact_email=onboarding_data.get("contact_email"),
            token=token,
        )
    except EntityAlreadyExists as exc:
        return fastapi.responses.RedirectResponse(_onboarding_complete_url(error=str(exc)))

    logger.info(
        f"business id={business.id} reference_id={business.reference_id} onboarded "
        f"(account_id={token.razorpay_account_id})"
    )

    try:
        webhook_secret = razorpay_webhook_client.generate_secret()
        webhook = await razorpay_webhook_client.create_webhook(
            account_id=token.razorpay_account_id or business.razorpay_account_id or "",
            access_token=token.access_token,
            secret=webhook_secret,
            events=WEBHOOK_EVENTS,
        )
        business = await business_repo.store_webhook(
            business=business,
            webhook_id=str(webhook.get("id", "")),
            webhook_secret=webhook_secret,
        )
    except RazorpayIntegrationError as exc:
        logger.error(f"Webhook registration failed for business {business.id}: {exc}")
        return fastapi.responses.RedirectResponse(
            _onboarding_complete_url(business_id=str(business.id), error=str(exc))
        )

    logger.info(f"business id={business.id} webhook registered id={webhook.get('id')}")
    return fastapi.responses.RedirectResponse(
        _onboarding_complete_url(business_id=str(business.id), status=business.status)
    )


@router.post(
    path="/businesses/{business_id}/refresh-token",
    name="razorpay:refresh-token",
    response_model=BusinessResponse,
)
async def refresh_business_token(
    business_id: int,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessResponse:
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
        refresh_token = business_repo.get_decrypted_refresh_token(business)
        token = await razorpay_oauth_client.refresh_access_token(refresh_token=refresh_token)
        business = await business_repo.store_oauth_tokens(business=business, token=token)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return BusinessResponse.model_validate(business)
