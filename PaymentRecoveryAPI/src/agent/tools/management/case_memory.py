"""
`record_case_memory` - how the agent writes to its own long-term memory
(`RecoveryAgentState`).

Only facts that must survive message trimming and the next re-run belong here:
the agent's understanding of the customer's situation, promises the customer
made, the final outcome, and when to look at the case again. Everything else
(case fields, webhook history, what was sent) is rebuilt from the database each
run and must NOT be duplicated through this tool.
"""

import datetime
import typing

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

_MAX_COMMITMENTS = 20


def _valid_iso(value: str) -> bool:
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


@tool
async def record_case_memory(
    tool_call_id: typing.Annotated[str, InjectedToolCallId],
    commitments: typing.Annotated[list[str], InjectedState("commitments")],
    customer_summary: str | None = None,
    new_commitment: str | None = None,
    resolution: str | None = None,
    next_check_after: str | None = None,
) -> Command:
    """Save durable notes about this case to your memory so you still have them
    on the next run, after older messages have been dropped from context.

    Call this whenever you learn something that would change how a *future* run
    handles this case. Do not use it to restate the case facts or what you sent
    - those are always rebuilt for you.

    Args:
        customer_summary: Your current one-paragraph understanding of the
            customer's situation and why they haven't paid (replaces the
            previous summary).
        new_commitment: A concrete promise the customer just made, e.g.
            "will pay by 2026-09-10" or "asked us to retry the card on Monday".
            Appended to the existing list.
        resolution: Set only when the case is done: "recovered",
            "unrecoverable: <short reason>", or "handed_off: <short reason>".
        next_check_after: ISO-8601 timestamp to revisit this case (e.g. after a
            promised pay date). The case is automatically re-queued for that time.
    """
    update: dict[str, typing.Any] = {}
    notes: list[str] = []

    if customer_summary and customer_summary.strip():
        update["customer_summary"] = customer_summary.strip()[:1000]
        notes.append("summary updated")

    if new_commitment and new_commitment.strip():
        update["commitments"] = [*commitments, new_commitment.strip()[:200]][-_MAX_COMMITMENTS:]
        notes.append("commitment recorded")

    if resolution and resolution.strip():
        update["resolution"] = resolution.strip()[:200]
        notes.append(f"resolution={update['resolution']}")

    if next_check_after and next_check_after.strip():
        if _valid_iso(next_check_after.strip()):
            update["next_check_after"] = next_check_after.strip()
            notes.append(f"will revisit at {update['next_check_after']}")
        else:
            notes.append("next_check_after ignored (not a valid ISO-8601 timestamp)")

    confirmation = "Case memory: " + (", ".join(notes) if notes else "nothing to record")
    update["messages"] = [ToolMessage(confirmation, tool_call_id=tool_call_id)]
    return Command(update=update)
