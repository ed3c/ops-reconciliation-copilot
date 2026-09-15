# Vercel deployment

The same FastAPI application and browser UI run on Vercel. Local development defaults to SQLite; hosted storage uses PostgreSQL via DATABASE_URL. A hosted request without DATABASE_URL returns HTTP 503 instead of falling back to an ephemeral SQLite file.

## Configure the hosted project

1. Import ed3c/ops-reconciliation-copilot into Vercel, using the repository root and FastAPI framework preset. Python is pinned to 3.12.
2. Connect a dedicated Supabase PostgreSQL database using the [Supabase setup](supabase.md) (Neon or another PostgreSQL provider also works). Set DATABASE_URL in the deployment environment. A pooled provider URL is supported; use the provider's TLS settings.
3. Initialize the schema once from a trusted shell with DATABASE_URL exported:

   ```sh
   python -m pip install -r requirements.txt
   python scripts/init_db.py
   ```

   The script creates the runs table if absent and enables backend-only database access with RLS and client grant revocation. It does not migrate or copy local SQLite data. Do not point it at an unrelated database.
4. For optional suggestions, set OPENROUTER_API_KEY and OPENROUTER_MODEL=openai/gpt-5.6-luna in Vercel. GitHub Actions secrets are not automatically Vercel environment variables.
5. Set RECON_OWNER_PASSWORD to a unique random password of at least 32 characters in Production and Preview, then deploy. Sign in at /workspace as owner. Missing owner configuration fails closed. Configure Vercel Authentication with Standard Protection for generated/older deployment URLs while keeping the production showcase public; see [owner access](owner-access.md). This is a single-owner application, not multi-tenant authorization.
6. Check public /health (process liveness); /ready (database access/schema) requires owner authentication. The home page is a static showcase. Follow [the complete demo](demo.md) at /workspace to verify the private workflow.

Never put database credentials or API keys in vercel.json, browser code, logs or commits. The deployment excludes local databases, environment files and test artifacts.

## Persistence and concurrency

Each request opens a database connection and closes it after commit or rollback. PostgreSQL mutation reads use SELECT FOR UPDATE to serialize updates to the same run across function instances. LLM network calls occur outside the storage transaction. SQLite retains BEGIN IMMEDIATE for local mutations.

CI runs the existing HTTP/restart, browser and fake-provider checks against both SQLite and a real PostgreSQL 16 service. A separate PostgreSQL verifier injects a transaction failure to check rollback and uses two OS processes to check that 20 increments remain 20. Hosted missing configuration is tested separately.

These checks do not prove power-loss durability, hosted network resilience, tenant isolation or live-model browser behavior. A deployment build success alone does not prove database readiness.

Sources: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [SQLite limitations](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
