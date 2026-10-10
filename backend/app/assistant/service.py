"""Orchestration service for the AI assistant and tool calling loop."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.assistant.prompts import SYSTEM_PROMPT, format_loan_context_prompt
from app.assistant.provider import (
    ChatMessage,
    LLMProvider,
    ProviderInvalidResponseError,
    ToolDefinition,
)
from app.assistant.schemas import AssistantChatRequest, AssistantChatResponse
from app.assistant.tools.registry import execute_tool, get_tool_definitions

logger = logging.getLogger(__name__)


class AssistantService:
    """Orchestrates conversations, tool calling, and structured response extraction."""

    def __init__(
        self,
        provider: LLMProvider,
        max_turns: int = 5,
        max_tool_calls: int = 5,
    ) -> None:
        self.provider = provider
        self.max_turns = max_turns
        self.max_tool_calls = max_tool_calls

    async def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        """Run the bounded agent orchestration loop and return a validated structured response."""
        # 1. Prepare initial conversation history
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=SYSTEM_PROMPT)
        ]
        context_prompt = format_loan_context_prompt(request.loan_context)
        if context_prompt:
            messages.append(ChatMessage(role="system", content=context_prompt))

        messages.append(ChatMessage(role="user", content=request.message))

        tool_defs: list[ToolDefinition] | None = get_tool_definitions()
        executed_tools: list[str] = []
        total_tool_calls = 0

        # 2. Agent orchestration loop
        for _ in range(self.max_turns):
            response = await self.provider.generate_response(messages, tools=tool_defs)

            # If no tool calls were requested, parse final structured output
            if not response.tool_calls:
                return self._parse_structured_response(response.content, executed_tools)

            # Record assistant turn with requested tool calls
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute requested tool calls with strict limit bounds
            for tc in response.tool_calls:
                if total_tool_calls >= self.max_tool_calls:
                    logger.warning("Tool call limit of %d reached; skipping tool %s", self.max_tool_calls, tc.name)
                    messages.append(
                        ChatMessage(
                            role="tool",
                            tool_call_id=tc.id,
                            name=tc.name,
                            content=json.dumps({"error": f"Tool execution limit of {self.max_tool_calls} calls exceeded."}),
                        )
                    )
                    continue

                total_tool_calls += 1
                result = execute_tool(tc.name, tc.arguments_json)
                if "error" not in result:
                    executed_tools.append(tc.name)

                messages.append(
                    ChatMessage(
                        role="tool",
                        tool_call_id=tc.id,
                        name=tc.name,
                        content=json.dumps(result),
                    )
                )

            # When limit is reached, disable tools on subsequent turns to force final output
            if total_tool_calls >= self.max_tool_calls:
                tool_defs = None

        # If turn limit reached without final text, request one final turn without tools
        final_response = await self.provider.generate_response(messages, tools=None)
        return self._parse_structured_response(final_response.content, executed_tools)

    def _extract_json_string(self, text: str) -> str:
        """Strip markdown code fences or extract the first JSON object."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Look for outer matching braces if extra text is present
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            return match.group(1).strip()
        return cleaned

    def _parse_structured_response(
        self, content: str | None, executed_tools: list[str]
    ) -> AssistantChatResponse:
        """Parse and strictly validate the structured JSON response."""
        if not content or not content.strip():
            raise ProviderInvalidResponseError("Provider returned an empty response.")

        json_str = self._extract_json_string(content)
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ProviderInvalidResponseError("Provider response is not a valid JSON dictionary.")

            # Ground tool calls: ensure recorded tool calls match deterministic engine invocations
            parsed["tool_calls_used"] = list(dict.fromkeys(executed_tools))

            return AssistantChatResponse.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Failed to parse structured model response: %s (content: %s)", exc, content)
            raise ProviderInvalidResponseError(
                f"Invalid or non-conforming structured response from assistant: {exc}"
            ) from exc
