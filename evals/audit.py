"""Re-score a saved mapping eval and state exactly what its evidence covers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llm import PROMPT_SHA


def audit_report(report, cases, dataset_sha, current_checkout):
    if not isinstance(report, dict):
        raise ValueError("report must be a JSON object")
    if report.get("status") != "completed" or report.get("live_llm") is not True:
        raise ValueError("report is not a completed live-model evaluation")
    if report.get("dataset_sha") != dataset_sha or report.get("prompt_sha") != PROMPT_SHA:
        raise ValueError("report dataset or prompt hash differs from this checkout")
    if not report.get("model") or not report.get("checkout_sha"):
        raise ValueError("report lacks model or checkout identity")

    expected = {case["id"]: case for case in cases}
    observed = report.get("cases")
    if len(expected) != len(cases) or not isinstance(observed, list) or any(not isinstance(item, dict) for item in observed):
        raise ValueError("dataset has duplicate IDs or report cases are missing")
    if len(observed) != len(expected) or {item.get("id") for item in observed} != set(expected):
        raise ValueError("report case IDs differ from dataset")
    if report.get("total") != len(expected):
        raise ValueError("stored total differs from dataset")

    exact_mapping = 0
    clarify_status = 0
    failed = []
    for item in observed:
        case = expected[item["id"]]
        actual = item.get("actual")
        metadata = item.get("metadata")
        if not isinstance(actual, dict) or not isinstance(metadata, dict):
            raise ValueError(f"{item['id']}: missing actual output or metadata")
        if (metadata.get("live_provider") is not True or
                metadata.get("model") != report["model"] or
                metadata.get("prompt_sha") != report["prompt_sha"] or
                not metadata.get("response_model")):
            raise ValueError(f"{item['id']}: provider or model provenance is incomplete")
        target = case["expected"]
        if target["status"] == "proposed":
            passed = actual.get("status") == "proposed" and actual.get("mapping") == target["mapping"]
            exact_mapping += passed
        elif target["status"] == "clarify":
            passed = actual.get("status") == "clarify"
            clarify_status += passed
        else:
            raise ValueError(f"{item['id']}: unsupported expected status")
        if item.get("passed") is not passed:
            raise ValueError(f"{item['id']}: stored pass disagrees with independent re-score")
        if not passed:
            failed.append(item["id"])

    recomputed_passed = exact_mapping + clarify_status
    if report.get("passed") != recomputed_passed:
        raise ValueError("stored pass count disagrees with independent re-score")
    return {
        "status": "audited",
        "source_checkout": report["checkout_sha"],
        "current_checkout": current_checkout,
        "source_is_current_checkout": report["checkout_sha"] == current_checkout,
        "dataset_sha": dataset_sha,
        "prompt_sha": PROMPT_SHA,
        "model": report["model"],
        "exact_mapping": {"passed": exact_mapping, "total": sum(c["expected"]["status"] == "proposed" for c in cases)},
        "clarify_status": {"passed": clarify_status, "total": sum(c["expected"]["status"] == "clarify" for c in cases)},
        "clarify_question_quality": "not_assessed",
        "failed_cases": failed,
        "product_correctness_supported": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/evidence/2026-09-15-luna-medium.json")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/cases.jsonl")
    args = parser.parse_args()
    try:
        dataset_bytes = args.dataset.read_bytes()
        cases = [json.loads(line) for line in dataset_bytes.splitlines() if line.strip()]
        checkout = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                  capture_output=True, text=True).stdout.strip()
        result = audit_report(json.loads(args.report.read_text()), cases,
                              hashlib.sha256(dataset_bytes).hexdigest(), checkout)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"AUDIT FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if not result["failed_cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
