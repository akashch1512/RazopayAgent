"""Rules for selecting customer-facing tools for a business."""

from langchain_core.tools import BaseTool

from src.models.db.business import Business

CHANNEL_TOOL_NAMES = frozenset(
	{"make_call", "send_sms", "send_whatsapp_message", "send_app_notification", "send_email"}
)


def filter_tools_for_business(tools: list[BaseTool], business: Business) -> list[BaseTool]:
	enabled = (business.agent_settings or {}).get("enabled_channels")
	if not enabled:
		return tools
	allowed = set(enabled)
	return [tool for tool in tools if tool.name not in CHANNEL_TOOL_NAMES or tool.name in allowed]
