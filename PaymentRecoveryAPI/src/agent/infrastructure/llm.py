"""
The chat model backing the recovery agent.

https://docs.langchain.com/oss/javascript/integrations/llms/openai (Python
equivalent: `langchain_openai.ChatOpenAI`).
"""

import functools

import pydantic
from langchain_openai import ChatOpenAI

from src.config.manager import settings


@functools.lru_cache
def get_chat_model() -> ChatOpenAI:
    api_key = pydantic.SecretStr(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    return ChatOpenAI(
        model=settings.AGENT_LLM_MODEL,
        api_key=api_key,
        temperature=settings.AGENT_LLM_TEMPERATURE,
        timeout=settings.AGENT_LLM_TIMEOUT_SECONDS,
    )
