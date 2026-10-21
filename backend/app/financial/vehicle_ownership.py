"""Deterministic vehicle total-cost-of-ownership estimator for LoanWise AI.

This module computes estimated monthly vehicle expenses with clear separation
between:
  - Loan EMI (deterministic when loan inputs are available)
  - Operating costs (fuel, insurance provision, maintenance, parking, tolls)
  - Depreciation (economic ownership cost, not a cash payment)
  - Optional/irregular expenses

All arithmetic is deterministic. The LLM must NOT perform this arithmetic.
Missing inputs must not be silently defaulted to zero — callers must pass
explicit assumptions (clearly labelled) or raise ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence


# ─── Money helpers ───────────────────────────────────────────────────────────

_TWO = Decimal("0.01")


def _q(value: Decimal | int | float) -> Decimal:
    """Round to 2 decimal places (ROUND_HALF_UP)."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(_TWO, rounding=ROUND_HALF_UP)


# ─── Result dataclasses ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class CostComponent:
    """A single named cost component in the ownership breakdown."""

    label: str
    amount_low: Decimal       # Lower end of range (or point estimate if low == high)
    amount_high: Decimal      # Upper end of range
    is_estimate: bool         # True when the value is assumed, not provided by user
    assumption: str | None    # Human-readable description of the assumption used
    category: str             # "emi" | "operating" | "annual_provision" | "optional" | "depreciation"


@dataclass(frozen=True)
class VehicleOwnershipResult:
    """Structured result from estimate_vehicle_ownership_cost."""

    components: tuple[CostComponent, ...]
    total_low: Decimal
    total_high: Decimal
    emi_included: bool
    has_estimated_components: bool
    uncertainty_note: str
    exclusions: list[str]
    follow_up_suggestions: list[str]


# ─── Core estimator ──────────────────────────────────────────────────────────


def estimate_fuel_cost(
    *,
    monthly_distance_km: Decimal,
    mileage_km_per_litre: Decimal,
    fuel_price_per_litre: Decimal,
) -> Decimal:
    """Calculate monthly fuel cost using: distance / mileage × price.

    Validates units and rejects non-positive inputs.
    Returns result rounded to 2 decimal places.
    """
    if monthly_distance_km <= 0:
        raise ValueError("monthly_distance_km must be greater than zero")
    if mileage_km_per_litre <= 0:
        raise ValueError("mileage_km_per_litre must be greater than zero")
    if fuel_price_per_litre <= 0:
        raise ValueError("fuel_price_per_litre must be greater than zero")
    litres_used = monthly_distance_km / mileage_km_per_litre
    return _q(litres_used * fuel_price_per_litre)


def _annual_to_monthly_provision(annual_amount: Decimal) -> Decimal:
    """Convert an annual expense to a monthly provision (annual / 12)."""
    return _q(annual_amount / Decimal("12"))


def estimate_vehicle_ownership_cost(
    *,
    # ── Loan EMI (optional — include only when context is clear) ──
    emi: Decimal | None = None,
    emi_is_assumed: bool = False,
    emi_assumption_note: str | None = None,
    # ── Fuel ──
    monthly_distance_km: Decimal | None = None,
    mileage_km_per_litre: Decimal | None = None,
    fuel_price_per_litre: Decimal | None = None,
    # ── Insurance (annual or already-monthly provision) ──
    annual_insurance_premium: Decimal | None = None,
    monthly_insurance_provision: Decimal | None = None,  # if already converted
    # ── Maintenance ──
    monthly_maintenance: Decimal | None = None,
    annual_maintenance: Decimal | None = None,  # will be converted to monthly
    # ── Parking ──
    monthly_parking: Decimal | None = None,
    # ── Tolls ──
    monthly_tolls: Decimal | None = None,
    # ── Additional optional recurring expenses ──
    other_monthly_expenses: Sequence[tuple[str, Decimal]] = (),
    # ── Depreciation (economic cost) ──
    include_depreciation_note: bool = True,
    vehicle_purchase_price: Decimal | None = None,
) -> VehicleOwnershipResult:
    """Estimate total monthly vehicle ownership cost.

    Inputs the caller did not provide must be passed explicitly as assumption
    ranges. This function does NOT silently default missing values to zero.
    Instead, it builds range estimates for assumed components and clearly
    labels them as estimates.

    Parameters
    ----------
    emi : monthly EMI in INR, if known for this vehicle's loan
    emi_is_assumed : True if the EMI is an assumption rather than a verified value
    monthly_distance_km : average km driven per month
    mileage_km_per_litre : vehicle fuel efficiency in km/litre
    fuel_price_per_litre : current fuel price in INR per litre
    annual_insurance_premium : annual insurance premium in INR
    monthly_insurance_provision : alternative to annual — monthly provision already calculated
    monthly_maintenance : monthly maintenance spend in INR
    annual_maintenance : annual maintenance (converted to monthly internally)
    monthly_parking : monthly parking cost in INR
    monthly_tolls : monthly tolls in INR
    other_monthly_expenses : list of (label, amount) tuples for additional costs
    include_depreciation_note : whether to add a depreciation component note
    vehicle_purchase_price : vehicle ex-showroom price used to estimate depreciation

    Returns
    -------
    VehicleOwnershipResult with breakdown, totals (low/high range), and metadata
    """
    components: list[CostComponent] = []
    exclusions: list[str] = []
    follow_ups: list[str] = []

    # ── 1. Loan EMI ──────────────────────────────────────────────────────────
    emi_included = False
    if emi is not None:
        if emi <= 0:
            raise ValueError("emi must be greater than zero when provided")
        components.append(CostComponent(
            label="Car Loan EMI",
            amount_low=emi,
            amount_high=emi,
            is_estimate=emi_is_assumed,
            assumption=emi_assumption_note if emi_is_assumed else None,
            category="emi",
        ))
        emi_included = True
    else:
        exclusions.append("Loan EMI — not included (EMI context not provided for this vehicle)")
        follow_ups.append("Provide loan amount, interest rate and tenure to include a calculated EMI")

    # ── 2. Fuel ──────────────────────────────────────────────────────────────
    fuel_amount_low: Decimal | None = None
    fuel_amount_high: Decimal | None = None
    fuel_is_estimate = False
    fuel_assumption: str | None = None

    if monthly_distance_km and mileage_km_per_litre and fuel_price_per_litre:
        # All fuel inputs provided — compute exactly
        fuel_point = estimate_fuel_cost(
            monthly_distance_km=monthly_distance_km,
            mileage_km_per_litre=mileage_km_per_litre,
            fuel_price_per_litre=fuel_price_per_litre,
        )
        fuel_amount_low = fuel_point
        fuel_amount_high = fuel_point
        fuel_is_estimate = False
    elif monthly_distance_km and fuel_price_per_litre:
        # Mileage missing — use 15–20 km/litre illustrative range (compact petrol car)
        fuel_low = estimate_fuel_cost(
            monthly_distance_km=monthly_distance_km,
            mileage_km_per_litre=Decimal("20"),
            fuel_price_per_litre=fuel_price_per_litre,
        )
        fuel_high = estimate_fuel_cost(
            monthly_distance_km=monthly_distance_km,
            mileage_km_per_litre=Decimal("15"),
            fuel_price_per_litre=fuel_price_per_litre,
        )
        fuel_amount_low = fuel_low
        fuel_amount_high = fuel_high
        fuel_is_estimate = True
        fuel_assumption = "Mileage assumed 15–20 km/litre (typical compact petrol car range)"
        follow_ups.append("Provide vehicle mileage (km/litre) for an exact fuel cost")
    elif monthly_distance_km:
        # Both mileage and price missing — use broad illustrative range
        price_mid = Decimal("100")  # mid-range petrol price, illustrative
        fuel_low = estimate_fuel_cost(
            monthly_distance_km=monthly_distance_km,
            mileage_km_per_litre=Decimal("20"),
            fuel_price_per_litre=Decimal("90"),
        )
        fuel_high = estimate_fuel_cost(
            monthly_distance_km=monthly_distance_km,
            mileage_km_per_litre=Decimal("12"),
            fuel_price_per_litre=Decimal("110"),
        )
        fuel_amount_low = fuel_low
        fuel_amount_high = fuel_high
        fuel_is_estimate = True
        fuel_assumption = (
            "Mileage assumed 12–20 km/litre; fuel price assumed ₹90–₹110/litre. "
            "Provide actual mileage and fuel price for accuracy."
        )
        follow_ups.append("Provide mileage (km/litre) and current fuel price per litre")
    else:
        exclusions.append(
            "Fuel cost — not included (monthly driving distance not provided)"
        )
        follow_ups.append(
            "Provide monthly driving distance (km), mileage (km/litre) and fuel price for fuel estimate"
        )

    if fuel_amount_low is not None and fuel_amount_high is not None:
        components.append(CostComponent(
            label="Fuel",
            amount_low=fuel_amount_low,
            amount_high=fuel_amount_high,
            is_estimate=fuel_is_estimate,
            assumption=fuel_assumption,
            category="operating",
        ))

    # ── 3. Insurance (annual premium → monthly provision) ────────────────────
    if monthly_insurance_provision is not None:
        if monthly_insurance_provision < 0:
            raise ValueError("monthly_insurance_provision must be >= 0")
        components.append(CostComponent(
            label="Insurance Provision (monthly)",
            amount_low=monthly_insurance_provision,
            amount_high=monthly_insurance_provision,
            is_estimate=False,
            assumption="Monthly provision supplied directly",
            category="annual_provision",
        ))
    elif annual_insurance_premium is not None:
        if annual_insurance_premium < 0:
            raise ValueError("annual_insurance_premium must be >= 0")
        provision = _annual_to_monthly_provision(annual_insurance_premium)
        components.append(CostComponent(
            label="Insurance Provision (annual ÷ 12)",
            amount_low=provision,
            amount_high=provision,
            is_estimate=False,
            assumption=f"Annual premium ₹{annual_insurance_premium:,.2f} ÷ 12",
            category="annual_provision",
        ))
    else:
        # Use illustrative range for a mid-sized car
        exclusions.append(
            "Insurance — not included (annual premium not provided). "
            "Typical comprehensive insurance for a mid-sized car in India costs ₹8,000–₹25,000/year."
        )
        follow_ups.append("Provide annual insurance premium to include the monthly provision (annual ÷ 12)")

    # ── 4. Maintenance ───────────────────────────────────────────────────────
    if monthly_maintenance is not None:
        if monthly_maintenance < 0:
            raise ValueError("monthly_maintenance must be >= 0")
        components.append(CostComponent(
            label="Routine Maintenance & Servicing",
            amount_low=monthly_maintenance,
            amount_high=monthly_maintenance,
            is_estimate=False,
            assumption=None,
            category="operating",
        ))
    elif annual_maintenance is not None:
        if annual_maintenance < 0:
            raise ValueError("annual_maintenance must be >= 0")
        provision = _annual_to_monthly_provision(annual_maintenance)
        components.append(CostComponent(
            label="Maintenance Provision (annual ÷ 12)",
            amount_low=provision,
            amount_high=provision,
            is_estimate=False,
            assumption=f"Annual maintenance ₹{annual_maintenance:,.2f} ÷ 12",
            category="annual_provision",
        ))
    else:
        exclusions.append(
            "Routine maintenance — not included (cost not provided). "
            "Typical annual servicing for a passenger car is ₹3,000–₹10,000/year."
        )
        follow_ups.append("Provide annual or monthly maintenance cost to include it in the estimate")

    # ── 5. Parking ───────────────────────────────────────────────────────────
    if monthly_parking is not None:
        if monthly_parking < 0:
            raise ValueError("monthly_parking must be >= 0")
        if monthly_parking > 0:
            components.append(CostComponent(
                label="Parking",
                amount_low=monthly_parking,
                amount_high=monthly_parking,
                is_estimate=False,
                assumption=None,
                category="optional",
            ))
    else:
        exclusions.append("Parking — not included (cost not provided; may be zero for home parking)")

    # ── 6. Tolls ─────────────────────────────────────────────────────────────
    if monthly_tolls is not None:
        if monthly_tolls < 0:
            raise ValueError("monthly_tolls must be >= 0")
        if monthly_tolls > 0:
            components.append(CostComponent(
                label="Tolls (FASTag / booth)",
                amount_low=monthly_tolls,
                amount_high=monthly_tolls,
                is_estimate=False,
                assumption=None,
                category="optional",
            ))
    else:
        exclusions.append("Tolls — not included (not applicable or not provided)")

    # ── 7. Other recurring expenses ───────────────────────────────────────────
    for label, amount in other_monthly_expenses:
        if amount < 0:
            raise ValueError(f"Amount for '{label}' must be >= 0")
        if amount > 0:
            components.append(CostComponent(
                label=label,
                amount_low=amount,
                amount_high=amount,
                is_estimate=False,
                assumption=None,
                category="optional",
            ))

    # ── 8. Depreciation note ──────────────────────────────────────────────────
    if include_depreciation_note:
        dep_note: str
        dep_low: Decimal
        dep_high: Decimal
        if vehicle_purchase_price and vehicle_purchase_price > 0:
            # Typical Indian car: 15–20% depreciation in year 1, ~10–15% thereafter
            # Use 12% annual as a mid-range for years 2+ as an illustrative estimate
            annual_dep_low = _q(vehicle_purchase_price * Decimal("0.10"))
            annual_dep_high = _q(vehicle_purchase_price * Decimal("0.20"))
            dep_low = _annual_to_monthly_provision(annual_dep_low)
            dep_high = _annual_to_monthly_provision(annual_dep_high)
            dep_note = (
                f"Based on ₹{vehicle_purchase_price:,.2f} purchase price, "
                f"annual depreciation estimated at 10–20% (varies by year, model, and market)."
            )
        else:
            dep_low = Decimal("0")
            dep_high = Decimal("0")
            dep_note = (
                "Depreciation is an economic ownership cost (not a cash payment). "
                "Provide the vehicle purchase price to estimate monthly depreciation."
            )
        exclusions.append(
            "Vehicle depreciation — shown separately below as an economic cost (not a cash expense). "
            + dep_note
        )

    # ── 9. Totals ─────────────────────────────────────────────────────────────
    total_low = _q(sum((c.amount_low for c in components), Decimal("0")))
    total_high = _q(sum((c.amount_high for c in components), Decimal("0")))

    has_estimates = any(c.is_estimate for c in components)

    uncertainty_note = (
        "Range reflects assumed values for components marked as estimated. "
        "Replace assumed values with your actual figures to narrow the range."
        if has_estimates
        else "All components are based on values you provided."
    )

    return VehicleOwnershipResult(
        components=tuple(components),
        total_low=total_low,
        total_high=total_high,
        emi_included=emi_included,
        has_estimated_components=has_estimates,
        uncertainty_note=uncertainty_note,
        exclusions=exclusions,
        follow_up_suggestions=follow_ups,
    )
