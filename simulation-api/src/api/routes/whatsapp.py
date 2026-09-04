"""DEMO ONLY - no real WhatsApp Business API is involved. Records the attempt
so `frontend-demo` can show it; nothing is actually sent."""

import fastapi

from src import store
from src.schemas import ActionResponse, WhatsappActionRequest

router = fastapi.APIRouter(prefix="/simulate", tags=["whatsapp"])


@router.post("/whatsapp", response_model=ActionResponse)
async def simulate_whatsapp(payload: WhatsappActionRequest) -> ActionResponse:
    communication = store.record_action(
        case_id=payload.case_id,
        channel="whatsapp",
        customer_id=payload.customer_id or payload.phone_number,
        message=payload.message,
        payment_id=payload.payment_id,
        context=payload.context,
    )
    return ActionResponse(
        channel="whatsapp",
        event_id=communication["event_id"],
        detail=f"Simulated WhatsApp message to {payload.phone_number} - no real message was sent.",
    )
