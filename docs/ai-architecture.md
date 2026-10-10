# AI Architecture — Phase 2: Agent Foundation & Financial Tool Calling

LoanWise AI decouples the reasoning and explanatory capabilities of LLMs from authoritative financial calculations. The LLM never performs mathematical calculations in its head. All numeric conclusions are computed through allowlisted deterministic tools backed by the validated financial engine.

## Core Architecture

```
User Request / LoanContext
            ↓
  POST /api/v1/assistant/chat
            ↓
  AssistantService (Orchestrator)
            ↓
  LLM Provider Adapter (e.g. OpenAIAdapter / native function calling)
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
```

## Provider Abstraction

- **`LLMProvider` interface** (`app/assistant/provider.py`): Abstract provider contract decoupling the application from specific vendor SDKs. Defines standardized messages (`ChatMessage`), tool definitions (`ToolDefinition`), tool calls (`ToolCallRequest`), and responses (`LLMResponse`).
- **`OpenAIAdapter`** (`app/assistant/adapters/openai_adapter.py`): Concrete adapter leveraging the official `openai` SDK with native tool/function calling (`tools` and `tool_calls`).
- **Domain Exceptions**:
  - `ProviderAuthError`: Missing or invalid API key &rarr; HTTP 503.
  - `ProviderTimeoutError`: Request timed out &rarr; HTTP 504.
  - `ProviderInvalidResponseError`: Unparseable or schema-violating output &rarr; HTTP 502.
  - `ProviderError`: Upstream provider failures &rarr; HTTP 502.

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

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Configured LLM provider name |
| `OPENAI_API_KEY` / `LLM_API_KEY` | None | API key for the provider (never commit or hardcode) |
| `LLM_MODEL` | `gpt-4o-mini` | Model identifier |
| `LLM_TIMEOUT_SECONDS` | `30` | Timeout in seconds for model requests |
| `LLM_MAX_TOOL_CALLS` | `5` | Maximum number of tool calls permitted per conversation turn |
| `LLM_MAX_TURNS` | `5` | Maximum conversation turns in orchestration loop |
| `LLM_MAX_INPUT_LENGTH` | `4000` | Maximum length of input prompt in characters |

## Local Testing

Automated tests use `MockLLMProvider` and require no API key or paid network calls:

```bash
cd backend
.venv/bin/python -m pytest tests/test_assistant_tools.py -v
.venv/bin/python -m pytest tests/test_assistant_service.py -v
.venv/bin/python -m pytest tests/test_assistant_api.py -v
```

## Known Limitations

- **Stateless Chat**: In accordance with Phase 2 requirements, conversations are stateless and not persisted to prevent storing sensitive financial parameters.
- **No RAG**: Retrieval Augmented Generation is not implemented in this phase.
- **Fixed Provider Adapter**: Single provider adapter (`openai`) is implemented initially to avoid premature multi-provider abstraction complexity.
