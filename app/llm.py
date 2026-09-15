"""Optional header-only mapping proposals. No model output has execution authority."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

PROMPT = (Path(__file__).parent / "prompts/mapping.txt").read_text()
PROMPT_SHA = hashlib.sha256(PROMPT.encode()).hexdigest()
FIELDS = {"transaction_id", "amount", "currency"}


class ProposalError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("ANTHROPIC_MODEL"))


def validate(value, headers):
    if not isinstance(value, dict) or set(value) != {"status", "mapping", "question"}:
        raise ProposalError("invalid_output")
    if value["status"] == "clarify":
        if value["mapping"] is not None or not isinstance(value["question"], str) or not 1 <= len(value["question"].strip()) <= 500:
            raise ProposalError("invalid_output")
    elif value["status"] == "proposed":
        mapping = value["mapping"]
        if value["question"] is not None or not isinstance(mapping, dict) or set(mapping) != {"left", "right"}:
            raise ProposalError("invalid_output")
        for side in ("left", "right"):
            cols = mapping[side]
            if not isinstance(cols, dict) or set(cols) != FIELDS:
                raise ProposalError("invalid_output")
            if not all(isinstance(v, str) and v in headers[side] for v in cols.values()):
                raise ProposalError("unknown_column")
            if len(set(cols.values())) != 3:
                raise ProposalError("duplicate_column")
    else:
        raise ProposalError("invalid_output")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def propose(headers):
    if not configured():
        raise ProposalError("not_configured")
    # Keep requests finite and send no transaction records or amounts.
    if set(headers) != {"left", "right"} or any(len(cols) > 100 or any(len(c) > 200 for c in cols) for cols in headers.values()):
        raise ProposalError("input_too_large")
    endpoint = os.environ.get("ANTHROPIC_MESSAGES_URL", "https://api.anthropic.com/v1/messages")
    if endpoint != "https://api.anthropic.com/v1/messages" and not endpoint.startswith("http://127.0.0.1:"):
        raise ProposalError("invalid_endpoint")
    payload = {"model": os.environ["ANTHROPIC_MODEL"], "max_tokens": 600,
               "system": PROMPT, "messages": [{"role": "user", "content": json.dumps(headers)}]}
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=10) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ProposalError("invalid_output")
        message = json.loads(raw)
        if message.get("stop_reason") != "end_turn":
            raise ProposalError("incomplete_output")
        blocks = message["content"]
        text = "".join(b["text"] for b in blocks if b["type"] == "text")
        value = validate(json.loads(text), headers)
        usage = message.get("usage", {})
        tokens = {k: usage[k] for k in ("input_tokens", "output_tokens") if type(usage.get(k)) is int and usage[k] >= 0}
    except urllib.error.HTTPError as error:
        raise ProposalError("provider_http_error") from error
    except (TimeoutError, urllib.error.URLError, OSError) as error:
        raise ProposalError("provider_unavailable") from error
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise ProposalError("invalid_output") from error
    return {"proposal": value, "metadata": {"provider": "anthropic", "model": payload["model"],
        "prompt_sha": PROMPT_SHA, "elapsed_ms": round((time.monotonic()-started)*1000),
        "usage": tokens, "live_provider": endpoint == "https://api.anthropic.com/v1/messages"}}
