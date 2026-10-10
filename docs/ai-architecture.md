# AI architecture

LoanWise does not use an LLM for authoritative financial math. A future provider abstraction may call deterministic tools—`calculate_emi`, `calculate_amortization`, `calculate_affordability`, `simulate_prepayment`, `simulate_rate_change`, and `compare_loans`—then return a validated structured explanation.

The UI should render fields such as headline, score, advantages, risks, action and assumptions from a schema, not free-form text. Any RAG answer must retain a source URL and retrieval timestamp. Missing lender/PDF information is returned as missing, not invented.
