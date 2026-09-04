"""
The consumer side: drain one merged recovery case from the priority queue and
(soon) hand it, with its full retry history, to the LangGraph agent.

Sequential processing is enforced at deploy time - this task's queue is drained
by a worker started with ``--concurrency=1 --prefetch-multiplier=1``. Because
dispatch happens at the *case* level (see `src.repository.crud.recovery_case`
and the route's `_dispatch_if_needed`), the agent is invoked once per problem
no matter how many times the customer retried, not once per webhook delivery.
"""

import datetime

import loguru
from celery.exceptions import SoftTimeLimitExceeded

from src.config.manager import settings
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.webhook_event import WebhookEventCRUDRepository
from src.workers import names
from src.workers.celery_app import celery_app
from src.workers.runtime import run_async, worker_session
from src.workers.tasks.base import DBTask, retry_backoff_seconds


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


async def _run_agent(case: RecoveryCase, history: list[WebhookEvent]) -> None:
    """
    TODO(agent): this is the only seam the LangGraph agent plugs into. It will
    receive the case (current status, priority, customer contact, retry count)
    plus its full delivery history - already merged and deduplicated, so it
    never has to reason about the same failed payment N separate times - and
    decide the recovery action.

    Until that exists we simply acknowledge the case so the whole
    route -> merge -> queue -> worker -> DB pipeline can be exercised end to end.
    """
    loguru.logger.info(
        f"[agent-stub] recovery_case id={case.id} key={case.case_key} "
        f"latest={case.latest_event_type}/{case.latest_entity_status} "
        f"retries={case.event_count} priority={case.priority} "
        f"history_len={len(history)} attempt={case.processing_attempts}"
    )


async def _process(task: DBTask, case_id: int) -> dict[str, object]:
    async with worker_session() as session:
        case_repo = RecoveryCaseCRUDRepository(async_session=session)
        event_repo = WebhookEventCRUDRepository(async_session=session)

        case = await case_repo.claim_for_processing(
            case_id=case_id, max_attempts=settings.WEBHOOK_MAX_PROCESSING_ATTEMPTS
        )
        if case is None:
            # Already processed / resolved / dead / gone, or over the attempt ceiling.
            loguru.logger.info(f"recovery_case id={case_id} not claimable - skipping")
            return {"case_id": case_id, "status": "skipped"}

        history = await event_repo.list_case_history(
            case_id=case_id, limit=settings.RECOVERY_CASE_HISTORY_LIMIT
        )

        try:
            await _run_agent(case, list(history))
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
                loguru.logger.error(
                    f"recovery_case id={case_id} parked DEAD after {attempts} attempts: {exc!r}"
                )
                return {"case_id": case_id, "status": "dead"}

            delay = retry_backoff_seconds(attempts)
            await case_repo.mark_failed(
                case_id=case_id,
                error=repr(exc),
                next_visible_at=_utcnow() + datetime.timedelta(seconds=delay),
            )
            # Best-effort fast retry; the reconciler is the backstop if this is lost.
            raise task.retry(exc=exc, countdown=delay) from exc

        await case_repo.mark_processed(case_id=case_id)
        return {"case_id": case_id, "status": "processed", "merged_events": len(history)}


@celery_app.task(
    bind=True,
    base=DBTask,
    name=names.RECOVERY_CASE_PROCESS_TASK,
    acks_late=True,
)
def process_recovery_case(self: DBTask, *, case_id: int) -> dict[str, object]:
    return run_async(_process(self, case_id))
