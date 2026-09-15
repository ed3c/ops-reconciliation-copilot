"""Verify rollback and concurrent updates using independent OS processes."""
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.storage import connect


def increment(run_id, barrier):
    barrier.wait(timeout=15)
    for _ in range(10):
        with connect(write=True) as store:
            data = store.read(run_id)
            data["count"] += 1
            store.save(run_id, data)


if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("This verifier requires a real PostgreSQL database")
    run_id = str(uuid.uuid4())
    with connect(write=True) as store:
        store.insert(run_id, {"count": 0})
    try:
        with connect(write=True) as store:
            data = store.read(run_id)
            data["count"] = 999
            store.save(run_id, data)
            raise ValueError("injected failure before commit")
    except ValueError:
        pass
    with connect() as store:
        assert store.read(run_id) == {"count": 0}, "Rollback failed"
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(2)
    workers = [ctx.Process(target=increment, args=(run_id, barrier)) for _ in range(2)]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=45)
            assert worker.exitcode == 0, "Concurrent worker failed or timed out"
        with connect() as store:
            assert store.read(run_id) == {"count": 20}, "Lost a concurrent update"
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join()
    out = ROOT / "evidence"
    out.mkdir(exist_ok=True)
    (out / "postgres.json").write_text(json.dumps({
        "rollback": True, "two_process_updates": 20, "lost_updates": 0,
        "run_id": os.environ.get("GITHUB_RUN_ID"), "live_llm": False
    }, indent=2))
    print("PASS: PostgreSQL rollback and two-process concurrent updates")
