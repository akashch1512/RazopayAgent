"""
The single entry point the Celery worker calls: given a claimed `RecoveryCase`
and its merged history, run the LangGraph agent end to end and report what it
did.

    case queue (Celery, N workers) -> settlement check -> context build -> agent (tools, MCP, memory) -> outcome
                                        \\_____________________ this module _____________________/

Before spending an LLM call, it asks Razorpay whether the payment is already
done (`src.services.recovery.settlement`); if so the case is closed and the
agent never runs. Otherwise the agent's own memory from any earlier run is
loaded from the checkpoint and folded into the prompt so the run resumes with
what it already learned.
"""

import logging
import typing

from src.agent.application.tool_registry import STATIC_TOOLS
from src.agent.infrastructure.audit import CaseActionAuditHandler
from src.agent.infrastructure.checkpointer import get_checkpointer
from src.agent.orchestration.context import (
    MEMORY_KEYS,
    build_case_context,
    build_system_prompt_context,
)
from src.agent.orchestration.graph import build_recovery_agent
from src.agent.policies.channel_policy import filter_tools_for_business
from src.integrations.razorpay.mcp import get_razorpay_mcp_tools
from src.models.db.business import Business
from src.models.db.case_action import CaseAction
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent
from src.services.recovery.settlement import is_case_settled

logger = logging.getLogger(__name__)


async def _load_prior_memory(checkpointer: typing.Any, thread_id: str) -> dict[str, typing.Any]:
    """The agent's `RecoveryAgentState` memory from its last run on this case,
    or `{}` on the first run."""
    try:
        checkpoint = await checkpointer.aget({"configurable": {"thread_id": thread_id}})
    except Exception as exc:  # noqa: BLE001 - a missing/broken checkpoint must not stop a fresh run
        logger.warning(f"case thread={thread_id}: could not load prior memory ({exc!r}); starting cold")
        return {}
    values = (checkpoint or {}).get("channel_values", {}) or {}
    return {key: values[key] for key in MEMORY_KEYS if key in values}


async def run_recovery_agent(
    *,
    case: RecoveryCase,
    history: list[WebhookEvent],
    business: Business,
    actions: list[CaseAction] | None = None,
) -> dict[str, typing.Any]:
    """
    Run the agent once for `case`. One LangGraph thread per case
    (`thread_id = str(case.id)`), so a re-run resumes the same checkpointed
    memory/conversation instead of starting cold.

    Returns a dict whose `status` the worker acts on:
        "resolved"  - payment is already done; close the case
        "processed" - the agent finished a run (plus optional `next_check_after`)
    """
    actions = actions or []

    if await is_case_settled(case=case, business=business):
        logger.info(f"recovery agent: case id={case.id} already settled at Razorpay; closing without a run")
        return {"status": "resolved", "reason": "payment already settled", "ran_agent": False}

    mcp_tools = await get_razorpay_mcp_tools(business)
    tools = filter_tools_for_business([*STATIC_TOOLS, *mcp_tools], business)
    thread_id = str(case.id)

    async with get_checkpointer() as checkpointer:
        prior_memory = await _load_prior_memory(checkpointer, thread_id)

        initial_state = build_case_context(
            case=case, history=history, business=business, actions=actions, prior_memory=prior_memory
        )
        system_prompt = build_system_prompt_context(
            case=case, history=history, business=business, actions=actions, prior_memory=prior_memory
        )

        agent = build_recovery_agent(tools=tools, checkpointer=checkpointer, system_prompt=system_prompt)
        result = await agent.ainvoke(
            initial_state,
            config={
                "configurable": {"thread_id": thread_id},
                # Records every tool call (ours and the MCP ones alike) as a
                # `CaseAction` audit row - see src.agent.infrastructure.audit.
                "callbacks": [CaseActionAuditHandler(case_id=case.id)],
            },
        )

    messages = result.get("messages", [])
    final_message = messages[-1] if messages else None
    summary = getattr(final_message, "content", None)

    resolution = result.get("resolution")
    next_check_after = result.get("next_check_after")
    settled = bool(result.get("payment_verified")) or (resolution or "").startswith("recovered")

    logger.info(
        f"recovery agent finished case id={case.id} static_tools={len(STATIC_TOOLS)} "
        f"mcp_tools={len(mcp_tools)} messages={len(messages)} "
        f"resolution={resolution!r} next_check_after={next_check_after!r}"
    )

    if settled:
        return {"status": "resolved", "reason": resolution or "payment verified", "ran_agent": True}

    return {
        "status": "processed",
        "resolution": resolution,
        "next_check_after": next_check_after,
        "tool_count": len(tools),
        "message_count": len(messages),
        "summary": summary,
    }
