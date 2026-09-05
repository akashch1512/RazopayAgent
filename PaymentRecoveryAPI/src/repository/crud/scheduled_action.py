import datetime
import typing

import sqlalchemy

from src.models.db.scheduled_action import ScheduledAction, ScheduledActionStatus
from src.repository.crud.base import BaseCRUDRepository


class ScheduledActionCRUDRepository(BaseCRUDRepository):
    async def create_action(
        self,
        *,
        case_id: int,
        channel: str,
        recipient: str,
        payload: dict[str, typing.Any],
        scheduled_for: datetime.datetime,
    ) -> ScheduledAction:
        action = ScheduledAction(
            case_id=case_id,
            channel=channel,
            recipient=recipient,
            payload=payload,
            scheduled_for=scheduled_for,
            status=ScheduledActionStatus.PENDING.value,
        )
        self.async_session.add(action)
        await self.async_session.commit()
        await self.async_session.refresh(action)
        return action

    async def list_due(self, *, now: datetime.datetime, limit: int) -> typing.Sequence[ScheduledAction]:
        stmt = (
            sqlalchemy.select(ScheduledAction)
            .where(
                ScheduledAction.status == ScheduledActionStatus.PENDING.value,
                ScheduledAction.scheduled_for <= now,
            )
            .order_by(ScheduledAction.scheduled_for.asc(), ScheduledAction.id.asc())
            .limit(limit)
        )
        return (await self.async_session.execute(stmt)).scalars().all()

    async def mark_queued(self, *, action_id: int, celery_task_id: str) -> bool:
        stmt = (
            sqlalchemy.update(ScheduledAction)
            .where(
                ScheduledAction.id == action_id,
                ScheduledAction.status == ScheduledActionStatus.PENDING.value,
            )
            .values(
                status=ScheduledActionStatus.QUEUED.value,
                celery_task_id=celery_task_id,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
            )
        )
        result = await self.async_session.execute(stmt)
        await self.async_session.commit()
        return result.rowcount == 1

    async def claim_for_delivery(self, *, action_id: int, now: datetime.datetime) -> ScheduledAction | None:
        stmt = (
            sqlalchemy.select(ScheduledAction)
            .where(
                ScheduledAction.id == action_id,
                ScheduledAction.scheduled_for <= now,
                ScheduledAction.status.in_(
                    [ScheduledActionStatus.PENDING.value, ScheduledActionStatus.QUEUED.value]
                ),
            )
            .with_for_update()
        )
        action = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if action is None:
            return None
        action.status = ScheduledActionStatus.PROCESSING.value
        action.attempts += 1
        action.updated_at = now
        await self.async_session.commit()
        return action

    async def mark_sent(self, *, action_id: int) -> None:
        await self.async_session.execute(
            sqlalchemy.update(ScheduledAction)
            .where(ScheduledAction.id == action_id)
            .values(status=ScheduledActionStatus.SENT.value, updated_at=datetime.datetime.now(tz=datetime.UTC))
        )
        await self.async_session.commit()

    async def mark_failed(self, *, action_id: int, error: str, retry: bool) -> None:
        status = ScheduledActionStatus.PENDING.value if retry else ScheduledActionStatus.FAILED.value
        await self.async_session.execute(
            sqlalchemy.update(ScheduledAction)
            .where(ScheduledAction.id == action_id)
            .values(
                status=status,
                last_error=error,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
            )
        )
        await self.async_session.commit()
