"""DEMO ONLY - no real SMS provider is involved. Records the attempt so
`frontend-demo` can show it; nothing is actually sent."""

import fastapi

from src import store
from src.schemas import ActionResponse, SmsActionRequest

router = fastapi.APIRouter(prefix="/simulate", tags=["sms"])


@router.post("/sms", response_model=ActionResponse)
async def simulate_sms(payload: SmsActionRequest) -> ActionResponse:
    communication = store.record_action(
        case_id=payload.case_id,
        channel="sms",
        customer_id=payload.customer_id or payload.phone_number,
        message=payload.message,
        payment_id=payload.payment_id,
        context=payload.context,
    )
    return ActionResponse(
        channel="sms",
        event_id=communication["event_id"],
        detail=f"Simulated SMS to {payload.phone_number} - no real message was sent.",
    )
