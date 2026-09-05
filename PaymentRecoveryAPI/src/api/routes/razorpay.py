import fastapi

from src.api.routes.onboarding import onboarding_callback, refresh_business_token
from src.models.schemas.business import BusinessResponse

router = fastapi.APIRouter(prefix="/integrations/razorpay", tags=["razorpay"])

router.add_api_route(
    "/callback",
    onboarding_callback,
    methods=["GET"],
    name="razorpay:callback",
)
router.add_api_route(
    "/businesses/{business_id}/refresh-token",
    refresh_business_token,
    methods=["POST"],
    name="razorpay:refresh-token",
    response_model=BusinessResponse,
)