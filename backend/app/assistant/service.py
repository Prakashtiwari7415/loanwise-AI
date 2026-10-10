"""Orchestration service for the AI assistant and tool calling loop."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.assistant.prompts import (
    SYSTEM_PROMPT,
    format_loan_context_prompt,
    format_rag_evidence_prompt,
)
from app.assistant.provider import (
    ChatMessage,
    LLMProvider,
    ProviderInvalidResponseError,
    ToolDefinition,
)
from app.assistant.schemas import AssistantChatRequest, AssistantChatResponse
from app.assistant.tools.registry import execute_tool, get_tool_definitions
from app.rag import KnowledgeRetriever, RetrievalResult, SourceCitation, get_default_retriever, to_citation

logger = logging.getLogger(__name__)


class AssistantService:
    """Orchestrates conversations, tool calling, grounded RAG evidence, and structured response extraction."""

    def __init__(
        self,
        provider: LLMProvider,
        retriever: KnowledgeRetriever | None = None,
        max_turns: int = 5,
        max_tool_calls: int = 5,
    ) -> None:
        self.provider = provider
        self.retriever = retriever if retriever is not None else get_default_retriever()
        self.max_turns = max_turns
        self.max_tool_calls = max_tool_calls

    async def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        """Run the bounded agent orchestration loop and return a validated structured response."""
        # 1. Retrieve grounded knowledge evidence
        retrieval_results: list[RetrievalResult] = []
        if self.retriever:
            retrieval_results = self.retriever.retrieve(request.message, top_k=3)

        # 2. Prepare initial conversation history
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=SYSTEM_PROMPT)
        ]

        # Inject grounded RAG evidence
        evidence_prompt = format_rag_evidence_prompt(retrieval_results)
        messages.append(ChatMessage(role="system", content=evidence_prompt))

        context_prompt = format_loan_context_prompt(request.loan_context)
        if context_prompt:
            messages.append(ChatMessage(role="system", content=context_prompt))

        messages.append(ChatMessage(role="user", content=request.message))

        tool_defs: list[ToolDefinition] | None = get_tool_definitions()
        executed_tools: list[str] = []
        total_tool_calls = 0

        # 3. Agent orchestration loop
        for turn_idx in range(self.max_turns):
            response = await self.provider.generate_response(messages, tools=tool_defs)

            # If no tool calls were requested, parse final structured output
            if not response.tool_calls:
                # If content already has a JSON structure, parse directly
                if response.content and "{" in response.content:
                    return self._parse_structured_response(response.content, executed_tools, retrieval_results)

                # If tools were active, model replied in prose, and turns remain,
                # do a quick formatting turn without tools to engage response_format=json_object
                if (
                    tool_defs is not None
                    and response.content
                    and "chatbot" not in response.content.lower()
                    and turn_idx + 1 < self.max_turns
                ):
                    messages.append(ChatMessage(role="assistant", content=response.content))
                    messages.append(
                        ChatMessage(
                            role="user",
                            content=(
                                "Format your response strictly as a single JSON object with schema: "
                                "headline, message, advantages, risks, recommended_action, assumptions, "
                                "needs_more_information, sources. Do not output text outside the JSON object."
                            ),
                        )
                    )
                    tool_defs = None
                    continue

                return self._parse_structured_response(response.content, executed_tools, retrieval_results)

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

            # Prompt model for final structured JSON synthesis after tool results
            messages.append(
                ChatMessage(
                    role="system",
                    content=(
                        "Tool execution completed. Output your final answer strictly as a single valid JSON object "
                        "with fields: headline, message, advantages, risks, recommended_action, assumptions, "
                        "needs_more_information, sources. Do not output text outside the JSON object."
                    ),
                )
            )
            tool_defs = None

        # If turn limit reached without final text, request one final turn without tools
        final_response = await self.provider.generate_response(messages, tools=None)
        return self._parse_structured_response(final_response.content, executed_tools, retrieval_results)

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
        self,
        content: str | None,
        executed_tools: list[str],
        retrieval_results: list[RetrievalResult] | None = None,
    ) -> AssistantChatResponse:
        """Parse and strictly validate the structured JSON response with grounded tool calls and citations."""
        if not content or not content.strip():
            raise ProviderInvalidResponseError("Provider returned an empty response.")

        json_str = self._extract_json_string(content)
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ProviderInvalidResponseError("Provider response is not a valid JSON dictionary.")

            # Ground tool calls: ensure recorded tool calls match deterministic engine invocations
            parsed["tool_calls_used"] = list(dict.fromkeys(executed_tools))

            # Ground sources and citations against actually retrieved evidence
            retrieved = retrieval_results or []
            verified_by_title: dict[str, SourceCitation] = {
                r.chunk.title.strip().lower(): to_citation(r) for r in retrieved
            }
            verified_by_url: dict[str, SourceCitation] = {
                r.chunk.url.strip().lower(): to_citation(r)
                for r in retrieved
                if r.chunk.url
            }

            model_sources = parsed.get("sources")
            grounded_sources: list[dict[str, Any]] = []

            if isinstance(model_sources, list) and model_sources:
                for item in model_sources:
                    if isinstance(item, dict):
                        title_key = str(item.get("title", "")).strip().lower()
                        url_key = str(item.get("url", "")).strip().lower()
                        matched_cit = verified_by_title.get(title_key) or verified_by_url.get(url_key)
                        if matched_cit:
                            cit_data = matched_cit.model_dump()
                            if item.get("excerpt"):
                                cit_data["excerpt"] = str(item["excerpt"])[:300]
                            grounded_sources.append(cit_data)
                        elif not retrieved:
                            logger.warning("Rejected hallucinated citation without evidence: %s", item.get("title"))

            # If model didn't return matching citation dicts but reliable evidence was retrieved,
            # attach the unique verified citations from the retrieved evidence
            if not grounded_sources and retrieved:
                seen_titles: set[str] = set()
                for r in retrieved:
                    cit = to_citation(r)
                    if cit.title not in seen_titles:
                        seen_titles.add(cit.title)
                        grounded_sources.append(cit.model_dump())

            parsed["sources"] = grounded_sources

            # Defensive normalization for model schema variations
            if isinstance(parsed.get("recommended_action"), list):
                parsed["recommended_action"] = " ".join(str(item) for item in parsed["recommended_action"])

            for list_field in ("advantages", "risks", "assumptions"):
                if isinstance(parsed.get(list_field), str):
                    parsed[list_field] = [parsed[list_field]]
                elif not isinstance(parsed.get(list_field), list):
                    parsed[list_field] = []

            nmi = parsed.get("needs_more_information")
            if isinstance(nmi, str):
                parsed["needs_more_information"] = nmi.strip().lower() in ("true", "yes", "1")
            elif not isinstance(nmi, bool):
                parsed["needs_more_information"] = bool(nmi)

            return AssistantChatResponse.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Failed to parse structured model response: %s (content: %s)", exc, content)
            raise ProviderInvalidResponseError(
                f"Invalid or non-conforming structured response from assistant: {exc}"
            ) from exc
