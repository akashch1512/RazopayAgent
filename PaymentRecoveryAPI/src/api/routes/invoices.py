import fastapi

from src.api.dependencies import get_repository
from src.integrations.razorpay.auth import build_auth_header
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.invoices import razorpay_invoices_client
from src.models.schemas.business import InvoiceResponse, StartInvoiceChaseRequest
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.services.recovery.ingestion import dispatch_case_if_needed, start_manual_case
from src.utilities.exceptions import EntityDoesNotExist

router = fastapi.APIRouter(prefix="/invoices", tags=["invoices"])


@router.get(path="/{business_id}", name="invoices:list", response_model=list[InvoiceResponse])
async def list_business_invoices(
    business_id: int,
    count: int = fastapi.Query(default=25, ge=1, le=100),
    skip: int = fastapi.Query(default=0, ge=0),
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
) -> list[InvoiceResponse]:
    """Live invoices from Razorpay (not cached) - lets a human pick one to start
    a B2B chase on."""
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
    path="/{business_id}/{invoice_id}/chase",
    name="invoices:start-chase",
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def start_invoice_chase(
    business_id: int,
    invoice_id: str,
    payload: StartInvoiceChaseRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(get_repository(repo_type=WebhookEventCRUDRepository)),
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
