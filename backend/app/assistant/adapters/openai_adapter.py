"""OpenAI provider adapter using native tool calling."""

from __future__ import annotations

import logging
from typing import Any

import openai
from openai import AsyncOpenAI

from app.assistant.provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderQuotaError,
    ProviderTimeoutError,
    ToolCallRequest,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


_CLIENT_POOL: dict[tuple[str, str | None, float], AsyncOpenAI] = {}


def clear_client_pool() -> None:
    """Clear cached AsyncOpenAI client instances (used for testing)."""
    _CLIENT_POOL.clear()


class OpenAIAdapter(LLMProvider):
    """Adapter for OpenAI-compatible models (including Google Gemini) implementing LLMProvider."""

    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        base_url: str | None = None,
        provider_name: str = "openai",
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url
        self.provider_name = provider_name.lower()
        if self.provider_name == "gemini" and model in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"):
            self.model = "gemini-2.5-flash"
        else:
            self.model = model
        self._client: AsyncOpenAI | None = None

    @property
    def provider_label(self) -> str:
        return "Gemini" if self.provider_name == "gemini" else "OpenAI"

    def _get_client(self) -> AsyncOpenAI:
        if not self.api_key or not self.api_key.strip():
            key_hint = "GEMINI_API_KEY or LLM_API_KEY" if self.provider_name == "gemini" else "OPENAI_API_KEY or LLM_API_KEY"
            raise ProviderAuthError(f"{self.provider_label} API key is missing or not configured. Set {key_hint}.")
        if self._client is None:
            cache_key = (self.api_key, self.base_url, self.timeout)
            if cache_key not in _CLIENT_POOL:
                _CLIENT_POOL[cache_key] = AsyncOpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    base_url=self.base_url,
                )
            self._client = _CLIENT_POOL[cache_key]
        return self._client


    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                converted.append({"role": "system", "content": msg.content or ""})
            elif msg.role == "user":
                converted.append({"role": "user", "content": msg.content or ""})
            elif msg.role == "assistant":
                item: dict[str, Any] = {"role": "assistant"}
                if msg.content is not None:
                    item["content"] = msg.content
                if msg.tool_calls:
                    item["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments_json,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                converted.append(item)
            elif msg.role == "tool":
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id or "",
                        "content": msg.content or "",
                    }
                )
            else:
                converted.append({"role": msg.role, "content": msg.content or ""})
        return converted

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            for tool in tools
        ]

    async def generate_response(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        formatted_messages = self._convert_messages(messages)
        formatted_tools = self._convert_tools(tools)

        params: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }
        if formatted_tools:
            params["tools"] = formatted_tools
        else:
            params["response_format"] = {"type": "json_object"}

        label = self.provider_label
        try:
            response = await client.chat.completions.create(**params)
        except openai.AuthenticationError as exc:
            logger.error("Authentication error calling %s API: %s", label, exc)
            raise ProviderAuthError(f"{label} authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            logger.error("Rate limit / quota error calling %s API: %s", label, exc)
            raise ProviderQuotaError(f"{label} quota exhausted or rate limit reached: {exc}") from exc
        except openai.NotFoundError as exc:
            logger.error("Model not found calling %s API: %s", label, exc)
            raise ProviderError(f"{label} model '{self.model}' not found or unavailable: {exc}") from exc
        except openai.APITimeoutError as exc:
            logger.error("Timeout error calling %s API: %s", label, exc)
            raise ProviderTimeoutError(f"{label} request timed out: {exc}") from exc
        except openai.APIConnectionError as exc:
            logger.error("Connection error calling %s API: %s", label, exc)
            raise ProviderError(f"{label} connection error: {exc}") from exc
        except openai.APIError as exc:
            logger.error("%s API error: %s", label, exc)
            raise ProviderError(f"{label} API returned error: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error calling %s API: %s", label, exc)
            raise ProviderError(f"Unexpected provider error from {label}: {exc}") from exc

        if not response.choices:
            raise ProviderInvalidResponseError(f"{label} returned no choices.")


        choice = response.choices[0]
        tool_calls: list[ToolCallRequest] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCallRequest(
                        id=tc.id,
                        name=tc.function.name,
                        arguments_json=tc.function.arguments,
                    )
                )

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )
