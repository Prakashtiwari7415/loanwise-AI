<img width="1366" height="768" alt="Screenshot from 2026-10-17 06-48-28" src="https://github.com/user-attachments/assets/bdbabf9a-f8d1-49c9-9bab-335cdd405eb0" />

<img width="1366" height="768" alt="Screenshot from 2026-10-17 06-48-04" src="https://github.com/user-attachments/assets/5acb3318-6a0b-4998-b618-b99c3393cddd" />

# LoanWise AI

Live Demo Link:https://loanwise-ai-1.onrender.com/

<!-- Project screen recording embedded for quick demo --><img width="1366" height="768" alt="Screenshot from 2026-10-17 06-48-16" src="https://github.com/user-attachments/assets/ff936a85-bb95-4bde-8f88-f7edfa3eb1d2" />

## Project screen recording

You can watch a quick screen recording of the project below (served from this repository):

<video controls width="720">
  <source src="https://raw.githubusercontent.com/Prakashtiwari7415/loanwise-AI/main/screen-capture.webm" type="video/webm">
  Your browser does not support the video tag. You can download the recording here: [screen-capture.webm](https://raw.githubusercontent.com/Prakashtiwari7415/loanwise-AI/main/screen-capture.webm).
</video>

If your browser doesn't show the embedded player, use the direct link above to download or stream the file.

LoanWise AI is an intelligent loan decision-support platform designed to help borrowers in India understand, compare, and evaluate loan offers before borrowing.

It combines a deterministic financial mathematics engine, Google Gemini-powered contextual AI assistance with allowlisted tool calling, grounded regulatory retrieval-augmented generation (RAG) with[...]

> **Financial Disclaimer**: LoanWise provides educational and decision-support analysis. It does not guarantee loan approval, claim certified financial advisory status, or replace formal lender ter[...]

---

## Architecture Overview

```mermaid
flowchart TD
    User["User Browser / Mobile Device"]
    StaticSite["Render Static Site\n(React + TypeScript + Vite SPA)"]
    WebService["Render Web Service\n(FastAPI + Uvicorn + Python 3.12)"]
    NeonDB[("Neon PostgreSQL\n(Serverless Database with SSL)")]
    Gemini["Google Gemini API\n(gemini-2.5-flash via OpenAI compat)"]

    User -->|"HTTPS (Port 443)"| StaticSite
    StaticSite -->|"REST API / JSON\n(VITE_API_BASE_URL)"| WebService
    WebService -->|"Strict CORS Check\n(CORS_ORIGINS)"| WebService
    WebService -->|"SQLAlchemy 2.0 (psycopg 3)\npool_recycle=300, sslmode=require"| NeonDB
    WebService -->|"Allowlisted Tool Calling\n& RAG Ingestion"| Gemini
```

---

## Key Capabilities

1. **Deterministic Financial Engine**: Precision reducing-balance calculations for EMI, total interest, borrowing costs, amortization schedules, affordability classification, and rate/prepayment s[...]
2. **Contextual AI Assistant (Gemini)**: Uses Google Gemini 2.5 Flash with allowlisted deterministic tool calling (`calculate_emi`, `calculate_affordability`, `compare_loans`, `simulate_prepayment[...]
3. **Grounded Regulatory RAG**: In-memory SQLite FTS5 search index over an authoritative curated corpus of Reserve Bank of India (RBI) circulars, KFS & APR mandates, and financial guides. Returns [...]
4. **KFS Document Intelligence**: In-memory PDF stream extraction for lender terms, loan amounts, interest rates, tenures, and fees with confidence scoring, side-by-side plan comparisons, and one-[...]
5. **Universal Loan Platform**: Built for car loans, personal loans, home loans, education loans, and two-wheeler loans with educational definitions and beginner-friendly guides.
6. **Mobile-First Responsive UX**: Optimized for smartphones (320px–430px), tablets, and desktop screens with sticky navigation, touch targets, and collapsible cards.

---

## Free-First Deployment Blueprint

LoanWise AI is designed for free-tier cloud deployment using:
- **Frontend**: [Render Static Site](https://render.com) (Free tier: unlimited static bandwidth, custom domains, free automated SSL).
- **Backend**: [Render Web Service](https://render.com) (Free tier: 512 MB RAM, Python 3.12, dynamic `$PORT` binding).
- **Database**: [Neon PostgreSQL](https://neon.tech) (Free tier: 0.5 GB storage, serverless autoscaling, automatic SSL encryption).

---

### Step 1: Provision Neon PostgreSQL Database

1. Sign up for a free account at [neon.tech](https://neon.tech).
2. Create a new project (e.g., `loanwise-db`) and select the region closest to your Render services.
3. In the Neon Console Dashboard under **Connection Details**:
   - Ensure the database name is set (default is `neondb`).
   - Copy the connection string. It will look like:
     ```
     postgresql://[username]:[password]@[endpoint].neon.tech/neondb?sslmode=require
     ```
4. **Driver & SSL Compatibility**:
   LoanWise AI uses SQLAlchemy 2.0 with the modern `psycopg` (v3) driver. The backend automatically:
   - Converts `postgres://` and `postgresql://` schemes to `postgresql+psycopg://`.
   - Appends `sslmode=require` if missing for remote database connections.
   - Sets `pool_pre_ping=True` and `pool_recycle=300` to handle Neon serverless idle autosuspension without dropped socket errors.

---

### Step 2: Deploy Backend to Render (Web Service)

1. Sign in to [Render](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your Git repository.
4. Configure the service settings:
   - **Name**: `loanwise-backend`
   - **Region**: Choose the same region as your Neon database.
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
     *(Render sets the `$PORT` environment variable dynamically. Uvicorn binds to `0.0.0.0:$PORT`.)*
5. Add the following **Environment Variables** in the Render dashboard:

| Environment Variable | Value / Description | Required |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Yes |
| `DATABASE_URL` | Neon connection string from Step 1 | Yes |
| `CORS_ORIGINS` | Your Render Static Site URL (e.g., `https://loanwise-frontend.onrender.com`) | Yes |
| `LLM_PROVIDER` | `gemini` | Yes |
| `GEMINI_API_KEY` | Your Google AI Studio API key | Yes |
| `LLM_MODEL` | `gemini-2.5-flash` | Yes |
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` | Optional |
| `LLM_TIMEOUT_SECONDS`| `30.0` | Optional |

> [!IMPORTANT]
> **Production CORS Rule**: When `ENVIRONMENT=production`, wildcard origin (`*`) is strictly rejected by the application on startup. You must provide the exact frontend origin(s) in `CORS_ORIGINS[...]

6. Click **Create Web Service**. Note your backend URL (e.g., `https://loanwise-backend.onrender.com`).

---

### Step 3: Deploy Frontend to Render (Static Site)

1. In the Render dashboard, click **New +** → **Static Site**.
2. Connect your Git repository.
3. Configure the static site settings:
   - **Name**: `loanwise-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**:
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory**: `dist`
4. Add the following **Environment Variable**:

| Environment Variable | Value / Description | Required |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://loanwise-backend.onrender.com` (Your backend Render URL from Step 2) | Yes |

5. Under **Redirects / Rewrites**, add a rewrite rule for single-page application routing (if needed):
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - **Action**: `Rewrite`
6. Click **Create Static Site**.
7. Once deployed, copy your static site URL (e.g. `https://loanwise-frontend.onrender.com`) and verify that it matches the `CORS_ORIGINS` value configured on your backend service in Step 2.

---

### Step 4: Run Database Migrations

Database schema migrations are managed with Alembic. When deploying via Render Web Service, migrations run automatically on startup via the start command:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Alternatively, you can run migrations as a **Pre-Deploy Command** (Release Command) in Render settings:
```bash
alembic upgrade head
```

To run migrations locally against Neon:
```bash
cd backend
DATABASE_URL="postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require" .venv/bin/alembic upgrade head
```

---

## Environment Variables Reference

| Variable | Description | Default (Local Dev) | Production (Render/Neon) |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode (`development` or `production`) | `development` | `production` |
| `PORT` | Listening HTTP port | `8000` | Assigned by platform (`$PORT`) |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://127.0.0.1:5173` | Explicit HTTPS origin (e.g. `https://loanwise.onrender.com`) |
| `VITE_API_BASE_URL` | Public API base URL for frontend fetch client | `http://127.0.0.1:8000` | Backend URL (e.g. `https://loanwise-api.onrender.com`) |
| `DATABASE_URL` | SQLAlchemy connection string | Local Postgres docker URL | Neon serverless connection string |
| `LLM_PROVIDER` | LLM backend (`gemini` or `openai`) | `gemini` | `gemini` |
| `GEMINI_API_KEY` | Google AI Studio API Key | Placeholder | Live API Key |
| `LLM_MODEL` | Gemini model name | `gemini-2.5-flash` | `gemini-2.5-flash` |
| `LLM_TIMEOUT_SECONDS`| LLM API request timeout | `30.0` | `30.0` |

---

## Security & Production Readiness Checklist

### 1. Database Driver & Connection Pooling
- **Driver**: Configured with `psycopg` (v3). Connection strings using legacy `postgres://` or `postgresql://` are automatically normalized to `postgresql+psycopg://`.
- **Neon Autosuspension Resilience**: Neon compute sleeps after idling. SQLAlchemy engine uses `pool_pre_ping=True` and `pool_recycle=300` (recycles connections every 5 minutes) to eliminate stal[...]
- **SSL Enforcement**: Remote database hosts automatically enforce `sslmode=require`.

### 2. Strict CORS Configuration
- In development, `http://localhost:5173` and `http://127.0.0.1:5173` are allowed.
- In production, wildcard origin (`*`) is blocked. The application refuses to start if `*` is passed in `CORS_ORIGINS`.

### 3. In-Memory Document Processing Safety
- Uploaded PDFs are parsed directly in-memory via PyMuPDF byte streams (`fitz.open(stream=content, filetype="pdf")`).
- Maximum document size is strictly capped at **8 MB** (`MAX_DOCUMENT_BYTES = 8 * 1024 * 1024`) on both client and server.
- MIME type (`application/pdf`) and magic header (`%PDF-`) verification are performed before parsing.
- Encrypted or password-protected PDFs are safely rejected without crashing.
- No files are ever written to the local filesystem or ephemeral disk.

### 4. Deterministic AI Grounding
- All calculations presented by the AI assistant are computed by allowlisted Python math functions, never by LLM generation.
- All RAG responses cite verified regulatory documents and warn users when lender fees may be subject to revision.

### 5. Recommended Enhancements for High-Volume Public Launch
- **Rate Limiting**: Add distributed rate limiting (e.g., `slowapi` with Redis) to protect the `/api/v1/assistant/chat` and `/api/v1/documents/analyze` endpoints against denial-of-service or quot[...]
- **User Authentication**: Add session tokens or OAuth 2.0 (e.g., Supabase Auth or Auth0) if persisting user-specific loan applications and documents across devices.
- **Observability**: Integrate centralized logging and performance monitoring (e.g., Sentry for error reporting, Datadog or OpenTelemetry for request tracing).
- **WAF & Cloudflare**: Put Cloudflare in front of the static site and web service for DDoS mitigation and global edge caching.

---

## Local Development

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- Docker & Docker Compose (optional for local PostgreSQL)

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Start Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open API Docs: `http://127.0.0.1:8000/docs`

### 4. Start Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open UI: `http://localhost:5173`

---

---

## CI / CD Pipeline

LoanWise AI uses a GitHub Actions workflow (`.github/workflows/ci.yml`) for automated quality checks and deployment.

### How it works

| Event | Quality checks | Production deploy |
| :--- | :--- | :--- |
| Pull request → `main` | ✅ Backend pytest + Frontend vitest + build | ❌ Never |
| Push to `main` | ✅ Same checks | ✅ Only after all checks pass |

### Required GitHub secrets

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
| :--- | :--- |
| `RENDER_BACKEND_DEPLOY_HOOK` | Render deploy hook URL for the backend Web Service |
| `RENDER_FRONTEND_DEPLOY_HOOK` | Render deploy hook URL for the frontend Static Site |

### Disable Render auto-deploy

> [!IMPORTANT]
> Render's built-in auto-deploy must be turned **off** for both services so GitHub Actions owns the production trigger and tests are never bypassed.
> 
> **Render dashboard → service → Settings → Auto-Deploy → No → Save Changes**

See [`docs/cicd.md`](docs/cicd.md) for the complete guide: secrets setup, deploy hook configuration, migration safety, troubleshooting, and known limitations.

---

## Running Automated Tests

All tests run offline without live database or cloud service dependencies:

### Backend Test Suite (81 Tests)
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v
```

### Frontend Test Suite (38 Tests) & Production Build
```bash
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

### Format and Cleanliness Verification
```bash
git diff --check
```
