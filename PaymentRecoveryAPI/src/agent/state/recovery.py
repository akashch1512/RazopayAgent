"""
The recovery agent's **memory** - one LangGraph thread (checkpoint) per case.

This is *not* a mirror of the case brief. Everything that can be rebuilt from
the database on the next run (case fields, webhook history, the outbound audit
trail) is rebuilt in `src.agent.orchestration.context`, not stored here. State
holds only what would otherwise be **lost** once older messages are trimmed and
is **expensive or impossible to re-derive**:

* what the customer actually told us the first time they engaged,
* the agent's own running understanding of the situation and any promises made,
* whether a live check has confirmed the payment is already done,
* the terminal outcome the agent reached and when it wants the case revisited.

On a re-run the context builder reads these back and *omits from the rebuilt
prompt* whatever state already carries - same information, fewer tokens.
"""

from langgraph.prebuilt.chat_agent_executor import AgentState


class RecoveryAgentState(AgentState):
    case_id: int

    # Verbatim first thing the customer said to us on this case (from the
    # earliest `customer.feedback` event). Set deterministically by the context
    # builder; pinned here so it survives message trimming across many re-runs.
    customer_first_message: str | None

    # The agent's own notes - written only via `record_case_memory`, never
    # guessed by the context builder.
    customer_summary: str | None  # running understanding of the customer's situation / objection
    commitments: list[str]  # concrete promises the customer made ("will pay by Fri")

    # A live Razorpay check has confirmed this payment is settled -> every
    # outreach tool must refuse and the run should wrap up.
    payment_verified: bool

    # Terminal outcome: "recovered" | "unrecoverable: <reason>" | "handed_off: <reason>".
    resolution: str | None
    # ISO-8601 time the agent wants this case picked up again (dunning cadence).
    next_check_after: str | None

    # Names of skills the agent pulled in via `load_skill`; the context builder
    # keeps re-injecting their full text so a run always follows the same playbook.
    loaded_skills: list[str]
