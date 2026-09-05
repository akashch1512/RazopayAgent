"""
The one call this service makes *out* to the real backend: forwarding a demo
customer's reply so the actual LangGraph agent gets to react to it, instead of
the reply only ever updating this service's own in-memory demo store.

    demo customer reply -> POST here -> POST /recovery-cases/{id}/feedback (backend)
                                          -> merged into the case, case re-queued
                                          -> agent sees the reply next run

Never allowed to break the demo UI: if the backend is unreachable, the reply
still updates the local store (so the dashboard reflects it), we just log a
warning instead of raising.
"""

import httpx
import loguru

from src.config import settings


async def forward_customer_feedback(*, case_id: str, channel: str, message: str) -> bool:
    """Returns whether the backend accepted it - purely informational, the
    caller should not fail the request over this."""
    url = f"{settings.BACKEND_API_BASE_URL.rstrip('/')}/recovery-cases/{case_id}/feedback"
    try:
        async with httpx.AsyncClient(timeout=settings.BACKEND_API_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json={"channel": channel, "message": message})
            response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        loguru.logger.warning(
            f"could not forward customer feedback for case {case_id} to the backend ({url}): {exc!r}"
        )
        return False
