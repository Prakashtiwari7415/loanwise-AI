# AI Architecture — Gemini AI Assistant & Financial Tool Calling

LoanWise AI decouples the reasoning and explanatory capabilities of LLMs from authoritative financial calculations. The LLM never performs mathematical calculations in its head. All numeric conclusions are computed through allowlisted deterministic tools backed by the validated financial engine.

## Core Architecture

```
User Request + Active LoanContext (from Dashboard)
            ↓
  POST /api/v1/assistant/chat
            ↓
  AssistantService (Orchestrator)
            ↓
  LLM Provider Adapter (OpenAI-compatible Google Gemini / OpenAI)
  Base URL: https://generativelanguage.googleapis.com/v1beta/openai/
            ↓
     Tool Call Request
            ↓
  Allowlisted Tool Registry (Pydantic validated)
            ↓
  Deterministic Financial Engine (app.financial.*)
            ↓
  Grounded Tool Execution Output
            ↓
  LLM Provider (generates structured explanation)
            ↓
  Validated AssistantChatResponse (Pydantic contract)
            ↓
  React Frontend AssistantPanel (Interactive Dashboard UI)
```

## Provider Abstraction & Google Gemini

- **Google Gemini via OpenAI-Compatible Endpoint**:
  - Official endpoint: `https://generativelanguage.googleapis.com/v1beta/openai/`
  - Documentation: [Google Gemini OpenAI Compatibility](https://ai.google.dev/gemini-api/docs/openai)
  - Uses the existing `openai` SDK with `base_url=settings.gemini_base_url`.
  - Recommended model: `gemini-1.5-flash` (fast, cost-effective, high rate limits, native function calling support).
- **`LLMProvider` interface** (`app/assistant/provider.py`): Abstract provider contract decoupling the application from vendor-specific SDK code.
- **`OpenAIAdapter`** (`app/assistant/adapters/openai_adapter.py`): Adapter handling both `gemini` and `openai` providers with native function/tool calling (`tools` and `tool_calls`).
- **Domain Exceptions**:
  - `ProviderAuthError`: Missing or invalid API key &rarr; HTTP 503.
  - `ProviderQuotaError`: Quota exhaustion or rate limit &rarr; HTTP 429.
  - `ProviderTimeoutError`: Request timed out &rarr; HTTP 504.
  - `ProviderInvalidResponseError`: Unparseable or schema-violating output &rarr; HTTP 502.
  - `ProviderError`: Model unavailable or upstream provider failure &rarr; HTTP 502.

## Financial Tool Registry

Only explicit allowlisted tools are callable (`app/assistant/tools/registry.py`). Arbitrary code execution, dynamic imports, and database queries are strictly prohibited.

1. **`calculate_emi`**:
   - Calls: `app.financial.emi.calculate_summary`
   - Inputs: `loan_amount`, `annual_interest_rate`, `tenure_months`, optional `processing_fee`, `other_charges`.
   - Outputs: `emi`, `total_interest`, `total_repayment`, `processing_fee`, `other_charges`, `total_borrowing_cost`.
2. **`calculate_affordability`**:
   - Calls: `app.financial.affordability.analyse_affordability`
   - Inputs: `monthly_income`, `existing_emis`, `proposed_emi`, optional `estimated_monthly_expenses`.
   - Outputs: `score`, `classification`, `current_emi_burden_percent`, `projected_emi_burden_percent`, `remaining_income_after_emis`, `reasons`, `risks`, `assumptions`.
3. **`compare_loans`**:
   - Calls: `app.financial.scenarios.recommend_offer`
   - Inputs: `offers` (1 to 10 offers), `objective` (`lowest_total_cost`, `lowest_emi`, `faster_repayment`, `maximum_flexibility`).
   - Outputs: `lender`, `score`, `reasons`, `risks`, `assumptions`.
4. **`simulate_prepayment`**:
   - Calls: `app.financial.payment.simulate_one_time_prepayment`
   - Inputs: `loan_amount`, `annual_interest_rate`, `tenure_months`, `prepayment_amount`, `prepayment_month`, fees.
   - Outputs: `new_total_repayment`, `new_total_interest`, `interest_saved`, `months_saved`, `assumptions`.
5. **`simulate_rate_change`**:
   - Calls: `app.financial.scenarios.simulate_rate_scenarios`
   - Inputs: `loan_amount`, `annual_interest_rate`, `tenure_months`, `rate_changes` (list of adjustments in percentage points).
   - Outputs: `scenarios` with revised EMIs, total interest, and monthly deltas.

## Operational Bounds & Safeguards

- **Turn Limit**: Maximum 5 turns per assistant request (`LLM_MAX_TURNS=5`).
- **Tool Call Limit**: Maximum 5 tool executions per request (`LLM_MAX_TOOL_CALLS=5`) to prevent infinite looping.
- **Input Length**: Maximum 4,000 characters per user message (`LLM_MAX_INPUT_LENGTH=4000`), enforced by Pydantic.
- **Timeout**: Enforced via `LLM_TIMEOUT_SECONDS=30` on provider requests.
- **Grounded Figures**: System prompts mandate that numeric values must strictly reflect tool outputs. The model may not alter or invent outputs.
- **Clarification Mechanism**: When required input fields are missing, the assistant returns `needs_more_information: true` and requests the missing details rather than fabricating parameters.
- **Disclaimers**: The assistant never presents itself as a lender or guarantees loan approval.

## Frontend Assistant Panel

Located in `frontend/src/AssistantPanel.tsx` and integrated directly into the loan analysis view:
- **Header**: Status pill (Ready / Calculating / Attention needed), title, and subtitle.
- **Suggested Scenarios**: Instant one-click questions:
  - "Explain my current EMI."
  - "What if I increase my down payment by ₹1 lakh?"
  - "What happens if interest rates rise by 1%?"
  - "Can I save interest through prepayment?"
  - "Why might this loan be risky?"
- **Context Awareness**: Automatically passes active loan parameters (`loan_amount`, `interest_rate`, `tenure`, `income`, etc.) from user inputs.
- **Structured Rendering**:
  - Summary headline.
  - Human-readable tool usage indicator (`Used financial tool: EMI & Borrowing Cost Engine`).
  - Key Advantages and Watch Out / Risks side-by-side callout blocks.
  - Recommended Next Action highlighted box.
  - Educational assumptions footnote.
- **Robust Error UX**: Specific helpful guidance for missing API keys (503), quota limits (429), or timeouts (504), with a one-click Retry button.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | Configured LLM provider (`gemini` or `openai`) |
| `GEMINI_API_KEY` / `LLM_API_KEY` | None | Google Gemini API key (never hardcode in code or Git) |
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` | Google OpenAI-compatible Gemini endpoint |
| `LLM_MODEL` | `gemini-1.5-flash` | Model identifier (`gemini-1.5-flash`, `gemini-2.0-flash`, `gpt-4o-mini`) |
| `OPENAI_API_KEY` | None | Optional fallback API key if using `LLM_PROVIDER=openai` |
| `LLM_TIMEOUT_SECONDS` | `30` | Timeout in seconds for model requests |
| `LLM_MAX_TOOL_CALLS` | `5` | Maximum number of tool calls permitted per conversation turn |
| `LLM_MAX_TURNS` | `5` | Maximum conversation turns in orchestration loop |
| `LLM_MAX_INPUT_LENGTH` | `4000` | Maximum length of input prompt in characters |

## Local Testing & Verification

### Automated Tests (No API Key Required)

Automated tests use `MockLLMProvider` and require no real API calls or keys:

```bash
# Backend test suite (53 tests)
cd backend
.venv/bin/python -m pytest -v

# Frontend test suite & production build
cd ../frontend
npm test
npm run build
```

### Live Testing with Real Gemini API Key

1. In `.env`, add your Gemini API key:
   ```bash
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   LLM_MODEL=gemini-1.5-flash
   ```
2. Start the backend:
   ```bash
   cd backend
   .venv/bin/uvicorn app.main:app --reload
   ```
3. In another terminal, start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```
4. Open `http://localhost:5173`.
5. Enter your car loan details in the calculator.
6. In the **LoanWise AI Assistant** panel, click **"Explain my current EMI."** or type:
   `"What would my EMI be if interest rates increase by 1.5%?"`
7. Verify that the assistant responds with structured advice and displays:
   `⚙ Used financial tool: Rate Sensitivity Engine` (or `EMI & Borrowing Cost Engine`).
