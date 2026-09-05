"""Celery delivery and reconciliation for durable outreach actions."""

import datetime
import logging

from src.agent.tools.outreach._scheduler import deliver_scheduled_action_payload
from src.config.manager import settings
from src.models.db.scheduled_action import ScheduledActionStatus
from src.repository.crud.scheduled_action import ScheduledActionCRUDRepository
from src.workers import names
from src.workers.celery_app import celery_app
from src.workers.enqueue import EnqueueError, enqueue
from src.workers.runtime import run_async, worker_session
from src.workers.tasks.base import DBTask, retry_backoff_seconds

logger = logging.getLogger(__name__)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


async def _deliver(action_id: int) -> dict[str, object]:
    now = _utcnow()
    async with worker_session() as session:
        repo = ScheduledActionCRUDRepository(async_session=session)
        action = await repo.claim_for_delivery(action_id=action_id, now=now)
        if action is None:
            return {"action_id": action_id, "status": "skipped"}

        result = await deliver_scheduled_action_payload(channel=action.channel, payload=action.payload)
        if result is None:
            retry = action.attempts < settings.SCHEDULED_ACTION_MAX_ATTEMPTS
            await repo.mark_failed(
                action_id=action.id,
                error="simulation provider unavailable",
                retry=retry,
            )
            if retry:
                raise RuntimeError(f"scheduled action {action.id} provider unavailable")
            return {"action_id": action.id, "status": ScheduledActionStatus.FAILED.value}

        await repo.mark_sent(action_id=action.id)
        return {"action_id": action.id, "status": ScheduledActionStatus.SENT.value}


@celery_app.task(bind=True, base=DBTask, name=names.SCHEDULED_ACTION_DELIVER_TASK, ignore_result=True)
def deliver_scheduled_action(self: DBTask, *, action_id: int) -> dict[str, object]:
    try:
        return run_async(_deliver(action_id))
    except RuntimeError as exc:
        attempt = self.request.retries + 1
        if attempt >= settings.SCHEDULED_ACTION_MAX_ATTEMPTS:
            logger.error(f"scheduled action id={action_id} exhausted delivery retries: {exc!r}")
            return {"action_id": action_id, "status": ScheduledActionStatus.FAILED.value}
        raise self.retry(exc=exc, countdown=retry_backoff_seconds(attempt)) from exc


async def _reconcile() -> dict[str, int]:
    now = _utcnow()
    dispatched = 0
    async with worker_session() as session:
        repo = ScheduledActionCRUDRepository(async_session=session)
        actions = await repo.list_due(now=now, limit=settings.SCHEDULED_ACTION_SWEEP_BATCH_SIZE)
        for action in actions:
            try:
                task_id = enqueue(
                    names.SCHEDULED_ACTION_DELIVER_TASK,
                    priority=1,
                    kwargs={"action_id": action.id},
                )
                if await repo.mark_queued(action_id=action.id, celery_task_id=task_id):
                    dispatched += 1
            except EnqueueError as exc:
                logger.warning(f"scheduled outreach reconcile stopped: {exc}")
                break
    return {"dispatched": dispatched}


@celery_app.task(base=DBTask, name=names.SCHEDULED_ACTION_RECONCILE_TASK, ignore_result=True)
def reconcile_scheduled_actions() -> dict[str, int]:
    return run_async(_reconcile())
