"""Synthetic transport/decision controls, NOT live-model accuracy evidence."""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error

from app.llm import ProposalError
from research.jev import ABSTAIN, ENDPOINT, build_request, decode_response, evaluate_live

ROOT = Path(__file__).resolve().parents[1]
MODEL = "jev-1.13.0"
HEADERS = {"left": ["txn_ref", "amount", "currency"],
           "right": ["reference_id", "paid", "ccy"]}
EXPECTED = {"status": "proposed", "question": None, "mapping": {
    "left": {"transaction_id": "txn_ref", "amount": "amount", "currency": "currency"},
    "right": {"transaction_id": "reference_id", "amount": "paid", "currency": "ccy"}}}
# Explicit labels are independent of the implementation's field iteration.
LABELS = {"left_transaction_id": "column_0", "left_amount": "column_1", "left_currency": "column_2",
          "right_transaction_id": "column_0", "right_amount": "column_1", "right_currency": "column_2"}


def fixture():
    return {"model": MODEL, "usage": {"input_tokens": 100, "output_tokens": 20}, "answers": {
        key: {"type": "choice", "choice": label, "confidence": 0.95,
              "probabilities": {p: (1.0 if p == label else 0.0)
                                for p in ("column_0", "column_1", "column_2", ABSTAIN)}}
        for key, label in LABELS.items()}}


class JevTests(unittest.TestCase):
    def setUp(self):
        self.request = build_request(HEADERS, MODEL)
        self.response = fixture()

    def test_batched_header_only_and_no_mutation(self):
        headers = copy.deepcopy(HEADERS)
        request = build_request(headers, MODEL)
        self.assertEqual(set(request["questions"]), set(LABELS))
        self.assertEqual(request["state"], HEADERS)
        self.assertEqual(decode_response(self.response, request), EXPECTED)
        self.assertEqual(headers, HEADERS)
        self.assertEqual(self.response, fixture())
        request["state"]["left"].append("local mutation")
        self.assertEqual(headers, HEADERS)

    def test_header_validation_and_model_pin(self):
        for model in ("jev-latest", "jev-preview", "typesafe-ai/jev", None):
            with self.subTest(model=model), self.assertRaises(ProposalError):
                build_request(HEADERS, model)
        for bad in ({}, {**HEADERS, "rows": [{"secret": "private"}]},
                    {**HEADERS, "left": []}, {**HEADERS, "left": ["a", "a"]},
                    {**HEADERS, "left": [True]}, {**HEADERS, "left": "columns"},
                    {**HEADERS, "left": ["x" * 201]},
                    {**HEADERS, "left": [str(i) for i in range(101)]}):
            with self.subTest(bad=bad), self.assertRaises(ProposalError):
                build_request(bad, MODEL)

    def test_explicit_abstention(self):
        a = self.response["answers"]["left_currency"]
        a.update(choice=ABSTAIN, probabilities={p: float(p == ABSTAIN) for p in a["probabilities"]})
        result = decode_response(self.response, self.request)
        self.assertEqual(result["status"], "clarify")
        self.assertIsNone(result["mapping"])

    def test_probability_and_confidence_are_both_required(self):
        for change in ({"confidence": 0.89},
                       {"probabilities": {"column_0": .89, "column_1": .11, "column_2": 0, ABSTAIN: 0}}):
            response = fixture()
            response["answers"]["left_transaction_id"].update(change)
            self.assertEqual(decode_response(response, self.request)["status"], "clarify")

    def test_invalid_distributions_refused_even_after_abstention(self):
        for change in ({"choice": "invented"}, {"choice": "column_1"}, {"type": "score"},
                       {"confidence": True}, {"confidence": math.nan}, {"extra": "bad"},
                       {"probabilities": {"column_0": 1}},
                       *({"probabilities": {"column_0": p, "column_1": 0, "column_2": 0, ABSTAIN: 0}}
                         for p in (math.nan, math.inf, -1, 1.1, .5, True))):
            with self.subTest(change=change):
                response = fixture()
                response["answers"]["left_transaction_id"]["confidence"] = .1
                response["answers"]["right_currency"].update(change)
                with self.assertRaises(ProposalError):
                    decode_response(response, self.request)

    def test_duplicate_mapping_refused(self):
        self.response["answers"]["left_amount"] = copy.deepcopy(self.response["answers"]["left_transaction_id"])
        with self.assertRaisesRegex(ProposalError, "duplicate_column"):
            decode_response(self.response, self.request)

    def test_subject_shape_usage_refused(self):
        for change in ({"model": "jev-1.14.0"}, {"answers": {}}, {"usage": {}},
                       {"usage": {"input_tokens": True, "output_tokens": 1}},
                       {"usage": {"input_tokens": -1, "output_tokens": 1}}):
            with self.subTest(change=change), self.assertRaises(ProposalError):
                decode_response({**self.response, **change}, self.request)

    @patch("research.jev.urllib.request.build_opener")
    def test_one_call_bounded_response_and_no_redirect_handler(self, build):
        stream = build.return_value.open.return_value.__enter__.return_value
        stream.read.return_value = json.dumps(self.response).encode()
        result = evaluate_live(self.request, "synthetic-test-key")
        self.assertEqual(result["proposal"], EXPECTED)
        # live_provider describes the fixed transport endpoint; this patched call
        # remains a fixture, never a real provider receipt.
        req = build.return_value.open.call_args.args[0]
        self.assertEqual(req.full_url, ENDPOINT)
        self.assertEqual(json.loads(req.data), self.request)
        self.assertEqual(build.return_value.open.call_args.kwargs, {"timeout": 45})
        stream.read.assert_called_once_with(65537)
        handler = build.call_args.args[0]()
        self.assertIsNone(handler.redirect_request(None, None, 302, None, None, "https://evil.invalid"))
        self.assertEqual(build.return_value.open.call_count, 1)

    @patch("research.jev.urllib.request.build_opener")
    def test_unicode_transport_uses_the_validated_byte_budget(self, build):
        headers = {side: [str(i) + "欄" * 150 for i in range(15)] for side in ("left", "right")}
        request = build_request(headers, MODEL)
        self.assertGreater(len(json.dumps(request).encode()), 65536)
        stream = build.return_value.open.return_value.__enter__.return_value
        stream.read.return_value = b"{}"
        with self.assertRaises(ProposalError):
            evaluate_live(request, "synthetic-test-key")
        sent = build.return_value.open.call_args.args[0].data
        self.assertEqual(sent, json.dumps(request, ensure_ascii=False).encode())
        self.assertLessEqual(len(sent), 65536)
        with self.assertRaisesRegex(ProposalError, "input_too_large"):
            build_request({side: [str(i) + "欄" * 190 for i in range(25)]
                           for side in ("left", "right")}, MODEL)

    @patch("research.jev.urllib.request.build_opener")
    def test_transport_failure_is_not_retried(self, build):
        for error in (TimeoutError(), urllib.error.HTTPError(ENDPOINT, 429, "rate", {}, None)):
            build.reset_mock()
            build.return_value.open.side_effect = error
            with self.assertRaises(ProposalError):
                evaluate_live(self.request, "synthetic-test-key")
            self.assertEqual(build.return_value.open.call_count, 1)

    @patch("research.jev.urllib.request.build_opener")
    def test_credentials_and_extra_state_refuse_before_network(self, build):
        with self.assertRaises(ProposalError):
            evaluate_live(self.request, "")
        self.request["state"]["rows"] = [{"secret": "not sent"}]
        with self.assertRaises(ProposalError):
            evaluate_live(self.request, "synthetic-test-key")
        build.assert_not_called()

    @patch("research.jev.urllib.request.build_opener")
    def test_oversize_and_invalid_json_refused(self, build):
        stream = build.return_value.open.return_value.__enter__.return_value
        for raw in (b"x" * 65537, b"not json"):
            stream.read.return_value = raw
            with self.assertRaises(ProposalError):
                evaluate_live(self.request, "synthetic-test-key")

    def test_cli_missing_key_has_no_live_claim(self):
        env = {k: v for k, v in os.environ.items() if k not in {"TYPESAFE_API_KEY", "TYPESAFE_MODEL"}}
        result = subprocess.run([sys.executable, "scripts/research.py", "live"], cwd=ROOT,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        output = json.loads(result.stdout)
        report = json.loads(Path(output["report"]).read_text())
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["live_provider"])
        self.assertEqual(report["requests_attempted"], 0)

    @patch("research.jev.urllib.request.build_opener", side_effect=AssertionError("offline network"))
    def test_offline_is_no_network_even_with_key(self, build):
        from scripts.research import main
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "synthetic", "TYPESAFE_MODEL": MODEL}):
            self.assertEqual(main([]), 0)
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
