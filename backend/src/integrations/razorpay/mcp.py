"""
Connects the agent to Razorpay's own MCP server so it can act with real
Razorpay tools (fetch payment/order details, create refunds, resend payment
links, ...) instead of us hand-writing a client for each one.

https://razorpay.com/docs/mcp-server/ (remote server; OAuth Bearer auth, or a
legacy Key ID / Key Secret pair encoded as `base64("key_id:key_secret")` and
sent the same way - "Encode your merchant token by running: echo
<key_id>:<key_secret> | base64").

Every business authenticates its own MCP session with the OAuth access token
captured during onboarding (`Business.encrypted_access_token`) - so the agent
only ever sees the data and permissions that business actually granted.
"""

import base64
import typing

import loguru
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config.manager import settings
from src.models.db.business import Business
from src.securities.encryption.encryptor import get_data_encryptor


def _demo_merchant_token() -> str | None:
    """`base64(key_id:key_secret)` - Razorpay's legacy API-key auth, encoded the
    same way the MCP docs ask for a "merchant token"."""
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return None
    raw = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}"
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def _resolve_mcp_token(business: Business) -> tuple[str | None, bool]:
    """Return `(bearer_token, is_demo_fallback)`."""
    if business.encrypted_access_token:
        try:
            return get_data_encryptor().decrypt(business.encrypted_access_token), False
        except ValueError:
            loguru.logger.error(f"business id={business.id}: could not decrypt stored Razorpay access token.")

    demo_token = _demo_merchant_token()
    if demo_token:
        return demo_token, True

    return None, False


async def get_razorpay_mcp_tools(business: Business) -> list[BaseTool]:
    """
    Build this business' Razorpay MCP tool set for one agent run.

    DEMO FALLBACK: if the business has not completed OAuth onboarding yet (no
    stored access token), this falls back to `RAZORPAY_KEY_ID` /
    `RAZORPAY_KEY_SECRET` - Razorpay's legacy API-key pair, base64-encoded into
    a merchant token - **for demo/development purposes only**. A production
    business must always authenticate with its own onboarded OAuth token.
    """
    token, is_demo = _resolve_mcp_token(business)
    if token is None:
        loguru.logger.warning(
            f"business id={business.id}: no Razorpay access token and no demo "
            "RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET configured - proceeding without "
            "Razorpay MCP tools."
        )
        return []

    if is_demo:
        loguru.logger.warning(
            f"business id={business.id}: using the DEMO Razorpay Key ID/Secret "
            "fallback for MCP auth - this is for demo purposes only, never use it "
            "in production."
        )

    # OAuth access tokens are Bearer per spec; the legacy base64(key_id:secret)
    # merchant token is RFC 7617 HTTP Basic auth, not Bearer - Razorpay's MCP
    # server 401s if it's sent as Bearer (verified against the live endpoint).
    scheme = "Basic" if is_demo else "Bearer"
    connections: dict[str, typing.Any] = {
        "razorpay": {
            "transport": settings.RAZORPAY_MCP_TRANSPORT,
            "url": settings.RAZORPAY_MCP_SERVER_URL,
            "headers": {"Authorization": f"{scheme} {token}"},
        }
    }

    try:
        client = MultiServerMCPClient(connections)
        return await client.get_tools()
    except Exception as exc:  # noqa: BLE001 - MCP being unreachable must not crash the agent
        loguru.logger.error(f"business id={business.id}: failed to load Razorpay MCP tools: {exc!r}")
        return []
