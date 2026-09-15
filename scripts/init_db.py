"""Initialize backend-only PostgreSQL storage without exposing credentials."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.storage import SCHEMA


def initialize():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("NOT RUN: DATABASE_URL is missing", file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None) as db:
            db.execute("SET LOCAL statement_timeout = '15s'")
            db.execute("SET LOCAL lock_timeout = '10s'")
            db.execute(SCHEMA)
            db.execute("ALTER TABLE runs ENABLE ROW LEVEL SECURITY")
            db.execute("REVOKE ALL ON TABLE runs FROM PUBLIC")
            for role in ("anon", "authenticated"):
                if db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                    db.execute(sql.SQL("REVOKE ALL ON TABLE runs FROM {}").format(sql.Identifier(role)))
            db.execute("SELECT id, data FROM runs LIMIT 0")
        print("Database schema ready; direct client access disabled")
        return 0
    except psycopg.Error:
        print("Database initialization failed; check credentials, connectivity and table ownership", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(initialize())
