import logging

import fastapi

from src.api.dependencies import get_repository
from src.api.onboarding_state import encode_onboarding_state
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.oauth import razorpay_oauth_client
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.schemas.business import (
    AgentSettings,
    BusinessOnboardInitResponse,
    BusinessOnboardRequest,
    BusinessResponse,
    WebhookConfigResponse,
)
from src.repository.crud.business import BusinessCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist

router = fastapi.APIRouter(prefix="/businesses", tags=["businesses"])

logger = logging.getLogger(__name__)


@router.post(
    path="/",
    name="businesses:initiate",
    response_model=BusinessOnboardInitResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def initiate_onboarding(
    onboard: BusinessOnboardRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessOnboardInitResponse:
    """
    Step 1 of onboarding.

    No `Business` row is created here - only a signed `state` token carrying the
    form fields. Redirect the business owner to the returned `authorization_url`;
    Razorpay calls back to `/integrations/razorpay/callback`, and a row is
    created there only if the OAuth grant actually completes.
    """
    try:
        await business_repo.read_business_by_reference_id(reference_id=onboard.reference_id)
    except EntityDoesNotExist:
        pass
    else:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail=f"A business with reference_id `{onboard.reference_id}` already exists!",
        )

    state = encode_onboarding_state(onboard)

    try:
        authorization_url = razorpay_oauth_client.build_authorization_url(state=state, scope=onboard.scope)
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return BusinessOnboardInitResponse(
        business_id=None,
        reference_id=onboard.reference_id,
        status="PENDING",
        authorization_url=authorization_url,
        state=state,
    )


@router.get(path="/", name="businesses:list", response_model=list[BusinessResponse])
async def list_businesses(
    limit: int = fastapi.Query(default=50, ge=1, le=200),
    offset: int = fastapi.Query(default=0, ge=0),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> list[BusinessResponse]:
    businesses = await business_repo.read_businesses(limit=limit, offset=offset)
    return [BusinessResponse.model_validate(b) for b in businesses]


@router.get(path="/lookup", name="businesses:lookup-by-reference-id", response_model=BusinessResponse)
async def lookup_business_by_reference_id(
    reference_id: str = fastapi.Query(..., min_length=1, max_length=255),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessResponse:
    """
    "Login" for an existing business - since there are no user accounts yet, the
    caller-supplied `reference_id` from onboarding is the only credential.
    """
    try:
        business = await business_repo.read_business_by_reference_id(reference_id=reference_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BusinessResponse.model_validate(business)


@router.get(path="/{business_id}", name="businesses:get-by-id", response_model=BusinessResponse)
async def get_business(
    business_id: int,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessResponse:
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BusinessResponse.model_validate(business)


@router.get(
    path="/{business_id}/webhook",
    name="businesses:get-webhook-config",
    response_model=WebhookConfigResponse,
)
async def get_business_webhook_config(
    business_id: int,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> WebhookConfigResponse:
    """
    Live config (url, active, events) of the webhook Razorpay has registered for
    this business - fetched from Razorpay on every call, not a local cache.
    """
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not business.webhook_id or not business.razorpay_account_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Business `{business_id}` has no webhook registered yet.",
        )

    try:
        access_token = business_repo.get_decrypted_access_token(business)
        webhook = await razorpay_webhook_client.get_webhook(
            account_id=business.razorpay_account_id,
            webhook_id=business.webhook_id,
            access_token=access_token,
        )
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return WebhookConfigResponse.model_validate(webhook)


@router.get(path="/{business_id}/settings", name="businesses:get-agent-settings", response_model=AgentSettings)
async def get_agent_settings(
    business_id: int,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> AgentSettings:
    """How this business has customized its agent - read on every case run by
    `src.agent.orchestration.context` / `src.agent.application.runner`."""
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AgentSettings.model_validate(business.agent_settings or {})


@router.put(path="/{business_id}/settings", name="businesses:update-agent-settings", response_model=AgentSettings)
async def update_agent_settings(
    business_id: int,
    payload: AgentSettings,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> AgentSettings:
    try:
        business = await business_repo.update_agent_settings(
            business_id=business_id, agent_settings=payload.model_dump(mode="json")
        )
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AgentSettings.model_validate(business.agent_settings or {})
