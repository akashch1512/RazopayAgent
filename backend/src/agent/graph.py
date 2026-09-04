"""
Compiles the recovery agent's graph.

We deliberately reach for LangGraph's own `create_react_agent` prebuilt
(https://docs.langchain.com/oss/python/langchain/tools#tools) instead of
hand-rolling the model-call / route-to-tools / loop-until-done graph: it
already implements that, plus structured state and checkpointer wiring, which
is exactly the "agent (tools, MCP, state)" step of the pipeline.
"""

from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from src.agent.llm import get_chat_model
from src.agent.state import RecoveryAgentState


def build_recovery_agent(
    *, tools: list[BaseTool], checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:
    return create_react_agent(
        model=get_chat_model(),
        tools=tools,
        state_schema=RecoveryAgentState,
        checkpointer=checkpointer,
        name="recovery_agent",
    )
