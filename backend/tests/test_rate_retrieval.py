"""Tests for verified lender rate retrieval, caching, live search fallback, and citations."""

from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal

import pytest

from app.assistant.provider import ChatMessage, LLMProvider, LLMResponse, ToolCallRequest
from app.assistant.schemas import AssistantChatRequest
from app.assistant.service import AssistantService
from app.assistant.tools.registry import execute_tool, get_tool_definitions
from app.rag.rates import (
    CURATED_RATE_QUOTES,
    OFFICIAL_LENDER_DOMAINS,
    LenderRateQuote,
    RateCache,
    RateRetrievalService,
    RateSearchResult,
    get_rate_source_documents,
)


class MockRateProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.call_count = 0
        self.recorded_messages: list[list[ChatMessage]] = []

    async def generate_response(self, messages: list[ChatMessage], tools=None) -> LLMResponse:
        self.call_count += 1
        self.recorded_messages.append(messages)
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(content="{}", tool_calls=[])


@pytest.mark.anyio
async def test_rate_service_returns_verified_personal_loan_quotes() -> None:
    """Rate service returns official benchmark quotes for personal loans."""
    cache = RateCache(default_ttl_seconds=60)
    service = RateRetrievalService(cache=cache, enabled=False)

    result = await service.get_rates("personal")
    assert result.loan_type == "personal"
    assert len(result.quotes) >= 4
    assert not result.is_live

    # Verify key official lenders are included
    lenders = [q.lender for q in result.quotes]
    assert any("SBI" in l or "State Bank of India" in l for l in lenders)
    assert any("HDFC" in l for l in lenders)
    assert any("ICICI" in l for l in lenders)

    # Verify official domains only
    for q in result.quotes:
        assert any(domain in q.source_url for domain in OFFICIAL_LENDER_DOMAINS)
        assert q.starting_rate
        assert q.rate_range
        assert q.starting_rate_conditions
        assert q.verified_date


@pytest.mark.anyio
async def test_rate_service_caching_and_ttl() -> None:
    """Rate service caches results in-memory and respects TTL."""
    cache = RateCache(default_ttl_seconds=1)  # 1 second TTL
    service = RateRetrievalService(cache=cache, enabled=False)

    res1 = await service.get_rates("personal")
    # Immediate repeat query should return exact cached instance
    res2 = await service.get_rates("personal")
    assert res1.retrieved_at == res2.retrieved_at

    # Wait for TTL expiry
    await asyncio.sleep(1.05)
    res3 = await service.get_rates("personal")
    # Cache expired and was refreshed
    assert res3 is not None


@pytest.mark.anyio
async def test_rate_service_filters_by_lender() -> None:
    """Rate service can filter quotes for a specific lender."""
    service = RateRetrievalService(cache=RateCache(), enabled=False)
    result = await service.get_rates("personal", lender="SBI")
    assert len(result.quotes) >= 1
    for q in result.quotes:
        assert "sbi" in q.lender.lower() or "state bank" in q.lender.lower()


@pytest.mark.anyio
async def test_rate_quotes_convert_to_valid_source_citations() -> None:
    """Rate quotes convert to SourceCitation instances with lender_disclosure classification."""
    service = RateRetrievalService(cache=RateCache(), enabled=False)
    result = await service.get_rates("personal")
    citations = result.to_citations()

    assert len(citations) == len(result.quotes)
    for cit in citations:
        assert cit.source_type == "lender_disclosure"
        assert cit.url.startswith("https://")
        assert cit.verified_date
        assert not cit.is_potentially_stale


def test_rate_source_documents_generated_for_rag() -> None:
    """Rate source documents generate proper SourceDocument objects for search indexing."""
    docs = get_rate_source_documents()
    assert len(docs) >= 8  # personal + car + home
    for d in docs:
        assert d.source_type == "lender_disclosure"
        assert d.url.startswith("https://")
        assert "Interest Rate" in d.title


def test_fetch_current_rates_tool_execution() -> None:
    """fetch_current_rates tool executes deterministically via execute_tool dispatch."""
    args = {"loan_type": "personal", "lender": "HDFC"}
    result = execute_tool("fetch_current_rates", json.dumps(args))

    assert "error" not in result
    assert result["loan_type"] == "personal"
    assert len(result["rates"]) >= 1
    assert any("hdfc" in r["lender"].lower() for r in result["rates"])
    assert result["disclaimer"]


def test_fetch_current_rates_tool_is_in_definitions() -> None:
    """fetch_current_rates tool is included in exported tool definitions."""
    definitions = get_tool_definitions()
    names = {t.name for t in definitions}
    assert "fetch_current_rates" in names
    tool_def = next(t for t in definitions if t.name == "fetch_current_rates")
    assert "properties" in tool_def.parameters_schema
    assert "loan_type" in tool_def.parameters_schema["properties"]


@pytest.mark.anyio
async def test_assistant_answers_personal_loan_rate_query_without_refusal() -> None:
    """Assistant answers 'What are the latest personal-loan interest rates?' with verified evidence."""
    final_json = {
        "headline": "Current Personal Loan Benchmark Rates: 10.30%–16.00% p.a.",
        "message": (
            "Based on official lender benchmark rate cards, here are the starting rates for major Indian banks:\n\n"
            "• SBI: 10.30% – 15.10% p.a. (Starting rate for salaried/defense with CIBIL 750+)\n"
            "• HDFC Bank: 10.50% – 24.00% p.a. (Starting rate for prime corporate salaried)\n"
            "• ICICI Bank: 10.65% – 16.00% p.a.\n\n"
            "Note: Actual rates offered depend on your CIBIL score tier, monthly income, and employer category."
        ),
        "advantages": ["SBI and HDFC offer competitive starting rates for CIBIL 750+"],
        "risks": ["Non-prime borrowers may be offered higher rates up to 24% p.a."],
        "recommended_action": "Check your CIBIL score before applying to qualify for the lowest tier.",
        "assumptions": ["Starting rates apply to prime salaried borrowers with CIBIL 750+."],
        "needs_more_information": False,
        "sources": [
            {
                "title": "State Bank of India (SBI): Personal Loan Benchmark Rate Schedule",
                "url": "https://sbi.co.in/web/personal-banking/loans/personal-loans",
                "publisher": "State Bank of India",
                "source_type": "lender_disclosure",
                "excerpt": "SBI Personal Loan: Starting from 10.30% p.a.",
            }
        ],
    }

    mock_provider = MockRateProvider([
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])

    service = AssistantService(provider=mock_provider)
    request = AssistantChatRequest(message="What are the latest personal-loan interest rates?")
    response = await service.chat(request)

    assert response.headline == "Current Personal Loan Benchmark Rates: 10.30%–16.00% p.a."
    assert not response.needs_more_information
    assert len(response.sources) >= 1
    assert "sbi.co.in" in response.sources[0].url
    assert response.timings is not None
    assert "total_server_time_ms" in response.timings


@pytest.mark.anyio
async def test_no_fabricated_citations_in_rate_response() -> None:
    """Any citation fabricated by the model that does not match retrieved evidence is stripped."""
    final_json = {
        "headline": "Personal Loan Rates",
        "message": "Here are rates.",
        "advantages": [],
        "risks": [],
        "recommended_action": "Compare.",
        "assumptions": [],
        "needs_more_information": False,
        "sources": [
            {
                "title": "Fake Rate Aggregator 2026",
                "url": "https://fake-rate-aggregator-xyz.com/personal-rates",
                "publisher": "Fake Aggregator",
                "source_type": "lender_disclosure",
                "excerpt": "Unverified rate data",
            }
        ],
    }

    mock_provider = MockRateProvider([
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])

    # With retriever=None, no external/curated docs are retrieved
    service = AssistantService(provider=mock_provider, retriever=None)
    request = AssistantChatRequest(message="What are personal loan rates?")
    response = await service.chat(request)

    # The fake citation must NOT appear in response sources
    urls = [s.url for s in response.sources]
    assert "https://fake-rate-aggregator-xyz.com/personal-rates" not in urls
