"""
Fetch-All-Orders client - the only way to detect a payment drop-off, since
Razorpay has no `order.created` (or any drop-off) webhook event.

https://razorpay.com/docs/api/orders/fetch-all
"""

import logging

import httpx

from src.config.manager import settings
from src.integrations.razorpay.client import razorpay_request
from src.integrations.razorpay.exceptions import RazorpayIntegrationError

_ORDERS_PATH = "/v1/orders"
_PAGE_SIZE = 100


logger = logging.getLogger(__name__)


class RazorpayOrdersClient:
    def __init__(self) -> None:
        self._api_base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        self._timeout = settings.HTTP_CLIENT_TIMEOUT

    async def fetch_orders(
        self,
        *,
        account_id: str,
        auth_header: dict[str, str],
        from_ts: int,
        to_ts: int,
        max_orders: int,
    ) -> list[dict]:
        """
        All orders created in `[from_ts, to_ts]` (Unix seconds), newest-first as
        Razorpay returns them, paginated via `count`/`skip` up to `max_orders`.
        The API has no status filter - callers decide what counts as a drop-off.
        """
        url = f"{self._api_base_url}{_ORDERS_PATH}"
        headers = {**auth_header, "X-Razorpay-Account": account_id}

        orders: list[dict] = []
        skip = 0

        while len(orders) < max_orders:
            params = {"from": from_ts, "to": to_ts, "count": _PAGE_SIZE, "skip": skip}
            response = await razorpay_request(
                method="GET",
                url=url,
                what="razorpay orders fetch",
                error=RazorpayIntegrationError,
                timeout=self._timeout,
                params=params,
                headers=headers,
            )

            if response.status_code != httpx.codes.OK:
                logger.error(f"Razorpay orders fetch error [{response.status_code}]: {response.text}")
                raise RazorpayIntegrationError(
                    f"Razorpay orders endpoint returned {response.status_code}: {response.text}"
                )

            page = response.json().get("items", [])
            orders.extend(page)
            if len(page) < _PAGE_SIZE:
                break
            skip += _PAGE_SIZE

        return orders[:max_orders]

    async def fetch_order(self, *, account_id: str, auth_header: dict[str, str], order_id: str) -> dict:
        """One order by id - used to check its *current* `status` (e.g. "paid")
        rather than trusting the case's last-webhook snapshot."""
        url = f"{self._api_base_url}{_ORDERS_PATH}/{order_id}"
        response = await razorpay_request(
            method="GET",
            url=url,
            what="razorpay order fetch",
            error=RazorpayIntegrationError,
            timeout=self._timeout,
            headers={**auth_header, "X-Razorpay-Account": account_id},
        )
        if response.status_code != httpx.codes.OK:
            logger.error(f"Razorpay order fetch error [{response.status_code}]: {response.text}")
            raise RazorpayIntegrationError(
                f"Razorpay order endpoint returned {response.status_code}: {response.text}"
            )
        return response.json()


razorpay_orders_client: RazorpayOrdersClient = RazorpayOrdersClient()
