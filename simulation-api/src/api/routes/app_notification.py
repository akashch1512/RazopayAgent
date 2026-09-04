"""DEMO ONLY - no real push-notification provider is involved. Records the
attempt so `frontend-demo` can show it; nothing is actually sent."""

import fastapi

from src import store
from src.schemas import ActionResponse, AppNotificationActionRequest

router = fastapi.APIRouter(prefix="/simulate", tags=["app-notification"])


@router.post("/app-notification", response_model=ActionResponse)
async def simulate_app_notification(payload: AppNotificationActionRequest) -> ActionResponse:
    communication = store.record_action(
        case_id=payload.case_id,
        channel="app_notification",
        customer_id=payload.customer_id,
        message=f"{payload.title}\n\n{payload.message}",
        payment_id=payload.payment_id,
        context=payload.context,
    )
    return ActionResponse(
        channel="app_notification",
        event_id=communication["event_id"],
        detail=f"Simulated app notification to {payload.customer_id} - no real notification was sent.",
    )
