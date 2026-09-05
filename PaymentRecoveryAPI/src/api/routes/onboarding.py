import datetime
import logging
import urllib.parse

import fastapi
from jose import JWTError
from jose import jwt as jose_jwt

from src.api.dependencies.repository import get_repository
from src.config.manager import settings
from src.integrations.razorpay.constants import WEBHOOK_EVENTS
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.helpers.auth import build_auth_header
from src.integrations.razorpay.invoices import razorpay_invoices_client
from src.integrations.razorpay.oauth import razorpay_oauth_client
from src.integrations.razorpay.webhooks import razorpay_webhook_client
from src.models.schemas.business import (
    AgentSettings,
    BusinessOnboardInitResponse,
    BusinessOnboardRequest,
    BusinessResponse,
    InvoiceResponse,
    StartInvoiceChaseRequest,
    WebhookConfigResponse,
)
from src.models.schemas.recovery_case import ManualRecoveryRequest, RecoveryCaseResponse
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.services.recovery.ingestion import dispatch_case_if_needed, start_manual_case
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist

router = fastapi.APIRouter(prefix="/onboard-business", tags=["onboarding"])

# How long a business owner has to complete the Razorpay OAuth grant before
# their onboarding attempt has to be restarted.
ONBOARDING_STATE_TTL_SECONDS = 900


logger = logging.getLogger(__name__)


def _encode_onboarding_state(onboard: BusinessOnboardRequest) -> str:
    """
    Self-contained, signed `state` token carrying the onboarding form fields.

    Nothing is written to the database at this point - the whole point is that
    a business only gets a DB row once they actually complete the Razorpay
    OAuth grant, not just for clicking "Continue with Razorpay".
    """
    payload = {
        "name": onboard.name,
        "reference_id": onboard.reference_id,
        "contact_email": onboard.contact_email,
        "exp": datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(seconds=ONBOARDING_STATE_TTL_SECONDS),
    }
    return jose_jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_onboarding_state(state: str) -> dict:
    return jose_jwt.decode(state, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


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

    No `Business` row is created here - only a signed `state` token carrying
    the form fields. Redirect the business owner to the returned
    `authorization_url`; Razorpay calls back to
    `/integrations/razorpay/callback`, and a row is created there only if the
    OAuth grant actually completes.
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

    state = _encode_onboarding_state(onboard)

    try:
        authorization_url = razorpay_oauth_client.build_authorization_url(
            state=state, scope=onboard.scope
        )
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


def _onboarding_complete_url(**params: str) -> str:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/business/onboard/complete?{query}"


@router.get(path="/callback", name="onboarding:callback")
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
    exchange succeeds, no row is ever written. Redirects the browser back to
    the dashboard (`FRONTEND_BASE_URL`) instead of dead-ending in raw JSON.
    """
    try:
        onboarding_data = _decode_onboarding_state(state)
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
        logger.error(
            f"Onboarding failed for reference_id {onboarding_data['reference_id']}: {exc}"
        )
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


@router.get(path="/", name="onboarding:list", response_model=list[BusinessResponse])
async def list_businesses(
    limit: int = fastapi.Query(default=50, ge=1, le=200),
    offset: int = fastapi.Query(default=0, ge=0),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> list[BusinessResponse]:
    businesses = await business_repo.read_businesses(limit=limit, offset=offset)
    return [BusinessResponse.model_validate(b) for b in businesses]


@router.get(path="/lookup", name="onboarding:lookup-by-reference-id", response_model=BusinessResponse)
async def lookup_business_by_reference_id(
    reference_id: str = fastapi.Query(..., min_length=1, max_length=255),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> BusinessResponse:
    """
    "Login" for an existing business - since there are no user accounts yet,
    the caller-supplied `reference_id` from onboarding is the only credential.
    """
    try:
        business = await business_repo.read_business_by_reference_id(reference_id=reference_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BusinessResponse.model_validate(business)


@router.get(path="/{business_id}", name="onboarding:get-by-id", response_model=BusinessResponse)
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
    path="/{business_id}/recovery-cases",
    name="onboarding:list-recovery-cases",
    response_model=list[RecoveryCaseResponse],
)
async def list_business_recovery_cases(
    business_id: int,
    limit: int = fastapi.Query(default=50, ge=1, le=200),
    offset: int = fastapi.Query(default=0, ge=0),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
) -> list[RecoveryCaseResponse]:
    """Every merged recovery case for this business, most recently active first."""
    try:
        await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    cases = await case_repo.list_cases_by_business(business_id=business_id, limit=limit, offset=offset)
    return [RecoveryCaseResponse.model_validate(case) for case in cases]


@router.get(
    path="/{business_id}/webhooks",
    name="onboarding:get-webhook-config",
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


@router.get(
    path="/{business_id}/settings",
    name="onboarding:get-agent-settings",
    response_model=AgentSettings,
)
async def get_agent_settings(
    business_id: int,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> AgentSettings:
    """How this business has customized its agent - read directly by
    `src.agent.context`/`src.agent.runner` on every case run."""
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AgentSettings.model_validate(business.agent_settings or {})


@router.put(
    path="/{business_id}/settings",
    name="onboarding:update-agent-settings",
    response_model=AgentSettings,
)
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


@router.get(
    path="/{business_id}/invoices",
    name="onboarding:list-invoices",
    response_model=list[InvoiceResponse],
)
async def list_business_invoices(
    business_id: int,
    count: int = fastapi.Query(default=25, ge=1, le=100),
    skip: int = fastapi.Query(default=0, ge=0),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> list[InvoiceResponse]:
    """Live invoices from Razorpay (not cached) - lets a human pick one to
    start a B2B chase on."""
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not business.razorpay_account_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Business `{business_id}` has not completed onboarding yet.",
        )

    headers, _is_demo = build_auth_header(business)
    if headers is None:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"No Razorpay auth available for business `{business_id}`.",
        )

    try:
        invoices = await razorpay_invoices_client.fetch_invoices(
            account_id=business.razorpay_account_id, auth_header=headers, count=count, skip=skip
        )
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return [InvoiceResponse.model_validate(invoice) for invoice in invoices]


@router.post(
    path="/{business_id}/invoices/{invoice_id}/chase",
    name="onboarding:start-invoice-chase",
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def start_invoice_chase(
    business_id: int,
    invoice_id: str,
    payload: StartInvoiceChaseRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
) -> dict[str, str]:
    """
    "Start B2B chase" - fetches the invoice fresh from Razorpay, then starts a
    recovery case for it (merges with any existing case for the same invoice/
    order) through the same pipeline every other event uses.
    """
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    headers, _is_demo = build_auth_header(business)
    if headers is None or not business.razorpay_account_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"No Razorpay auth available for business `{business_id}`.",
        )

    try:
        invoice = await razorpay_invoices_client.fetch_invoice(
            account_id=business.razorpay_account_id, auth_header=headers, invoice_id=invoice_id
        )
    except RazorpayIntegrationError as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    customer = invoice.get("customer_details") or {}
    reason = payload.reason or f"B2B chase requested for invoice {invoice_id}"

    case, is_new, resolving, event = await start_manual_case(
        case_repo=case_repo,
        webhook_repo=webhook_repo,
        business_id=business.id,
        razorpay_account_id=business.razorpay_account_id,
        event_type="invoice.b2b_chase",
        order_reference=invoice.get("id", invoice_id),
        customer_email=customer.get("email"),
        customer_contact=customer.get("contact"),
        amount=invoice.get("amount_due") or invoice.get("amount"),
        currency=invoice.get("currency", "INR"),
        reason=reason,
    )
    if event is None:
        return {"status": "duplicate", "case_id": str(case.id)}

    status = await dispatch_case_if_needed(case_repo=case_repo, case=case, is_new=is_new, is_resolving=resolving)
    return {"status": status, "case_id": str(case.id)}


@router.post(
    path="/{business_id}/recovery-cases/start",
    name="onboarding:start-manual-recovery",
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def start_custom_recovery(
    business_id: int,
    payload: ManualRecoveryRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
) -> dict[str, str]:
    """
    "Start custom recovery" - a human manually asks the agent to chase an
    order/customer that didn't (yet) trigger any webhook, drop-off, or invoice
    detection - e.g. a support ticket, a manual escalation. Merges with any
    existing case for the same `order_reference`.
    """
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not business.razorpay_account_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Business `{business_id}` has not completed onboarding yet.",
        )

    case, is_new, resolving, event = await start_manual_case(
        case_repo=case_repo,
        webhook_repo=webhook_repo,
        business_id=business.id,
        razorpay_account_id=business.razorpay_account_id,
        event_type="manual.recovery",
        order_reference=payload.order_reference,
        customer_email=payload.customer_email,
        customer_contact=payload.customer_contact,
        amount=payload.amount,
        currency=payload.currency,
        reason=payload.reason,
    )
    if event is None:
        return {"status": "duplicate", "case_id": str(case.id)}

    status = await dispatch_case_if_needed(case_repo=case_repo, case=case, is_new=is_new, is_resolving=resolving)
    return {"status": status, "case_id": str(case.id)}
