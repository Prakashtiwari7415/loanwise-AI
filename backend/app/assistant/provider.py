"""Provider-independent abstraction for LLM interactions and tool calling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    """Base exception for provider communication and execution failures."""


class ProviderAuthError(ProviderError):
    """Exception raised when API authentication credentials are missing or invalid."""


class ProviderTimeoutError(ProviderError):
    """Exception raised when an LLM provider request times out."""


class ProviderInvalidResponseError(ProviderError):
    """Exception raised when an LLM provider returns an unparseable or invalid response."""


@dataclass(frozen=True)
class ToolCallRequest:
    """Represents a validated tool call requested by the LLM."""
    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ToolDefinition:
    """Definition of an allowlisted tool exposed to the provider."""
    name: str
    description: str
    parameters_schema: dict[str, Any]


@dataclass
class ChatMessage:
    """A single turn in the LLM conversation history."""
    role: str
    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    """Standardized response from an LLM provider adapter."""
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str | None = None


class LLMProvider(ABC):
    """Abstract interface for LLM provider adapters."""

    @abstractmethod
    async def generate_response(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Send messages and optional tool definitions to the LLM and return a response."""
