# API specification

All endpoints are versioned under `/api/v1` and documented interactively at `/docs`.

## Existing Financial & Document Endpoints

- `POST /loans/calculate` — EMI, interest, repayment and fees.
- `POST /loans/amortization` — monthly reducing-balance schedule.
- `POST /loans/affordability` — explainable score and risk signals.
- `POST /loans/prepayment` — lump-sum prepayment impact.
- `POST /loans/scenario` — user-selected interest-rate scenarios.
- `POST /loans/compare` — objective-based recommendation from normalized offers.
- `POST /documents/analyze` — validated, 8 MB maximum text-PDF extraction.

Every calculation request accepts `loan_amount`, `annual_interest_rate`, `tenure_months`, optional `processing_fee`, and optional `other_charges`. Numeric domain validation returns HTTP 422. Internal tracebacks are not returned.

---

## AI Assistant Endpoint

### `POST /api/v1/assistant/chat`

Chat with the AI decision-support assistant using allowlisted deterministic financial tools.

#### Request Schema (`AssistantChatRequest`)

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | User inquiry (1 to 4,000 characters) |
| `loan_context` | object | No | Active dashboard loan context |
| `loan_context.loan_amount` | number / decimal | No | Principal loan amount in INR (> 0) |
| `loan_context.annual_interest_rate` | number / decimal | No | Annual interest rate (0 to 100) |
| `loan_context.tenure_months` | integer | No | Tenure in months (1 to 480) |
| `loan_context.processing_fee` | number / decimal | No | Processing fee in INR (&ge; 0) |
| `loan_context.other_charges` | number / decimal | No | Other charges in INR (&ge; 0) |
| `loan_context.monthly_income` | number / decimal | No | Monthly income in INR (> 0) |
| `loan_context.existing_emis` | number / decimal | No | Current EMIs in INR (&ge; 0) |
| `loan_context.estimated_monthly_expenses` | number / decimal | No | Living expenses in INR (&ge; 0) |

##### Example Request

```json
{
  "message": "What will my monthly EMI be for a 10 lakh loan at 8.75% over 5 years?",
  "loan_context": {
    "loan_amount": 1000000,
    "annual_interest_rate": 8.75,
    "tenure_months": 60,
    "processing_fee": 5000
  }
}
```

#### Response Schema (`AssistantChatResponse`)

| Field | Type | Description |
|---|---|---|
| `headline` | string | Concise summary headline |
| `message` | string | Educational commentary grounded in tool outputs |
| `advantages` | array of strings | Identified loan benefits or positive trade-offs |
| `risks` | array of strings | Risk factors, sensitivities, or caveats |
| `recommended_action` | string | Suggested educational next step |
| `assumptions` | array of strings | Assumptions and standard disclaimers |
| `tool_calls_used` | array of strings | Allowlisted tools executed during orchestration |
| `needs_more_information` | boolean | True if required parameters were missing |

##### Example Response

```json
{
  "headline": "Estimated Monthly EMI is ₹20,636.85",
  "message": "For a ₹10,00,000 loan at 8.75% over 60 months, your monthly EMI is ₹20,636.85, with total interest of ₹2,38,211.00 and total borrowing cost of ₹12,43,211.00 including ₹5,000 processing fee.",
  "advantages": [
    "Fixed predictable monthly payment",
    "Moderate 5-year loan tenure"
  ],
  "risks": [
    "Total interest represents over 23% of principal"
  ],
  "recommended_action": "Check if competing lenders offer lower processing fees or a rate concession.",
  "assumptions": [
    "Educational calculation based on reducing balance method.",
    "Not a lender loan offer or approval guarantee."
  ],
  "tool_calls_used": [
    "calculate_emi"
  ],
  "needs_more_information": false
}
```

#### HTTP Status Codes

- `200 OK`: Successful response adhering to `AssistantChatResponse`.
- `422 Unprocessable Entity`: Request validation failure (empty message, message > 4000 chars, invalid context numbers).
- `502 Bad Gateway`: Upstream LLM provider failure or invalid/unparseable structured response from model.
- `503 Service Unavailable`: LLM provider is not configured (missing `OPENAI_API_KEY` / `LLM_API_KEY`).
- `504 Gateway Timeout`: LLM provider request timed out.
