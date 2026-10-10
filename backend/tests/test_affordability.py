from decimal import Decimal

import pytest

from app.financial.affordability import analyse_affordability


def test_affordability_returns_explainable_safe_result() -> None:
    result = analyse_affordability(Decimal("100000"), Decimal("10000"), Decimal("15000"), Decimal("30000"))
    assert result.classification == "MANAGEABLE"
    assert 60 <= result.score < 80
    assert result.projected_emi_burden_percent == Decimal("25.0")
    assert result.assumptions


def test_income_must_be_positive() -> None:
    with pytest.raises(ValueError):
        analyse_affordability(Decimal("0"), Decimal("0"), Decimal("1000"))
