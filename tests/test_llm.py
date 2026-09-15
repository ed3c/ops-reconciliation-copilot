import io
import json
import os
import unittest
from unittest.mock import patch
from app.llm import ProposalError, propose, validate

HEADERS = {"left": ["id", "amount", "ccy"], "right": ["ref", "paid", "currency"]}
GOOD = {"status": "proposed", "mapping": {
    "left": {"transaction_id": "id", "amount": "amount", "currency": "ccy"},
    "right": {"transaction_id": "ref", "amount": "paid", "currency": "currency"}}, "question": None}


class FakeOpener:
    def __init__(self, result):
        self.result = result
    def open(self, req, timeout):
        assert timeout == 10
        body = json.loads(req.data)
        assert json.loads(body["messages"][0]["content"]) == HEADERS
        assert body["max_tokens"] == 600
        if isinstance(self.result, Exception):
            raise self.result
        return io.BytesIO(self.result)


class LLMContract(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(GOOD, HEADERS), GOOD)

    def test_unknown_column(self):
        bad = json.loads(json.dumps(GOOD))
        bad["mapping"]["left"]["amount"] = "invented"
        with self.assertRaisesRegex(ProposalError, "unknown_column"):
            validate(bad, HEADERS)

    def test_duplicate_column(self):
        bad = json.loads(json.dumps(GOOD))
        bad["mapping"]["left"]["amount"] = "id"
        with self.assertRaisesRegex(ProposalError, "duplicate_column"):
            validate(bad, HEADERS)

    def test_clarification(self):
        value = {"status": "clarify", "mapping": None, "question": "Which column is the ID?"}
        self.assertEqual(validate(value, HEADERS), value)

    def test_malformed(self):
        for value in (None, [], {}, {"status": "execute", "mapping": None, "question": None}):
            with self.subTest(value=value), self.assertRaises(ProposalError):
                validate(value, HEADERS)

    def test_unconfigured(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ProposalError, "not_configured"):
            propose(HEADERS)

    def test_transport_and_bad_json(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only", "ANTHROPIC_MODEL": "test-model"}):
            for result in (TimeoutError(), b"not-json"):
                with self.subTest(result=str(result)), patch("urllib.request.build_opener", return_value=FakeOpener(result)), self.assertRaises(ProposalError):
                    propose(HEADERS)

    def test_provider_envelope(self):
        response = json.dumps({"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(GOOD)}], "usage": {"input_tokens": 20, "output_tokens": 40}}).encode()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only", "ANTHROPIC_MODEL": "test-model", "ANTHROPIC_MESSAGES_URL": "http://127.0.0.1:9999/v1/messages"}), patch("urllib.request.build_opener", return_value=FakeOpener(response)):
            result = propose(HEADERS)
        self.assertEqual(result["proposal"], GOOD)
        self.assertFalse(result["metadata"]["live_provider"])

if __name__ == "__main__":
    unittest.main()
