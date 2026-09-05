"""
A phone number's country dial code is a decent proxy for the customer's local
time - good enough to decide "is it 3am for this person right now" without
pulling in a full number-formatting library.

Deliberately simple: a dial-code -> IANA timezone table, longest prefix first.
Multi-timezone countries (US, Russia, Australia, Brazil, ...) collapse to one
representative zone - close enough for "don't call at 3am", not meant to be
exact. Swap in `phonenumbers` + `timezonefinder` later if real precision on
those countries is needed.
"""

import re

from src.config.manager import settings

# Ordered by dial-code length doesn't matter here - `resolve_timezone` tries
# 3, then 2, then 1-digit prefixes so e.g. "971" (UAE) is checked before "97"
# or "9" ever could shadow it.
_DIAL_CODE_TIMEZONES: dict[str, str] = {
    # --- South Asia ---
    "91": "Asia/Kolkata",  # India
    "92": "Asia/Karachi",  # Pakistan
    "880": "Asia/Dhaka",  # Bangladesh
    "94": "Asia/Colombo",  # Sri Lanka
    "977": "Asia/Kathmandu",  # Nepal
    # --- Middle East ---
    "971": "Asia/Dubai",  # UAE
    "966": "Asia/Riyadh",  # Saudi Arabia
    "974": "Asia/Qatar",  # Qatar
    "965": "Asia/Kuwait",  # Kuwait
    # --- East / Southeast Asia ---
    "86": "Asia/Shanghai",  # China
    "81": "Asia/Tokyo",  # Japan
    "82": "Asia/Seoul",  # South Korea
    "65": "Asia/Singapore",  # Singapore
    "60": "Asia/Kuala_Lumpur",  # Malaysia
    "62": "Asia/Jakarta",  # Indonesia
    "63": "Asia/Manila",  # Philippines
    "66": "Asia/Bangkok",  # Thailand
    "84": "Asia/Ho_Chi_Minh",  # Vietnam
    # --- Europe ---
    "44": "Europe/London",  # UK
    "49": "Europe/Berlin",  # Germany
    "33": "Europe/Paris",  # France
    "34": "Europe/Madrid",  # Spain
    "39": "Europe/Rome",  # Italy
    "31": "Europe/Amsterdam",  # Netherlands
    "46": "Europe/Stockholm",  # Sweden
    "7": "Europe/Moscow",  # Russia / Kazakhstan
    # --- Americas ---
    "1": "America/New_York",  # US / Canada (NANP - many zones, this is a default)
    "55": "America/Sao_Paulo",  # Brazil
    "52": "America/Mexico_City",  # Mexico
    # --- Africa ---
    "20": "Africa/Cairo",  # Egypt
    "27": "Africa/Johannesburg",  # South Africa
    "234": "Africa/Lagos",  # Nigeria
    # --- Oceania ---
    "61": "Australia/Sydney",  # Australia
    "64": "Pacific/Auckland",  # New Zealand
}

_MAX_DIAL_CODE_LENGTH = 3


def resolve_timezone(phone_number: str | None) -> str:
    """
    Best-effort IANA timezone for an E.164-ish phone number, e.g. `+919876543210`
    -> `Asia/Kolkata`. Falls back to `settings.DEFAULT_CUSTOMER_TIMEZONE`.
    """
    if not phone_number:
        return settings.DEFAULT_CUSTOMER_TIMEZONE

    digits = re.sub(r"\D", "", phone_number)
    if not digits:
        return settings.DEFAULT_CUSTOMER_TIMEZONE

    for length in range(_MAX_DIAL_CODE_LENGTH, 0, -1):
        prefix = digits[:length]
        timezone = _DIAL_CODE_TIMEZONES.get(prefix)
        if timezone:
            return timezone

    return settings.DEFAULT_CUSTOMER_TIMEZONE
