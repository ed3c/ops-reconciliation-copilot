# ops-reconciliation-copilot

A small reconciliation service with reproducible runtime evidence.

## Current milestone

Upload two CSV files, confirm column mappings, compare exact transaction IDs,
review differences, restart the service, and export the saved results.
Decimal arithmetic uses exact comparison; this MVP accepts amounts with at most
two decimal places. Duplicate IDs are reported, never guessed. Currency
mismatches are not subtracted.

## Run

Requires Python 3.12.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app
```

Open http://127.0.0.1:8000 for the browser workspace, or /docs for the interactive API.
The database defaults to var/reconciliation.sqlite3; override RECON_DB if needed.

## Verify

```sh
python scripts/verify_runtime.py
```

This starts a real HTTP server, uploads fixture files, checks an independent
expected result, repeats reconciliation, saves a review, terminates and restarts
the process with the same SQLite database, and validates the downloaded CSV.
A deliberately corrupted export must be rejected by the verifier.
Reports are written to evidence/ and uploaded by the PR workflow.

## Scope and limits

This is a local/single-user prototype, not an authenticated production service.
Optional LLM mapping proposals are implemented. Live model quality remains unverified until the separate authenticated evaluation runs.
Reviews persist the current decision and reason; authenticated actor identity and
append-only review history remain future work.
The restart test proves persistence after graceful process termination; it does
not claim power-loss durability or crash-at-commit coverage.
Amounts and source rows are checked against committed, hand-authored fixtures.
The service uses explicit mapping confirmation, so this milestone requires no
model API secrets. Do not upload private data to public CI artifacts.

## Architecture

app/main.py contains the initial HTTP endpoints, validation, pure reconciliation
function and SQLite transaction boundary. Inputs become immutable after
reconciliation. BEGIN IMMEDIATE serializes per-database mutations so repeated
reconciliation returns the stored result.

Next milestones: broader failure injection and evidence-backed explanations.

## Browser verification

```sh
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python scripts/verify_browser.py
```

Chromium performs actual upload, mapping correction, review, page reload and CSV download. The downloaded report is compared against the existing independent fixture. Desktop/mobile screenshots and a Playwright trace are saved in evidence/browser. No model API is involved. Each run URL can be reopened on the same service to recover saved work.

## Optional mapping suggestions

Export OPENROUTER_API_KEY and OPENROUTER_MODEL before starting the service. Choose an available model ID in your OpenRouter account; use the full provider/model ID from the OpenRouter model catalog. No model is selected automatically. The browser then shows Suggest columns. Only header names go to the provider; row data stays local. Review suggested columns before confirming. Ambiguous headers request clarification. The header-only approach intentionally cannot resolve ambiguous columns from cell values.

Transport uses the OpenRouter Chat Completions API with a 10-second socket timeout, 600 output-token limit and no application-level automatic retries. OpenRouter may route requests between upstream providers. Validated results store prompt hash, model, token usage and latency with the run. Failed calls store a bounded error code; provider response bodies and keys are never included in client errors. This does not impose a total spending cap on repeated user requests. Manual mapping remains available without a key.

Source: https://openrouter.ai/docs/api/reference/overview

## Model evidence

PR CI runs 9 contract tests and real HTTP/browser integration against a LOCAL FAKE provider. These are integration evidence, not model-quality scores. Run locally with:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_mapping.py
```

For live evaluation, configure repository secret OPENROUTER_API_KEY and repository variable OPENROUTER_MODEL. On main, manually run Live mapping evaluation in Actions (or run python evals/run.py locally with exported configuration). It makes four bounded calls on hand-authored header cases. Missing configuration exits 2 and writes status=not_run; it never reports a mocked pass. Four cases are smoke coverage, not a representative enterprise benchmark. Output includes dataset/prompt hashes, checkout SHA, per-case decisions, usage and timing.
