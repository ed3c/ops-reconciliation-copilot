"""Small hand-labeled live smoke evaluation, not a production accuracy estimate."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llm import PROMPT_SHA, ProposalError, configured, propose

out = ROOT / "evidence/live-eval.json"
out.parent.mkdir(exist_ok=True)
dataset = ROOT / "evals/cases.jsonl"
report = {"status": "not_run", "live_llm": False, "model": os.environ.get("ANTHROPIC_MODEL"),
          "prompt_sha": PROMPT_SHA, "dataset_sha": hashlib.sha256(dataset.read_bytes()).hexdigest(),
          "checkout_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
          "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "cases": []}
if not configured():
    report["reason"] = "ANTHROPIC_API_KEY and ANTHROPIC_MODEL are required"
    out.write_text(json.dumps(report, indent=2))
    print("NOT RUN: live model configuration missing")
    sys.exit(2)
if os.environ.get("ANTHROPIC_MESSAGES_URL", "https://api.anthropic.com/v1/messages") != "https://api.anthropic.com/v1/messages":
    raise SystemExit("Live evaluation requires the official provider endpoint")
for line in dataset.read_text().splitlines():
    case = json.loads(line)
    item = {"id": case["id"], "passed": False}
    try:
        result = propose(case["headers"])
        actual = result["proposal"]
        expected = case["expected"]
        item.update(actual=actual, metadata=result["metadata"])
        item["passed"] = actual["status"] == expected["status"] and (
            expected["status"] == "clarify" or actual["mapping"] == expected["mapping"])
        report["live_llm"] = True
    except ProposalError as error:
        item["error"] = error.code
    report["cases"].append(item)
report["status"] = "completed"
report["passed"] = sum(c["passed"] for c in report["cases"])
report["total"] = len(report["cases"])
out.write_text(json.dumps(report, indent=2))
print(f"Live smoke evaluation: {report['passed']}/{report['total']}; live_llm={report['live_llm']}")
sys.exit(0 if report["passed"] == report["total"] else 1)
