import datetime
import typing

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db.recovery_case import (
    IN_FLIGHT_CASE_STATUSES,
    RECLAIMABLE_CASE_STATUSES,
    RecoveryCase,
    RecoveryCaseStatus,
)
from src.repository.crud.base import BaseCRUDRepository
from src.utilities.exceptions.database import EntityDoesNotExist


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


class RecoveryCaseCRUDRepository(BaseCRUDRepository):
    """
    Owns the merge (many `webhook_event` -> one `RecoveryCase`) and the case's
    dispatch lifecycle. The agent worker only ever sees rows from this table.
    """

    async def upsert_case(
        self,
        *,
        business_id: int | None,
        razorpay_account_id: str,
        case_key: str,
        entity_type: str | None,
        primary_entity_id: str | None,
        event_type: str,
        entity_status: str | None,
        customer_email: str | None,
        customer_contact: str | None,
        priority: int,
        priority_reason: str,
        is_resolving: bool,
    ) -> tuple[RecoveryCase, bool]:
        """
        Insert a new case, or merge onto an existing one for the same
        `(razorpay_account_id, case_key)`. Returns `(case, is_new)`.

        Merge behaviour:
        * `event_count` increments - this is the "customer retried N times" signal.
        * priority only ever gets *more* urgent on merge (`LEAST`), plus a small
          bonus for repeated failures (every 3 retries -> one tier more urgent,
          capped at +2) - a case that keeps failing should not stay buried.
        * a resolving event (payment eventually captured, ...) force-closes the
          case regardless of its current dispatch state.
        """
        now = _utcnow()

        insert_values: dict[str, typing.Any] = {
            "business_id": business_id,
            "razorpay_account_id": razorpay_account_id,
            "case_key": case_key,
            "entity_type": entity_type,
            "primary_entity_id": primary_entity_id,
            "customer_email": customer_email,
            "customer_contact": customer_contact,
            "latest_event_type": event_type,
            "latest_entity_status": entity_status,
            "event_count": 1,
            "priority": priority,
            "priority_reason": priority_reason,
            "processing_status": (
                RecoveryCaseStatus.RESOLVED.value if is_resolving else RecoveryCaseStatus.RECEIVED.value
            ),
            "resolved_at": now if is_resolving else None,
            "first_event_at": now,
            "last_event_at": now,
        }

        repeat_bonus = sqlalchemy.func.least(2, RecoveryCase.event_count / 3)
        merged_priority = sqlalchemy.func.greatest(
            0, sqlalchemy.func.least(RecoveryCase.priority, priority) - repeat_bonus
        )
        update_values: dict[str, typing.Any] = {
            "business_id": sqlalchemy.func.coalesce(RecoveryCase.business_id, business_id),
            "event_count": RecoveryCase.event_count + 1,
            "latest_event_type": event_type,
            "latest_entity_status": entity_status,
            "customer_email": sqlalchemy.func.coalesce(customer_email, RecoveryCase.customer_email),
            "customer_contact": sqlalchemy.func.coalesce(customer_contact, RecoveryCase.customer_contact),
            "priority": merged_priority,
            "priority_reason": priority_reason,
            "last_event_at": now,
        }
        if is_resolving:
            update_values["processing_status"] = RecoveryCaseStatus.RESOLVED.value
            update_values["resolved_at"] = now

        stmt = (
            pg_insert(RecoveryCase)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["razorpay_account_id", "case_key"],
                set_=update_values,
            )
            .returning(RecoveryCase)
        )
        row = (await self.async_session.execute(stmt)).scalar_one()
        await self.async_session.commit()
        return row, row.event_count == 1

    # ------------------------------------------------------------------ #
    # Reads - exposed to the outside world via the recovery-cases API.   #
    # ------------------------------------------------------------------ #

    async def read_case_by_id(self, *, case_id: int) -> RecoveryCase:
        stmt = sqlalchemy.select(RecoveryCase).where(RecoveryCase.id == case_id)
        case = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if case is None:
            raise EntityDoesNotExist(f"Recovery case with id `{case_id}` does not exist!")
        return case

    async def list_cases_by_business(
        self, *, business_id: int, limit: int = 50, offset: int = 0
    ) -> typing.Sequence[RecoveryCase]:
        """Most recently active case first - what a support/ops view wants."""
        return await self.list_cases(business_id=business_id, limit=limit, offset=offset)

    async def list_cases(
        self,
        *,
        business_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> typing.Sequence[RecoveryCase]:
        """
        General-purpose case listing (an ops/support dashboard's main query):
        optionally scoped to one business and/or one `RecoveryCaseStatus`, most
        recently active first.
        """
        stmt = sqlalchemy.select(RecoveryCase)
        if business_id is not None:
            stmt = stmt.where(RecoveryCase.business_id == business_id)
        if status is not None:
            stmt = stmt.where(RecoveryCase.processing_status == status)
        stmt = stmt.order_by(RecoveryCase.last_event_at.desc()).limit(limit).offset(offset)
        return (await self.async_session.execute(stmt)).scalars().all()

    async def reset_case_for_retry(self, *, case_id: int) -> RecoveryCase:
        """
        Manually reopen a `DEAD` or `FAILED` case for another attempt - clears the
        attempt counter and last error. The caller is still responsible for
        enqueueing it (mirrors the route's own dispatch step).
        """
        stmt = (
            sqlalchemy.update(RecoveryCase)
            .where(
                RecoveryCase.id == case_id,
                RecoveryCase.processing_status.in_(
                    (RecoveryCaseStatus.DEAD.value, RecoveryCaseStatus.FAILED.value)
                ),
            )
            .values(
                processing_status=RecoveryCaseStatus.RECEIVED.value,
                processing_attempts=0,
                last_error=None,
                next_visible_at=None,
            )
            .returning(RecoveryCase)
        )
        row = (await self.async_session.execute(stmt)).scalar_one_or_none()
        await self.async_session.commit()
        if row is None:
            raise EntityDoesNotExist(
                f"Recovery case with id `{case_id}` does not exist, or is not DEAD/FAILED!"
            )
        return row

    @staticmethod
    def needs_dispatch(case: RecoveryCase, *, is_resolving: bool) -> bool:
        """Should the route enqueue this case right now?"""
        if is_resolving:
            return False
        return case.processing_status not in IN_FLIGHT_CASE_STATUSES

    async def mark_queued(
        self, *, case_id: int, celery_task_id: str, priority: int, priority_reason: str
    ) -> None:
        stmt = (
            sqlalchemy.update(RecoveryCase)
            .where(
                RecoveryCase.id == case_id,
                RecoveryCase.processing_status != RecoveryCaseStatus.PROCESSING.value,
            )
            .values(
                processing_status=RecoveryCaseStatus.QUEUED.value,
                celery_task_id=celery_task_id,
                priority=priority,
                priority_reason=priority_reason,
                queued_at=_utcnow(),
                next_visible_at=None,
            )
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def claim_for_processing(self, *, case_id: int, max_attempts: int) -> RecoveryCase | None:
        """Atomically move a reclaimable case to PROCESSING; `None` if not claimable."""
        stmt = (
            sqlalchemy.update(RecoveryCase)
            .where(
                RecoveryCase.id == case_id,
                RecoveryCase.processing_status.in_(RECLAIMABLE_CASE_STATUSES),
                RecoveryCase.processing_attempts < max_attempts,
            )
            .values(
                processing_status=RecoveryCaseStatus.PROCESSING.value,
                processing_attempts=RecoveryCase.processing_attempts + 1,
                queued_at=_utcnow(),
            )
            .returning(RecoveryCase)
        )
        row = (await self.async_session.execute(stmt)).scalar_one_or_none()
        await self.async_session.commit()
        return row

    async def mark_processed(self, *, case_id: int) -> None:
        await self._set_status(case_id=case_id, status=RecoveryCaseStatus.PROCESSED.value)

    async def mark_resolved(self, *, case_id: int, reason: str | None = None) -> None:
        """Close a case the agent (or a live settlement check) found already
        paid. Terminal - `claim_for_processing` will not reclaim a RESOLVED row.
        `reason` is for the caller's log line; the row has no note column."""
        stmt = (
            sqlalchemy.update(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .values(
                processing_status=RecoveryCaseStatus.RESOLVED.value,
                resolved_at=_utcnow(),
                next_visible_at=None,
            )
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def mark_dead(self, *, case_id: int, error: str) -> None:
        await self._set_status(case_id=case_id, status=RecoveryCaseStatus.DEAD.value, last_error=error[:2000])

    async def mark_failed(self, *, case_id: int, error: str, next_visible_at: datetime.datetime) -> None:
        stmt = (
            sqlalchemy.update(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .values(
                processing_status=RecoveryCaseStatus.FAILED.value,
                last_error=error[:2000],
                next_visible_at=next_visible_at,
            )
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def _set_status(self, *, case_id: int, status: str, last_error: str | None = None) -> None:
        values: dict[str, typing.Any] = {"processing_status": status}
        if last_error is not None:
            values["last_error"] = last_error
        stmt = sqlalchemy.update(RecoveryCase).where(RecoveryCase.id == case_id).values(**values)
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def list_reconcilable(
        self, *, now: datetime.datetime, stuck_before: datetime.datetime, limit: int
    ) -> typing.Sequence[RecoveryCase]:
        """
        Cases the reconciler should (re)dispatch, most urgent first:

        * RECEIVED            - hot-path enqueue never happened / failed
        * FAILED               - retry backoff has elapsed
        * QUEUED / PROCESSING  - untouched past the stuck threshold (lost message
          or a worker that died mid-run)
        """
        stmt = (
            sqlalchemy.select(RecoveryCase)
            .where(
                sqlalchemy.or_(
                    RecoveryCase.processing_status == RecoveryCaseStatus.RECEIVED.value,
                    sqlalchemy.and_(
                        RecoveryCase.processing_status == RecoveryCaseStatus.FAILED.value,
                        sqlalchemy.or_(
                            RecoveryCase.next_visible_at.is_(None),
                            RecoveryCase.next_visible_at <= now,
                        ),
                    ),
                    sqlalchemy.and_(
                        RecoveryCase.processing_status.in_(IN_FLIGHT_CASE_STATUSES),
                        RecoveryCase.queued_at <= stuck_before,
                    ),
                )
            )
            .order_by(RecoveryCase.priority.asc(), RecoveryCase.first_event_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self.async_session.execute(stmt)).scalars().all()
