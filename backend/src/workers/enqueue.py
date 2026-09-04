"""
The one function producers call to put work on the queue.

Generic on purpose: any future task (not just recovery cases) enqueues through
here so priority clamping, queue defaulting and logging live in a single place.
"""

import typing

import loguru

from src.config.manager import settings
from src.workers.celery_app import celery_app

_MIN_PRIORITY = 0
_MAX_PRIORITY = settings.WEBHOOK_PRIORITY_STEPS - 1


class EnqueueError(RuntimeError):
    """Raised when the broker could not accept a task."""


def enqueue(
    task_name: str,
    *,
    priority: int,
    queue: str | None = None,
    kwargs: dict[str, typing.Any] | None = None,
) -> str:
    """
    Send `task_name` to the broker and return its Celery task id.

    `priority` follows the queue convention: 0 = most urgent, higher = less.
    Values outside the band are clamped rather than rejected.
    """
    clamped = max(_MIN_PRIORITY, min(_MAX_PRIORITY, priority))
    target_queue = queue or settings.WEBHOOK_QUEUE_NAME

    try:
        result = celery_app.send_task(
            task_name,
            kwargs=kwargs or {},
            queue=target_queue,
            priority=clamped,
        )
    except Exception as exc:  # broker down / connection refused
        raise EnqueueError(f"could not enqueue `{task_name}`: {exc}") from exc

    loguru.logger.debug(
        f"enqueued {task_name} id={result.id} queue={target_queue} priority={clamped} kwargs={kwargs}"
    )
    return result.id
