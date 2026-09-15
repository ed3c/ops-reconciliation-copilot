"""Transactional run storage: local SQLite or hosted PostgreSQL."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

SCHEMA = "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT NOT NULL)"


class RunStore:
    def __init__(self, db, postgres, write):
        self.db = db
        self.postgres = postgres
        self.write = write
        self.marker = "%s" if postgres else "?"

    def read(self, run_id):
        lock = " FOR UPDATE" if self.postgres and self.write else ""
        row = self.db.execute(
            f"SELECT data FROM runs WHERE id={self.marker}" + lock, (run_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Run not found")
        return json.loads(row[0])

    def insert(self, run_id, data):
        self.db.execute(
            f"INSERT INTO runs (id,data) VALUES ({self.marker},{self.marker})",
            (run_id, json.dumps(data)),
        )

    def save(self, run_id, data):
        self.db.execute(
            f"UPDATE runs SET data={self.marker} WHERE id={self.marker}",
            (json.dumps(data), run_id),
        )


@contextmanager
def connect(write=False):
    url = os.environ.get("DATABASE_URL")
    if url:
        import psycopg
        # A fresh connection per request works with a provider's pooled URL.
        # Schema is initialized explicitly before serving traffic.
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None) as db:
            db.execute("SET LOCAL statement_timeout = '15s'")
            db.execute("SET LOCAL lock_timeout = '10s'")
            yield RunStore(db, postgres=True, write=write)
        return
    if os.environ.get("VERCEL"):
        raise HTTPException(503, "Hosting setup incomplete: configure DATABASE_URL")
    path = Path(os.environ.get("RECON_DB", "var/reconciliation.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.execute(SCHEMA)
        db.commit()
        with db:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield RunStore(db, postgres=False, write=write)
    finally:
        db.close()
