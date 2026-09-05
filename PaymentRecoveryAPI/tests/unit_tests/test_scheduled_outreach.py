import datetime

import pytest

from src.agent.application.tool_registry import STATIC_TOOLS
from src.agent.tools.outreach._scheduler import _parse_schedule


def test_schedule_parser_normalizes_utc_timestamp() -> None:
    scheduled_for = _parse_schedule("2026-09-05T12:30:00+05:30")

    assert scheduled_for == datetime.datetime(2026, 9, 5, 7, 0, tzinfo=datetime.UTC)


def test_schedule_parser_treats_naive_timestamp_as_utc() -> None:
    scheduled_for = _parse_schedule("2026-09-05T12:30:00")

    assert scheduled_for.tzinfo == datetime.UTC
    assert scheduled_for.hour == 12


def test_schedule_parser_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError):
        _parse_schedule("tomorrow morning")


def test_outreach_tools_expose_scheduling_argument() -> None:
    tool_names = {tool.name for tool in STATIC_TOOLS}
    assert {"make_call", "send_sms", "send_whatsapp_message", "send_email"}.issubset(tool_names)

    call_tool = next(tool for tool in STATIC_TOOLS if tool.name == "make_call")
    assert "scheduled_for" in call_tool.args_schema.model_fields
