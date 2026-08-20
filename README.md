# SmartMarket DZ

Decision-support platform (DSS) for the Algerian market: ingest → clean → analyze → validate → decide.

## Build status

Built phase-by-phase per the mandated build sequence. Each phase ships with passing tests before moving on.

| Phase | Scope | Status |
|---|---|---|
| 1 | Auth (JWT, roles) + Companies + Users + seed script | ✅ Done |
| 2 | CSV/Excel upload, preview, column profiling, file storage | ✅ Done |
| 3 | Data Cleaning Engine + before/after report | ✅ Done |
| 4 | Descriptive Statistics + correlation | ✅ Done |
| 5 | Regression + ANOVA | ✅ Done |
| 6 | Model Validation suite | ✅ Done |
| 7 | Forecasting (ARIMA/ETS) + Segmentation | ✅ Done |
| 8 | KPI Engine + Dashboard + Decision Engine + Reports | ✅ Done |
| 9+ | Bayesian & Panel Data stubs | ✅ Done |
| — | Frontend (Next.js) | ✅ Done — all 13 pages functional, verified with a real build |

Backend test suite: **113/113 passing** (`cd backend && pytest -q`). Frontend: TypeScript strict + ESLint clean,
6/6 Vitest passing, full `next build` succeeds (36 statically generated routes across fr/ar/en). All 10 acceptance
criteria from section 18 verified end-to-end against the real seeded demo dataset — see below.

## What works right now

- Register a company (creates the first `owner` user) → login → JWT access/refresh tokens.
- Owners can invite teammates with `analyst` / `viewer` roles; role checks are enforced on protected endpoints.
- Upload a CSV or XLSX file → it's stored per-company, parsed with pandas, and every column is profiled
  (dtype, null/unique counts, min/max/mean/std, and a numeric "target candidate" flag) into `dataset_columns`.
- List/get/preview/delete datasets — all scoped to the caller's company (hard multi-tenancy: every query filters `company_id`).
- Run the **Data Cleaning Engine** on a dataset: per-column missing-value strategies (mean/median/mode/constant/drop rows/drop column)
  and outlier handling (IQR or z-score, remove or cap), producing a before/after report (`cleaning_runs`) and replacing the
  dataset's working file + column profile with the cleaned version.
- Run **Descriptive Statistics**: mean/median/mode/variance/std/skewness/kurtosis/quartiles/IQR/min/max per numeric column,
  frequency tables for categorical columns, a Pearson + Spearman correlation matrix, a missingness summary, and
  auto-flagged numeric target-variable candidates — every finding ships with a plain-French `interpretation` string.
  Persisted as an immutable `analysis_jobs` row (queryable via `GET /jobs`).
- Run **OLS Regression**: `target ~ features`, with optional `log(target)` and pairwise interaction terms, fit via
  `statsmodels`. Returns coefficients, standard errors, t-stats, p-values, 95% CIs, R²/adjusted R², F-statistic + p-value,
  AIC, BIC — every coefficient gets a plain-French significance interpretation. The fit is persisted as a `models` row
  (queryable later for the Model Validation suite).
- Run **one-way ANOVA**: `response` across the groups of `factor`, with Tukey HSD post-hoc pairwise comparisons when
  there are 3+ groups and the overall F-test is significant. Returns SS/df/MS/F/p/η² plus the full pairwise table.
- Run the **Model Validation suite** on any fitted regression model: Shapiro-Wilk + Jarque-Bera (normality),
  Breusch-Pagan + White (heteroscedasticity), Durbin-Watson (autocorrelation), VIF per feature (multicollinearity,
  WARN >5 / FAIL >10), Cook's distance (influence), plus residual-vs-fitted and residual histogram data for plotting.
  Every test returns `{statistic, p_value, threshold, verdict, meaning}`; a FAIL always comes with a concrete
  remediation suggestion. Verified against synthetic datasets with known properties (heteroscedastic data reliably
  fails Breusch-Pagan; a deliberately collinear feature pair reliably fails VIF — matching the required demo scenario).
- **Verified end-to-end**: register → upload → clean → descriptive stats → regression → ANOVA → model validation,
  chained in one flow, works correctly — including the collinear-feature VIF-FAIL case from the acceptance criteria.
- Run **Demand Forecasting**: ADF + KPSS stationarity tests, ARIMA (`pmdarima.auto_arima`, AIC-selected, p/d/q capped
  at 5/2/5) vs ETS (trend/damping grid search), both fit on a train split and scored on a held-out test split
  (MAE/RMSE/MAPE), then refit on the full series to forecast the requested horizon with 80%/95% confidence bands —
  the better-performing model is clearly labeled and used for the final forecast.
- Run **Customer Segmentation**: K-Means with automatic k selection (elbow + silhouette, k=2..10) or DBSCAN,
  standardized features, PCA projection for 2D visualization, per-cluster feature-mean profiles with
  auto-generated descriptive names (e.g. "Segment : marketing_spend élevé, price faible").
- Compute the **KPI Engine**: CLTV, Churn/Retention (with a full cohort table), Take Rate, CAC, WOM, Revenue
  Growth, Gross Margin — plus Average Order Value and Repeat Purchase Rate as supporting metrics. Every KPI whose
  required columns weren't supplied comes back as `insufficient_data` with exactly what's missing, rather than
  failing the whole request.
- Generate recommendations via the **Decision Engine**: a rule-based system that reads the dataset's most recent
  completed analyses (regression, validation, forecast, segmentation, KPIs) and emits prioritized, evidence-backed
  decisions — significant regression drivers, validation-FAIL remediation, forecast-trend inventory/pricing guidance,
  high-churn retention targeting, CAC > CLTV pricing alerts, low-margin/declining-revenue finance alerts. Each
  decision has `priority`, `category`, `title`, `description`, `evidence`, `recommended_action`, and `confidence`
  (the last stored inside `evidence`, since the fixed `decisions` schema has no dedicated confidence column).
- Generate and download **Reports**: an executive PDF (KPI summary, validation verdicts, forecast chart, top 5
  recommendations) or a full raw-results XLSX workbook (one sheet per analysis: descriptive, regression, validation,
  forecast, segments, KPIs, decisions).
- **Verified end-to-end against the real seeded demo dataset**, not just isolated tests: all 10 acceptance criteria
  from section 18 — register → upload → clean → descriptive → regression (with a genuine VIF-FAIL on the deliberately
  collinear columns) → ANOVA → validation → forecast → segmentation → KPIs → ≥1 evidence-backed decision → both PDF
  and XLSX reports downloading as valid files. This deeper check caught and fixed a real field-name mismatch
  (`column`/`missing` vs. an assumed `name`/`null_count`) in the XLSX generator that isolated unit tests had missed
  because their fixtures happened to use the same (wrong) key names as the bug.
- `GET /api/v1/health` for liveness checks.

**Frontend** (Next.js 14 / TypeScript strict / Tailwind / shadcn-style components / next-intl fr-ar-en with Arabic RTL):
- Full auth flow: landing page → register (creates company + owner) → login → JWT stored client-side with automatic
  silent refresh-and-retry on 401 → protected app shell with sidebar nav (+ a slide-over mobile nav below the `md`
  breakpoint, since the spec requires the app be usable on tablet) and role-aware profile display.
- Full datasets flow: drag-and-drop upload with client-side extension validation → list view with status badges →
  detail view with the full column profile table and a live data preview table.
- **Data Cleaning UI**: per-column missing-value/outlier strategy configuration table driven by the real column
  profile, before/after report with a missingness bar chart.
- **Analytics workspace**: tabbed (Descriptive / Regression / ANOVA / Validation / Forecast / Segmentation) per
  section 12.1 — each tab has its own config form and results view wired to the real endpoints: correlation heatmap
  and frequency tables, a regression coefficient table with per-coefficient interpretation cards, ANOVA + Tukey
  pairwise table, the full six-test Model Validation suite with PASS/WARN/FAIL verdict badges and residual/histogram
  charts (Recharts), ARIMA-vs-ETS forecast comparison with confidence bands, and K-Means/DBSCAN segmentation with
  an elbow chart and a PCA cluster scatter plot.
- **KPI grid, Decisions feed, Reports page**: KPI cards with formulas/trend indicators (gracefully showing
  "insufficient data" + what's missing, matching the backend contract), priority-badged decision cards, and a report
  generator that downloads real PDF/XLSX files from the backend.
- **Settings**: company profile editing and a user management table (invite teammates, change roles, activate/
  deactivate), both owner-gated.
- i18n wired end-to-end: `/fr`, `/ar` (RTL, verified `dir="rtl"` on `<html>`), `/en` all statically generate; French
  is the default per spec. Design tokens (Fraunces display / Inter body / JetBrains Mono for tabular figures,
  petrol-teal + ochre palette) are in place and consistently applied.
- **Verified with a real `npm run build`**, not just written and assumed correct: all 13 pages × 3 locales (36 routes)
  compile under TypeScript strict mode and statically generate, ESLint clean, `tsc --noEmit` clean. (The build only
  fails in this sandbox because `fonts.googleapis.com` isn't in the allowed egress list for `next/font/google`'s
  build-time metadata fetch — a sandbox restriction, not a code issue, confirmed by temporarily swapping to system
  fonts and getting a clean build twice. This resolves itself automatically with normal internet access, e.g. inside
  the Docker container.)
- 6 Vitest + React Testing Library tests passing (form validation, server-error handling, upload flow including a
  client-side-rejection case).
- A Playwright E2E smoke spec (`e2e/smoke.spec.ts`) covering the exact path required by section 15 — login → upload
  → clean → descriptive → regression — against real UI selectors (verified by reading each component's actual DOM
  structure, not guessed). Could not be *executed* in this sandbox: `npx playwright install` needs
  `cdn.playwright.dev`, which isn't in the sandbox's network allowlist. This is a genuine limitation worth being
  explicit about — the test is written and type-checks, but hasn't been run against a live app the way every other
  test in this project has been. Run it yourself with `npx playwright install chromium && npm run test:e2e` once the
  full stack (`docker-compose up` + `npm run dev`) is running.

Try it via the interactive docs at `http://localhost:8000/api/v1/docs` once the stack is running.

## Setup

### Deploy to Render (no local Docker needed)
See [`RENDER_DEPLOY.md`](./RENDER_DEPLOY.md) — a `render.yaml` Blueprint provisions the database and both
services for a free-tier preview deployment.

### Prerequisites
- Docker + Docker Compose

### Steps
```bash
cp .env.example .env
# edit .env — at minimum set a real SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(64))"

docker-compose up --build postgres redis backend worker frontend
```
The app will be available at `http://localhost:3000` (redirects to `/fr`), with the API at `http://localhost:8000/api/v1`.

To run the frontend outside Docker (faster iteration):
```bash
cd frontend
npm install
cp .env.example .env.local   # sets NEXT_PUBLIC_API_URL
npm run dev
```

The backend container runs `alembic upgrade head` automatically on startup, applying the full schema
(companies, users, datasets, dataset_columns, cleaning_runs, analysis_jobs, models, forecasts,
segments, kpis, decisions, reports).

### Seed demo data
```bash
docker-compose exec backend python -m app.db.seed
```
This creates:
- Demo company: **Demo Algérie Retail**
- Demo owner login: `demo@smartmarket.dz` / `Demo12345!`
- A synthetic-but-realistic Algerian retail CSV at `storage/uploads/demo_sales_algeria.csv`
  (date, region, product, price, quantity, marketing_spend, marketing_spend_2, customer_id, sales —
  with injected missing values, one outlier, and a deliberately collinear feature pair for later
  cleaning/VIF-FAIL demos). Upload it via `POST /api/v1/datasets` to exercise the pipeline.

### Running backend tests locally (no Docker required)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
Tests run against an in-memory SQLite DB (via portable `GUID`/`JSONBType` column types) and a temp
upload directory, so they need no running Postgres/Redis.

### Running frontend tests locally
```bash
cd frontend
npm install
npm test          # Vitest + React Testing Library
npm run build      # full production build + type-check
```

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | JWT signing secret — **must** be changed in any non-local environment | `CHANGE_ME...` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `DATABASE_URL` | Async (asyncpg) connection string used by the app | see `.env.example` |
| `DATABASE_URL_SYNC` | Sync (psycopg2) connection string used by Alembic | see `.env.example` |
| `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis + Celery wiring | see `.env.example` |
| `CORS_ORIGINS` | Allowed frontend origins (JSON array) | `["http://localhost:3000"]` |
| `UPLOAD_DIR` / `REPORT_DIR` | On-disk storage paths (mounted as a Docker volume) | `/app/storage/...` |
| `MAX_UPLOAD_SIZE_MB` | Upload size cap | `200` |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Rate limit on `/auth/*` endpoints | `10` |
| `NEXT_PUBLIC_API_URL` | Frontend → backend base URL | `http://localhost:8000/api/v1` |

## Repository layout
See `backend/app/` and `frontend/src/` for the full structure (matches the mandated layout: `core/`,
`api/v1/`, `models/`, `schemas/`, `services/{cleaning,analytics,decision,reports}/`, `jobs/`, `db/`).

## API reference
Full OpenAPI schema is auto-generated by FastAPI at `/api/v1/openapi.json`; interactive docs at `/api/v1/docs`.

## What's left

- **Frontend pages**: all 13 pages are now built and functional against the real API (auth, datasets, cleaning,
  analytics workspace, KPIs, decisions, reports, settings) — see "What works right now" above for details.
- **Bayesian & Panel Data (Phase 9)**: interface-only, as scoped — `backend/app/services/analytics/bayesian.py` and
  `panel_data.py` define the typed abstract contracts (`BayesianRegressionService`, `PanelDataService`) with full
  docstrings on inputs/outputs, but raise `NotImplementedError`. No real Bayesian/panel logic exists yet; that's
  correct per section 4.2 (explicitly out of MVP scope), but worth flagging so it's not mistaken for a gap.
- **Celery async dispatch**: every analytics/cleaning job is currently executed synchronously inside the request
  while still writing the `queued→running→completed` status transitions to the DB. The Celery app scaffold exists
  (`app/jobs/celery_app.py`, `worker` service in `docker-compose.yml`) but no task is actually dispatched to it yet.
  Fine for the current dataset sizes; would need revisiting before large production datasets or truly long-running
  forecasts. Correspondingly, the frontend calls these endpoints synchronously too (spinner + disabled button while
  the request is in flight) rather than polling `GET /jobs/{id}` with a progress bar — that SSE/polling UX from
  section 12.3 is real future work once true async dispatch exists; building it now would be UI for a backend
  behavior that doesn't exist yet.
- **Automated web scraping / live connectors, e-commerce & social APIs**: explicitly out of MVP scope (section 4.2).
- **Playwright E2E smoke test**: written (`e2e/smoke.spec.ts`, the exact login → upload → clean → descriptive →
  regression path from section 15, selectors verified against real component source) but not executed — this
  sandbox can't reach `cdn.playwright.dev` to install browser binaries. Run `npx playwright install chromium && npm
  run test:e2e` yourself against a running stack to actually exercise it; treat it as unverified until then.
- **shadcn/ui Toast notifications, dark mode toggle**: not wired up in the frontend, though the design tokens already
  support a dark theme (`.dark` block in `globals.css`) and `@radix-ui/react-toast` is already a dependency.
- **Decision status actions** (acknowledge/apply/dismiss, mentioned in section 11): the Decisions page displays
  generated recommendations but the corresponding `PATCH` endpoint to change a decision's `status` doesn't exist in
  the backend yet, so the frontend has nothing to call. A real, not-yet-addressed gap on both sides.

