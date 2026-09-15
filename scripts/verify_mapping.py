"""Real HTTP transport with a LOCAL FAKE provider. Not model-quality evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
GOOD = {"status": "proposed", "mapping": {
    "left": {"transaction_id": "txn_ref", "amount": "amount", "currency": "currency"},
    "right": {"transaction_id": "reference_id", "amount": "paid", "currency": "ccy"}}, "question": None}


class Handler(BaseHTTPRequestHandler):
    calls = 0
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert json.loads(body["messages"][0]["content"]) == {
            "left": ["txn_ref", "amount", "currency"], "right": ["reference_id", "paid", "ccy"]}
        Handler.calls += 1
        # First suggestion fails, second returns a valid proposal.
        if Handler.calls == 1:
            self.send_response(503)
            self.end_headers()
            return
        raw = json.dumps({"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(GOOD)}], "usage": {"input_tokens": 20, "output_tokens": 40}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    env = {**os.environ, "ANTHROPIC_API_KEY": "local-fake-only", "ANTHROPIC_MODEL": "fake-model",
           "ANTHROPIC_MESSAGES_URL": f"http://127.0.0.1:{server.server_port}/v1/messages",
           "VERIFY_FAKE_MAPPING": "1"}
    subprocess.run([sys.executable, "scripts/verify_browser.py"], cwd=ROOT, env=env, check=True)
    assert Handler.calls == 2, Handler.calls
finally:
    server.shutdown()
    server.server_close()
    thread.join()
print("PASS: local fake provider failure, recovery and human confirmation; live_llm=false")
