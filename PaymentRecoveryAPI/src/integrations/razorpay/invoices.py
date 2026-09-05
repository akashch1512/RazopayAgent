"""
Fetch-All-Invoices client - powers the dashboard's invoices view and "start a
B2B chase" action.

https://razorpay.com/docs/api/payments/invoices/fetch-all
"""

import logging

import httpx

from src.config.manager import settings
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.helpers.http import razorpay_request

_INVOICES_PATH = "/v1/invoices"
_PAGE_SIZE = 100


logger = logging.getLogger(__name__)


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

        response = await razorpay_request(
            method="GET",
            url=url,
            what="razorpay invoices fetch",
            error=RazorpayIntegrationError,
            timeout=self._timeout,
            params=params,
            headers=headers,
        )

        if response.status_code != httpx.codes.OK:
            logger.error(f"Razorpay invoices fetch error [{response.status_code}]: {response.text}")
            raise RazorpayIntegrationError(
                f"Razorpay invoices endpoint returned {response.status_code}: {response.text}"
            )

        return response.json().get("items", [])

    async def fetch_invoice(self, *, account_id: str, auth_header: dict[str, str], invoice_id: str) -> dict:
        url = f"{self._api_base_url}{_INVOICES_PATH}/{invoice_id}"
        headers = {**auth_header, "X-Razorpay-Account": account_id}

        response = await razorpay_request(
            method="GET",
            url=url,
            what="razorpay invoice fetch",
            error=RazorpayIntegrationError,
            timeout=self._timeout,
            headers=headers,
        )

        if response.status_code != httpx.codes.OK:
            logger.error(f"Razorpay invoice fetch error [{response.status_code}]: {response.text}")
            raise RazorpayIntegrationError(
                f"Razorpay invoice endpoint returned {response.status_code}: {response.text}"
            )

        return response.json()


razorpay_invoices_client: RazorpayInvoicesClient = RazorpayInvoicesClient()
