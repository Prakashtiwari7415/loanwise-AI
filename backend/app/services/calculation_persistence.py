"""Optional persistence of deterministic financial calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.db.session import database_is_configured, session_scope
from app.repositories.calculation_results import create_calculation_result


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def persist_calculation_if_configured(
    *, calculation_type: str, inputs: dict[str, Any], outputs: dict[str, Any]
) -> None:
    """Persist only when DATABASE_URL is configured; local calculator use remains stateless."""
    if not database_is_configured():
        return
    with session_scope() as session:
        create_calculation_result(
            session,
            calculation_type=calculation_type,
            inputs=_json_ready(inputs),
            outputs=_json_ready(outputs),
        )
