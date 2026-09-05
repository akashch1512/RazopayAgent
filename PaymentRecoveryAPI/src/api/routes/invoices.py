import fastapi

from src.api.routes.onboarding import list_business_invoices, start_invoice_chase
from src.models.schemas.business import InvoiceResponse

router = fastapi.APIRouter(prefix="/invoices", tags=["invoices"])

router.add_api_route(
    "/{business_id}",
    list_business_invoices,
    methods=["GET"],
    name="invoices:list",
    response_model=list[InvoiceResponse],
)
router.add_api_route(
    "/{business_id}/{invoice_id}/chase",
    start_invoice_chase,
    methods=["POST"],
    name="invoices:start-chase",
    status_code=fastapi.status.HTTP_201_CREATED,
)