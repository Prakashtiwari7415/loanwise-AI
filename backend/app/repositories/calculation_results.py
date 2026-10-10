"""Repository for auditable deterministic calculation snapshots."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CalculationResult


def create_calculation_result(
    session: Session,
    *,
    calculation_type: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    profile_id: str | None = None,
) -> CalculationResult:
    record = CalculationResult(
        profile_id=profile_id,
        calculation_type=calculation_type,
        inputs=inputs,
        outputs=outputs,
    )
    session.add(record)
    session.flush()
    return record


def get_calculation_result(session: Session, calculation_id: str) -> CalculationResult | None:
    return session.scalar(select(CalculationResult).where(CalculationResult.id == calculation_id))
