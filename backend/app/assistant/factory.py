"""Factory and dependency injection for assistant components."""

from __future__ import annotations

from fastapi import Depends

from app.assistant.adapters.openai_adapter import OpenAIAdapter
from app.assistant.provider import LLMProvider, ProviderAuthError
from app.assistant.service import AssistantService
from app.core.config import Settings, get_settings


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    """Instantiate the configured LLM provider adapter."""
    provider_name = settings.llm_provider.lower()
    if provider_name == "gemini":
        return OpenAIAdapter(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            base_url=settings.gemini_base_url,
            provider_name="gemini",
        )
    if provider_name == "openai":
        return OpenAIAdapter(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            base_url=None,
            provider_name="openai",
        )
    raise ProviderAuthError(f"Unsupported LLM provider: '{settings.llm_provider}'")



from app.rag import get_default_retriever


def get_assistant_service(
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AssistantService:
    """Instantiate AssistantService with configured operational bounds and knowledge retriever."""
    return AssistantService(
        provider=provider,
        retriever=get_default_retriever(),
        max_turns=settings.llm_max_turns,
        max_tool_calls=settings.llm_max_tool_calls,
    )
