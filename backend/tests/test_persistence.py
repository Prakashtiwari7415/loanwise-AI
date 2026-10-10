from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.db.base import Base
from app.db.models import CalculationResult
from app.db.session import configure_database, get_engine, reset_database, session_scope
from app.main import app
from app.repositories.calculation_results import create_calculation_result, get_calculation_result


@pytest.fixture
def configured_database(tmp_path):
    configure_database(f"sqlite+pysqlite:///{tmp_path / 'loanwise-test.db'}")
    Base.metadata.create_all(get_engine())
    try:
        yield
    finally:
        reset_database()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_calculation_result_round_trips_through_repository(configured_database) -> None:
    with session_scope() as session:
        saved = create_calculation_result(
            session,
            calculation_type="loan_summary",
            inputs={"loan_amount": "500000"},
            outputs={"emi": "15668.18"},
        )
        calculation_id = saved.id

    with session_scope() as session:
        loaded = get_calculation_result(session, calculation_id)
        assert loaded is not None
        assert loaded.calculation_type == "loan_summary"
        assert loaded.outputs == {"emi": "15668.18"}


@pytest.mark.anyio
async def test_calculate_route_persists_a_result_when_database_is_configured(configured_database) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/loans/calculate",
            json={"loan_amount": 500000, "annual_interest_rate": 8, "tenure_months": 36},
        )
    assert response.status_code == 200

    with session_scope() as session:
        result = session.query(CalculationResult).one()
        assert result.inputs["loan_amount"] == "500000"
        assert result.outputs["emi"] == "15668.18"
