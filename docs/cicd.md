# LoanWise AI — CI/CD Pipeline Guide

## Overview

The pipeline is defined in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and runs as a GitHub Actions workflow.

```mermaid
flowchart TD
    Push["Push to main / Open PR"]
    Backend["backend job\npytest 81 tests\nPython 3.12\nSQLite in-memory"]
    Frontend["frontend job\nvitest 38 tests\nTypeScript build\nNode 22"]
    Deploy["deploy job\nmain only\nafter both pass"]
    BackendHook["Render — Backend\ndeploy hook"]
    FrontendHook["Render — Frontend\ndeploy hook"]

    Push --> Backend
    Push --> Frontend
    Backend --> Deploy
    Frontend --> Deploy
    Deploy -->|"backend changed"| BackendHook
    Deploy -->|"frontend changed"| FrontendHook
```

### Trigger rules

| Event | backend | frontend | deploy |
|---|---|---|---|
| PR targeting `main` | ✅ runs | ✅ runs | ❌ never |
| Push to `main` | ✅ runs | ✅ runs | ✅ if checks pass |

### Concurrency

If a new commit is pushed to `main` while a run is in progress for the same ref, the old run is cancelled before the new one starts. This prevents duplicate concurrent deployments.

---

## Required GitHub Repository Secrets

Configure in **Settings → Secrets and variables → Actions → New repository secret**.

| Secret name | Where to get the value |
|---|---|
| `RENDER_BACKEND_DEPLOY_HOOK` | Render Dashboard → Backend service → Settings → Deploy Hook → copy the URL |
| `RENDER_FRONTEND_DEPLOY_HOOK` | Render Dashboard → Frontend static site → Settings → Deploy Hook → copy the URL |

> [!CAUTION]
> Never paste a deploy hook URL into workflow YAML directly. It grants anyone who knows the URL the ability to trigger a production deployment. Always store it as a GitHub secret.

---

## How to Configure Render Deploy Hooks

1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Open the **loanwise-backend** Web Service → **Settings** tab → scroll to **Deploy Hook**.
3. Click **Generate Deploy Hook**. Copy the URL.
4. Add it as `RENDER_BACKEND_DEPLOY_HOOK` in your GitHub repository secrets.
5. Repeat steps 2–4 for the **loanwise-ai-1** Static Site and secret `RENDER_FRONTEND_DEPLOY_HOOK`.

---

## Preventing Duplicate Render Auto-Deploys

> [!IMPORTANT]
> By default, Render watches the connected Git branch and auto-deploys on every push. This means a commit to `main` would trigger **two** deployments: one from Render's auto-deploy and one from GitHub Actions. You must disable Render's auto-deploy so that GitHub Actions owns the production trigger.

**Required change (manual, not automated):**

For **each** Render service (backend and frontend):

1. Render Dashboard → service → **Settings** tab.
2. Find **Auto-Deploy** (under the Git section).
3. Change it from **Yes** to **No**.
4. Click **Save Changes**.

This change has **not** been made automatically. You must verify and change it yourself in the Render dashboard before pushing to `main` with this workflow active.

**Trade-off**: With auto-deploy disabled, if GitHub Actions is broken or the secrets are not configured, no deployment will happen at all. This is safer than the alternative (duplicated deploys bypassing tests).

---

## How Deployment Is Triggered

After `backend` and `frontend` jobs both succeed on a `main` push, the `deploy` job:

1. Runs `git diff --name-only HEAD~1 HEAD` to detect which files changed.
2. If `backend/`, `docker/`, `.github/`, `.env.example`, or `docker-compose.yml` changed → calls `RENDER_BACKEND_DEPLOY_HOOK`.
3. If `frontend/`, `docker/`, `.github/`, `.env.example`, or `docker-compose.yml` changed → calls `RENDER_FRONTEND_DEPLOY_HOOK`.
4. If neither service's files changed, deployment is skipped and logged.

**Override selective deployment**: If you need to force a full redeploy even with no file changes, add a trivial whitespace-only comment to `backend/requirements.txt` or `frontend/package.json`. This is documented as the manual override.

---

## How to Test CI Locally

Run exactly the same commands GitHub Actions runs:

```bash
# Backend (from repo root)
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v --tb=short

# Frontend tests
npm --prefix frontend test -- --run

# Frontend production build
VITE_API_BASE_URL=https://loanwise-ai-pqdj.onrender.com npm --prefix frontend run build

# Whitespace/formatting check
git diff --check
```

---

## How to Investigate Failed Workflows

1. Go to your repository on GitHub → **Actions** tab.
2. Click the failed workflow run.
3. Click the failing job (`backend`, `frontend`, or `deploy`).
4. Expand the failing step to see the full output.

Common failures and remedies:

| Symptom | Likely cause | Fix |
|---|---|---|
| `pytest` import error (`ModuleNotFoundError`) | `PYTHONPATH` not set | Check workflow `env: PYTHONPATH: .` under the pytest step |
| `npm ci` fails | `package-lock.json` out of sync | Run `npm install` locally and commit the updated lockfile |
| `deploy` step: "secret is not set" | Secret not added to GitHub | Add the secret in Settings → Secrets |
| Render deploy hook returns 4xx | Hook URL revoked or wrong | Regenerate the hook in Render and update the secret |
| `git diff HEAD~1 HEAD` fails | First commit on branch | This only fails on the very first commit; subsequent pushes are safe |

---

## Database Migrations

> [!WARNING]
> This pipeline does **not** run `alembic upgrade head` automatically as a CI or deployment step. Running arbitrary migrations against Neon from CI would risk destructive changes to production data.

**Current approach (safe):**
Migrations run automatically on backend startup via Render's start command:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

This means:
- Migrations are run against the **production Neon database** when the backend service restarts after a Render deploy hook fires.
- Alembic tracks applied revisions in the `alembic_version` table, so migrations are idempotent across restarts.

**When a migration fails:**
- The backend process exits on startup before uvicorn starts.
- Render marks the deploy as failed; the previous deployment remains active (Render keeps the last healthy instance running).
- Check the Render dashboard → service → **Logs** for the `alembic` error traceback.

**How to roll back a bad migration:**
```bash
# Run from your local machine against Neon (never from CI)
cd backend
DATABASE_URL="postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require" \
  .venv/bin/alembic downgrade -1
```

**Backups:**
Neon provides automated point-in-time recovery. Before applying a destructive schema change, take a manual backup from the Neon Console → **Branches** → **Create branch** (creates a read-replica snapshot).

> [!CAUTION]
> Never run `alembic downgrade base` or destructive `DROP TABLE` statements against the production Neon database without a verified backup. These are irreversible on the free tier.

---

## Known Limitations

1. **No live deployment verification**: The pipeline fires the Render deploy hook and checks the HTTP response code (2xx = accepted). It does not wait for Render to finish building and starting the service, nor does it probe the health endpoint afterwards. The Render dashboard is the authoritative source of deployment status.

2. **Single-branch strategy**: The pipeline only targets `main`. Feature branches require a PR to get quality checks.

3. **No rate-limit protection on deploy hooks**: Render deploy hooks have no built-in rate limiting; rapid pushes to `main` are protected by the `concurrency: cancel-in-progress` guard.

4. **No secret rotation automation**: If `GEMINI_API_KEY` or `DATABASE_URL` is rotated on Render, you must update the Render dashboard manually. The pipeline does not validate production secrets.

5. **Render free-tier cold starts**: After a deployment, the backend may take 30–60 seconds to respond while it wakes from idle (Render free tier). This is expected behaviour.
