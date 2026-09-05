"""DEMO ONLY - no real transactional email provider is involved. Records the
attempt so `frontend-demo` can show it; nothing is actually sent."""

import fastapi

from src import store
from src.schemas import ActionResponse, EmailActionRequest

router = fastapi.APIRouter(prefix="/simulate", tags=["email"])


@router.post("/email", response_model=ActionResponse)
async def simulate_email(payload: EmailActionRequest) -> ActionResponse:
    communication = store.record_action(
        case_id=payload.case_id,
        channel="email",
        customer_id=payload.customer_id or payload.email_address,
        message=f"{payload.subject}\n\n{payload.message}",
        payment_id=payload.payment_id,
        context=payload.context,
    )
    return ActionResponse(
        channel="email",
        event_id=communication["event_id"],
        detail=f"Simulated email to {payload.email_address} - no real email was sent.",
    )
