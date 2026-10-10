"""API endpoint tests for POST /api/v1/assistant/chat and provider error handling."""

import json
from decimal import Decimal
import httpx
import pytest

from app.assistant.adapters.openai_adapter import OpenAIAdapter
from app.assistant.factory import get_llm_provider
from app.assistant.provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
    ToolCallRequest,
    ToolDefinition,
)
from app.main import app


class MockApiProvider(LLMProvider):
    def __init__(self, mode: str = "success") -> None:
        self.mode = mode

    async def generate_response(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        if self.mode == "timeout":
            raise ProviderTimeoutError("Connection timed out waiting for OpenAI.")
        if self.mode == "error":
            raise ProviderError("Upstream OpenAI server returned 500.")
        if self.mode == "invalid_json":
            return LLMResponse(content="not valid json at all", tool_calls=[])
        if self.mode == "missing_key":
            raise ProviderAuthError("OpenAI API key is missing or not configured.")

        # Default success mode: check if calculating EMI
        # If user asked for EMI, simulate tool call on first turn, then result
        if any(m.role == "tool" for m in messages):
            # Second turn: provide grounded structured answer
            return LLMResponse(
                content=json.dumps({
                    "headline": "Monthly EMI: ₹10,623.52",
                    "message": "Your estimated EMI for ₹5,00,000 at 10% for 60 months is ₹10,623.52.",
                    "advantages": ["Standard fixed tenure"],
                    "risks": ["Processing fees may apply"],
                    "recommended_action": "Compare across 2-3 public lenders.",
                    "assumptions": ["Educational calculation."],
                    "needs_more_information": False,
                }),
                tool_calls=[],
            )
        else:
            # First turn: call calculate_emi
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCallRequest(
                        id="call_emi_api",
                        name="calculate_emi",
                        arguments_json=json.dumps({
                            "loan_amount": "500000.00",
                            "annual_interest_rate": "10.00",
                            "tenure_months": 60,
                        }),
                    )
                ],
            )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_assistant_chat_endpoint_success() -> None:
    mock_provider = MockApiProvider(mode="success")
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Calculate EMI for 5 lakhs at 10% for 5 years",
                    "loan_context": {
                        "loan_amount": 500000,
                        "annual_interest_rate": 10.0,
                        "tenure_months": 60,
                    },
                },
            )
        assert response.status_code == 200
        body = response.json()
        assert body["headline"] == "Monthly EMI: ₹10,623.52"
        assert body["tool_calls_used"] == ["calculate_emi"]
        assert body["needs_more_information"] is False
        assert len(body["advantages"]) > 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_assistant_chat_missing_api_key_returns_503() -> None:
    mock_provider = MockApiProvider(mode="missing_key")
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Calculate my EMI"},
            )
        assert response.status_code == 503
        assert "Missing or invalid API key" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_assistant_chat_provider_timeout_returns_504() -> None:
    mock_provider = MockApiProvider(mode="timeout")
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Calculate my EMI"},
            )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_assistant_chat_provider_error_returns_502() -> None:
    mock_provider = MockApiProvider(mode="error")
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Calculate my EMI"},
            )
        assert response.status_code == 502
        assert "AI Assistant provider error" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_assistant_chat_invalid_model_response_returns_502() -> None:
    mock_provider = MockApiProvider(mode="invalid_json")
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Calculate my EMI"},
            )
        assert response.status_code == 502
        assert "invalid or non-conforming response" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_assistant_chat_rejects_empty_message() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/chat",
            json={"message": ""},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_assistant_chat_rejects_oversized_message() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/chat",
            json={"message": "x" * 4001},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_openai_adapter_raises_auth_error_when_api_key_is_missing() -> None:
    adapter = OpenAIAdapter(api_key=None)
    with pytest.raises(ProviderAuthError):
        await adapter.generate_response([ChatMessage(role="user", content="hello")])

    empty_adapter = OpenAIAdapter(api_key="   ")
    with pytest.raises(ProviderAuthError):
        await empty_adapter.generate_response([ChatMessage(role="user", content="hello")])
