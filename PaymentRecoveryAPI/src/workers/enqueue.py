"""
The one function producers call to put work on the queue.

Generic on purpose: any future task (not just recovery cases) enqueues through
here so priority clamping, queue defaulting and logging live in a single place.
"""

import logging
import typing

from src.config.manager import settings
from src.workers.celery_app import celery_app

_MIN_PRIORITY = 0
_MAX_PRIORITY = settings.WEBHOOK_PRIORITY_STEPS - 1


logger = logging.getLogger(__name__)


class EnqueueError(RuntimeError):
    """Raised when the broker could not accept a task."""


def enqueue(
    task_name: str,
    *,
    priority: int,
    queue: str | None = None,
    kwargs: dict[str, typing.Any] | None = None,
    countdown: int | None = None,
) -> str:
    """
    Send `task_name` to the broker and return its Celery task id.

    `priority` follows the queue convention: 0 = most urgent, higher = less.
    Values outside the band are clamped rather than rejected. `countdown`
    delays visibility to the worker by that many seconds (e.g. the recovery
    grace period) instead of dispatching immediately.
    """
    clamped = max(_MIN_PRIORITY, min(_MAX_PRIORITY, priority))
    target_queue = queue or settings.WEBHOOK_QUEUE_NAME

    try:
        result = celery_app.send_task(
            task_name,
            kwargs=kwargs or {},
            queue=target_queue,
            priority=clamped,
            countdown=countdown,
        )
    except Exception as exc:  # broker down / connection refused
        raise EnqueueError(f"could not enqueue `{task_name}`: {exc}") from exc

    logger.debug(
        f"enqueued {task_name} id={result.id} queue={target_queue} priority={clamped} "
        f"countdown={countdown} kwargs={kwargs}"
    )
    return result.id
