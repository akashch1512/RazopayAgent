"""
The consumer side: drain one merged recovery case from the priority queue and
hand it, with its full retry history, to the LangGraph recovery agent.

Cases are dispatched independently by `case_id`, so any number of workers can
process *different* cases in parallel - `claim_for_processing`'s atomic
`UPDATE ... WHERE processing_status IN (...)` is what stops two workers from
double-processing the *same* case, not a `--concurrency=1` restriction. Scale
the number of parallel workers with `celery worker --concurrency=N` (see
`CELERY_WORKER_CONCURRENCY` in docker-compose / `.env`).
"""

import datetime
import logging

from celery.exceptions import SoftTimeLimitExceeded

from src.agent.application.runner import run_recovery_agent
from src.config.manager import settings
from src.models.db.business import Business
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.case_action import CaseActionCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist
from src.workers import names
from src.workers.celery_app import celery_app
from src.workers.enqueue import EnqueueError, enqueue
from src.workers.runtime import run_async, worker_session
from src.workers.tasks.base import DBTask, retry_backoff_seconds

logger = logging.getLogger(__name__)

# Hard ceiling on an agent-requested follow-up delay, so a bad `next_check_after`
# can't park a case for months.
_MAX_FOLLOWUP_SECONDS = 14 * 24 * 3600


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


async def _schedule_followup_if_requested(
    *,
    case_repo: RecoveryCaseCRUDRepository,
    case_id: int,
    priority: int,
    iso_time: object,
) -> str | None:
    """Re-queue a just-processed case for a future run the agent asked for
    (`record_case_memory(next_check_after=...)`). Returns the effective time, or
    `None` if nothing was scheduled."""
    if not isinstance(iso_time, str) or not iso_time.strip():
        return None
    try:
        due = datetime.datetime.fromisoformat(iso_time.strip().replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"recovery_case id={case_id}: ignoring invalid next_check_after={iso_time!r}")
        return None
    if due.tzinfo is None:
        due = due.replace(tzinfo=datetime.UTC)

    countdown = int(min(_MAX_FOLLOWUP_SECONDS, max(0, (due - _utcnow()).total_seconds())))
    try:
        task_id = enqueue(
            names.RECOVERY_CASE_PROCESS_TASK,
            priority=priority,
            kwargs={"case_id": case_id},
            countdown=countdown,
        )
    except EnqueueError as exc:
        logger.warning(f"recovery_case id={case_id}: could not schedule follow-up ({exc!r}); reconciler will retry")
        return None

    await case_repo.mark_queued(
        case_id=case_id,
        celery_task_id=task_id,
        priority=priority,
        priority_reason="agent-scheduled follow-up",
        not_before=due,
    )
    logger.info(f"recovery_case id={case_id} follow-up scheduled for {due.isoformat()} (in {countdown}s)")
    return due.isoformat()


async def _load_business(business_id: int | None, *, business_repo: BusinessCRUDRepository) -> Business:
    """
    A best-effort `Business` for context/MCP purposes. Most cases resolve one
    (via `account_id` at ingest time); for the rare one that doesn't, a
    transient, never-persisted stand-in keeps the agent's context builder and
    MCP tool loader from needing a separate "no business" code path.
    """
    if business_id is not None:
        try:
            return await business_repo.read_business_by_id(business_id=business_id)
        except EntityDoesNotExist:
            logger.warning(f"business_id={business_id} referenced by a case no longer exists")

    return Business(name="Unknown Business", reference_id="unresolved")


async def _process(task: DBTask, case_id: int) -> dict[str, object]:
    async with worker_session() as session:
        case_repo = RecoveryCaseCRUDRepository(async_session=session)
        event_repo = WebhookEventCRUDRepository(async_session=session)
        action_repo = CaseActionCRUDRepository(async_session=session)
        business_repo = BusinessCRUDRepository(async_session=session)

        case = await case_repo.claim_for_processing(
            case_id=case_id, max_attempts=settings.WEBHOOK_MAX_PROCESSING_ATTEMPTS
        )
        if case is None:
            # Already processed / resolved / dead / gone, or over the attempt ceiling.
            logger.info(f"recovery_case id={case_id} not claimable - skipping")
            return {"case_id": case_id, "status": "skipped"}

        logger.info(
            f"recovery_case id={case_id} claimed for processing "
            f"(attempt {case.processing_attempts}, priority {case.priority})"
        )
        history = await event_repo.list_case_history(case_id=case_id, limit=settings.RECOVERY_CASE_HISTORY_LIMIT)
        actions = await action_repo.list_actions_by_case(case_id=case_id, limit=12)
        business = await _load_business(case.business_id, business_repo=business_repo)

        try:
            agent_result = await run_recovery_agent(
                case=case, history=list(history), business=business, actions=list(actions)
            )
        except SoftTimeLimitExceeded:
            await case_repo.mark_failed(
                case_id=case_id,
                error="soft time limit exceeded",
                next_visible_at=_utcnow()
                + datetime.timedelta(seconds=retry_backoff_seconds(case.processing_attempts)),
            )
            raise
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all around the agent
            attempts = case.processing_attempts
            if attempts >= settings.WEBHOOK_MAX_PROCESSING_ATTEMPTS:
                await case_repo.mark_dead(case_id=case_id, error=repr(exc))
                logger.error(f"recovery_case id={case_id} parked DEAD after {attempts} attempts: {exc!r}")
                return {"case_id": case_id, "status": "dead"}

            delay = retry_backoff_seconds(attempts)
            await case_repo.mark_failed(
                case_id=case_id,
                error=repr(exc),
                next_visible_at=_utcnow() + datetime.timedelta(seconds=delay),
            )
            # Best-effort fast retry; the reconciler is the backstop if this is lost.
            raise task.retry(exc=exc, countdown=delay) from exc

        if agent_result.get("status") == "resolved":
            reason = str(agent_result.get("reason") or "resolved by agent")
            await case_repo.mark_resolved(case_id=case_id, reason=reason)
            logger.info(f"recovery_case id={case_id} resolved: {reason}")
            return {"case_id": case_id, "status": "resolved", "reason": reason}

        await case_repo.mark_processed(case_id=case_id)
        logger.info(f"recovery_case id={case_id} processed ({len(history)} merged events)")

        followup_at = await _schedule_followup_if_requested(
            case_repo=case_repo,
            case_id=case_id,
            priority=case.priority,
            iso_time=agent_result.get("next_check_after"),
        )
        return {
            "case_id": case_id,
            "status": "processed",
            "merged_events": len(history),
            "followup_scheduled_for": followup_at,
            **agent_result,
        }


@celery_app.task(
    bind=True,
    base=DBTask,
    name=names.RECOVERY_CASE_PROCESS_TASK,
    acks_late=True,
)
def process_recovery_case(self: DBTask, *, case_id: int) -> dict[str, object]:
    return run_async(_process(self, case_id))
