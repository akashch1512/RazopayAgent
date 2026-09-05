"""
One retrying HTTP round-trip shared by every Razorpay REST client.

Each client method should only build its request and parse the response; the
transient-failure policy (connect/read timeout, transport error, HTTP 429/5xx)
lives here so it is identical everywhere: bounded exponential backoff with
jitter, a warning logged per retry, and the client's own domain exception
raised once the budget is spent. Non-retryable error statuses (400/401/404 ...)
are handed back to the caller unchanged so it can inspect the body.
"""

import logging

import httpx

from src.config.manager import settings
from src.utilities.retry import RETRYABLE_HTTP_STATUS, http_retry

logger = logging.getLogger(__name__)


async def razorpay_request(
    *,
    method: str,
    url: str,
    what: str,
    error: type[Exception],
    timeout: float | None = None,
    **request_kwargs: object,
) -> httpx.Response:
    """
    Send one request, retrying only transient failures. Returns the
    `httpx.Response` for the caller to validate; raises `error` if the request
    could not be completed at all (network failure, or retries exhausted on a
    5xx/429).
    """
    effective_timeout = timeout if timeout is not None else settings.HTTP_CLIENT_TIMEOUT
    try:
        async for attempt in http_retry(what=what):
            with attempt:
                async with httpx.AsyncClient(timeout=effective_timeout) as client:
                    response = await client.request(method, url, **request_kwargs)  # type: ignore[arg-type]
                # Turn a retryable status into an exception so tenacity sees it;
                # anything else goes back to the caller as-is.
                if response.status_code in RETRYABLE_HTTP_STATUS:
                    response.raise_for_status()
                return response
    except httpx.HTTPStatusError as exc:
        logger.error(f"{what}: {exc.response.status_code} after retries: {exc.response.text}")
        raise error(f"{what} returned {exc.response.status_code}: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error(f"{what}: request failed: {exc!r}")
        raise error(f"{what} failed: {exc}") from exc
    raise error(f"{what}: retry loop exited without a response")  # pragma: no cover - reraise=True
