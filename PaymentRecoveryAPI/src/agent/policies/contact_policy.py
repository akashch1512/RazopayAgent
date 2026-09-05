"""Customer-contact timing helpers."""

import datetime
import zoneinfo


def local_time_string(timezone_name: str) -> str:
	try:
		timezone = zoneinfo.ZoneInfo(timezone_name)
	except zoneinfo.ZoneInfoNotFoundError:
		timezone = zoneinfo.ZoneInfo("UTC")
	return datetime.datetime.now(tz=timezone).strftime("%A, %Y-%m-%d %H:%M %Z")
