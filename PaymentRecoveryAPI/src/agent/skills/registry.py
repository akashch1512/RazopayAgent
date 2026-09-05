"""
Loads and indexes the skill markdown files in this package.

Frontmatter is a deliberately tiny subset of YAML (flat `key: value`, with
`when` a comma-separated list) so there is no dependency to add:

    ---
    name: payment_failure_handling
    description: One-line summary the agent sees in the catalog.
    when: payment.failed, order.dropoff
    ---

    <markdown body: the actual playbook>
"""

import dataclasses
import functools
import logging
import pathlib
import re

logger = logging.getLogger(__name__)

_SKILLS_DIR = pathlib.Path(__file__).parent
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclasses.dataclass(frozen=True)
class Skill:
    name: str
    description: str
    triggers: tuple[str, ...]  # event types this skill is relevant to
    body: str


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()
    return meta, match.group(2)


def _load_one(path: pathlib.Path) -> Skill | None:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    meta, body = _parse_frontmatter(raw)
    body = body.strip()
    if not body:
        return None
    triggers = tuple(t.strip() for t in meta.get("when", "").split(",") if t.strip())
    return Skill(
        name=meta.get("name", path.stem).strip(),
        description=meta.get("description", "").strip() or "(no description)",
        triggers=triggers,
        body=body,
    )


@functools.cache
def load_skills() -> dict[str, Skill]:
    """All non-empty skills, keyed by name. Cached for the process lifetime."""
    skills: dict[str, Skill] = {}
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skill = _load_one(path)
        if skill is None:
            continue
        if skill.name in skills:
            logger.warning(f"duplicate skill name {skill.name!r} ({path.name}); keeping the first")
            continue
        skills[skill.name] = skill
    return skills


def list_skills() -> list[Skill]:
    return list(load_skills().values())


def get_skill(name: str) -> Skill | None:
    return load_skills().get(name.strip())


def skills_for_event(event_type: str | None) -> list[Skill]:
    """Skills whose `when:` names this event type - the ones worth suggesting."""
    if not event_type:
        return []
    return [skill for skill in load_skills().values() if event_type in skill.triggers]


def render_skills_section(*, latest_event_type: str | None, loaded: list[str] | None) -> str:
    """
    The `{skills_section}` block of the system prompt: the catalog of every
    skill, a hint about which fit this case, and the full text of any skill the
    agent has already loaded (so it persists across message trimming / re-runs).
    """
    skills = list_skills()
    if not skills:
        return "No skills are available."

    loaded = loaded or []
    suggested = {s.name for s in skills_for_event(latest_event_type)}

    lines = ["Available skills - call `load_skill(\"<name>\")` to pull the full playbook when a case needs it:"]
    for skill in skills:
        tag = ""
        if skill.name in loaded:
            tag = " [loaded below]"
        elif skill.name in suggested:
            tag = " [suggested for this case]"
        lines.append(f"- {skill.name}: {skill.description}{tag}")

    for name in loaded:
        loaded_skill = load_skills().get(name)
        if loaded_skill is not None:
            lines.append(f"\n--- skill: {loaded_skill.name} ---\n{loaded_skill.body}")

    return "\n".join(lines)
