"""
Shared HTTP client the outreach tools (call/SMS/WhatsApp/email/app
notification) use to reach the demo `simulation-api` service instead of a real
(paid) provider. See `/simulation-api/README.md`.

Not a tool itself - `_`-prefixed so it's never mistaken for one and never
picked up if this package is ever scanned for `@tool`-decorated callables.
"""

import logging
import typing

import httpx

from src.config.manager import settings
from src.utilities.retry import http_retry

logger = logging.getLogger(__name__)


async def call_simulation_api(path: str, payload: dict[str, typing.Any]) -> dict[str, typing.Any] | None:
    """POST `payload` to `{SIMULATION_API_BASE_URL}{path}`. Retries transient
    failures with backoff; returns `None` (never raises) if the simulation
    service stays unreachable - a demo dependency being down must not crash the
    agent run."""
    url = f"{settings.SIMULATION_API_BASE_URL.rstrip('/')}{path}"
    try:
        async for attempt in http_retry(what=f"simulation-api {path}"):
            with attempt:
                async with httpx.AsyncClient(timeout=settings.SIMULATION_API_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
    except httpx.HTTPError as exc:
        logger.warning(f"simulation-api call to {path} failed after retries: {exc!r}")
        return None
    return None
