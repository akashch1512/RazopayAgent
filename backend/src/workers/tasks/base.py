"""
Shared behaviour for every Celery task in the codebase.

Keeps the reliability knobs and the retry-backoff maths in one place so a new
task type only has to implement its own logic.
"""

import random

import loguru
from celery import Task

from src.config.manager import settings


def retry_backoff_seconds(attempt: int) -> float:
    """
    Exponential backoff with full jitter, capped.

    `attempt` is 1-based (the attempt that just failed). 50-100% jitter spreads
    a thundering herd of retries after a downstream outage.
    """
    raw = settings.WEBHOOK_RETRY_BASE_DELAY_SECONDS * (2 ** max(0, attempt - 1))
    capped = min(raw, settings.WEBHOOK_RETRY_MAX_DELAY_SECONDS)
    return round(capped * (0.5 + random.random() / 2), 2)


class DBTask(Task):
    """Base task: late ack, requeue on worker loss, bounded retries, loud failures."""

    acks_late = True
    reject_on_worker_lost = True
    max_retries = settings.WEBHOOK_MAX_PROCESSING_ATTEMPTS
    # We manage our own backoff via `self.retry(countdown=...)`.
    default_retry_delay = settings.WEBHOOK_RETRY_BASE_DELAY_SECONDS

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: ANN001
        loguru.logger.error(
            f"task {self.name} id={task_id} exhausted retries: {exc!r} kwargs={kwargs}"
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):  # noqa: ANN001
        loguru.logger.warning(f"task {self.name} id={task_id} retrying: {exc!r}")
