"""Check real PostgreSQL permissions on the disposable CI database only."""
import os
import uuid
import psycopg
from psycopg import sql

with psycopg.connect(os.environ["DATABASE_URL"]) as db:
    role = "recon_probe_" + uuid.uuid4().hex[:12]
    db.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
    db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
    # Simulate a public API role with table grants; RLS must still hide rows.
    db.execute(sql.SQL("GRANT SELECT, INSERT ON runs TO {}").format(sql.Identifier(role)))
    db.execute("INSERT INTO runs VALUES (%s,%s)", (str(uuid.uuid4()), '{"probe":true}'))
    db.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
    assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    denied = False
    try:
        with db.transaction():
            db.execute("INSERT INTO runs VALUES (%s,%s)", (str(uuid.uuid4()), '{}'))
    except psycopg.errors.InsufficientPrivilege:
        denied = True
    assert denied, "Unprivileged role inserted a row"
    db.execute("RESET ROLE")
    assert db.execute("SELECT count(*) FROM runs").fetchone()[0] > 0
    # Remove all probe data, grants and role together.
    db.rollback()
print("PASS: unprivileged read/write denied; backend owner access preserved")
