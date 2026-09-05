import hashlib
import hmac
import logging
import secrets

import httpx

from src.config.manager import settings
from src.integrations.razorpay.constants import WEBHOOK_EVENTS, WEBHOOKS_PATH_TEMPLATE
from src.integrations.razorpay.exceptions import RazorpayWebhookError
from src.integrations.razorpay.helpers.http import razorpay_request

logger = logging.getLogger(__name__)


class RazorpayWebhookClient:
    """
    Creates webhooks on a sub-merchant account using the partner access token.

    Docs: https://razorpay.com/docs/api/partners/webhooks/create
    """

    def __init__(self) -> None:
        self._api_base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        self._timeout = settings.HTTP_CLIENT_TIMEOUT

    @staticmethod
    def generate_secret() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_signature(*, raw_body: bytes, signature: str | None, secret: str) -> bool:
        """
        Validate the `X-Razorpay-Signature` header: it is the hex HMAC-SHA256 of
        the raw request body keyed with the webhook secret.
        Docs: https://razorpay.com/docs/webhooks/validate-test/
        """
        if not signature or not secret:
            return False
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def create_webhook(
        self,
        *,
        account_id: str,
        access_token: str,
        secret: str,
        events: list[str] | None = None,
    ) -> dict:
        """
        Register a webhook for `events` on the given sub-merchant `account_id`.
        Returns the raw Razorpay webhook object (contains `id`, `active`, ...).
        """
        url = f"{self._api_base_url}{WEBHOOKS_PATH_TEMPLATE.format(account_id=account_id)}"
        body: dict = {
            "url": settings.RAZORPAY_WEBHOOK_URL,
            "events": events or WEBHOOK_EVENTS,
            "secret": secret,
        }
        if settings.RAZORPAY_WEBHOOK_ALERT_EMAIL:
            body["alert_email"] = settings.RAZORPAY_WEBHOOK_ALERT_EMAIL

        response = await razorpay_request(
            method="POST",
            url=url,
            what="razorpay webhook create",
            error=RazorpayWebhookError,
            timeout=self._timeout,
            json=body,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
            logger.error(f"Razorpay webhook error [{response.status_code}]: {response.text}")
            raise RazorpayWebhookError(
                f"Razorpay webhook endpoint returned {response.status_code}: {response.text}"
            )

        return response.json()

    async def get_webhook(self, *, account_id: str, webhook_id: str, access_token: str) -> dict:
        """
        Fetch the live config (url, active, events, ...) of a webhook already
        registered on a sub-merchant account - a read-only view, no local cache.
        """
        url = f"{self._api_base_url}{WEBHOOKS_PATH_TEMPLATE.format(account_id=account_id)}/{webhook_id}"

        response = await razorpay_request(
            method="GET",
            url=url,
            what="razorpay webhook fetch",
            error=RazorpayWebhookError,
            timeout=self._timeout,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != httpx.codes.OK:
            logger.error(f"Razorpay webhook fetch error [{response.status_code}]: {response.text}")
            raise RazorpayWebhookError(
                f"Razorpay webhook endpoint returned {response.status_code}: {response.text}"
            )

        return response.json()


razorpay_webhook_client: RazorpayWebhookClient = RazorpayWebhookClient()
