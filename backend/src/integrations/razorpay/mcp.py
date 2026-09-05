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

import typing

import loguru
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config.manager import settings
from src.integrations.razorpay.auth import build_auth_header
from src.models.db.business import Business


async def get_razorpay_mcp_tools(business: Business) -> list[BaseTool]:
    """
    Build this business' Razorpay MCP tool set for one agent run.

    DEMO FALLBACK: if the business has not completed OAuth onboarding yet (no
    stored access token), this falls back to `RAZORPAY_KEY_ID` /
    `RAZORPAY_KEY_SECRET` - Razorpay's legacy API-key pair, base64-encoded into
    a merchant token - **for demo/development purposes only**. A production
    business must always authenticate with its own onboarded OAuth token.
    """
    headers, is_demo = build_auth_header(business)
    if headers is None:
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

    connections: dict[str, typing.Any] = {
        "razorpay": {
            "transport": settings.RAZORPAY_MCP_TRANSPORT,
            "url": settings.RAZORPAY_MCP_SERVER_URL,
            "headers": headers,
        }
    }

    try:
        client = MultiServerMCPClient(connections)
        return await client.get_tools()
    except Exception as exc:  # noqa: BLE001 - MCP being unreachable must not crash the agent
        loguru.logger.error(f"business id={business.id}: failed to load Razorpay MCP tools: {exc!r}")
        return []
