"""
Shared HTTP client the outreach tools (call/SMS/WhatsApp/email/app
notification) use to reach the demo `simulation-api` service instead of a real
(paid) provider. See `/simulation-api/README.md`.

Not a tool itself - `_`-prefixed so it's never mistaken for one and never
picked up if this package is ever scanned for `@tool`-decorated callables.
"""

import typing

import httpx
import loguru

from src.config.manager import settings


async def call_simulation_api(path: str, payload: dict[str, typing.Any]) -> dict[str, typing.Any] | None:
    """POST `payload` to `{SIMULATION_API_BASE_URL}{path}`. Returns `None` (never
    raises) if the simulation service is unreachable - a demo dependency being
    down must not crash the agent run."""
    url = f"{settings.SIMULATION_API_BASE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.SIMULATION_API_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        loguru.logger.warning(f"simulation-api call to {path} failed: {exc!r}")
        return None
