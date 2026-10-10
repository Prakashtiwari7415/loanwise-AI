# LoanWise AI

LoanWise AI is an intelligent car loan decision-support platform for Indian consumers. It combines a deterministic financial mathematics engine, Google Gemini-powered contextual AI assistance with allowlisted tool calling, grounded regulatory retrieval-augmented generation (RAG) with traceable citations, and Key Fact Statement (KFS) document intelligence.

> **Financial Disclaimer**: LoanWise provides educational and decision-support analysis. It does not guarantee loan approval, claim certified financial advisory status, or replace formal lender terms.

---

## Key Capabilities

1. **Deterministic Financial Engine**: Precision reducing-balance calculations for EMI, total interest, borrowing costs, amortization schedules, affordability classification, and rate/prepayment scenario simulations.
2. **Contextual AI Assistant (Gemini)**: Uses Google Gemini (via OpenAI-compatible API) with allowlisted tool calling (`calculate_emi`, `calculate_affordability`, `compare_loans`, `simulate_prepayment`, `simulate_rate_change`). All numbers in assistant responses are strictly grounded in deterministic tool outputs.
3. **Grounded Regulatory RAG**: In-memory SQLite FTS5 BM25 search index over an authoritative curated corpus of Reserve Bank of India (RBI) circulars, KFS & APR mandates, and financial guides. Returns traceable citations, publisher attribution, and staleness warnings for outdated lender terms.
4. **KFS Document Intelligence**: In-memory PDF stream extraction for lender terms, loan amounts, interest rates, tenures, and fees with confidence scoring, side-by-side plan comparisons, and one-click assistant prompt dispatch.
5. **Normalized Persistence**: PostgreSQL database backing with SQLAlchemy models and Alembic migrations.

---

## Project Structure

```
loanwise-ai/
├── backend/
│   ├── app/
│   │   ├── assistant/       # Gemini adapter, tool registry, prompts & orchestration
│   │   ├── core/            # Config and environment management
│   │   ├── db/              # SQLAlchemy models, session, and engine
│   │   ├── financial/       # Deterministic math engine (EMI, amortization, affordability)
│   │   ├── rag/             # Curated corpus, chunker, FTS5 retriever, ingestion CLI
│   │   ├── document_extraction.py # PyMuPDF PDF stream extraction
│   │   └── main.py          # FastAPI application & API endpoints
│   ├── alembic/             # Versioned schema migrations
│   ├── tests/               # 71 comprehensive unit and integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application dashboard
│   │   ├── AssistantPanel.tsx # AI Assistant with tools & clickable citations
│   │   ├── KfsAnalysisSection.tsx # PDF upload and document analysis
│   │   ├── api.ts           # Type-safe API client
│   │   └── styles.css
│   └── package.json
├── docker/                  # Production Dockerfiles and Nginx configuration
├── docker-compose.yml       # PostgreSQL, Backend, and Frontend orchestration
├── .env.example             # Safe environment variable template (no credentials)
└── .env                     # Local environment configuration (gitignored)
```

---

## Getting Started

### 1. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your Gemini API key and PostgreSQL credentials:

```bash
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM Configuration (Google Gemini)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_gemini_api_key_here
LLM_API_KEY=your_actual_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash

# PostgreSQL Configuration
POSTGRES_DB=loanwise
POSTGRES_USER=loanwise
POSTGRES_PASSWORD=replace-with-a-local-development-password
DATABASE_URL=postgresql+psycopg://loanwise:replace-with-a-local-development-password@localhost:5432/loanwise
```

---

### 2. Start PostgreSQL & Run Migrations

Start PostgreSQL using Docker Compose:

```bash
docker compose up -d postgres
```

Verify PostgreSQL is healthy and accepting connections:

```bash
docker compose exec postgres pg_isready -U loanwise -d loanwise
```

Apply versioned Alembic database migrations:

```bash
cd backend
.venv/bin/alembic upgrade head
```

---

### 3. Run the Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`.

---

### 4. Run the Frontend (React + Vite)

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running Automated Tests

All test suites run independently without requiring live external API credentials or databases:

### Backend Test Suite (71 Tests)
```bash
cd backend
.venv/bin/python -m pytest -v
```

### Frontend Test Suite (13 Tests) & Production Build
```bash
cd frontend
npm test -- --run
npm run build
```

### Code Formatting & Git Diff Verification
```bash
git diff --check
```

---

## Demonstrating Core User Flows

### Workflow 1: Main Loan Calculator & Scenarios
1. Open `http://localhost:5173`.
2. In **01 / Loan Calculator**, set Loan Amount (`₹10,00,000`), Interest Rate (`9.0%`), and Tenure (`60 months`).
3. View the deterministic reducing-balance EMI (`₹20,758.36`), total interest (`₹2,45,501`), and amortization chart.
4. Test prepayment and interest-rate sensitivity scenarios in the comparison panel.

### Workflow 2: KFS Document Intelligence
1. Scroll to **02 / Key Fact Statement (KFS) Intelligence**.
2. Drag and drop or browse for a loan sanction letter or KFS PDF.
3. Click **Analyze document →**.
4. Inspect extracted fields (Lender, Principal, Rate, Rate Type, Tenure, Processing Fee) and confidence badges (`High`, `Medium`, `Needs Review`, `Not Found`).
5. Review the side-by-side plan comparison delta showing potential savings or cost differences.
6. Click any contextual action button (e.g. *Explain this KFS in simple language*) to populate the AI assistant.

### Workflow 3: Gemini Contextual Assistant with Tool Calling
1. Scroll to **03 / LoanWise AI Assistant**.
2. Ask a computational loan question:
   `"What is my EMI for a 10 lakh car loan at 9% for 5 years?"`
3. Notice the assistant invokes the allowlisted `calculate_emi` deterministic tool and displays:
   - Tool execution badge (`⚙ Used financial tool: EMI & Borrowing Cost Engine`)
   - Headline and grounded numerical commentary
   - Key advantages and risks
   - Actionable recommended steps and disclaimers

### Workflow 4: Grounded Regulatory RAG & Citations
1. Ask a compliance or regulatory question:
   `"What does RBI mandate about Key Fact Statement (KFS) and cooling-off period?"`
2. Verify that the assistant answers based on retrieved RBI evidence and renders the **Verified Regulatory & Research Sources** card:
   - Clickable source link to official RBI circular
   - Publisher tag: `Reserve Bank of India`
   - Classification badge: `Regulatory Mandate`
   - Verification date and verbatim evidence excerpt
3. Ask about lender charges:
   `"What are SBI car loan processing fees?"`
4. Notice the **Staleness Notice** banner warning that lender terms change frequently and should be verified directly with the lender.

---

## Full Docker Deployment

To build and run the entire stack (PostgreSQL, FastAPI Backend, and React/Nginx Frontend) in containers:

```bash
docker compose up --build -d
```

- Frontend Dashboard: `http://localhost:8080`
- FastAPI Backend: `http://localhost:8000`
- API Health Check: `http://localhost:8000/health`
