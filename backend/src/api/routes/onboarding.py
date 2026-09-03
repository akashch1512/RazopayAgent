import secrets

import fastapi
import loguru

from src.api.dependencies.repository import get_repository
from src.integrations.razorpay.constants import WEBHOOK_EVENTS
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.oauth import razorpay_oauth_client
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.schemas.business import (
    BusinessOnboardInitResponse,
    BusinessOnboardRequest,
    BusinessResponse,
)
from src.repository.crud.business import BusinessCRUDRepository
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist

router = fastapi.APIRouter(prefix="/onboard-business", tags=["onboarding"])


@router.post(
    path="/",
    name="onboarding:initiate",
    response_model=BusinessOnboardInitResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def initiate_onboarding(
    onboard: BusinessOnboardRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessOnboardInitResponse:
    """
    Step 1 of onboarding.

    Registers a `PENDING` business row and returns the Razorpay `authorization_url`.
    Redirect the business owner there; Razorpay calls back to `/onboard-business/callback`.
    """
    state = secrets.token_urlsafe(32)

    try:
        business = await business_repo.create_pending_business(onboard=onboard, oauth_state=state)
    except EntityAlreadyExists as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    try:
        authorization_url = razorpay_oauth_client.build_authorization_url(
            state=state, scope=onboard.scope
        )
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return BusinessOnboardInitResponse(
        business_id=business.id,
        reference_id=business.reference_id,
        status=business.status,
        authorization_url=authorization_url,
        state=state,
    )


@router.get(
    path="/callback",
    name="onboarding:callback",
    response_model=BusinessResponse,
)
async def onboarding_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessResponse:
    """
    Step 2 of onboarding (Razorpay OAuth redirect target).

    Exchanges `code` for tokens, stores them encrypted, then creates the
    sub-merchant webhook for the configured event triggers.
    """
    try:
        business = await business_repo.read_business_by_oauth_state(oauth_state=state)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if error or not code:
        business.status = "DENIED"
        await business_repo.async_session.commit()
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Authorization was not granted: {error or 'missing authorization code'}",
        )

    try:
        token = await razorpay_oauth_client.exchange_code_for_token(code=code)
        business = await business_repo.store_oauth_tokens(business=business, token=token)

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
        loguru.logger.error(f"Onboarding failed for business {business.id}: {exc}")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return BusinessResponse.model_validate(business)


@router.get(path="/", name="onboarding:list", response_model=list[BusinessResponse])
async def list_businesses(
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> list[BusinessResponse]:
    businesses = await business_repo.read_businesses()
    return [BusinessResponse.model_validate(b) for b in businesses]


@router.post(
    path="/{business_id}/refresh-token",
    name="onboarding:refresh-token",
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
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return BusinessResponse.model_validate(business)
