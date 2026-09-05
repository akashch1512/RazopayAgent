"""
`check_payment_status` - ask Razorpay, right now, whether this case's payment
is already done, instead of trusting the case's last-webhook `entity_status`
(which can be stale by the time the agent runs).

On a confirmed "paid" it flips `payment_verified` in the agent's memory; every
outreach tool refuses once that is set, so the agent cannot nudge a customer
who has already paid. The recovery worker also runs this same check before the
agent starts and closes the case outright if it comes back paid.
"""

import typing

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.models.db.business import Business
from src.repository.crud.business import BusinessCRUDRepository
from src.repository.crud.recovery_case import RecoveryCaseCRUDRepository
from src.services.recovery.settlement import is_case_settled
from src.utilities.exceptions.database import EntityDoesNotExist
from src.workers.runtime import worker_session


@tool
async def check_payment_status(
    tool_call_id: typing.Annotated[str, InjectedToolCallId],
    case_id: typing.Annotated[int, InjectedState("case_id")],
) -> Command:
    """Check with Razorpay whether this case's payment has already been completed.

    Call this before your first outreach on a run, and again before escalating
    or sending a repeat nudge - it avoids chasing a customer who has already
    paid, been refunded, or otherwise moved on since the last webhook.
    """
    async with worker_session() as session:
        try:
            case = await RecoveryCaseCRUDRepository(async_session=session).read_case_by_id(case_id=case_id)
        except EntityDoesNotExist:
            return Command(
                update={
                    "messages": [ToolMessage(f"Case {case_id} not found.", tool_call_id=tool_call_id)]
                }
            )
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

    settled = await is_case_settled(case=case, business=business, use_cache=False)

    if settled is True:
        message = (
            "CONFIRMED PAID: Razorpay shows this payment is already completed. "
            'Do not send any further outreach. Call record_case_memory(resolution="recovered") '
            "and finish."
        )
        return Command(
            update={
                "payment_verified": True,
                "messages": [ToolMessage(message, tool_call_id=tool_call_id)],
            }
        )

    if settled is False:
        message = "Razorpay shows this payment is still NOT completed - the case is genuine, continue."
    else:
        message = (
            "Could not verify payment status with Razorpay for this entity type - "
            "fall back to the case's last known status from its history."
        )
    return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})
