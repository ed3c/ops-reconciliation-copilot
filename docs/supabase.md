# Supabase setup

Use a dedicated Supabase project for this prototype. The existing FastAPI backend connects using psycopg; no Supabase SDK or browser database key is needed.

1. Create or select the dedicated project. Use a region close to the Vercel function.
2. In Connect, copy the Transaction pooler PostgreSQL connection string for the Vercel runtime. Replace the password placeholder correctly; URL-encode password characters when constructing a URI. Keep the provider's TLS settings.
3. Add DATABASE_URL in Vercel's Production environment. This must be a PostgreSQL connection URI, not the Supabase project HTTPS URL or an anon/service-role API key.
4. Add the connection string for this SAME database as repository Actions secret DATABASE_URL. A Session pooler connection is also suitable for initialization on IPv4 GitHub runners.
5. In GitHub Actions select Initialize cloud database, then Run workflow on main. It creates the runs table if missing, enables RLS, revokes PUBLIC/anon/authenticated table grants and verifies schema access. It does not delete rows, create test fixtures or copy local SQLite data. Use the table owner for initialization and the current backend connection; unprivileged roles have no RLS policies.
6. Set OPENROUTER_API_KEY and OPENROUTER_MODEL in Vercel if suggestions are wanted, then redeploy.
7. Verify /ready returns 200 and perform the complete upload, mapping, review and export demo.

The cloud initializer is manual and main-only. PR tests only use a disposable PostgreSQL container and do not receive the production database secret. Ordinary pushes do not initialize the cloud database.

RLS here blocks direct database client roles; it does NOT authenticate FastAPI users or isolate tenants. The app remains a single-user prototype. Existing policies in an unrelated database are not removed; therefore use a dedicated database/table. Keep database credentials server-side and use deployment protection for private data.

CI executes initialization twice to check repeatability, exercises unprivileged read/write denial with a temporary role, and runs the existing database and browser verifiers. Supabase-specific hosted behavior still requires live validation.

Sources: [Connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
