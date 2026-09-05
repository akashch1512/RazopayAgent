"""
Fetch-All-Invoices client - powers the dashboard's invoices view and "start a
B2B chase" action.

https://razorpay.com/docs/api/payments/invoices/fetch-all
"""

import httpx
import loguru

from src.config.manager import settings
from src.integrations.razorpay.exceptions import RazorpayIntegrationError

_INVOICES_PATH = "/v1/invoices"
_PAGE_SIZE = 100


class RazorpayInvoicesClient:
    def __init__(self) -> None:
        self._api_base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        self._timeout = settings.HTTP_CLIENT_TIMEOUT

    async def fetch_invoices(
        self,
        *,
        account_id: str,
        auth_header: dict[str, str],
        count: int,
        skip: int,
    ) -> list[dict]:
        """One page of this business' invoices, newest-first, as Razorpay
        returns them - no server-side status filter, callers filter client-side."""
        url = f"{self._api_base_url}{_INVOICES_PATH}"
        headers = {**auth_header, "X-Razorpay-Account": account_id}
        params: dict[str, str | int] = {"type": "invoice", "count": min(count, _PAGE_SIZE), "skip": skip}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise RazorpayIntegrationError(f"Razorpay invoices fetch failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            loguru.logger.error(f"Razorpay invoices fetch error [{response.status_code}]: {response.text}")
            raise RazorpayIntegrationError(
                f"Razorpay invoices endpoint returned {response.status_code}: {response.text}"
            )

        return response.json().get("items", [])

    async def fetch_invoice(self, *, account_id: str, auth_header: dict[str, str], invoice_id: str) -> dict:
        url = f"{self._api_base_url}{_INVOICES_PATH}/{invoice_id}"
        headers = {**auth_header, "X-Razorpay-Account": account_id}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise RazorpayIntegrationError(f"Razorpay invoice fetch failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            loguru.logger.error(f"Razorpay invoice fetch error [{response.status_code}]: {response.text}")
            raise RazorpayIntegrationError(
                f"Razorpay invoice endpoint returned {response.status_code}: {response.text}"
            )

        return response.json()


razorpay_invoices_client: RazorpayInvoicesClient = RazorpayInvoicesClient()
