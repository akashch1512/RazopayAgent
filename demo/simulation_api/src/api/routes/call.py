"""DEMO ONLY - no real telephony provider is involved. Records the attempt so
`frontend-demo`'s call log/popup can show it; nothing is actually dialed."""

import fastapi

from src import store
from src.schemas import ActionResponse, CallActionRequest

router = fastapi.APIRouter(prefix="/simulate", tags=["call"])


@router.post("/call", response_model=ActionResponse)
async def simulate_call(payload: CallActionRequest) -> ActionResponse:
    communication = store.record_action(
        case_id=payload.case_id,
        channel="call",
        customer_id=payload.customer_id or payload.phone_number,
        message=payload.message,
        payment_id=payload.payment_id,
        context=payload.context,
    )
    return ActionResponse(
        channel="call",
        event_id=communication["event_id"],
        detail=f"Simulated call to {payload.phone_number} - no real call was placed.",
    )
