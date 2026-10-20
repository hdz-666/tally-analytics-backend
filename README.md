# Tally Analytics — Backend

FastAPI service that serves stock, sales, purchases, ledger/P&L and forecast analytics from Tally data synced into Supabase Postgres. The frontend lives in [tally-analytics](https://github.com/hdz-666/tally-analytics).

- **Stack:** Python 3.12, FastAPI, asyncpg, pandas/numpy
- **Database:** Supabase Postgres (Tally data loaded via `tally-database-loader`)
- **Auth:** Supabase JWT — every `/api/*` route requires `Authorization: Bearer <access_token>`
- **Deploy:** Railway (`railway.toml`, `Procfile`)

## Project layout

```
app/
  core/          config (env settings), database pool, auth dependency
  routers/       HTTP endpoints: stock, sales, purchases, forecast, ledger
  repositories/  SQL queries against Postgres
  schemas/       Pydantic response models
  services/      forecasting logic
  scripts/       one-off jobs (geocode_parties.py)
  main.py        app entrypoint
sql/             schema + materialized view definitions (run in Supabase SQL editor)
tests/           api/ and unit/ pytest suites
```

## Getting started

### 1. Prerequisites

- Python **3.12** (see `.python-version`)
- Access to the Supabase project (database connection string + secret key)

### 2. Clone and create a virtual environment

```bash
git clone https://github.com/hdz-666/tally-analytics-backend.git
cd tally-analytics-backend

python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux / Git Bash
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Configure environment

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | — | Postgres connection string from Supabase (Project Settings → Database) |
| `SUPABASE_URL` | yes | — | `https://<project-ref>.supabase.co` — used to validate user tokens |
| `SUPABASE_SECRET_KEY` | yes | — | Supabase secret (service) key, sent as `apikey` when verifying tokens |
| `ALLOWED_ORIGINS` | no | `http://localhost:5173` | Comma-separated CORS origins (add your Vercel URL in prod) |
| `FORECAST_HORIZON_MONTHS` | no | `6` | Months ahead to forecast |
| `FORECAST_MIN_MONTHS` | no | `3` | Minimum months of history needed to forecast an item |
| `LEAD_TIME_MONTHS` | no | `1.0` | Supplier lead time used for reorder points |
| `SAFETY_STOCK_Z` | no | `1.65` | Z-score for safety stock (1.65 ≈ 95% service level) |

`.env` is gitignored — never commit real credentials.

### 4. Database setup (first time only)

Run the files in `sql/` in the Supabase SQL editor, in this order:

1. `views_phase1.sql` — Company A views and the `stock_forecast` table
2. `company_b_schema.sql` — Company B schema (then sync Company B with `tally-database-loader`)
3. `views.sql` — switches stock views to Company B data
4. `ledger_pnl.sql` — ledger analytics and P&L views
5. `geo_sales.sql` — area-wise sales tables/view

Then populate party locations for the area-wise sales map (safe to re-run after each data sync; it caches lookups):

```bash
python -m app.scripts.geocode_parties
```

> Company A has complete purchases but unsplit items; Company B has all billing with split items. Company B is the source of truth for sales and items.

### 5. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs

The frontend dev server proxies `/api` to `http://localhost:8000` by default.

### 6. Run tests

```bash
pytest
```

CI (`.github/workflows/ci.yml`) runs the same command on every push and pull request to `main`.

## Working on a branch

`main` is the deployed branch — don't commit to it directly.

```bash
git checkout main
git pull origin main
git checkout -b <short-feature-name>     # e.g. area-wise-sales, unit-test

# ...make changes, run pytest...

git add <files>
git commit -m "feat: add area wise sales"
git push -u origin <short-feature-name>
```

Then open a pull request into `main`. CI must pass before merging.

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `chore:`, `refactor:`, `docs:`.

If the change needs a new API field, keep the matching frontend branch in [tally-analytics](https://github.com/hdz-666/tally-analytics) under the same branch name and merge the backend first.

Dependabot opens weekly dependency PRs — review and merge them once CI is green.

## Deployment

Railway builds from `main` and starts the app with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set the same environment variables from the table above in the Railway service settings, with `ALLOWED_ORIGINS` including the production frontend URL. Railway health-checks `/health`.
