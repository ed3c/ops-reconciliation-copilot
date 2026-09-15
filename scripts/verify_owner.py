"""Real HTTP access checks using a local RSA issuer, not live Google login."""
import http.cookiejar
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
from auth_test_support import environment, keys, token, EMAIL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/owner-access"
OUT.mkdir(parents=True, exist_ok=True)
checks = []
PRIVATE = [("GET", "/ready"), ("GET", "/capabilities"), ("GET", "/auth/me"),
           ("GET", "/docs"), ("GET", "/openapi.json"), ("GET", "/runs/private"),
           ("GET", "/runs/private/export"), ("POST", "/runs"),
           ("PUT", "/runs/private/mapping"), ("POST", "/runs/private/reconcile"),
           ("PUT", "/runs/private/reviews/F001"), ("POST", "/runs/private/mapping-proposal")]


def verify(config):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory() as tmp, (OUT / (config + ".log")).open("w") as log:
        key, public = keys(tmp)
        env = {**os.environ, **environment(public), "DATABASE_URL": "",
               "OPENROUTER_API_KEY": "fake-must-not-be-called", "OPENROUTER_MODEL": "fake",
               "OPENROUTER_CHAT_URL": "http://127.0.0.1:1/never"}
        if config == "missing":
            env.update(VERCEL="1", GOOGLE_CLIENT_ID="", AUTH_SESSION_SECRET="")
        server = subprocess.Popen([sys.executable, "-m", "uvicorn",
            "scripts.auth_test_support:app_factory", "--factory", "--host", "127.0.0.1",
            "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=log)
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        def request(path, method="GET", headers=None, body=None):
            headers = dict(headers or {})
            if body is not None:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(base + path, method=method, headers=headers,
                data=json.dumps(body).encode() if body is not None else None)
            try:
                response = opener.open(req, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, response.headers, response.read()

        def login(**claims):
            status, headers, raw = request("/auth/config")
            assert status == 200
            assert "HttpOnly" in headers["Set-Cookie"] and "SameSite=lax" in headers["Set-Cookie"]
            nonce = json.loads(raw)["nonce"]
            return request("/auth/google", "POST", {"X-Recon-Request": "1", "Origin": base},
                           {"credential": token(key, nonce, **claims)})

        try:
            for _ in range(100):
                try:
                    if request("/health")[0] == 200: break
                except OSError: time.sleep(.1)
            else: raise RuntimeError("Owner test server did not start")
            assert request("/")[0] == 200
            status, headers, raw = request("/workspace")
            assert status == 200 and b"/login.js" in raw and b"/app.js" not in raw
            assert "no-store" in headers["Cache-Control"]
            assert request("/showcase.csv")[2] == (ROOT / "tests/fixtures/expected-export.csv").read_bytes()
            expected = 503 if config == "missing" else 401
            for method, path in PRIVATE:
                status, headers, _ = request(path, method)
                assert status == expected, (config, method, path, status)
                assert "no-store" in headers["Cache-Control"]
            assert request("/capabilities", headers={"Authorization": "Basic b3duZXI6cGFzcw=="})[0] == expected
            checks.append(config + ": public showcase/login; every private API blocked before DB/provider")
            if config == "missing":
                assert request("/auth/config")[0] == 503
                return
            assert login(email="other@gmail.com", sub="other-user")[0] == 403
            assert login(email_verified=False)[0] == 401
            assert login(aud="wrong-client")[0] == 401
            assert login(iss="https://attacker.invalid")[0] == 401
            assert login(exp=int(time.time()) - 60, iat=int(time.time()) - 3600)[0] == 401
            request("/auth/config")
            assert request("/auth/google", "POST", {"X-Recon-Request": "1"},
                           {"credential": token(key, "wrong-nonce")})[0] == 403
            request("/auth/config")
            assert request("/auth/google", "POST", {"X-Recon-Request": "1"},
                           {"credential": "forged.jwt.value"})[0] == 401
            assert request("/auth/google", "POST", body={"credential": "x"})[0] == 403
            assert request("/auth/google", "POST", {"X-Recon-Request": "1", "Origin": "https://evil.test"},
                           {"credential": "x"})[0] == 403
            checks.append("configured: other account 403; invalid signature/audience/issuer/expiry/unverified email and nonce rejected")
            status, headers, _ = login()
            assert status == 200, status
            assert "HttpOnly" in headers["Set-Cookie"] and "SameSite=lax" in headers["Set-Cookie"]
            assert json.loads(request("/auth/me")[2])["email"] == EMAIL
            assert b"Upload records" in request("/workspace")[2]
            assert request("/capabilities")[0] == 200
            assert request("/runs", "POST")[0] == 403
            assert request("/runs", "POST", {"X-Recon-Request": "1", "Origin": "https://evil.test"})[0] == 403
            assert request("/runs", "POST", {"X-Recon-Request": "1", "Origin": base})[0] == 422
            assert request("/auth/logout", "POST", {"X-Recon-Request": "1"})[0] == 200
            assert request("/capabilities")[0] == 401
            checks.append("configured: owner session accepted, mutation CSRF blocked, logout removes browser access")
        finally:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()


verify("missing")
verify("configured")
(OUT / "result.json").write_text(json.dumps({"passed": True, "checks": checks,
    "live_google": False, "live_llm": False}, indent=2))
print("PASS:", "; ".join(checks))
