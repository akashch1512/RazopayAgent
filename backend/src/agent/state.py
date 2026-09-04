"""
The graph's mutable state - extends `create_react_agent`'s own `AgentState`
(which already gives us the `messages` key + its reducer, *and* the
`remaining_steps` budget its internal loop-continuation check requires) with
the handful of recovery-specific facts the agent needs across a run.
Everything here is checkpointed automatically by whatever `BaseCheckpointSaver`
the graph is compiled with; no bespoke persistence code needed.
"""

from langgraph.prebuilt.chat_agent_executor import AgentState


class RecoveryAgentState(AgentState):
    """State for one recovery-case run - one LangGraph thread per `case_id`."""

    case_id: int
    business_id: int | None
    razorpay_account_id: str
    # IANA zone name, e.g. "Asia/Kolkata" - see `timezone_lookup.resolve_timezone`.
    customer_timezone: str
