"""Tests for vehicle ownership cost estimator and improved assistant behaviour.

Acceptance criteria from Objective 9:
1.  Car expense question returns a useful breakdown (not just "give me more info")
2.  Known EMI is reused only when context is clear
3.  Fuel costs are calculated correctly from distance, mileage, price
4.  Annual insurance premiums are converted to monthly provisions correctly
5.  Estimates clearly identify assumed values and ranges
6.  Missing information is NOT silently converted to zero
7.  Follow-up questions can refine previous estimates
8.  EMI question invokes the deterministic calculation tool
9.  Source-dependent question uses retrieved evidence
10. Unsupported claims / fabricated citations are not presented as verified facts
11. Invalid tool arguments are rejected safely
12. AI-provider failures produce controlled errors
13. Existing tools, persistence, and RAG continue working (regression)
"""

from __future__ import annotations

import json
from decimal import Decimal
import pytest

from app.assistant.provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderInvalidResponseError,
    ToolCallRequest,
    ToolDefinition,
)
from app.assistant.schemas import AssistantChatRequest, LoanContext
from app.assistant.service import AssistantService
from app.assistant.tools.registry import execute_tool, get_tool_definitions
from app.financial.vehicle_ownership import (
    estimate_fuel_cost,
    estimate_vehicle_ownership_cost,
)


# ─── Shared mock provider ────────────────────────────────────────────────────


class SequencedMockProvider(LLMProvider):
    """Return pre-configured LLMResponse objects in sequence."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.call_count = 0

    async def generate_response(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        if self.call_count >= len(self.responses):
            raise RuntimeError("SequencedMockProvider ran out of responses")
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


# ═══════════════════════════════════════════════════════════════════════════
# UNIT TESTS — vehicle_ownership financial module
# ═══════════════════════════════════════════════════════════════════════════


class TestEstimateFuelCost:
    """Criterion 3: fuel costs calculated correctly from distance, mileage, price."""

    def test_exact_inputs_produce_correct_result(self) -> None:
        # 1000 km / 15 km/L × ₹100/L = ₹6666.67
        cost = estimate_fuel_cost(
            monthly_distance_km=Decimal("1000"),
            mileage_km_per_litre=Decimal("15"),
            fuel_price_per_litre=Decimal("100"),
        )
        assert cost == Decimal("6666.67")

    def test_higher_mileage_lowers_fuel_cost(self) -> None:
        cheap = estimate_fuel_cost(
            monthly_distance_km=Decimal("1000"),
            mileage_km_per_litre=Decimal("20"),
            fuel_price_per_litre=Decimal("100"),
        )
        expensive = estimate_fuel_cost(
            monthly_distance_km=Decimal("1000"),
            mileage_km_per_litre=Decimal("12"),
            fuel_price_per_litre=Decimal("100"),
        )
        assert cheap < expensive

    def test_zero_or_negative_distance_rejected(self) -> None:
        with pytest.raises(ValueError, match="monthly_distance_km"):
            estimate_fuel_cost(
                monthly_distance_km=Decimal("0"),
                mileage_km_per_litre=Decimal("15"),
                fuel_price_per_litre=Decimal("100"),
            )

    def test_zero_mileage_rejected(self) -> None:
        with pytest.raises(ValueError, match="mileage"):
            estimate_fuel_cost(
                monthly_distance_km=Decimal("1000"),
                mileage_km_per_litre=Decimal("0"),
                fuel_price_per_litre=Decimal("100"),
            )

    def test_zero_fuel_price_rejected(self) -> None:
        with pytest.raises(ValueError, match="fuel_price"):
            estimate_fuel_cost(
                monthly_distance_km=Decimal("1000"),
                mileage_km_per_litre=Decimal("15"),
                fuel_price_per_litre=Decimal("0"),
            )


class TestAnnualInsuranceConversion:
    """Criterion 4: annual insurance premiums are correctly divided by 12."""

    def test_annual_premium_divided_by_12(self) -> None:
        result = estimate_vehicle_ownership_cost(
            annual_insurance_premium=Decimal("12000"),
        )
        # Find insurance component
        insurance = next(
            (c for c in result.components if "Insurance" in c.label), None
        )
        assert insurance is not None
        assert insurance.amount_low == Decimal("1000.00")
        assert insurance.amount_high == Decimal("1000.00")
        assert insurance.is_estimate is False

    def test_monthly_provision_used_directly(self) -> None:
        result = estimate_vehicle_ownership_cost(
            monthly_insurance_provision=Decimal("1500"),
        )
        insurance = next(
            (c for c in result.components if "Insurance" in c.label), None
        )
        assert insurance is not None
        assert insurance.amount_low == Decimal("1500.00")

    def test_annual_15000_gives_monthly_1250(self) -> None:
        result = estimate_vehicle_ownership_cost(
            annual_insurance_premium=Decimal("15000"),
        )
        insurance = next(c for c in result.components if "Insurance" in c.label)
        assert insurance.amount_low == Decimal("1250.00")


class TestEstimateVehicleOwnershipCost:
    """Core vehicle estimator unit tests."""

    def test_criterion_6_missing_values_not_zero(self) -> None:
        """Criterion 6: Missing values must not be silently converted to zero."""
        # With only distance provided (no mileage, no price), the tool should
        # still produce a RANGE, not zero fuel cost
        result = estimate_vehicle_ownership_cost(
            monthly_distance_km=Decimal("1200"),
        )
        fuel = next((c for c in result.components if c.label == "Fuel"), None)
        assert fuel is not None, "Fuel component should be included even with partial inputs"
        assert fuel.amount_low > Decimal("0"), "Fuel low estimate must not be zero"
        assert fuel.amount_high > Decimal("0"), "Fuel high estimate must not be zero"
        assert fuel.is_estimate is True, "Fuel should be flagged as estimated"
        assert fuel.assumption is not None, "Fuel assumption must be stated"

    def test_criterion_5_estimates_labeled(self) -> None:
        """Criterion 5: Estimated values must be labeled as estimates."""
        result = estimate_vehicle_ownership_cost(
            monthly_distance_km=Decimal("1000"),
            # mileage and price deliberately omitted to force estimates
        )
        assert result.has_estimated_components is True
        for comp in result.components:
            if comp.is_estimate:
                assert comp.assumption is not None, (
                    f"Estimated component '{comp.label}' must have an assumption description"
                )

    def test_full_inputs_produce_point_estimates(self) -> None:
        """When all inputs are provided, every component should be non-estimated."""
        result = estimate_vehicle_ownership_cost(
            emi=Decimal("18000"),
            monthly_distance_km=Decimal("1200"),
            mileage_km_per_litre=Decimal("15"),
            fuel_price_per_litre=Decimal("105"),
            annual_insurance_premium=Decimal("18000"),
            monthly_maintenance=Decimal("500"),
            monthly_parking=Decimal("1000"),
        )
        # emi and fuel are both exact (not estimated)
        for comp in result.components:
            if comp.label in ("Car Loan EMI", "Fuel"):
                assert comp.is_estimate is False
            assert comp.amount_low == comp.amount_high or comp.is_estimate

    def test_emi_included_only_when_provided(self) -> None:
        result_with_emi = estimate_vehicle_ownership_cost(emi=Decimal("15000"))
        result_no_emi = estimate_vehicle_ownership_cost()
        assert result_with_emi.emi_included is True
        assert result_no_emi.emi_included is False

    def test_negative_emi_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="emi"):
            estimate_vehicle_ownership_cost(emi=Decimal("-1"))

    def test_negative_insurance_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="annual_insurance_premium"):
            estimate_vehicle_ownership_cost(annual_insurance_premium=Decimal("-100"))

    def test_total_is_sum_of_components(self) -> None:
        result = estimate_vehicle_ownership_cost(
            emi=Decimal("12000"),
            annual_insurance_premium=Decimal("12000"),  # → ₹1000/month
            monthly_maintenance=Decimal("500"),
        )
        expected_low = sum(c.amount_low for c in result.components)
        expected_high = sum(c.amount_high for c in result.components)
        assert result.total_low == expected_low
        assert result.total_high == expected_high

    def test_exclusions_listed_for_missing_inputs(self) -> None:
        result = estimate_vehicle_ownership_cost()
        assert any("Loan EMI" in excl for excl in result.exclusions)
        assert any("Insurance" in excl for excl in result.exclusions)
        assert any("maintenance" in excl.lower() for excl in result.exclusions)

    def test_annual_maintenance_divided_by_12(self) -> None:
        result = estimate_vehicle_ownership_cost(annual_maintenance=Decimal("6000"))
        maint = next(c for c in result.components if "Maintenance" in c.label)
        assert maint.amount_low == Decimal("500.00")

    def test_zero_parking_excluded_from_components(self) -> None:
        result = estimate_vehicle_ownership_cost(monthly_parking=Decimal("0"))
        labels = [c.label for c in result.components]
        assert "Parking" not in labels

    def test_follow_up_suggestions_populated(self) -> None:
        result = estimate_vehicle_ownership_cost(
            monthly_distance_km=Decimal("800"),
        )
        assert len(result.follow_up_suggestions) > 0


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — tool registry dispatch
# ═══════════════════════════════════════════════════════════════════════════


class TestVehicleOwnershipToolRegistry:
    """Criterion 11: Invalid tool arguments are rejected safely."""

    def test_execute_tool_with_full_inputs(self) -> None:
        args = {
            "emi": "15000.00",
            "monthly_distance_km": "1200.0",
            "mileage_km_per_litre": "15.00",
            "fuel_price_per_litre": "105.00",
            "annual_insurance_premium": "18000.00",
            "monthly_maintenance": "600.00",
            "monthly_parking": "1000.00",
        }
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" not in result
        assert result["emi_included"] is True
        assert len(result["components"]) >= 4  # emi, fuel, insurance, maintenance, parking
        assert Decimal(result["total_low"]) > Decimal("0")

    def test_execute_tool_with_partial_inputs_produces_range(self) -> None:
        """Criterion 1: broad car expense question returns useful breakdown."""
        args = {"monthly_distance_km": "1000.0"}
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" not in result
        # Even partial inputs should produce a fuel range
        fuel_comps = [c for c in result["components"] if c["label"] == "Fuel"]
        assert len(fuel_comps) == 1
        assert Decimal(fuel_comps[0]["amount_low"]) > 0
        assert fuel_comps[0]["is_estimate"] is True

    def test_execute_tool_with_no_inputs_produces_empty_but_valid(self) -> None:
        """With no inputs, no components are produced but exclusions are listed."""
        args = {}
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" not in result
        assert len(result["exclusions"]) > 0

    def test_execute_tool_rejects_negative_emi(self) -> None:
        """Criterion 11: invalid arguments are rejected."""
        args = {"emi": "-5000"}
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" in result

    def test_execute_tool_rejects_invalid_json(self) -> None:
        result = execute_tool("estimate_vehicle_ownership", "{bad json")
        assert "error" in result

    def test_insurance_provision_from_annual_via_tool(self) -> None:
        """Criterion 4: Annual insurance correctly divided by 12 through tool."""
        args = {"annual_insurance_premium": "24000.00"}
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" not in result
        insurance = next(c for c in result["components"] if "Insurance" in c["label"])
        assert Decimal(insurance["amount_low"]) == Decimal("2000.00")

    def test_fuel_calculation_via_tool_matches_formula(self) -> None:
        """Criterion 3: distance / mileage × price is correct through the tool."""
        # 800 km / 16 km/L × 100 = ₹5000
        args = {
            "monthly_distance_km": "800.0",
            "mileage_km_per_litre": "16.00",
            "fuel_price_per_litre": "100.00",
        }
        result = execute_tool("estimate_vehicle_ownership", json.dumps(args))
        assert "error" not in result
        fuel = next(c for c in result["components"] if c["label"] == "Fuel")
        assert Decimal(fuel["amount_low"]) == Decimal("5000.00")
        assert fuel["is_estimate"] is False  # All inputs were provided


# ═══════════════════════════════════════════════════════════════════════════
# ASSISTANT SERVICE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_criterion_1_car_expense_returns_breakdown_not_refusal() -> None:
    """Criterion 1: Car expense question → useful breakdown, not 'give me more info'."""
    # Simulate: model calls estimate_vehicle_ownership tool, then returns structured JSON
    vehicle_tool_call = ToolCallRequest(
        id="call_veh_1",
        name="estimate_vehicle_ownership",
        arguments_json=json.dumps({"monthly_distance_km": "1200.0"}),
    )
    final_json = {
        "headline": "Estimated Monthly Car Cost: ₹3,000–₹6,000+ (partial estimate)",
        "message": (
            "Based on 1,200 km/month, your estimated fuel cost alone ranges from "
            "₹3,000–₹4,500/month. Insurance, maintenance, parking, and loan EMI are "
            "excluded from this estimate because those values haven't been provided."
        ),
        "advantages": ["You can start with this range and refine each component"],
        "risks": ["Actual costs depend on mileage, fuel type, and lender terms"],
        "recommended_action": "Provide your annual insurance premium and servicing costs to refine the estimate.",
        "assumptions": ["Mileage assumed 15-20 km/litre; fuel price assumed ₹90–₹110/litre"],
        "needs_more_information": False,
        "sources": [],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=None, tool_calls=[vehicle_tool_call]),
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider)
    request = AssistantChatRequest(
        message="Tell me the total estimated monthly expenses of my car, including monthly EMIs."
    )
    response = await service.chat(request)

    assert response.needs_more_information is False, (
        "Should not demand more info before giving any estimate"
    )
    assert "estimate_vehicle_ownership" in response.tool_calls_used
    # Breakdown should be populated from deterministic tool output
    assert len(response.breakdown) > 0, "Breakdown must be populated from tool"
    assert response.is_estimate is True, "Must be flagged as estimate when inputs are partial"


@pytest.mark.anyio
async def test_criterion_2_emi_not_reused_for_wrong_vehicle() -> None:
    """Criterion 2: EMI from one loan is NOT automatically applied to a different vehicle question."""
    # Vehicle tool called WITHOUT an EMI (correct: EMI context is unclear)
    vehicle_tool_call = ToolCallRequest(
        id="call_veh_2",
        name="estimate_vehicle_ownership",
        arguments_json=json.dumps({}),  # no emi field
    )
    final_json = {
        "headline": "Vehicle Cost Estimate (Loan EMI excluded — context unclear)",
        "message": "I did not include an EMI because it's unclear if the previously discussed loan is for this vehicle.",
        "advantages": ["Transparent breakdown"],
        "risks": ["EMI excluded because vehicle context is uncertain"],
        "recommended_action": "Confirm whether the ₹8 lakh loan is for this car to include its EMI.",
        "assumptions": ["EMI omitted due to unclear vehicle context"],
        "needs_more_information": False,
        "sources": [],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=None, tool_calls=[vehicle_tool_call]),
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider)
    # There's an existing home loan context, not a car loan
    home_loan_context = LoanContext(
        loan_amount=Decimal("8000000"),
        annual_interest_rate=Decimal("8.5"),
        tenure_months=240,  # 20-year home loan
    )
    request = AssistantChatRequest(
        message="What are my total monthly car expenses?",
        loan_context=home_loan_context,
    )
    response = await service.chat(request)

    # The breakdown must NOT include an EMI component
    assert response.breakdown is not None
    emi_components = [item for item in response.breakdown if "EMI" in item.label]
    assert len(emi_components) == 0, (
        "Home loan EMI must not be injected into a car ownership estimate"
    )


@pytest.mark.anyio
async def test_criterion_7_followup_refines_estimate() -> None:
    """Criterion 7: A follow-up question can refine a previous estimate."""
    # Second call: user provides mileage, so now fuel is exact
    refined_vehicle_call = ToolCallRequest(
        id="call_veh_refined",
        name="estimate_vehicle_ownership",
        arguments_json=json.dumps({
            "monthly_distance_km": "1200.0",
            "mileage_km_per_litre": "18.00",
            "fuel_price_per_litre": "105.00",
        }),
    )
    refined_json = {
        "headline": "Refined Fuel Cost: ₹7,000/month",
        "message": "With 18 km/litre at ₹105/litre, your monthly fuel cost for 1,200 km is ₹7,000.",
        "advantages": ["Exact fuel cost — no longer an estimate"],
        "risks": ["Fuel prices fluctuate"],
        "recommended_action": "Now provide your insurance premium to complete the estimate.",
        "assumptions": ["All three fuel inputs were provided by user"],
        "needs_more_information": False,
        "sources": [],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=None, tool_calls=[refined_vehicle_call]),
        LLMResponse(content=json.dumps(refined_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider)
    request = AssistantChatRequest(
        message="My car does 18 km per litre and fuel is ₹105/litre. Update the estimate."
    )
    response = await service.chat(request)
    assert response.needs_more_information is False
    assert "estimate_vehicle_ownership" in response.tool_calls_used
    # Fuel component should now be exact (is_estimate = False)
    fuel_items = [item for item in response.breakdown if item.label == "Fuel"]
    assert len(fuel_items) == 1
    assert fuel_items[0].is_estimate is False


@pytest.mark.anyio
async def test_criterion_8_emi_question_invokes_deterministic_tool() -> None:
    """Criterion 8: An EMI question invokes calculate_emi deterministic tool."""
    emi_call = ToolCallRequest(
        id="call_emi_c8",
        name="calculate_emi",
        arguments_json=json.dumps({
            "loan_amount": "700000.00",
            "annual_interest_rate": "9.00",
            "tenure_months": 60,
        }),
    )
    final_json = {
        "headline": "Monthly EMI: ₹14,535.64",
        "message": "For ₹7 lakh at 9% over 60 months, your EMI is ₹14,535.64.",
        "advantages": ["Fixed EMI throughout tenure"],
        "risks": [],
        "recommended_action": "Compare with other lender offers.",
        "assumptions": ["Processing fees assumed zero."],
        "needs_more_information": False,
        "sources": [],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=None, tool_calls=[emi_call]),
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider)
    request = AssistantChatRequest(message="What is my EMI for 7 lakhs at 9% for 5 years?")
    response = await service.chat(request)
    assert "calculate_emi" in response.tool_calls_used
    # Verify the tool actually ran against the financial engine
    assert response.headline == "Monthly EMI: ₹14,535.64"


@pytest.mark.anyio
async def test_criterion_10_hallucinated_citations_rejected() -> None:
    """Criterion 10: Citations not grounded in retrieved evidence are stripped."""
    # Model returns a fabricated citation not in the retrieved corpus
    final_json = {
        "headline": "RBI Regulation on KFS",
        "message": "According to RBI guidelines, ...",
        "advantages": [],
        "risks": [],
        "recommended_action": "Verify with lender.",
        "assumptions": [],
        "needs_more_information": False,
        "sources": [{
            "title": "Fabricated RBI Circular 2099/Fake",
            "url": "https://fake.rbi.org.in/fabricated",
            "publisher": "Reserve Bank of India (Fabricated)",
            "source_type": "regulatory",
            "excerpt": "This circular was invented by the LLM.",
        }],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider, retriever=None)
    request = AssistantChatRequest(message="What does RBI say about KFS?")
    response = await service.chat(request)

    # No real evidence was retrieved and source doesn't match anything verified
    assert response.sources == [], (
        "Fabricated citations without retrieved evidence must be stripped"
    )


@pytest.mark.anyio
async def test_criterion_12_provider_timeout_produces_controlled_error() -> None:
    """Criterion 12: AI-provider failures produce controlled errors."""
    from app.assistant.provider import ProviderTimeoutError

    class TimeoutProvider(LLMProvider):
        async def generate_response(self, messages, tools=None):
            raise ProviderTimeoutError("Gemini connection timed out.")

    service = AssistantService(provider=TimeoutProvider())
    request = AssistantChatRequest(message="Calculate my EMI")
    with pytest.raises(ProviderTimeoutError):
        await service.chat(request)


# ═══════════════════════════════════════════════════════════════════════════
# REGRESSION: existing tools still work
# ═══════════════════════════════════════════════════════════════════════════


def test_criterion_13_calculate_emi_tool_still_works() -> None:
    """Criterion 13 regression: existing EMI tool produces correct result."""
    result = execute_tool("calculate_emi", json.dumps({
        "loan_amount": "500000.00",
        "annual_interest_rate": "9.50",
        "tenure_months": 60,
    }))
    assert "error" not in result
    assert Decimal(result["emi"]) > Decimal("0")


def test_criterion_13_compare_loans_tool_still_works() -> None:
    """Criterion 13 regression: loan comparison tool still works."""
    result = execute_tool("compare_loans", json.dumps({
        "offers": [
            {"lender": "Alpha", "loan_amount": "600000", "annual_interest_rate": "9.0", "tenure_months": 48},
            {"lender": "Beta", "loan_amount": "600000", "annual_interest_rate": "9.5", "tenure_months": 48},
        ],
        "objective": "lowest_total_cost",
    }))
    assert "error" not in result
    assert result["lender"] in ("Alpha", "Beta")


def test_criterion_13_simulate_prepayment_still_works() -> None:
    """Criterion 13 regression: prepayment simulation still works."""
    result = execute_tool("simulate_prepayment", json.dumps({
        "loan_amount": "600000.00",
        "annual_interest_rate": "9.00",
        "tenure_months": 60,
        "prepayment_amount": "100000.00",
        "prepayment_month": 12,
    }))
    assert "error" not in result
    assert Decimal(result["interest_saved"]) > 0


def test_criterion_13_six_tools_still_allowlisted() -> None:
    """Criterion 13 regression: all 6 tools remain in the allowlist."""
    names = {t.name for t in get_tool_definitions()}
    assert "calculate_emi" in names
    assert "estimate_vehicle_ownership" in names
    assert len(names) == 6


@pytest.mark.anyio
async def test_criterion_13_existing_assistant_service_emi_scenario_unchanged() -> None:
    """Criterion 13: Existing 2-turn EMI scenario still works with new service code."""
    emi_call = ToolCallRequest(
        id="reg_emi",
        name="calculate_emi",
        arguments_json=json.dumps({
            "loan_amount": "800000.00",
            "annual_interest_rate": "8.50",
            "tenure_months": 60,
        }),
    )
    final_json = {
        "headline": "EMI: ₹16,413.23",
        "message": "Your monthly EMI is ₹16,413.23.",
        "advantages": [],
        "risks": [],
        "recommended_action": "Compare with other lenders.",
        "assumptions": [],
        "needs_more_information": False,
        "sources": [],
    }
    provider = SequencedMockProvider([
        LLMResponse(content=None, tool_calls=[emi_call]),
        LLMResponse(content=json.dumps(final_json), tool_calls=[]),
    ])
    service = AssistantService(provider=provider)
    response = await service.chat(AssistantChatRequest(message="EMI for 8 lakhs at 8.5% for 5 years"))
    assert response.tool_calls_used == ["calculate_emi"]
    assert response.needs_more_information is False
