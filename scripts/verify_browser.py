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
from auth_test_support import environment, keys, token

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ("evidence/mapping-browser" if os.environ.get("VERIFY_FAKE_MAPPING") else "evidence/browser")
OUT.mkdir(parents=True, exist_ok=True)
FIX = ROOT / "tests/fixtures"
passed = False
with tempfile.TemporaryDirectory() as temp, (OUT / "server.log").open("w") as log:
    key, public = keys(temp)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "scripts.auth_test_support:app_factory", "--factory", "--host", "127.0.0.1", "--port", "8765"], cwd=ROOT, env={**os.environ, "RECON_DB": str(Path(temp) / "db.sqlite3"), **environment(public)}, stdout=log, stderr=log)
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
            nonce = {}
            def config_route(route):
                response = route.fetch()
                nonce["value"] = response.json()["nonce"]
                route.fulfill(response=response)
            page.route("**/auth/config", config_route)
            def gis_route(route):
                credential = token(key, nonce["value"])
                script = "window.google = {accounts:{id:{initialize(c){this.config=c},renderButton(el){const b=document.createElement('button');b.textContent='Test Google sign-in';b.onclick=()=>this.config.callback({credential:" + json.dumps(credential) + "});el.append(b)}}}};"
                route.fulfill(content_type="application/javascript", body=script)
            page.route("https://accounts.google.com/gsi/client", gis_route)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            try:
                page.goto("http://127.0.0.1:8765/workspace")
                page.get_by_role("button", name="Test Google sign-in").click()
                expect(page.get_by_role("button", name="Sign out")).to_be_visible()
                page.get_by_label("Left CSV").set_input_files(FIX / "left.csv")
                page.get_by_label("Right CSV").set_input_files(FIX / "right.csv")
                page.get_by_role("button", name="Upload files").click()
                if os.environ.get("VERIFY_FAKE_MAPPING"):
                    page.get_by_role("button", name="Suggest columns").click()
                    expect(page.get_by_role("alert")).to_contain_text("Suggestions unavailable")
                    expect(page.get_by_role("button", name="Confirm and reconcile")).to_be_enabled()
                    page.get_by_role("button", name="Suggest columns").click()
                    expect(page.locator("#suggestion-note")).to_contain_text("Check them before confirming")
                    expect(page.get_by_label("left transaction_id", exact=True)).to_have_value("txn_ref")
                    expect(page.get_by_label("right amount", exact=True)).to_have_value("paid")
                    expect(page.locator("#results")).to_be_hidden()
                    run_id = page.url.split("?run=")[1]
                    data = page.request.get(f"http://127.0.0.1:8765/runs/{run_id}").json()
                    assert data["mapping"] is None and data["state"] == "uploaded"
                    assert data["mapping_proposal"]["metadata"]["live_provider"] is False
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
                page.get_by_role("button", name="Sign out").click()
                expect(page.get_by_role("heading", name="使用 Google 登入", exact=True)).to_be_visible()
                assert page.request.get("http://127.0.0.1:8765/capabilities").status == 401
                passed = True
            finally:
                if not passed:
                    print("PAGE ERRORS:", errors)
                    print("PAGE TEXT:", page.locator("body").inner_text())
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
        (OUT / "result.json").write_text(json.dumps({"passed": passed, "live_llm": False, "live_google": False, "run_id": os.environ.get("GITHUB_RUN_ID")}))
print("PASS: local test Google login/logout, browser upload, mapping recovery, source display, review persistence, export and mobile layout")
