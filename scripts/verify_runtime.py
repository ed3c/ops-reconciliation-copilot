"""Run real HTTP/restart checks; no in-process API client or LLM mock."""
import csv
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
FIXTURES = ROOT / "tests/fixtures"
EVIDENCE.mkdir(exist_ok=True)
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
base = f"http://127.0.0.1:{port}"
server = None
log = (EVIDENCE / "server.log").open("w")
checks = []


def request(method, path, body=None, content_type="application/json", expected=200):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": content_type})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        assert response.status == expected, (path, response.status, raw)
        return json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw.decode()


def start(db):
    global server
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env={**os.environ, "RECON_DB": str(db)}, stdout=log, stderr=log,
    )
    for _ in range(100):
        if server.poll() is not None:
            raise RuntimeError("Server exited; see server.log")
        try:
            request("GET", "/health")
            return
        except (OSError, AssertionError):
            time.sleep(.1)
    raise RuntimeError("Server did not become ready")


def stop():
    if server is not None and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def upload(left=None, right=None, mode="transaction"):
    boundary = "reconciliation-test-boundary"
    parts = []
    for side, value in (("left", left), ("right", right)):
        raw = value if value is not None else (FIXTURES / f"{side}.csv").read_text()
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{side}"; filename="{side}.csv"\r\nContent-Type: text/csv\r\n\r\n{raw}\r\n')
    body = ("".join(parts) + f"--{boundary}--\r\n").encode()
    return request("POST", "/runs?mode=" + mode, body, f"multipart/form-data; boundary={boundary}", 201)["id"]


mapping = {
    "left": {"transaction_id": "txn_ref", "amount": "amount", "currency": "currency"},
    "right": {"transaction_id": "reference_id", "amount": "paid", "currency": "ccy"},
}


def check(name, fn):
    started = time.monotonic()
    try:
        fn()
        checks.append((name, time.monotonic() - started, None))
    except Exception:
        checks.append((name, time.monotonic() - started, traceback.format_exc()))
        raise


def equal_export(actual):
    expected = list(csv.reader(io.StringIO((FIXTURES / "expected-export.csv").read_text())))
    assert list(csv.reader(io.StringIO(actual))) == expected


try:
    with tempfile.TemporaryDirectory() as temp:
        db = Path(temp) / "runtime.sqlite3"
        start(db)
        run_id = upload()
        path = f"/runs/{run_id}"
        check("mapping_required", lambda: request("POST", path + "/reconcile", expected=409))
        request("PUT", path + "/mapping", mapping)
        actual = request("POST", path + "/reconcile")
        expected = json.loads((FIXTURES / "expected.json").read_text())
        def exact_findings():
            assert actual == expected, actual
        check("exact_findings_and_sources", exact_findings)
        def repeated():
            assert request("POST", path + "/reconcile") == expected
        check("repeat_reconciliation", repeated)
        request("PUT", path + "/reviews/F001", {"decision": "accepted", "reason": "Checked source rows"})
        stop()
        start(db)
        def persisted():
            data = request("GET", path)
            assert data["findings"] == expected
            assert data["reviews"]["F001"]["decision"] == "accepted"
        check("restart_persistence", persisted)
        check("mapping_frozen", lambda: request("PUT", path + "/mapping", mapping, expected=409))
        exported = request("GET", path + "/export")
        (EVIDENCE / "actual-export.csv").write_text(exported)
        check("export_matches_independent_oracle", lambda: equal_export(exported))
        def negative_control():
            corrupted = exported.replace("2.00", "200.00")
            try:
                equal_export(corrupted)
            except AssertionError:
                return
            raise AssertionError("Verifier accepted deliberately corrupted amount")
        check("negative_control_rejects_wrong_amount", negative_control)
        def duplicate():
            other = upload(left="txn_ref,amount,currency\nT100,100.00,USD\nT100,100.00,USD\n")
            request("PUT", f"/runs/{other}/mapping", mapping)
            result = request("POST", f"/runs/{other}/reconcile")
            assert len(result) == 1 and result[0]["type"] == "duplicate_key"
            assert result[0]["delta"] is None and len(result[0]["left"]) == 2
        check("duplicate_key_not_guessed", duplicate)
        def bad_amount():
            other = upload(left="txn_ref,amount,currency\nT100,NaN,USD\n")
            request("PUT", f"/runs/{other}/mapping", mapping, expected=422)
        check("invalid_amount_rejected", bad_amount)
        def currency():
            other = upload(right="reference_id,paid,ccy\nT100,98.00,EUR\n")
            request("PUT", f"/runs/{other}/mapping", mapping)
            result = request("POST", f"/runs/{other}/reconcile")
            assert result[0]["type"] == "currency_mismatch" and result[0]["delta"] is None
        check("cross_currency_not_subtracted", currency)
        def batch():
            batch_left = (FIXTURES / "batch-expected.csv").read_text()
            batch_right = (FIXTURES / "batch-bank.csv").read_text()
            batch_mapping = {"left": {"batch_id": "batch_ref", "payment_id": "payment_ref", "amount": "amount", "currency": "ccy"},
                             "right": {"batch_id": "batch_ref", "amount": "deposit", "currency": "ccy"}}
            batch_id = upload(batch_left, batch_right, mode="batch")
            route = f"/runs/{batch_id}"
            request("POST", route + "/mapping-proposal", expected=409)
            request("PUT", route + "/mapping", batch_mapping)
            findings = request("POST", route + "/reconcile")
            expected_batch = json.loads((FIXTURES / "batch-expected.json").read_text())
            assert findings == expected_batch["findings"]
            state = request("GET", route)
            assert state["matched_batches"] == expected_batch["matched_batches"]
            assert request("POST", route + "/reconcile") == findings
            request("PUT", route + "/reviews/F001", {"decision": "accepted", "reason": "Investigate bank difference"})
            assert request("GET", route)["reviews"]["F001"]["decision"] == "accepted"
            exported = list(csv.reader(io.StringIO(request("GET", route + "/export"))))
            assert exported[0] == ["finding_id", "type", "batch_id", "delta", "decision"]
            assert exported[1] == ["F001", "amount_mismatch", "B-200", "5.00", "accepted"]
            duplicate_bank = upload(batch_left, "batch_ref,deposit,ccy\nB-100,60.00,USD\nB-100,40.00,USD\n", mode="batch")
            request("PUT", f"/runs/{duplicate_bank}/mapping", batch_mapping)
            result = request("POST", f"/runs/{duplicate_bank}/reconcile")
            assert result[0]["type"] == "ambiguous_bank_batch"
            assert request("GET", f"/runs/{duplicate_bank}")["matched_batches"] == []
            duplicate_payment = upload("batch_ref,payment_ref,amount,ccy\nB-100,P-001,60.00,USD\nB-100,P-001,40.00,USD\n", batch_right, mode="batch")
            request("PUT", f"/runs/{duplicate_payment}/mapping", batch_mapping, expected=422)
            mixed_currency = upload("batch_ref,payment_ref,amount,ccy\nB-100,P-001,60.00,USD\nB-100,P-002,40.00,EUR\n", batch_right, mode="batch")
            request("PUT", f"/runs/{mixed_currency}/mapping", batch_mapping)
            result = request("POST", f"/runs/{mixed_currency}/reconcile")
            assert result[0]["type"] == "mixed_expected_currency" and result[0]["delta"] is None
            no_inferred_match = upload("batch_ref,payment_ref,amount,ccy\nB-999,P-001,100.00,USD\n",
                                       "batch_ref,deposit,ccy\nB-100,100.00,USD\n", mode="batch")
            request("PUT", f"/runs/{no_inferred_match}/mapping", batch_mapping)
            result = request("POST", f"/runs/{no_inferred_match}/reconcile")
            assert {item["type"] for item in result} == {"missing_expected", "missing_bank"}
        check("explicit_batch_settlement", batch)
finally:
    stop()
    log.close()
    suite = ET.Element("testsuite", name="runtime", tests=str(len(checks)), failures=str(sum(error is not None for _, _, error in checks)))
    for name, elapsed, error in checks:
        case = ET.SubElement(suite, "testcase", name=name, time=str(elapsed))
        if error:
            ET.SubElement(case, "failure").text = error
    ET.ElementTree(suite).write(EVIDENCE / "junit.xml", encoding="unicode")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    (EVIDENCE / "manifest.json").write_text(json.dumps({
        "checkout_sha": sha, "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "python": sys.version,
        "checks": [{"name": n, "passed": e is None} for n, _, e in checks],
        "live_llm": False,
    }, indent=2))
print(f"PASS: {len(checks)} runtime checks")
