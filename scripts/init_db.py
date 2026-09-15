"""Initialize the hosted schema using a configured DATABASE_URL."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from app.storage import SCHEMA

if __name__ == "__main__":
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as db:
        db.execute(SCHEMA)
    print("Database schema ready")
