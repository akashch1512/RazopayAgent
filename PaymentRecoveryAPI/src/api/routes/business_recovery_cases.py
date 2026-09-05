import fastapi

from src.api.routes.onboarding import list_business_recovery_cases, start_custom_recovery
from src.models.schemas.recovery_case import RecoveryCaseResponse

router = fastapi.APIRouter(prefix="/recovery-cases", tags=["recovery-cases"])

router.add_api_route(
    "/businesses/{business_id}",
    list_business_recovery_cases,
    methods=["GET"],
    name="recovery-cases:list-by-business",
    response_model=list[RecoveryCaseResponse],
)
router.add_api_route(
    "/businesses/{business_id}/start",
    start_custom_recovery,
    methods=["POST"],
    name="recovery-cases:start-manual",
    status_code=fastapi.status.HTTP_201_CREATED,
)