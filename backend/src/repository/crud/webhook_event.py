import time
import typing

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db.business import Business
from src.models.db.webhook_event import WebhookEvent
from src.repository.crud.base import BaseCRUDRepository
from src.securities.encryption.encryptor import get_data_encryptor

# Process-local cache: razorpay_account_id -> (business_id, webhook_secret, expiry).
# All businesses' webhooks point at the same endpoint, so this lookup is the
# hot path; a short TTL keeps it cheap without going stale for long.
_ACCOUNT_CACHE: dict[str, tuple[int, str | None, float]] = {}
_ACCOUNT_CACHE_TTL_SECONDS = 300


class WebhookEventCRUDRepository(BaseCRUDRepository):
    async def resolve_business(
        self, *, account_id: str | None
    ) -> tuple[int | None, str | None]:
        """Return `(business_id, decrypted_webhook_secret)` for a webhook `account_id`."""
        if not account_id:
            return None, None

        cached = _ACCOUNT_CACHE.get(account_id)
        if cached and cached[2] > time.monotonic():
            return cached[0], cached[1]

        stmt = sqlalchemy.select(
            Business.id, Business.encrypted_webhook_secret
        ).where(Business.razorpay_account_id == account_id)
        row = (await self.async_session.execute(stmt)).one_or_none()
        if row is None:
            return None, None

        secret = get_data_encryptor().decrypt(row.encrypted_webhook_secret) if row.encrypted_webhook_secret else None
        _ACCOUNT_CACHE[account_id] = (row.id, secret, time.monotonic() + _ACCOUNT_CACHE_TTL_SECONDS)
        return row.id, secret

    async def store_event(self, *, values: dict[str, typing.Any]) -> bool:
        """
        Insert one normalized event. Returns `True` if a new row was written,
        `False` if it was a duplicate delivery (idempotent via `dedupe_key`).
        """
        stmt = (
            pg_insert(WebhookEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
        )
        result = await self.async_session.execute(stmt)
        await self.async_session.commit()
        return bool(result.rowcount)
