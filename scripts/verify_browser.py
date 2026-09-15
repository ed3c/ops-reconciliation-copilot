"""Real browser flow against the existing service and independent CSV oracle."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/browser"
OUT.mkdir(parents=True, exist_ok=True)
FIX = ROOT / "tests/fixtures"
passed = False
with tempfile.TemporaryDirectory() as temp, (OUT / "server.log").open("w") as log:
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"], cwd=ROOT, env={**os.environ, "RECON_DB": str(Path(temp) / "db.sqlite3")}, stdout=log, stderr=log)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("Server exited")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Server readiness timeout")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1100, "height": 900})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            try:
                page.goto("http://127.0.0.1:8765")
                page.get_by_label("Left CSV").set_input_files(FIX / "left.csv")
                page.get_by_label("Right CSV").set_input_files(FIX / "right.csv")
                page.get_by_role("button", name="Upload files").click()
                for side, values in {"left": ["txn_ref", "amount", "currency"], "right": ["reference_id", "paid", "ccy"]}.items():
                    for field, value in zip(["transaction_id", "amount", "currency"], values):
                        page.get_by_label(side + " " + field, exact=True).select_option(value)
                # Duplicate column mapping must fail visibly, then allow correction.
                page.get_by_label("left amount", exact=True).select_option("txn_ref")
                page.get_by_role("button", name="Confirm and reconcile").click()
                expect(page.get_by_role("alert")).to_contain_text("three distinct")
                page.get_by_label("left amount", exact=True).select_option("amount")
                page.get_by_role("button", name="Confirm and reconcile").click()
                expect(page.locator("#summary")).to_have_text("1 differences found")
                expect(page.locator(".finding")).to_contain_text("Difference: 2.00")
                expect(page.locator(".sources")).to_contain_text('"row":2')
                page.get_by_label("Reason F001").fill("Checked source rows")
                page.get_by_role("button", name="Save review F001").click()
                expect(page.get_by_role("status")).to_have_text("Review saved")
                page.reload()
                expect(page.get_by_label("Reason F001")).to_have_value("Checked source rows")
                expect(page.locator(".finding")).to_contain_text("Saved: accepted")
                with page.expect_download() as download:
                    page.get_by_role("link", name="Download CSV").click()
                target = OUT / "download.csv"
                download.value.save_as(target)
                assert list(csv.reader(io.StringIO(target.read_text()))) == list(csv.reader(io.StringIO((FIX / "expected-export.csv").read_text())))
                page.screenshot(path=str(OUT / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                assert not errors, errors
                passed = True
            finally:
                if not passed:
                    page.screenshot(path=str(OUT / "failure.png"), full_page=True)
                context.tracing.stop(path=str(OUT / "trace.zip"))
                browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        (OUT / "result.json").write_text(json.dumps({"passed": passed, "live_llm": False, "run_id": os.environ.get("GITHUB_RUN_ID")}))
print("PASS: browser upload, mapping recovery, source display, review persistence, export and mobile layout")
