import fastapi
import loguru

from src.api.dependencies.repository import get_repository
from src.models.db.recovery_case import RecoveryCaseStatus
from src.models.schemas.recovery_case import (
    CaseActionResponse,
    RecoveryCaseDetailResponse,
    RecoveryCaseResponse,
    WebhookEventResponse,
)
from src.repository.crud.case_action import CaseActionCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.utilities.exceptions.database import EntityDoesNotExist
from src.workers import names
from src.workers.enqueue import enqueue

router = fastapi.APIRouter(prefix="/recovery-cases", tags=["recovery-cases"])


@router.get(path="/", name="recovery-cases:list", response_model=list[RecoveryCaseResponse])
async def list_recovery_cases(
    business_id: int | None = None,
    status: RecoveryCaseStatus | None = None,
    limit: int = fastapi.Query(default=50, ge=1, le=200),
    offset: int = fastapi.Query(default=0, ge=0),
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
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


@router.get(
    path="/{case_id}",
    name="recovery-cases:get-by-id",
    response_model=RecoveryCaseDetailResponse,
)
async def get_recovery_case(
    case_id: int,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
    webhook_repo: WebhookEventCRUDRepository = fastapi.Depends(
        get_repository(repo_type=WebhookEventCRUDRepository)
    ),
    action_repo: CaseActionCRUDRepository = fastapi.Depends(
        get_repository(repo_type=CaseActionCRUDRepository)
    ),
) -> RecoveryCaseDetailResponse:
    """
    One merged case plus its full delivery history (inbound, from Razorpay)
    and its audit trail of agent actions (outbound - what was attempted and
    what came back, if anything) - "what happened with this case", end to end.
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


@router.post(
    path="/{case_id}/retry",
    name="recovery-cases:retry",
    response_model=RecoveryCaseResponse,
)
async def retry_recovery_case(
    case_id: int,
    case_repo: RecoveryCaseCRUDRepository = fastapi.Depends(
        get_repository(repo_type=RecoveryCaseCRUDRepository)
    ),
) -> RecoveryCaseResponse:
    """
    Manually reopen a `DEAD` or `FAILED` case and dispatch it again - for a
    human who just fixed the underlying issue (or wants another shot) rather
    than waiting on the reconciler's own backoff/aging.
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
        loguru.logger.warning(
            f"recovery_case id={case.id} reset but not enqueued ({exc!r}); reconciler will retry"
        )

    return RecoveryCaseResponse.model_validate(case)
