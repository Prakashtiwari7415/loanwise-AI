"""Tests for financial tool registry, argument validation, and deterministic engine dispatch."""

import json
from decimal import Decimal
import pytest

from app.assistant.tools.registry import REGISTERED_TOOLS, execute_tool, get_tool_definitions
from app.financial.emi import calculate_summary
from app.financial.types import LoanInputs


def test_tool_definitions_expose_all_allowlisted_tools() -> None:
    definitions = get_tool_definitions()
    tool_names = {t.name for t in definitions}
    expected_tools = {
        "calculate_emi",
        "calculate_affordability",
        "compare_loans",
        "simulate_prepayment",
        "simulate_rate_change",
        "estimate_vehicle_ownership",
        "fetch_current_rates",
    }
    assert tool_names == expected_tools
    for tool_def in definitions:
        assert tool_def.name in REGISTERED_TOOLS
        assert tool_def.description
        assert "properties" in tool_def.parameters_schema


def test_calculate_emi_tool_executes_financial_engine() -> None:
    args = {
        "loan_amount": "1000000.00",
        "annual_interest_rate": "9.50",
        "tenure_months": 60,
        "processing_fee": "5000.00",
        "other_charges": "500.00",
    }
    result = execute_tool("calculate_emi", json.dumps(args))
    assert "error" not in result

    # Verify exact deterministic match with direct financial engine calculation
    expected = calculate_summary(
        LoanInputs(
            principal=Decimal("1000000.00"),
            annual_interest_rate=Decimal("9.50"),
            tenure_months=60,
            processing_fee=Decimal("5000.00"),
            other_charges=Decimal("500.00"),
        )
    )
    assert result["emi"] == str(expected.emi)
    assert result["total_interest"] == str(expected.total_interest)
    assert result["total_repayment"] == str(expected.total_repayment)
    assert result["total_borrowing_cost"] == str(expected.total_borrowing_cost)


def test_calculate_emi_tool_rejects_invalid_inputs() -> None:
    # Negative loan amount
    bad_args_1 = {
        "loan_amount": "-500000",
        "annual_interest_rate": "8.5",
        "tenure_months": 36,
    }
    res_1 = execute_tool("calculate_emi", json.dumps(bad_args_1))
    assert "error" in res_1

    # Zero tenure
    bad_args_2 = {
        "loan_amount": "500000",
        "annual_interest_rate": "8.5",
        "tenure_months": 0,
    }
    res_2 = execute_tool("calculate_emi", json.dumps(bad_args_2))
    assert "error" in res_2


def test_calculate_affordability_tool_executes_correctly() -> None:
    args = {
        "monthly_income": "100000.00",
        "existing_emis": "15000.00",
        "proposed_emi": "20000.00",
        "estimated_monthly_expenses": "30000.00",
    }
    result = execute_tool("calculate_affordability", json.dumps(args))
    assert "error" not in result
    assert result["score"] > 0
    assert result["classification"] in {"GOOD FIT", "MANAGEABLE", "STRETCHED", "HIGH STRAIN"}
    assert result["remaining_income_after_emis"] == "35000.00"
    assert result["projected_emi_burden_percent"] == "35.0"
    assert len(result["assumptions"]) > 0


def test_calculate_affordability_tool_rejects_negative_income() -> None:
    args = {
        "monthly_income": "-50000",
        "proposed_emi": "15000",
    }
    result = execute_tool("calculate_affordability", json.dumps(args))
    assert "error" in result


def test_compare_loans_tool_executes_correctly() -> None:
    args = {
        "objective": "lowest_total_cost",
        "offers": [
            {
                "lender": "Bank Alpha",
                "loan_amount": "800000.00",
                "annual_interest_rate": "9.25",
                "tenure_months": 48,
                "processing_fee": "2000.00",
            },
            {
                "lender": "Bank Beta",
                "loan_amount": "800000.00",
                "annual_interest_rate": "8.75",
                "tenure_months": 48,
                "processing_fee": "4000.00",
            },
        ],
    }
    result = execute_tool("compare_loans", json.dumps(args))
    assert "error" not in result
    assert result["lender"] in {"Bank Alpha", "Bank Beta"}
    assert result["score"] in {65, 75}
    assert len(result["reasons"]) > 0


def test_simulate_prepayment_tool_executes_correctly() -> None:
    args = {
        "loan_amount": "600000.00",
        "annual_interest_rate": "9.00",
        "tenure_months": 60,
        "prepayment_amount": "100000.00",
        "prepayment_month": 12,
    }
    result = execute_tool("simulate_prepayment", json.dumps(args))
    assert "error" not in result
    assert Decimal(result["interest_saved"]) > Decimal("0")
    assert result["months_saved"] > 0
    assert len(result["assumptions"]) > 0


def test_simulate_prepayment_tool_rejects_invalid_month() -> None:
    # prepayment month equals tenure
    args = {
        "loan_amount": "600000.00",
        "annual_interest_rate": "9.00",
        "tenure_months": 60,
        "prepayment_amount": "100000.00",
        "prepayment_month": 60,
    }
    result = execute_tool("simulate_prepayment", json.dumps(args))
    assert "error" in result


def test_simulate_rate_change_tool_executes_correctly() -> None:
    args = {
        "loan_amount": "700000.00",
        "annual_interest_rate": "9.00",
        "tenure_months": 48,
        "rate_changes": ["-0.5", "0.5", "1.5"],
    }
    result = execute_tool("simulate_rate_change", json.dumps(args))
    assert "error" not in result
    assert len(result["scenarios"]) == 3
    # Check that +0.5 rate increases monthly EMI
    baseline_emi = execute_tool(
        "calculate_emi",
        json.dumps({"loan_amount": "700000.00", "annual_interest_rate": "9.00", "tenure_months": 48}),
    )["emi"]
    plus_half_scenario = [s for s in result["scenarios"] if s["annual_interest_rate"] == "9.50"][0]
    assert Decimal(plus_half_scenario["emi"]) > Decimal(baseline_emi)


def test_execute_tool_rejects_unknown_tool() -> None:
    result = execute_tool("unregistered_arbitrary_eval", "{}")
    assert "error" in result
    assert "not recognized or not allowlisted" in result["error"]


def test_execute_tool_handles_malformed_json() -> None:
    result = execute_tool("calculate_emi", "{malformed-json")
    assert "error" in result
    assert "Invalid JSON" in result["error"]
