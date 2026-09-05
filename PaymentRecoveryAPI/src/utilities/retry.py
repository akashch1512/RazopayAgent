"""
Small, reusable retry helpers built on `tenacity`.

`transient_db_retry` is meant for short, bounded retries on the request hot path:
a dropped connection or a serialization failure should not turn into a 5xx if a
second attempt a few milliseconds later would succeed. It deliberately does *not*
retry for long - a genuinely overloaded database should surface fast so the
caller can shed load (e.g. return 503 and let the sender redeliver).
"""

import logging

import httpx
import tenacity
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from src.config.manager import settings

logger = logging.getLogger(__name__)

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


# HTTP status codes worth another attempt: rate-limit + transient server errors.
RETRYABLE_HTTP_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def _is_transient_http(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUS
    return False


def http_retry(*, what: str, max_attempts: int | None = None) -> tenacity.AsyncRetrying:
    """
    `AsyncRetrying` controller for an outbound HTTP call (`async for attempt in
    http_retry(...)`). Retries only transient failures - connect/read timeouts,
    transport errors, HTTP 429/5xx - with exponential backoff + jitter, logs
    every retry, and re-raises the last exception once the budget is spent so
    the caller still sees a hard failure.

    `what` is a short label for the log line ("razorpay orders fetch").
    """
    def _log_retry(state: tenacity.RetryCallState) -> None:
        exc = state.outcome.exception() if state.outcome else None
        sleep_for = state.next_action.sleep if state.next_action else 0.0
        logger.warning(
            f"{what}: transient failure on attempt {state.attempt_number} "
            f"({exc!r}); retrying in {sleep_for:.1f}s"
        )

    return tenacity.AsyncRetrying(
        retry=tenacity.retry_if_exception(_is_transient_http),
        stop=tenacity.stop_after_attempt(max_attempts or settings.HTTP_MAX_RETRY_ATTEMPTS),
        wait=tenacity.wait_random_exponential(
            multiplier=settings.HTTP_RETRY_BASE_DELAY_SECONDS,
            max=settings.HTTP_RETRY_MAX_DELAY_SECONDS,
        ),
        before_sleep=_log_retry,
        reraise=True,
    )
