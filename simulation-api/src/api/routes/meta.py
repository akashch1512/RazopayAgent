"""
The dashboard-facing side of the demo: what `frontend-demo` polls and posts to
(see `frontend-demo/src/demoApi.js`). `user_id` in the URL is whatever
identifier the agent tools used as `case_id` when they called `/simulate/*` -
in practice, the real backend's `RecoveryCase.id`.
"""

import fastapi

from src import store
from src.schemas import DashboardResponse, PayRequest, ReplyRequest

router = fastapi.APIRouter(prefix="/dashboard", tags=["dashboard"])


def _not_found(user_id: str) -> fastapi.HTTPException:
    return fastapi.HTTPException(
        status_code=fastapi.status.HTTP_404_NOT_FOUND,
        detail=f"No recovery case found for '{user_id}' yet - the agent hasn't taken an action on it.",
    )


@router.get("/users/{user_id}", response_model=DashboardResponse)
async def get_user_dashboard(user_id: str) -> DashboardResponse:
    case = store.get_case(user_id)
    if case is None:
        raise _not_found(user_id)
    return DashboardResponse(recovery_case=case, metrics=store.metrics())


@router.post("/users/{user_id}/messages", response_model=DashboardResponse)
async def post_dashboard_message(user_id: str, payload: ReplyRequest) -> DashboardResponse:
    """Simulates the *customer* replying on `payload.channel`."""
    communication = store.record_customer_reply(case_id=user_id, channel=payload.channel, message=payload.message)
    if communication is None:
        raise _not_found(user_id)
    case = store.get_case(user_id)
    assert case is not None  # record_customer_reply only returns non-None if the case exists
    return DashboardResponse(recovery_case=case, metrics=store.metrics())


@router.post("/users/{user_id}/pay", response_model=DashboardResponse)
async def post_dashboard_pay(user_id: str, payload: PayRequest) -> DashboardResponse:
    """Simulates the customer completing the payment out-of-band."""
    case = store.mark_paid(case_id=user_id)
    if case is None:
        raise _not_found(user_id)
    return DashboardResponse(recovery_case=case, metrics=store.metrics())
