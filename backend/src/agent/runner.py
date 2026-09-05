"""
The single entry point the Celery worker calls: given a claimed `RecoveryCase`
and its merged history, run the LangGraph agent end to end and report what it
did.

    case queue (Celery, N workers) -> context build -> agent (tools, MCP, state) -> action -> DB checkpoint
                                       \\____________________ this module ____________________/

The queue side (priority dispatch, retries, dead-lettering) lives in
`src.workers`; this module is only responsible for turning a case into an
agent run and reporting the outcome. It raises on failure - the caller owns
retry/backoff/dead-lettering decisions.
"""

import typing

import loguru
from langchain_core.tools import BaseTool

from src.agent.audit import CaseActionAuditHandler
from src.agent.checkpointer import get_checkpointer
from src.agent.context import build_case_context
from src.agent.graph import build_recovery_agent
from src.agent.tools import STATIC_TOOLS
from src.integrations.razorpay.mcp import get_razorpay_mcp_tools
from src.models.db.business import Business
from src.models.db.recovery_case import RecoveryCase
from src.models.db.webhook_event import WebhookEvent

# Outreach-channel tools a business can disable via `AgentSettings.enabled_channels`
# (see `src.models.schemas.business.AGENT_CHANNELS`). Every other static tool
# (e.g. `track_payment_status`) is never gated - it isn't a customer channel.
_CHANNEL_TOOL_NAMES = frozenset(
    {"make_call", "send_sms", "send_whatsapp_message", "send_app_notification", "send_email", "send_payment_link"}
)


def _filter_tools_for_business(tools: list[BaseTool], business: Business) -> list[BaseTool]:
    enabled = (business.agent_settings or {}).get("enabled_channels")
    if not enabled:
        return tools
    allowed = set(enabled)
    return [tool for tool in tools if tool.name not in _CHANNEL_TOOL_NAMES or tool.name in allowed]


async def run_recovery_agent(
    *, case: RecoveryCase, history: list[WebhookEvent], business: Business
) -> dict[str, typing.Any]:
    """
    Run the agent once for `case`. One LangGraph thread per case
    (`thread_id = str(case.id)`), so a re-run (retry, or a later reopen after
    a new failure) resumes the same checkpointed conversation instead of
    starting cold.
    """
    mcp_tools = await get_razorpay_mcp_tools(business)
    tools = _filter_tools_for_business([*STATIC_TOOLS, *mcp_tools], business)

    initial_state = build_case_context(case=case, history=history, business=business)

    async with get_checkpointer() as checkpointer:
        agent = build_recovery_agent(tools=tools, checkpointer=checkpointer)
        result = await agent.ainvoke(
            initial_state,
            config={
                "configurable": {"thread_id": str(case.id)},
                # Records every tool call (ours and the MCP ones alike) as a
                # `CaseAction` audit row - see src.agent.audit.
                "callbacks": [CaseActionAuditHandler(case_id=case.id)],
            },
        )

    messages = result.get("messages", [])
    final_message = messages[-1] if messages else None
    summary = getattr(final_message, "content", None)

    loguru.logger.info(
        f"recovery agent finished case id={case.id} static_tools={len(STATIC_TOOLS)} "
        f"mcp_tools={len(mcp_tools)} messages={len(messages)}"
    )

    return {"tool_count": len(tools), "message_count": len(messages), "summary": summary}
