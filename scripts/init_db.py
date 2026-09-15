"""Initialize backend-only PostgreSQL storage without exposing credentials."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.storage import SCHEMA


def failure_category(error):
    # Inspect locally, emit only fixed categories. Never print libpq error text.
    state = getattr(error, "sqlstate", None)
    message = str(error).lower()
    if state in ("28P01", "28000") or "password authentication failed" in message:
        return "authentication_failed"
    if "tenant or user not found" in message:
        return "pooler_project_or_user_invalid"
    if "network is unreachable" in message:
        return "network_unreachable_use_ipv4_pooler"
    if "translate host name" in message or "name or service not known" in message:
        return "dns_resolution_failed"
    if "timeout" in message or "timed out" in message:
        return "connection_or_query_timeout"
    if "connection refused" in message:
        return "connection_refused"
    if state == "42501":
        return "insufficient_database_privileges"
    if state == "3D000":
        return "database_not_found"
    if "ssl" in message or "certificate" in message:
        return "tls_configuration_error"
    return "unclassified_database_error"


def initialize():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("NOT RUN: DATABASE_URL is missing", file=sys.stderr)
        return 2
    if not url.startswith(("postgresql://", "postgres://")):
        print("NOT RUN: DATABASE_URL must be a PostgreSQL URI, not an HTTPS project URL", file=sys.stderr)
        return 2
    try:
        info = psycopg.conninfo.conninfo_to_dict(url)
    except psycopg.Error:
        print("NOT RUN: invalid PostgreSQL URI; check password URL encoding", file=sys.stderr)
        return 2
    if not info.get("password") or "[YOUR-PASSWORD]" in info["password"]:
        print("NOT RUN: replace the database password placeholder in DATABASE_URL", file=sys.stderr)
        return 2
    stage = "connect"
    try:
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None) as db:
            stage = "schema"
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
    except psycopg.Error as error:
        print(f"Database initialization failed: stage={stage}; category={failure_category(error)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(initialize())
