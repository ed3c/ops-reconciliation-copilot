"""Offline by default. `live` explicitly sends only the four synthetic header cases."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llm import ProposalError
from research.jev import build_request, decode_response, digest, evaluate_live


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("offline", "live"), default="offline")
    args = parser.parse_args(argv)
    dataset = ROOT / "evals/cases.jsonl"
    raw = dataset.read_bytes()
    cases = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    # Fixed smoke suite; expanding paid-call scope requires a reviewed change.
    if len(cases) != 4 or len({c["id"] for c in cases}) != 4:
        raise SystemExit("Expected exactly four unique synthetic cases")
    model = os.environ.get("TYPESAFE_MODEL", "jev-1.13.0")
    report = {"schema": 1, "mode": args.mode, "status": "not_run", "live_provider": False,
              "authorizes_execution": False, "authorizes_landing": False,
              "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "dataset_sha256": hashlib.sha256(raw).hexdigest(), "requested_model": model,
              "checkout_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              capture_output=True, text=True).stdout.strip(),
              "working_tree_dirty": bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                                         capture_output=True, text=True).stdout),
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                                ("research/jev.py", "scripts/research.py", "app/llm.py")},
              "requests_attempted": 0, "cases": []}
    exit_code = 0
    try:
        requests = [build_request(c["headers"], model) for c in cases]
        if args.mode == "live" and not os.environ.get("TYPESAFE_API_KEY"):
            raise ProposalError("not_configured")
        for case, request in zip(cases, requests):
            item = {"id": case["id"], "request_sha256": digest(request),
                    "questions": len(request["questions"])}
            report["cases"].append(item)
            if args.mode == "live":
                report["requests_attempted"] += 1
                result = evaluate_live(request, os.environ["TYPESAFE_API_KEY"])
                report["live_provider"] = True
                # Revalidate in the consumer; transport success is not verdict success.
                actual = decode_response(result["response"], request)
                expected = case["expected"]
                item.update(result)
                item["passed"] = actual["status"] == expected["status"] and (
                    expected["status"] == "clarify" or actual["mapping"] == expected["mapping"])
        if args.mode == "offline":
            report["reason"] = "Offline request validation only; no model invoked or accuracy measured"
            report["offline_request_validation"] = "passed"
        else:
            report["status"] = "completed"
            report["passed"] = sum(c["passed"] for c in report["cases"])
            exit_code = 0 if report["passed"] == len(cases) else 1
    except ProposalError as error:
        report["status"] = "failed" if report["requests_attempted"] else "not_run"
        report["reason"] = error.code
        exit_code = 1 if report["requests_attempted"] else 2
    directory = ROOT / "evidence/research"
    directory.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=directory)) / "report.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "reason": report.get("reason"),
                      "report": str(target), "live_provider": report["live_provider"]}))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
