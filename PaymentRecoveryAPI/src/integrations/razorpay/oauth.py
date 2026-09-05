import logging
import urllib.parse

import httpx

from src.config.manager import settings
from src.integrations.razorpay.client import razorpay_request
from src.integrations.razorpay.constants import AUTHORIZE_PATH, TOKEN_PATH
from src.integrations.razorpay.exceptions import RazorpayOAuthError
from src.integrations.razorpay.schemas import RazorpayTokenResponse

logger = logging.getLogger(__name__)


class RazorpayOAuthClient:
    """
    Thin wrapper around the Razorpay Partner OAuth endpoints.

    Docs: https://razorpay.com/docs/partners/technology-partners/onboard-businesses/integrate-oauth/integration-steps
    """

    def __init__(self) -> None:
        self._auth_base_url = settings.RAZORPAY_AUTH_BASE_URL.rstrip("/")
        self._client_id = settings.RAZORPAY_CLIENT_ID
        self._client_secret = settings.RAZORPAY_CLIENT_SECRET
        self._redirect_uri = settings.RAZORPAY_OAUTH_REDIRECT_URI
        self._mode = settings.RAZORPAY_OAUTH_MODE
        self._timeout = settings.HTTP_CLIENT_TIMEOUT

    def build_authorization_url(self, *, state: str, scope: str | None = None) -> str:
        """Step 1: URL the business owner is redirected to in order to grant access."""
        if not self._client_id:
            raise RazorpayOAuthError("`RAZORPAY_CLIENT_ID` is not configured.")

        query = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "scope": scope or settings.RAZORPAY_OAUTH_SCOPE,
            "state": state,
        }
        return f"{self._auth_base_url}{AUTHORIZE_PATH}?{urllib.parse.urlencode(query)}"

    async def exchange_code_for_token(self, *, code: str) -> RazorpayTokenResponse:
        """Step 2: swap the authorization `code` for an access/refresh token pair."""
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
            "code": code,
            "mode": self._mode,
        }
        return await self._post_token(payload=payload)

    async def refresh_access_token(self, *, refresh_token: str) -> RazorpayTokenResponse:
        """Exchange a stored refresh token for a fresh access/refresh token pair."""
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return await self._post_token(payload=payload)

    async def _post_token(self, *, payload: dict[str, str]) -> RazorpayTokenResponse:
        url = f"{self._auth_base_url}{TOKEN_PATH}"
        response = await razorpay_request(
            method="POST",
            url=url,
            what="razorpay oauth token",
            error=RazorpayOAuthError,
            timeout=self._timeout,
            data=payload,
        )

        if response.status_code != httpx.codes.OK:
            logger.error(f"Razorpay token error [{response.status_code}]: {response.text}")
            raise RazorpayOAuthError(
                f"Razorpay token endpoint returned {response.status_code}: {response.text}"
            )

        try:
            return RazorpayTokenResponse.model_validate(response.json())
        except ValueError as exc:
            raise RazorpayOAuthError(f"Malformed Razorpay token response: {exc}") from exc


razorpay_oauth_client: RazorpayOAuthClient = RazorpayOAuthClient()
