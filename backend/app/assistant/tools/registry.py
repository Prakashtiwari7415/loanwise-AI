"""Validated, allowlisted tool registry invoking the existing financial engine."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app.assistant.provider import ToolDefinition
from app.financial.affordability import analyse_affordability
from app.financial.emi import calculate_summary
from app.financial.payment import simulate_one_time_prepayment
from app.financial.scenarios import recommend_offer, simulate_rate_scenarios
from app.financial.types import LoanInputs, LoanOffer
from app.financial.vehicle_ownership import estimate_vehicle_ownership_cost

from .schemas import (
    CalculateAffordabilityArgs,
    CalculateAffordabilityResult,
    CalculateEMIArgs,
    CalculateEMIResult,
    CompareLoansArgs,
    CompareLoansResult,
    CostComponentResult,
    EstimateVehicleOwnershipArgs,
    RateScenarioItem,
    SimulatePrepaymentArgs,
    SimulatePrepaymentResult,
    SimulateRateChangeArgs,
    SimulateRateChangeResult,
    VehicleOwnershipCostResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[[Any], BaseModel]


def _handle_calculate_emi(args: CalculateEMIArgs) -> CalculateEMIResult:
    inputs = LoanInputs(
        principal=args.loan_amount,
        annual_interest_rate=args.annual_interest_rate,
        tenure_months=args.tenure_months,
        processing_fee=args.processing_fee,
        other_charges=args.other_charges,
    )
    summary = calculate_summary(inputs)
    return CalculateEMIResult(
        emi=summary.emi,
        total_interest=summary.total_interest,
        total_repayment=summary.total_repayment,
        processing_fee=summary.processing_fee,
        other_charges=summary.other_charges,
        total_borrowing_cost=summary.total_borrowing_cost,
    )


def _handle_calculate_affordability(args: CalculateAffordabilityArgs) -> CalculateAffordabilityResult:
    res = analyse_affordability(
        monthly_income=args.monthly_income,
        existing_emis=args.existing_emis,
        proposed_emi=args.proposed_emi,
        estimated_monthly_expenses=args.estimated_monthly_expenses,
    )
    return CalculateAffordabilityResult(
        score=res.score,
        classification=res.classification,
        current_emi_burden_percent=res.current_emi_burden_percent,
        projected_emi_burden_percent=res.projected_emi_burden_percent,
        remaining_income_after_emis=res.remaining_income_after_emis,
        reasons=list(res.reasons),
        risks=list(res.risks),
        assumptions=list(res.assumptions),
    )


def _handle_compare_loans(args: CompareLoansArgs) -> CompareLoansResult:
    offers = tuple(
        LoanOffer(
            lender=item.lender,
            loan_type=item.loan_type,
            principal=item.loan_amount,
            annual_interest_rate=item.annual_interest_rate,
            tenure_months=item.tenure_months,
            processing_fee=item.processing_fee,
            other_charges=item.other_charges,
            rate_type=item.rate_type,
            prepayment_terms=item.prepayment_terms,
            foreclosure_terms=item.foreclosure_terms,
            source_url=item.source_url,
            retrieved_at=item.retrieved_at,
            verified_at=item.verified_at,
            is_demo=item.is_demo,
        )
        for item in args.offers
    )
    recommendation = recommend_offer(offers, args.objective)
    return CompareLoansResult(
        lender=recommendation.lender,
        score=recommendation.score,
        reasons=list(recommendation.reasons),
        risks=list(recommendation.risks),
        assumptions=list(recommendation.assumptions),
    )


def _handle_simulate_prepayment(args: SimulatePrepaymentArgs) -> SimulatePrepaymentResult:
    inputs = LoanInputs(
        principal=args.loan_amount,
        annual_interest_rate=args.annual_interest_rate,
        tenure_months=args.tenure_months,
        processing_fee=args.processing_fee,
        other_charges=args.other_charges,
    )
    res = simulate_one_time_prepayment(
        inputs,
        prepayment_amount=args.prepayment_amount,
        prepayment_month=args.prepayment_month,
    )
    return SimulatePrepaymentResult(
        new_total_repayment=res.new_total_repayment,
        new_total_interest=res.new_total_interest,
        interest_saved=res.interest_saved,
        months_saved=res.months_saved,
        assumptions=["Prepayment penalties are not included unless lender terms are provided."],
    )


def _handle_simulate_rate_change(args: SimulateRateChangeArgs) -> SimulateRateChangeResult:
    inputs = LoanInputs(
        principal=args.loan_amount,
        annual_interest_rate=args.annual_interest_rate,
        tenure_months=args.tenure_months,
        processing_fee=args.processing_fee,
        other_charges=args.other_charges,
    )
    scenarios = simulate_rate_scenarios(inputs, tuple(args.rate_changes))
    return SimulateRateChangeResult(
        scenarios=[
            RateScenarioItem(
                annual_interest_rate=item.annual_interest_rate,
                emi=item.emi,
                total_interest=item.total_interest,
                additional_monthly_cost=item.additional_monthly_cost,
                additional_total_interest=item.additional_total_interest,
            )
            for item in scenarios
        ]
    )


def _handle_estimate_vehicle_ownership(args: EstimateVehicleOwnershipArgs) -> VehicleOwnershipCostResult:
    other_expenses = [(item.label, item.amount) for item in args.other_monthly_expenses]
    result = estimate_vehicle_ownership_cost(
        emi=args.emi,
        emi_is_assumed=args.emi_is_assumed,
        emi_assumption_note=args.emi_assumption_note,
        monthly_distance_km=args.monthly_distance_km,
        mileage_km_per_litre=args.mileage_km_per_litre,
        fuel_price_per_litre=args.fuel_price_per_litre,
        annual_insurance_premium=args.annual_insurance_premium,
        monthly_insurance_provision=args.monthly_insurance_provision,
        monthly_maintenance=args.monthly_maintenance,
        annual_maintenance=args.annual_maintenance,
        monthly_parking=args.monthly_parking,
        monthly_tolls=args.monthly_tolls,
        other_monthly_expenses=other_expenses,
        vehicle_purchase_price=args.vehicle_purchase_price,
        include_depreciation_note=args.include_depreciation_note,
    )
    return VehicleOwnershipCostResult(
        components=[
            CostComponentResult(
                label=c.label,
                amount_low=c.amount_low,
                amount_high=c.amount_high,
                is_estimate=c.is_estimate,
                assumption=c.assumption,
                category=c.category,
            )
            for c in result.components
        ],
        total_low=result.total_low,
        total_high=result.total_high,
        emi_included=result.emi_included,
        has_estimated_components=result.has_estimated_components,
        uncertainty_note=result.uncertainty_note,
        exclusions=result.exclusions,
        follow_up_suggestions=result.follow_up_suggestions,
    )


REGISTERED_TOOLS: dict[str, RegisteredTool] = {
    "calculate_emi": RegisteredTool(
        name="calculate_emi",
        description=(
            "Calculate deterministic reducing-balance monthly EMI, total interest, and total borrowing "
            "cost for a loan based on principal, annual interest rate, tenure, and fees."
        ),
        args_schema=CalculateEMIArgs,
        handler=_handle_calculate_emi,
    ),
    "calculate_affordability": RegisteredTool(
        name="calculate_affordability",
        description=(
            "Calculate an explainable affordability score (0-100), classification, and EMI burden percentages "
            "based on net monthly income, existing EMIs, proposed EMI, and monthly expenses."
        ),
        args_schema=CalculateAffordabilityArgs,
        handler=_handle_calculate_affordability,
    ),
    "compare_loans": RegisteredTool(
        name="compare_loans",
        description=(
            "Compare 1 to 10 loan offers and recommend the best offer based on objective "
            "(lowest_total_cost, lowest_emi, faster_repayment, maximum_flexibility)."
        ),
        args_schema=CompareLoansArgs,
        handler=_handle_compare_loans,
    ),
    "simulate_prepayment": RegisteredTool(
        name="simulate_prepayment",
        description=(
            "Simulate a one-time lump-sum prepayment for an active loan and calculate interest saved "
            "and months saved off tenure."
        ),
        args_schema=SimulatePrepaymentArgs,
        handler=_handle_simulate_prepayment,
    ),
    "simulate_rate_change": RegisteredTool(
        name="simulate_rate_change",
        description=(
            "Simulate the impact of interest-rate changes (in percentage points) on monthly EMI and total interest."
        ),
        args_schema=SimulateRateChangeArgs,
        handler=_handle_simulate_rate_change,
    ),
    "estimate_vehicle_ownership": RegisteredTool(
        name="estimate_vehicle_ownership",
        description=(
            "Estimate total monthly vehicle ownership costs including loan EMI, fuel, insurance provision "
            "(annual ÷ 12), maintenance, parking, and tolls. Produces a transparent breakdown with "
            "estimated ranges for missing inputs, clearly labelled assumptions, and exclusions. "
            "Use this tool for questions about total car expenses, monthly vehicle budget, or ownership costs. "
            "Do NOT silently default missing values to zero — use the tool to produce a range."
        ),
        args_schema=EstimateVehicleOwnershipArgs,
        handler=_handle_estimate_vehicle_ownership,
    ),
}


def get_tool_definitions() -> list[ToolDefinition]:
    """Return tool definitions formatted for LLM function calling."""
    return [
        ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters_schema=tool.args_schema.model_json_schema(),
        )
        for tool in REGISTERED_TOOLS.values()
    ]


def execute_tool(tool_name: str, arguments_json: str) -> dict[str, Any]:
    """Safely validate arguments and dispatch to allowlisted deterministic financial functions."""
    if tool_name not in REGISTERED_TOOLS:
        return {"error": f"Tool '{tool_name}' is not recognized or not allowlisted."}

    tool = REGISTERED_TOOLS[tool_name]

    try:
        if isinstance(arguments_json, str):
            parsed_args = json.loads(arguments_json) if arguments_json.strip() else {}
        elif isinstance(arguments_json, dict):
            parsed_args = arguments_json
        else:
            return {"error": f"Malformed arguments payload for '{tool_name}'."}
        validated_args = tool.args_schema.model_validate(parsed_args)
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON in arguments for tool '{tool_name}': {exc}"}
    except ValidationError as exc:
        return {"error": f"Validation error for tool '{tool_name}': {exc.errors()}"}

    try:
        result = tool.handler(validated_args)
        return result.model_dump(mode="json")
    except ValueError as exc:
        return {"error": f"Financial calculation error: {str(exc)}"}
    except Exception as exc:
        logger.exception("Unexpected error executing tool '%s': %s", tool_name, exc)
        return {"error": "An internal error occurred during financial calculation."}
