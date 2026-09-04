"""
The starvation guard and the lost-message backstop - operates on `RecoveryCase`
rows, the unit the agent worker actually claims.

Celery + Redis priority alone can starve a low-priority case forever behind a
busy queue, and an at-least-once broker can still drop a message if a worker
dies at the wrong moment. This periodic task (Celery beat) makes the
`recovery_case` table the real source of truth:

* it re-dispatches anything RECEIVED (hot-path enqueue failed), FAILED (backoff
  elapsed), or stuck in QUEUED/PROCESSING past the staleness threshold;
* it *ages* priority - every `WEBHOOK_PRIORITY_AGING_STEP_SECONDS` a case has
  waited, the number it hands the broker drops by one, so it eventually reaches
  0 (most urgent) no matter how low it started;
* it parks cases that have burned all their attempts as DEAD (the dead-letter
  state - queryable, alertable, never silently retried).
"""

import datetime

import loguru

from src.config.manager import settings
from src.models.db.recovery_case import RecoveryCase
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.workers import names
from src.workers.celery_app import celery_app
from src.workers.enqueue import EnqueueError, enqueue
from src.workers.runtime import run_async, worker_session
from src.workers.tasks.base import DBTask


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def _aged_priority(case: RecoveryCase, now: datetime.datetime) -> int:
    waited = (now - case.first_event_at).total_seconds()
    steps = int(waited // settings.WEBHOOK_PRIORITY_AGING_STEP_SECONDS)
    return max(0, case.priority - steps)


async def _reconcile() -> dict[str, int]:
    now = _utcnow()
    stuck_before = now - datetime.timedelta(seconds=settings.WEBHOOK_STUCK_AFTER_SECONDS)
    redispatched = 0
    parked_dead = 0

    async with worker_session() as session:
        repo = RecoveryCaseCRUDRepository(async_session=session)
        cases = await repo.list_reconcilable(
            now=now, stuck_before=stuck_before, limit=settings.WEBHOOK_RECONCILE_BATCH_SIZE
        )

        for case in cases:
            if case.processing_attempts >= settings.WEBHOOK_MAX_PROCESSING_ATTEMPTS:
                await repo.mark_dead(case_id=case.id, error="max attempts reached (reconciler)")
                parked_dead += 1
                continue

            priority = _aged_priority(case, now)
            try:
                task_id = enqueue(
                    names.RECOVERY_CASE_PROCESS_TASK,
                    priority=priority,
                    kwargs={"case_id": case.id},
                )
            except EnqueueError as exc:
                loguru.logger.warning(f"reconcile: broker unavailable, stopping sweep: {exc}")
                break

            await repo.mark_queued(
                case_id=case.id,
                celery_task_id=task_id,
                priority=priority,
                priority_reason=f"reconciled (base={case.priority})",
            )
            redispatched += 1

    if redispatched or parked_dead:
        loguru.logger.info(f"reconcile: redispatched={redispatched} parked_dead={parked_dead}")
    return {"redispatched": redispatched, "parked_dead": parked_dead}


@celery_app.task(base=DBTask, name=names.RECOVERY_CASE_RECONCILE_TASK, ignore_result=True)
def reconcile_recovery_cases() -> dict[str, int]:
    return run_async(_reconcile())
