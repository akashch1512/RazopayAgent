"""
Shared Razorpay auth resolution for anything that calls Razorpay's APIs *on
behalf of an onboarded business* (the MCP session, the drop-off Orders-API
poller, ...): prefer the business' own OAuth access token; fall back to the
legacy Key ID/Secret pair - **for demo/development purposes only** - so a
feature can be exercised before a business finishes onboarding.
"""

import base64
import logging

from src.config.manager import settings
from src.models.db.business import Business
from src.securities.encryption.encryptor import get_data_encryptor

logger = logging.getLogger(__name__)


def _demo_merchant_token() -> str | None:
    """`base64(key_id:key_secret)` - Razorpay's legacy API-key auth, encoded the
    same way its docs ask for a "merchant token"."""
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return None
    raw = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}"
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def resolve_business_token(business: Business) -> tuple[str | None, bool]:
    """Return `(token, is_demo_fallback)`."""
    if business.encrypted_access_token:
        try:
            return get_data_encryptor().decrypt(business.encrypted_access_token), False
        except ValueError:
            logger.error(f"business id={business.id}: could not decrypt stored Razorpay access token.")

    demo_token = _demo_merchant_token()
    if demo_token:
        return demo_token, True

    return None, False


def build_auth_header(business: Business) -> tuple[dict[str, str] | None, bool]:
    """
    Return `(headers, is_demo)`; `headers` is `None` if no auth is available at
    all. OAuth access tokens are Bearer per spec; the legacy base64
    `key_id:key_secret` token is RFC 7617 HTTP Basic auth, not Bearer -
    Razorpay's own endpoints 401 if it's sent as Bearer (verified directly
    against the MCP server; assumed to hold for the REST API too).
    """
    token, is_demo = resolve_business_token(business)
    if token is None:
        return None, False

    scheme = "Basic" if is_demo else "Bearer"
    return {"Authorization": f"{scheme} {token}"}, is_demo
