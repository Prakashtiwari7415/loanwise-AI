# API specification

All endpoints are versioned under `/api/v1` and documented interactively at `/docs`.

- `POST /loans/calculate` — EMI, interest, repayment and fees.
- `POST /loans/amortization` — monthly reducing-balance schedule.
- `POST /loans/affordability` — explainable score and risk signals.
- `POST /loans/prepayment` — lump-sum prepayment impact.
- `POST /loans/scenario` — user-selected interest-rate scenarios.
- `POST /loans/compare` — objective-based recommendation from normalized offers.
- `POST /documents/analyze` — validated, 8 MB maximum text-PDF extraction.

Every calculation request accepts `loan_amount`, `annual_interest_rate`, `tenure_months`, optional `processing_fee`, and optional `other_charges`. Numeric domain validation returns HTTP 422. Internal tracebacks are not returned.
