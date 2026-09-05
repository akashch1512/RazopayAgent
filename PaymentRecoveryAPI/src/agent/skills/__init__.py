"""
Agent skills: focused, per-situation playbooks kept out of the base prompt.

Each `*.md` file in this package is one skill - a small frontmatter block
(`name`, `description`, `when`) plus a markdown body of tactics. The agent sees
only the catalog (name + description) by default; it calls the `load_skill`
tool to pull a full body into context when a case actually needs it, and the
choice is remembered in `RecoveryAgentState.loaded_skills` so it survives
message trimming and later runs.
"""

from src.agent.skills.registry import (
    Skill,
    get_skill,
    list_skills,
    render_skills_section,
    skills_for_event,
)

__all__ = [
    "Skill",
    "get_skill",
    "list_skills",
    "render_skills_section",
    "skills_for_event",
]
