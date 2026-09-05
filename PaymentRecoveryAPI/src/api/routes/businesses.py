import fastapi

from src.api.routes.onboarding import (
    get_agent_settings,
    get_business,
    get_business_webhook_config,
    initiate_onboarding,
    list_businesses,
    lookup_business_by_reference_id,
    update_agent_settings,
)
from src.models.schemas.business import (
    AgentSettings,
    BusinessOnboardInitResponse,
    BusinessResponse,
    WebhookConfigResponse,
)

router = fastapi.APIRouter(prefix="/businesses", tags=["businesses"])

router.add_api_route(
    "/",
    initiate_onboarding,
    methods=["POST"],
    name="businesses:initiate",
    response_model=BusinessOnboardInitResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
)
router.add_api_route(
    "/",
    list_businesses,
    methods=["GET"],
    name="businesses:list",
    response_model=list[BusinessResponse],
)
router.add_api_route(
    "/lookup",
    lookup_business_by_reference_id,
    methods=["GET"],
    name="businesses:lookup-by-reference-id",
    response_model=BusinessResponse,
)
router.add_api_route(
    "/{business_id}",
    get_business,
    methods=["GET"],
    name="businesses:get-by-id",
    response_model=BusinessResponse,
)
router.add_api_route(
    "/{business_id}/webhook",
    get_business_webhook_config,
    methods=["GET"],
    name="businesses:get-webhook-config",
    response_model=WebhookConfigResponse,
)
router.add_api_route(
    "/{business_id}/settings",
    get_agent_settings,
    methods=["GET"],
    name="businesses:get-agent-settings",
    response_model=AgentSettings,
)
router.add_api_route(
    "/{business_id}/settings",
    update_agent_settings,
    methods=["PUT"],
    name="businesses:update-agent-settings",
    response_model=AgentSettings,
)