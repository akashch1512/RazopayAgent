import fastapi

from src.api.dependencies.repository import get_repository
from src.models.schemas.recovery_case import WebhookEventResponse
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.utilities.exceptions.database import EntityDoesNotExist

router = fastapi.APIRouter(prefix="/webhook-events", tags=["webhook-events"])


@router.get(
    path="/{event_id}",
    name="webhook-events:get-by-id",
    response_model=WebhookEventResponse,
)
async def get_webhook_event(
    event_id: int,
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
) -> WebhookEventResponse:
    """One raw delivery (full verbatim `payload` included) - for debugging a
    specific webhook outside the context of its merged recovery case."""
    try:
        event = await webhook_repo.read_event_by_id(event_id=event_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return WebhookEventResponse.model_validate(event)
