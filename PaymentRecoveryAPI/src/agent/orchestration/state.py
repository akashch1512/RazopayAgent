"""
The graph's mutable state - extends `create_react_agent`'s own `AgentState`
(which already gives us the `messages` key + its reducer, *and* the
`remaining_steps` budget its internal loop-continuation check requires) with
the handful of recovery-specific facts the agent needs across a run.
Everything here is checkpointed automatically by whatever `BaseCheckpointSaver`
the graph is compiled with; no bespoke persistence code needed.
"""

from src.agent.state.recovery import RecoveryAgentState

__all__ = ["RecoveryAgentState"]
