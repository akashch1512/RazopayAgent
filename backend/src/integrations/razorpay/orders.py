"""
Fetch-All-Orders client - the only way to detect a payment drop-off, since
Razorpay has no `order.created` (or any drop-off) webhook event.

https://razorpay.com/docs/api/orders/fetch-all
"""

import httpx
import loguru

from src.config.manager import settings
from src.integrations.razorpay.exceptions import RazorpayIntegrationError

_ORDERS_PATH = "/v1/orders"
_PAGE_SIZE = 100


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

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while len(orders) < max_orders:
                params = {"from": from_ts, "to": to_ts, "count": _PAGE_SIZE, "skip": skip}
                try:
                    response = await client.get(url, params=params, headers=headers)
                except httpx.HTTPError as exc:
                    raise RazorpayIntegrationError(f"Razorpay orders fetch failed: {exc}") from exc

                if response.status_code != httpx.codes.OK:
                    loguru.logger.error(f"Razorpay orders fetch error [{response.status_code}]: {response.text}")
                    raise RazorpayIntegrationError(
                        f"Razorpay orders endpoint returned {response.status_code}: {response.text}"
                    )

                page = response.json().get("items", [])
                orders.extend(page)
                if len(page) < _PAGE_SIZE:
                    break
                skip += _PAGE_SIZE

        return orders[:max_orders]


razorpay_orders_client: RazorpayOrdersClient = RazorpayOrdersClient()
