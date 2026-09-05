import logging

import fastapi

from src.api.dependencies import get_repository
from src.models.db.recovery_case import RecoveryCaseStatus
from src.models.schemas.recovery_case import (
    CaseActionResponse,
    CustomerFeedbackRequest,
    ManualRecoveryRequest,
    RecoveryCaseDetailResponse,
    RecoveryCaseResponse,
    WebhookEventResponse,
)
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.case_action import CaseActionCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.services.recovery.ingestion import (
    dispatch_case_if_needed,
    record_customer_feedback,
    record_manual_resolution,
    start_manual_case,
)
from src.utilities.exceptions import EntityDoesNotExist
from src.workers import names
from src.workers.enqueue import enqueue

router = fastapi.APIRouter(prefix="/recovery-cases", tags=["recovery-cases"])

logger = logging.getLogger(__name__)


@router.get(path="/", name="recovery-cases:list", response_model=list[RecoveryCaseResponse])
async def list_recovery_cases(
    business_id: int | None = None,
    status: RecoveryCaseStatus | None = None,
    limit: int = fastapi.Query(default=50, ge=1, le=200),
    offset: int = fastapi.Query(default=0, ge=0),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
) -> list[RecoveryCaseResponse]:
    """
    Every recovery case, most recently active first - an ops/support dashboard's
    main query. Optionally narrow by `business_id` and/or `status` (e.g.
    `?status=DEAD` to find cases that need a human).
    """
    cases = await case_repo.list_cases(
        business_id=business_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )
    return [RecoveryCaseResponse.model_validate(case) for case in cases]


@router.post(
    path="/businesses/{business_id}/start",
    name="recovery-cases:start-manual",
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def start_custom_recovery(
    business_id: int,
    payload: ManualRecoveryRequest,
    business_repo: BusinessCRUDRepository = fastapi.Depends(get_repository(repo_type=BusinessCRUDRepository)),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(get_repository(repo_type=WebhookEventCRUDRepository)),
) -> dict[str, str]:
    """
    "Start custom recovery" - a human manually asks the agent to chase a specific
    order/customer that didn't (yet) trigger any webhook, drop-off, or invoice
    detection (e.g. a support ticket, a manual escalation). Merges with any
    existing case for the same `order_reference`.
    """
    try:
        business = await business_repo.read_business_by_id(business_id=business_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not business.razorpay_account_id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Business `{business_id}` has not completed onboarding yet.",
        )

    case, is_new, resolving, event = await start_manual_case(
        case_repo=case_repo,
        webhook_repo=webhook_repo,
        business_id=business.id,
        razorpay_account_id=business.razorpay_account_id,
        event_type="manual.recovery",
        order_reference=payload.order_reference,
        customer_email=payload.customer_email,
        customer_contact=payload.customer_contact,
        amount=payload.amount,
        currency=payload.currency,
        reason=payload.reason,
    )
    if event is None:
        return {"status": "duplicate", "case_id": str(case.id)}

    status = await dispatch_case_if_needed(case_repo=case_repo, case=case, is_new=is_new, is_resolving=resolving)
    return {"status": status, "case_id": str(case.id)}


@router.get(path="/{case_id}", name="recovery-cases:get-by-id", response_model=RecoveryCaseDetailResponse)
async def get_recovery_case(
    case_id: int,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(get_repository(repo_type=WebhookEventCRUDRepository)),
    action_repo: CaseActionCRUDRepository = fastapi.Depends(get_repository(repo_type=CaseActionCRUDRepository)),
) -> RecoveryCaseDetailResponse:
    """
    One merged case plus its full delivery history (inbound, from Razorpay) and
    its audit trail of agent actions (outbound - what was attempted and what came
    back, if anything) - "what happened with this case", end to end.
    """
    try:
        case = await case_repo.read_case_by_id(case_id=case_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    history = await webhook_repo.list_case_history(case_id=case_id)
    actions = await action_repo.list_actions_by_case(case_id=case_id)
    embedded_fields = ("history", "actions")
    return RecoveryCaseDetailResponse(
        **{
            field: getattr(case, field)
            for field in RecoveryCaseDetailResponse.model_fields
            if field not in embedded_fields
        },
        history=[WebhookEventResponse.model_validate(event) for event in history],
        actions=[CaseActionResponse.model_validate(action) for action in actions],
    )


@router.post(path="/{case_id}/feedback", name="recovery-cases:feedback", status_code=fastapi.status.HTTP_200_OK)
async def submit_customer_feedback(
    case_id: int,
    payload: CustomerFeedbackRequest,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(get_repository(repo_type=WebhookEventCRUDRepository)),
) -> dict[str, str]:
    """
    A customer replied on some channel (today: the demo dashboard, via
    `simulation-api`) - merge it into the case's history and re-dispatch the
    agent with that feedback in context. Reuses the same merge/priority/dispatch
    pipeline as a real webhook (`src.services.recovery.ingestion`).
    """
    try:
        case = await case_repo.read_case_by_id(case_id=case_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    case, event = await record_customer_feedback(
        case_repo=case_repo,
        webhook_repo=webhook_repo,
        case=case,
        channel=payload.channel,
        message=payload.message,
    )
    if event is None:
        return {"status": "duplicate", "case_id": str(case.id)}

    status = await dispatch_case_if_needed(case_repo=case_repo, case=case, is_new=False, is_resolving=False)
    return {"status": status, "case_id": str(case.id)}


@router.post(path="/{case_id}/mark-paid", name="recovery-cases:mark-paid", status_code=fastapi.status.HTTP_200_OK)
async def mark_recovery_case_paid(
    case_id: int,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(get_repository(repo_type=WebhookEventCRUDRepository)),
) -> dict[str, str]:
    """
    A human confirms this case is paid (the demo dashboard's "mark as paid", or
    ops closing it out of band). Synthesized as a `payment.captured` event so it
    flows through the same pipeline as a real resolving webhook and the case is
    force-closed to RESOLVED.
    """
    try:
        case = await case_repo.read_case_by_id(case_id=case_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    case, _event = await record_manual_resolution(case_repo=case_repo, webhook_repo=webhook_repo, case=case)
    return {"status": case.processing_status, "case_id": str(case.id)}


@router.post(path="/{case_id}/retry", name="recovery-cases:retry", response_model=RecoveryCaseResponse)
async def retry_recovery_case(
    case_id: int,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(get_repository(repo_type=RecoveryCaseCRUDRepository)),
) -> RecoveryCaseResponse:
    """
    Manually reopen a `DEAD` or `FAILED` case and dispatch it again - for a human
    who just fixed the underlying issue (or wants another shot) rather than
    waiting on the reconciler's own backoff/aging.
    """
    try:
        case = await case_repo.reset_case_for_retry(case_id=case_id)
    except EntityDoesNotExist as exc:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        task_id = enqueue(names.RECOVERY_CASE_PROCESS_TASK, priority=case.priority, kwargs={"case_id": case.id})
        await case_repo.mark_queued(
            case_id=case.id,
            celery_task_id=task_id,
            priority=case.priority,
            priority_reason="manual retry",
        )
        case = await case_repo.read_case_by_id(case_id=case.id)
    except Exception as exc:  # noqa: BLE001 - never fail the request over dispatch
        logger.warning(f"recovery_case id={case.id} reset but not enqueued ({exc!r}); reconciler will retry")

    return RecoveryCaseResponse.model_validate(case)
