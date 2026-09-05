"""Durable scheduling shared by all customer-outreach tools."""

import datetime
import logging
import typing

from src.models.db.business import Business
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.repository.crud.scheduled_action import ScheduledActionCRUDRepository
from src.services.recovery.settlement import is_case_settled
from src.utilities.exceptions.database import EntityDoesNotExist
from src.workers import names
from src.workers.enqueue import EnqueueError, enqueue
from src.workers.runtime import worker_session

logger = logging.getLogger(__name__)

_ALREADY_PAID_REFUSAL = (
    "Not sent: a live Razorpay check shows this payment is already completed. "
    "Do not contact the customer about it. Call record_case_memory(resolution=\"recovered\") and stop."
)


async def _case_already_paid(case_id: int) -> bool:
    """Guard every outreach: never message a customer whose payment has landed
    since the agent last looked. Cached, so a burst of sends costs one call."""
    async with worker_session() as session:
        try:
            case = await RecoveryCaseCRUDRepository(async_session=session).read_case_by_id(case_id=case_id)
        except EntityDoesNotExist:
            return False
        business: Business
        if case.business_id is not None:
            try:
                business = await BusinessCRUDRepository(async_session=session).read_business_by_id(
                    business_id=case.business_id
                )
            except EntityDoesNotExist:
                business = Business(name="Unknown Business", reference_id="unresolved")
        else:
            business = Business(name="Unknown Business", reference_id="unresolved")

    return await is_case_settled(case=case, business=business) is True


def _parse_schedule(value: str | None) -> datetime.datetime:
    if not value:
        return datetime.datetime.now(tz=datetime.UTC)
    scheduled_for = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=datetime.UTC)
    return scheduled_for.astimezone(datetime.UTC)


async def schedule_outreach(
    *,
    case_id: int,
    channel: str,
    recipient: str,
    payload: dict[str, typing.Any],
    scheduled_for: str | None,
) -> str:
    """Persist an outreach action and enqueue it now when it is due."""
    if await _case_already_paid(case_id):
        logger.info(f"case id={case_id}: outreach ({channel}) blocked - payment already completed")
        return _ALREADY_PAID_REFUSAL

    try:
        due_at = _parse_schedule(scheduled_for)
    except ValueError:
        return "Invalid scheduled_for. Use an ISO-8601 timestamp, preferably with a timezone."

    now = datetime.datetime.now(tz=datetime.UTC)
    immediate = due_at <= now
    async with worker_session() as session:
        repo = ScheduledActionCRUDRepository(async_session=session)
        action = await repo.create_action(
            case_id=case_id,
            channel=channel,
            recipient=recipient,
            payload={**payload, "case_id": str(case_id)},
            scheduled_for=due_at,
        )

        if not immediate:
            return f"Outreach scheduled for {due_at.isoformat()} (action_id={action.id})."

        try:
            task_id = enqueue(
                names.SCHEDULED_ACTION_DELIVER_TASK,
                priority=1,
                kwargs={"action_id": action.id},
            )
        except EnqueueError:
            return f"Outreach saved for immediate delivery (action_id={action.id}); the worker will retry queueing it."

        await repo.mark_queued(action_id=action.id, celery_task_id=task_id)
        return f"Outreach queued for immediate delivery (action_id={action.id})."


async def deliver_scheduled_action_payload(
    *, channel: str, payload: dict[str, typing.Any]
) -> dict[str, typing.Any] | None:
    """Send one persisted action through the simulation provider."""
    from src.agent.tools.outreach._simulation_client import call_simulation_api

    path = {
        "call": "/simulate/call",
        "sms": "/simulate/sms",
        "whatsapp": "/simulate/whatsapp",
        "email": "/simulate/email",
        "app_notification": "/simulate/app-notification",
    }[channel]
    return await call_simulation_api(path, payload)
