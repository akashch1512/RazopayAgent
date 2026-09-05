from src.agent.utilities.timezone import resolve_timezone


def test_india_dial_code() -> None:
    assert resolve_timezone("+919876543210") == "Asia/Kolkata"


def test_uae_three_digit_code_not_shadowed_by_shorter_prefixes() -> None:
    # "971" (UAE) must win over any single/double-digit prefix match.
    assert resolve_timezone("+971501234567") == "Asia/Dubai"


def test_unrecognised_prefix_falls_back_to_default() -> None:
    assert resolve_timezone("+000123456") == "UTC"


def test_missing_number_falls_back_to_default() -> None:
    assert resolve_timezone(None) == "UTC"
    assert resolve_timezone("") == "UTC"


def test_non_digit_characters_are_stripped() -> None:
    assert resolve_timezone("+91 98765-43210") == "Asia/Kolkata"
