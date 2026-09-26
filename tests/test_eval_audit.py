import copy
import hashlib
import json
from pathlib import Path
import unittest

from evals.audit import audit_report

ROOT = Path(__file__).resolve().parents[1]
DATASET = (ROOT / "evals/cases.jsonl").read_bytes()
CASES = [json.loads(line) for line in DATASET.splitlines()]
DATASET_SHA = hashlib.sha256(DATASET).hexdigest()
REPORT = json.loads((ROOT / "docs/evidence/2026-09-15-luna-medium.json").read_text())


class EvidenceScopeAudit(unittest.TestCase):
    def test_historical_report_has_narrow_scope(self):
        result = audit_report(REPORT, CASES, DATASET_SHA, "new-checkout")
        self.assertEqual(result["exact_mapping"], {"passed": 2, "total": 2})
        self.assertEqual(result["clarify_status"], {"passed": 2, "total": 2})
        self.assertEqual(result["clarify_question_quality"], "not_assessed")
        self.assertFalse(result["source_is_current_checkout"])
        self.assertFalse(result["product_correctness_supported"])

    def test_planted_false_pass_is_detected(self):
        corrupted = copy.deepcopy(REPORT)
        corrupted["cases"][0]["actual"]["mapping"]["left"]["amount"] = "currency"
        with self.assertRaisesRegex(ValueError, "stored pass disagrees"):
            audit_report(corrupted, CASES, DATASET_SHA, "new-checkout")

    def test_irrelevant_question_cannot_gain_quality_claim(self):
        corrupted = copy.deepcopy(REPORT)
        corrupted["cases"][2]["actual"]["question"] = "What is the weather?"
        result = audit_report(corrupted, CASES, DATASET_SHA, "new-checkout")
        self.assertEqual(result["clarify_status"], {"passed": 2, "total": 2})
        self.assertEqual(result["clarify_question_quality"], "not_assessed")
        self.assertFalse(result["product_correctness_supported"])

    def test_report_must_match_dataset_and_provider_metadata(self):
        with self.assertRaisesRegex(ValueError, "dataset or prompt hash"):
            audit_report(REPORT, CASES, "wrong-dataset", "new-checkout")
        corrupted = copy.deepcopy(REPORT)
        corrupted["cases"][0]["metadata"]["live_provider"] = False
        with self.assertRaisesRegex(ValueError, "provenance"):
            audit_report(corrupted, CASES, DATASET_SHA, "new-checkout")


if __name__ == "__main__":
    unittest.main()
