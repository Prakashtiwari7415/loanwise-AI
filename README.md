# LoanWise AI

LoanWise AI is a visual car-loan decision-support MVP for Indian consumers. It makes the monthly payment, total borrowing cost, affordability and interest-rate sensitivity easy to understand without claiming lender approval or financial certainty.

> Financial disclaimer: LoanWise provides educational and decision-support analysis. It does not guarantee loan approval and does not replace professional financial advice.

## Included MVP

- Decimal-based EMI, cost and amortization calculations.
- Explainable affordability score based on user-selected assumptions.
- One-time prepayment and interest-rate scenario simulations.
- Objective-based offer recommendation that preserves source/demo metadata.
- Versioned FastAPI endpoints and a responsive React dashboard.
- Conservative PDF/KFS field extraction: absent values are returned as `not_found`, never guessed.

## Architecture

`React dashboard → FastAPI routes → Pydantic contracts → deterministic financial engine`

Financial calculations never use an LLM. The UI is structured around API results so a future contextual AI explanation layer can only interpret calculated data.

## Run locally

```bash
cp .env.example .env
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`; API documentation is at `http://localhost:8000/docs`.

Do not open `frontend/index.html` directly in a browser. It is a Vite module application and must be served over HTTP. For a built preview, run `npm run build && npm run serve`, then open `http://127.0.0.1:5173`.

## Database and migrations

LoanWise uses PostgreSQL through SQLAlchemy. Set `DATABASE_URL` in `.env`, then apply the versioned schema before starting the backend:

```bash
cd backend
DATABASE_URL='postgresql+psycopg://loanwise:your-password@localhost:5432/loanwise' .venv/bin/alembic upgrade head
```

The calculation endpoint records a deterministic input/output snapshot when `DATABASE_URL` is configured. It remains stateless for local calculator use without database configuration. Docker Compose starts PostgreSQL and runs migrations automatically before the API starts.

## Test and build

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build
```

## Docker

```bash
docker compose up --build
```

The dashboard is then at `http://localhost:8080` and the API at `http://localhost:8000`.

## Current limitations

- The MVP has no login or persistence yet; it intentionally does not store user financial data.
- Document extraction only processes text-based PDFs. OCR is a later addition for scanned documents.
- The application ships no live lender rates. Any `is_demo: true` offer must remain clearly illustrative until source URLs and retrieval timestamps are supplied.
- Lender-specific penalties, approval criteria and changing regulations are not inferred.

See [architecture](docs/architecture.md), [financial model](docs/financial-model.md), [API spec](docs/api-spec.md), [security](docs/security.md), and [roadmap](docs/roadmap.md).
