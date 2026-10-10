"""Unit and integration tests for AssistantService orchestration, tool bounds, and structured responses."""

import json
from decimal import Decimal
import pytest

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
from app.assistant.schemas import AssistantChatRequest, AssistantChatResponse, LoanContext
from app.assistant.service import AssistantService


class MockLLMProvider(LLMProvider):
    """Mock LLM provider returning predefined responses based on turn count or message inspection."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.call_count = 0
        self.received_messages: list[list[ChatMessage]] = []
        self.received_tools: list[list[ToolDefinition] | None] = []

    async def generate_response(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        self.received_messages.append(list(messages))
        self.received_tools.append(tools)
        if self.call_count >= len(self.responses):
            raise RuntimeError("MockLLMProvider ran out of configured responses.")
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


@pytest.mark.anyio
async def test_assistant_service_executes_tool_and_returns_grounded_response() -> None:
    # Turn 1: Model requests calculate_emi tool
    tool_call = ToolCallRequest(
        id="call_emi_1",
        name="calculate_emi",
        arguments_json=json.dumps({
            "loan_amount": "800000.00",
            "annual_interest_rate": "8.50",
            "tenure_months": 60,
        }),
    )
    turn_1 = LLMResponse(content=None, tool_calls=[tool_call])

    # Turn 2: Model returns structured JSON with grounded numbers
    final_json = {
        "headline": "Estimated Monthly EMI is ₹16,413.23",
        "message": "For a ₹8,00,000 loan at 8.5% over 5 years, your monthly EMI is ₹16,413.23 with total interest of ₹184,793.43.",
        "advantages": ["Consistent reducing-balance repayment schedule", "Moderate 5-year tenure"],
        "risks": ["Interest rate rises if opting for a floating rate later"],
        "recommended_action": "Check whether lenders offer zero processing fee promotions.",
        "assumptions": ["Educational estimate; processing fees assumed zero unless provided."],
        "needs_more_information": False,
    }
    turn_2 = LLMResponse(content=json.dumps(final_json), tool_calls=[])

    mock_provider = MockLLMProvider([turn_1, turn_2])
    service = AssistantService(provider=mock_provider, max_turns=5, max_tool_calls=5)

    request = AssistantChatRequest(message="What is the EMI for 8 lakhs at 8.5% for 5 years?")
    response = await service.chat(request)

    assert isinstance(response, AssistantChatResponse)
    assert response.headline == "Estimated Monthly EMI is ₹16,413.23"
    assert response.tool_calls_used == ["calculate_emi"]
    assert response.needs_more_information is False
    assert mock_provider.call_count == 2

    # Check that tool execution result was returned to provider in turn 2 messages
    turn_2_messages = mock_provider.received_messages[1]
    tool_response_msg = [m for m in turn_2_messages if m.role == "tool"][0]
    tool_data = json.loads(tool_response_msg.content)
    assert tool_data["emi"] == "16413.23"
    assert tool_data["total_interest"] == "184793.43"


@pytest.mark.anyio
async def test_assistant_service_handles_missing_user_inputs() -> None:
    # Model detects missing inputs and asks for loan amount, rate, tenure
    clarification_json = {
        "headline": "Loan Details Needed",
        "message": "To calculate your EMI, please share the loan amount, interest rate, and tenure.",
        "advantages": [],
        "risks": [],
        "recommended_action": "Provide your preferred loan amount and tenure.",
        "assumptions": ["No parameters provided."],
        "needs_more_information": True,
    }
    resp = LLMResponse(content=json.dumps(clarification_json), tool_calls=[])
    mock_provider = MockLLMProvider([resp])
    service = AssistantService(provider=mock_provider)

    request = AssistantChatRequest(message="Can you calculate my EMI?")
    response = await service.chat(request)

    assert response.needs_more_information is True
    assert response.tool_calls_used == []
    assert mock_provider.call_count == 1


@pytest.mark.anyio
async def test_assistant_service_incorporates_loan_context() -> None:
    # When loan context is passed, verify it is injected into the prompt
    final_json = {
        "headline": "Affordability Analysis",
        "message": "Based on your ₹1,00,000 income, the loan appears manageable.",
        "advantages": ["Manageable debt ratio"],
        "risks": ["Limited buffer for additional debt"],
        "recommended_action": "Maintain an emergency fund before taking the loan.",
        "assumptions": ["Educational affordability heuristic."],
        "needs_more_information": False,
    }
    resp = LLMResponse(content=json.dumps(final_json), tool_calls=[])
    mock_provider = MockLLMProvider([resp])
    service = AssistantService(provider=mock_provider)

    context = LoanContext(
        loan_amount=Decimal("500000"),
        annual_interest_rate=Decimal("9.0"),
        tenure_months=36,
        monthly_income=Decimal("100000"),
    )
    request = AssistantChatRequest(message="Can I afford this loan?", loan_context=context)
    response = await service.chat(request)

    assert response.needs_more_information is False
    # Check that context prompt was included in messages
    first_messages = mock_provider.received_messages[0]
    context_msgs = [m for m in first_messages if "ACTIVE LOAN CONTEXT" in (m.content or "")]
    assert len(context_msgs) == 1
    assert "500000" in context_msgs[0].content


@pytest.mark.anyio
async def test_assistant_service_enforces_tool_call_limits() -> None:
    # Model attempts infinite tool calling by continuously requesting tools
    infinite_tool_call = ToolCallRequest(
        id="loop_call",
        name="calculate_emi",
        arguments_json=json.dumps({"loan_amount": "500000", "annual_interest_rate": "9.0", "tenure_months": 36}),
    )

    final_json = {
        "headline": "Calculation Completed",
        "message": "Final calculation reached.",
        "advantages": [],
        "risks": [],
        "recommended_action": "Proceed with caution.",
        "assumptions": [],
        "needs_more_information": False,
    }

    # Responses: 3 tool call turns, then final response
    responses = [
        LLMResponse(content=None, tool_calls=[infinite_tool_call]),
        LLMResponse(content=None, tool_calls=[infinite_tool_call]),
        LLMResponse(content=None, tool_calls=[infinite_tool_call]),
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ]

    mock_provider = MockLLMProvider(responses)
    # Set max_tool_calls to 2
    service = AssistantService(provider=mock_provider, max_turns=5, max_tool_calls=2)

    request = AssistantChatRequest(message="Calculate repeatedly")
    response = await service.chat(request)

    assert response.headline == "Calculation Completed"
    # Even though model requested 3 calls, only 2 were executed
    assert len(response.tool_calls_used) <= 2


@pytest.mark.anyio
async def test_assistant_service_raises_on_invalid_model_output() -> None:
    # Model returns non-JSON garbage
    invalid_resp = LLMResponse(content="I am just a chatbot, here is some plain text without valid schema.", tool_calls=[])
    mock_provider = MockLLMProvider([invalid_resp])
    service = AssistantService(provider=mock_provider)

    request = AssistantChatRequest(message="Calculate EMI")
    with pytest.raises(ProviderInvalidResponseError):
        await service.chat(request)


@pytest.mark.anyio
async def test_assistant_service_raises_on_empty_content() -> None:
    empty_resp = LLMResponse(content="", tool_calls=[])
    mock_provider = MockLLMProvider([empty_resp])
    service = AssistantService(provider=mock_provider)

    request = AssistantChatRequest(message="Hello")
    with pytest.raises(ProviderInvalidResponseError):
        await service.chat(request)
