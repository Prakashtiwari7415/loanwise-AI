"""Tests for intent routing, multilingual handling, connection pooling, and latency metrics."""

from __future__ import annotations

import json
import time

import pytest

from app.assistant.adapters.openai_adapter import OpenAIAdapter, _CLIENT_POOL, clear_client_pool
from app.assistant.intent import LanguagePreference, QueryIntent, analyze_intent
from app.assistant.prompts import format_language_prompt
from app.assistant.provider import ChatMessage, LLMProvider, LLMResponse, ToolCallRequest
from app.assistant.schemas import AssistantChatRequest
from app.assistant.service import AssistantService


class MockInstrumentedProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.call_count = 0
        self.captured_messages: list[list[ChatMessage]] = []

    async def generate_response(self, messages: list[ChatMessage], tools=None) -> LLMResponse:
        self.call_count += 1
        self.captured_messages.append(messages)
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(content="{}", tool_calls=[])


def test_intent_routing_rate_inquiry() -> None:
    """Intent router correctly classifies rate queries."""
    r1 = analyze_intent("What are the latest personal-loan interest rates?")
    assert r1.is_rate_query
    assert r1.intent == QueryIntent.RATE_INQUIRY
    assert r1.loan_type == "personal"

    r2 = analyze_intent("Show me current car loan interest rates from SBI and HDFC")
    assert r2.is_rate_query
    assert r2.intent == QueryIntent.RATE_INQUIRY
    assert r2.loan_type == "car"


def test_intent_routing_calculations() -> None:
    """Intent router classifies calculation queries."""
    r1 = analyze_intent("Calculate EMI for 10 lakhs at 9.5% for 5 years")
    assert r1.intent == QueryIntent.CALCULATION
    assert r1.requires_financial_tools

    r2 = analyze_intent("What are my total monthly car expenses including EMI and fuel?")
    assert r2.intent == QueryIntent.CALCULATION
    assert r2.requires_financial_tools


def test_intent_routing_conceptual() -> None:
    """Intent router classifies conceptual/KFS queries."""
    r = analyze_intent("What is the RBI mandate on KFS cooling-off period?")
    assert r.intent == QueryIntent.CONCEPTUAL
    assert not r.requires_financial_tools


def test_intent_language_detection() -> None:
    """Intent router detects English, Hindi, and Hinglish preferences."""
    # English
    r_en = analyze_intent("What is reducing balance EMI?")
    assert r_en.language == LanguagePreference.ENGLISH

    # Hindi (Devanagari)
    r_hi_1 = analyze_intent("मुझे व्यक्तिगत ऋण की ब्याज दरों के बारे में हिंदी में बताइए")
    assert r_hi_1.language == LanguagePreference.HINDI

    # Hindi (keyword)
    r_hi_2 = analyze_intent("Explain personal loan rates in Hindi please")
    assert r_hi_2.language == LanguagePreference.HINDI

    # Hinglish
    r_hing = analyze_intent("EMI kitna hoga Hinglish mein samjhao")
    assert r_hing.language == LanguagePreference.HINGLISH

    r_hing_2 = analyze_intent("Personal loan interest rates kya chal rahe hain batao")
    assert r_hing_2.language == LanguagePreference.HINGLISH


def test_format_language_prompt_generates_correct_instructions() -> None:
    """format_language_prompt injects appropriate script and terminology guidance."""
    p_hi = format_language_prompt("hi")
    assert p_hi is not None
    assert "हिंदी" in p_hi
    assert "Devanagari" in p_hi

    p_hing = format_language_prompt("hinglish")
    assert p_hing is not None
    assert "Hinglish" in p_hing

    p_en = format_language_prompt("en")
    assert p_en is None


@pytest.mark.anyio
async def test_assistant_injects_language_instruction_for_hindi() -> None:
    """Assistant includes language prompt in messages when Hindi is detected."""
    final_json = {
        "headline": "व्यक्तिगत ऋण ब्याज दरें",
        "message": "एसबीआई और एचडीएफसी बैंक की ब्याज दरें 10.30% से शुरू होती हैं।",
        "advantages": ["कम ब्याज दर"],
        "risks": ["क्रेडिट स्कोर पर निर्भर"],
        "recommended_action": "अपना सिबिल स्कोर जांचें।",
        "assumptions": ["प्रारंभिक दरें 750+ सिबिल स्कोर के लिए हैं।"],
        "needs_more_information": False,
        "sources": [],
    }

    provider = MockInstrumentedProvider([
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])

    service = AssistantService(provider=provider)
    request = AssistantChatRequest(message="ऋण के बारे में हिंदी में बताइए")
    response = await service.chat(request)

    assert response.headline == "व्यक्तिगत ऋण ब्याज दरें"
    # Verify language instruction was injected into system messages
    first_turn_messages = provider.captured_messages[0]
    has_lang_instruction = any(
        "हिंदी" in (m.content or "") for m in first_turn_messages if m.role == "system"
    )
    assert has_lang_instruction


@pytest.mark.anyio
async def test_latency_timings_recorded_in_response() -> None:
    """Assistant chat response includes non-negative stage timing metrics."""
    final_json = {
        "headline": "Loan Advice",
        "message": "Your loan advice.",
        "advantages": [],
        "risks": [],
        "recommended_action": "Review.",
        "assumptions": [],
        "needs_more_information": False,
        "sources": [],
    }

    provider = MockInstrumentedProvider([
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])

    service = AssistantService(provider=provider)
    request = AssistantChatRequest(message="What is the difference between flat and reducing rate?")
    response = await service.chat(request)

    assert response.timings is not None
    assert "validation_ms" in response.timings
    assert "retrieval_ms" in response.timings
    assert "model_call_ms" in response.timings
    assert "total_server_time_ms" in response.timings
    assert response.timings["total_server_time_ms"] >= 0


def test_openai_adapter_connection_pool_reuses_client() -> None:
    """OpenAIAdapter reuses cached AsyncOpenAI client instance for identical configuration."""
    clear_client_pool()

    adapter1 = OpenAIAdapter(api_key="sk-test-key-12345", base_url=None, timeout=30.0)
    client1 = adapter1._get_client()

    adapter2 = OpenAIAdapter(api_key="sk-test-key-12345", base_url=None, timeout=30.0)
    client2 = adapter2._get_client()

    assert client1 is client2
    assert len(_CLIENT_POOL) == 1

    # Different key gets a different client
    adapter3 = OpenAIAdapter(api_key="sk-test-different-key", base_url=None, timeout=30.0)
    client3 = adapter3._get_client()
    assert client3 is not client1
    assert len(_CLIENT_POOL) == 2
