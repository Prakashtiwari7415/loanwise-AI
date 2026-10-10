"""Environment-backed configuration without embedding deployment secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str | None
    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    llm_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: float = 30.0
    llm_max_tool_calls: int = 5
    llm_max_turns: int = 5
    llm_max_input_length: int = 4000
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    env_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not env_provider:
        if os.getenv("OPENAI_API_KEY") and not (os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")):
            provider = "openai"
        else:
            provider = "gemini"
    else:
        provider = env_provider

    gemini_base_url = (
        os.getenv("GEMINI_BASE_URL", "").strip()
        or "https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    if provider == "gemini":
        api_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        default_model = "gemini-1.5-flash"
    else:
        api_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        default_model = "gpt-4o-mini"

    model = os.getenv("LLM_MODEL", "").strip() or default_model

    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    except ValueError:
        timeout = 30.0
    try:
        max_tool_calls = int(os.getenv("LLM_MAX_TOOL_CALLS", "5"))
    except ValueError:
        max_tool_calls = 5
    try:
        max_turns = int(os.getenv("LLM_MAX_TURNS", "5"))
    except ValueError:
        max_turns = 5
    try:
        max_input_length = int(os.getenv("LLM_MAX_INPUT_LENGTH", "4000"))
    except ValueError:
        max_input_length = 4000

    return Settings(
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=database_url or None,
        llm_provider=provider,
        llm_api_key=api_key or None,
        llm_model=model,
        llm_timeout_seconds=timeout,
        llm_max_tool_calls=max_tool_calls,
        llm_max_turns=max_turns,
        llm_max_input_length=max_input_length,
        gemini_base_url=gemini_base_url,
    )

