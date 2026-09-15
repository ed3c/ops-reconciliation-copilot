"""Real HTTP access tests. No paid provider requests or real credentials."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/owner-access"
OUT.mkdir(parents=True, exist_ok=True)
PASSWORD = "ci-only-owner-password-not-a-real-secret"
AUTH = "Basic " + base64.b64encode(("owner:" + PASSWORD).encode()).decode()
checks = []


def verify(config):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory() as tmp, (OUT / (config + ".log")).open("w") as log:
        env = {**os.environ, "VERCEL": "1", "DATABASE_URL": "",
               "RECON_DB": str(Path(tmp) / "unused.sqlite3"),
               "OPENROUTER_API_KEY": "fake-must-not-be-called",
               "OPENROUTER_MODEL": "fake-model",
               "OPENROUTER_CHAT_URL": "http://127.0.0.1:1/never",
               "RECON_OWNER_PASSWORD": PASSWORD if config == "configured" else ""}
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                                   "--host", "127.0.0.1", "--port", str(port)],
                                  cwd=ROOT, env=env, stdout=log, stderr=log)

        def request(path, method="GET", headers=None):
            req = urllib.request.Request(base + path, method=method, headers=headers or {})
            try:
                response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, response.headers, response.read()

        try:
            for _ in range(100):
                try:
                    if request("/health")[0] == 200:
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Owner test server did not start")
            status, _, body = request("/")
            assert status == 200 and b"read-only" in body and b"/app.js" not in body
            assert request("/showcase.csv")[2].decode().strip() == (
                ROOT / "tests/fixtures/expected-export.csv").read_text().strip()
            checks.append(config + ": public snapshot without database")
            expected = 401 if config == "configured" else 503
            for method, path in [
                ("GET", "/workspace"), ("GET", "/ready"), ("GET", "/capabilities"),
                ("GET", "/docs"), ("GET", "/openapi.json"),
                ("GET", "/runs/private"), ("GET", "/runs/private/export"),
                ("POST", "/runs"), ("PUT", "/runs/private/mapping"),
                ("POST", "/runs/private/reconcile"),
                ("PUT", "/runs/private/reviews/F001"),
                ("POST", "/runs/private/mapping-proposal"),
            ]:
                status, headers, _ = request(path, method)
                assert status == expected, (config, path, status)
                assert "no-store" in headers["Cache-Control"]
            checks.append(config + ": all private routes blocked before database or provider access")
            if config == "configured":
                for bad in ["Basic invalid", "Bearer fake", "Basic " + base64.b64encode(b"owner:wrong").decode()]:
                    assert request("/workspace", headers={"Authorization": bad})[0] == 401
                auth = {"Authorization": AUTH}
                status, headers, body = request("/workspace", headers=auth)
                assert status == 200 and b"Upload records" in body
                assert "no-store" in headers["Cache-Control"]
                assert json.loads(request("/capabilities", headers=auth)[2])["mapping_suggestions"] is True
                assert request("/runs", "POST", auth)[0] == 403
                csrf = {**auth, "X-Recon-Request": "1"}
                assert request("/runs", "POST", {**csrf, "Origin": "https://attacker.invalid"})[0] == 403
                assert request("/runs", "POST", {**csrf, "Sec-Fetch-Site": "cross-site"})[0] == 403
                assert request("/runs", "POST", {**csrf, "Origin": base})[0] == 422
                checks.append("configured: wrong credentials and CSRF blocked; owner reaches workspace and validation")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


verify("missing")
verify("configured")
(OUT / "result.json").write_text(json.dumps({"passed": True, "checks": checks, "live_llm": False}, indent=2))
print("PASS:", "; ".join(checks))
