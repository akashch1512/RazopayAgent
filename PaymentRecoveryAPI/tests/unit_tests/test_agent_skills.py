"""The skill registry: every skill file parses, has a description, and the
event->skill and catalog rendering behave."""

from src.agent.skills import get_skill, list_skills, render_skills_section, skills_for_event


def test_all_skills_parse_with_metadata() -> None:
    skills = list_skills()
    assert skills, "no skills were loaded"
    for skill in skills:
        assert skill.name and " " not in skill.name
        assert skill.description and skill.description != "(no description)"
        assert skill.body
        assert skill.triggers  # every playbook declares when it applies


def test_skills_for_event_matches_triggers() -> None:
    names = {s.name for s in skills_for_event("payment.failed")}
    assert "payment_failure_handling" in names
    assert skills_for_event("no.such.event") == []
    assert skills_for_event(None) == []


def test_catalog_marks_suggested_and_loaded() -> None:
    section = render_skills_section(
        latest_event_type="order.dropoff", loaded=["payment_dropoff_recovery"]
    )
    assert "payment_dropoff_recovery" in section
    assert "[loaded below]" in section
    # The loaded skill's full body is injected.
    assert get_skill("payment_dropoff_recovery").body[:20] in section


def test_catalog_suggests_by_event() -> None:
    section = render_skills_section(latest_event_type="invoice.expired", loaded=[])
    assert "overdue_invoice_recovery" in section
    assert "[suggested for this case]" in section
