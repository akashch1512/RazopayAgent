"""
"Is this case's payment actually done already?" - a live check against
Razorpay's REST API, used to avoid the two worst failure modes of an automated
dunning agent:

* running the whole agent on a case the customer already paid (the stored
  `entity_status` is a stale last-webhook snapshot; a captured payment or a
  completed drop-off may not have produced a resolving webhook yet), and
* sending "you still owe us" outreach *after* the customer paid.

Only order- and invoice-shaped cases have a cheap, unambiguous "paid" signal,
so this returns:

    True   - confirmed settled (order/invoice status == "paid")
    False  - confirmed not settled
    None   - could not determine (subscription/payout/etc., no auth, API error)

A short per-case in-process cache keeps a burst of outreach calls in one agent
run from making one Razorpay request each.
"""

import logging
import time

from src.config.manager import settings
from src.integrations.razorpay.exceptions import RazorpayIntegrationError
from src.integrations.razorpay.helpers.auth import build_auth_header
from src.integrations.razorpay.invoices import razorpay_invoices_client
from src.integrations.razorpay.orders import razorpay_orders_client
from src.models.db.business import Business
from src.models.db.recovery_case import RecoveryCase

logger = logging.getLogger(__name__)

_PAID_STATUSES: frozenset[str] = frozenset({"paid"})

# case_id -> (monotonic_ts, result). Process-local and tiny; entries are only
# read within their TTL so it never needs pruning at any real scale.
_cache: dict[int, tuple[float, bool | None]] = {}


def _entity_ref(case: RecoveryCase) -> tuple[str, str] | None:
    """`("order"|"invoice", id)` for the cases we can verify, else `None`."""
    entity_id = case.primary_entity_id or ""
    entity_type = (case.entity_type or "").lower()
    if entity_id.startswith("order_") or entity_type in ("order", "payment"):
        return ("order", entity_id) if entity_id else None
    if entity_id.startswith("inv_") or entity_type == "invoice":
        return ("invoice", entity_id) if entity_id else None
    return None


async def _check(case: RecoveryCase, business: Business) -> bool | None:
    ref = _entity_ref(case)
    if ref is None:
        return None

    headers, _is_demo = build_auth_header(business)
    if headers is None:
        logger.warning(f"case id={case.id}: no Razorpay auth available, cannot verify settlement")
        return None

    kind, entity_id = ref
    account_id = case.razorpay_account_id
    try:
        if kind == "order":
            entity = await razorpay_orders_client.fetch_order(
                account_id=account_id, auth_header=headers, order_id=entity_id
            )
        else:
            entity = await razorpay_invoices_client.fetch_invoice(
                account_id=account_id, auth_header=headers, invoice_id=entity_id
            )
    except RazorpayIntegrationError as exc:
        logger.warning(f"case id={case.id}: settlement check failed ({exc!r}); treating as unknown")
        return None

    return str(entity.get("status") or "").lower() in _PAID_STATUSES


async def is_case_settled(
    *, case: RecoveryCase, business: Business, use_cache: bool = True
) -> bool | None:
    """See module docstring. `use_cache=False` forces a fresh Razorpay call."""
    now = time.monotonic()
    if use_cache:
        cached = _cache.get(case.id)
        if cached is not None and now - cached[0] < settings.SETTLEMENT_CHECK_CACHE_SECONDS:
            return cached[1]

    result = await _check(case, business)
    _cache[case.id] = (now, result)
    return result
