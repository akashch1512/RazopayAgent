import secrets

import httpx
import loguru

from src.config.manager import settings
from src.integrations.razorpay.constants import WEBHOOK_EVENTS, WEBHOOKS_PATH_TEMPLATE
from src.integrations.razorpay.exceptions import RazorpayWebhookError


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

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise RazorpayWebhookError(f"Razorpay webhook request failed: {exc}") from exc

        if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
            loguru.logger.error(f"Razorpay webhook error [{response.status_code}]: {response.text}")
            raise RazorpayWebhookError(
                f"Razorpay webhook endpoint returned {response.status_code}: {response.text}"
            )

        return response.json()


razorpay_webhook_client: RazorpayWebhookClient = RazorpayWebhookClient()
