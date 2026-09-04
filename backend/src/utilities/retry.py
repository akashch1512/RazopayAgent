"""
Small, reusable retry helpers built on `tenacity`.

`transient_db_retry` is meant for short, bounded retries on the request hot path:
a dropped connection or a serialization failure should not turn into a 5xx if a
second attempt a few milliseconds later would succeed. It deliberately does *not*
retry for long - a genuinely overloaded database should surface fast so the
caller can shed load (e.g. return 503 and let the sender redeliver).
"""

import tenacity
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from src.config.manager import settings

# Postgres SQLSTATEs worth a quick retry: serialization failure & deadlock.
_RETRYABLE_PGCODES: frozenset[str] = frozenset({"40001", "40P01"})


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, OperationalError | InterfaceError):
        return True
    if isinstance(exc, DBAPIError):
        if getattr(exc, "connection_invalidated", False):
            return True
        pgcode = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
            getattr(exc, "orig", None), "pgcode", None
        )
        return pgcode in _RETRYABLE_PGCODES
    return False


def transient_db_retry(
    *,
    max_attempts: int | None = None,
) -> tenacity.AsyncRetrying:
    """An `AsyncRetrying` controller for `async with` around a DB write."""
    return tenacity.AsyncRetrying(
        retry=tenacity.retry_if_exception(_is_transient),
        stop=tenacity.stop_after_attempt(max_attempts or settings.WEBHOOK_DB_WRITE_MAX_RETRIES),
        wait=tenacity.wait_random_exponential(multiplier=0.05, max=0.5),
        reraise=True,
    )
