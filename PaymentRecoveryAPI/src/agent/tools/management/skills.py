"""
`load_skill` - how the agent pulls a focused playbook into context.

The base prompt only carries the skills *catalog* (name + one-line description).
When a case actually needs the detailed tactics for its situation, the agent
calls this with the skill name; the full body is returned as the tool result
and the name is recorded in `RecoveryAgentState.loaded_skills`, so the context
builder keeps re-injecting that body on later turns and runs even after the
tool message itself has been trimmed.
"""

import typing

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.agent.skills import get_skill, list_skills

_MAX_LOADED = 4


@tool
async def load_skill(
    skill_name: str,
    tool_call_id: typing.Annotated[str, InjectedToolCallId],
    loaded_skills: typing.Annotated[list[str], InjectedState("loaded_skills")],
) -> Command:
    """Load the full playbook for one skill from the catalog in your instructions.

    Do this once, early, for the skill that matches the case's situation, then
    follow its guidance. The playbook stays in your context for the rest of this
    case.

    Args:
        skill_name: Exact name of a skill from the "Available skills" list.
    """
    skill = get_skill(skill_name)
    if skill is None:
        available = ", ".join(s.name for s in list_skills()) or "(none)"
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"No skill named {skill_name!r}. Available skills: {available}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )

    already = skill.name in (loaded_skills or [])
    next_loaded = [*(loaded_skills or []), skill.name] if not already else list(loaded_skills or [])
    next_loaded = next_loaded[-_MAX_LOADED:]

    note = " (already loaded; re-sending)" if already else ""
    return Command(
        update={
            "loaded_skills": next_loaded,
            "messages": [
                ToolMessage(
                    f"Skill loaded: {skill.name}{note}. Follow this playbook:\n\n{skill.body}",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
