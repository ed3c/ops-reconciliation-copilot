# RESEARCH.HEADERS.001 — bounded Jev research

Owner: [Issue #21](https://github.com/ed3c/ops-reconciliation-copilot/issues/21).
Contract prose is not evidence. Boundary: [research/jev.py](../research/jev.py);
consumer: [scripts/research.py](../scripts/research.py);
controls: [tests/test_jev.py](../tests/test_jev.py).

## Behavior

One call evaluates six independent Choice questions: transaction ID, amount and
currency for each side. State contains only headers, never CSV records, customer
identities, holdings or account credentials. Options are indexed observed headers
plus `insufficient_evidence`; no free-text generation is needed. Validate all
answers, even when an earlier answer abstains. Non-finite/boolean probabilities,
wrong option sets, bad sums, non-maximal choices, invalid usage, duplicate mapped
columns and response-model drift are rejected. Missing/ambiguous or low-probability
answers yield `clarify` with no mapping. Both 0.9 thresholds are experimental,
not calibrated claims or execution permission. Fixed clarification text is ours.

No production code imports this module. Existing `app.llm.validate` provides the
same final mapping structural checks. A valid proposal does not write storage,
confirm mapping, run reconciliation, settle discrepancies or place an order.
Schema safety is not semantic correctness. Unknown headers must be evaluated
against independently labeled examples before this can influence real workflows.

## Environment and shortest commands

Python 3.12 and stdlib suffice for the isolated research command/tests. Existing
runtime checks retain `requirements.txt`; no Node service, model server, GPU,
queue, new database or infrastructure account is needed for this milestone.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/research.py
python scripts/verify_runtime.py
```

Offline is the default even when a key exists. It builds requests against the
existing four synthetic `evals/cases.jsonl` inputs, emits
`offline_request_validation=passed`, `status=not_run`, `live_provider=false`, and
does not fabricate answers/accuracy. Each invocation writes a new directory under
ignored `evidence/research/`; stdout names the report. Keep evidence private until
reviewed. Test transports are synthetic and never count as live results.

Optional later live experiment, with explicit cost/data authorization:

```sh
# Set TYPESAFE_API_KEY through your secret manager, never in Git or chat.
# TYPESAFE_MODEL defaults to the explicit version jev-1.13.0, not a moving alias.
python scripts/research.py live
```

Only `https://api.typesafe.ai/v1/systemone` is allowed; redirects are refused.
At most four calls, six questions per call, 64 KiB request/response caps, 45-second
socket timeout, no application retry. Socket timeout is not a total wall-clock SLA;
the CI job has a separate time bound. This is not a global spending cap. Missing
key or invalid version exits 2/not_run before transport. Transport/validation
failure stops the batch (exit 1 after an attempted call); do not label it accurate
or silently switch providers. A completed live batch exits 1 on label mismatch.

Reports bind dataset/request/source hashes, checkout SHA and dirty status,
requested/returned model, raw synthetic response, usage and elapsed time. Evidence
always sets `authorizes_execution=false` and `authorizes_landing=false`. A dirty
local report is diagnostic, not exact-commit acceptance. Invalid/timeout outcomes
can have `requests_attempted>0` without a valid provider result; costs may still
have been incurred. Do not infer zero billing from failure.

## Verification and delivery

The existing Runtime evidence workflow keeps all prior SQLite/PostgreSQL checks;
new unit controls are discovered normally and the offline CLI is an additional
step in the SQLite job. No secret or live Jev workflow is added. The existing
OpenRouter live-eval workflow remains unchanged (including its existing triggers).

Required controls: valid mapping, high-confidence abstention, low confidence,
low selected probability, unknown choice, malformed/non-finite distributions,
wrong model, duplicate assignment, empty/duplicate/oversized headers, extra raw
state, response size, timeout/rate-limit without retry, offline with key, live
without key. Preserve old fixtures and runtime regressions. CI provides candidate
self-test evidence, not a candidate-selected external oracle or automatic merge.

Create/update one Draft PR for this atom. Observe its exact head, base, run/attempt
and jobs. Do not merge or close the Issue. Rollback removes these research-only
files and their entry links/CI step; production schema and behavior are unchanged.

## Deferred boundaries

Roadmap: [docs/research-roadmap.md](../docs/research-roadmap.md) (N-class).
Soodles currently cannot admit this repository. Cross-repo support requires a
separate Soodles-owned causal atom, not a local bypass or copied scheduler.
No RPC/wallet/order interface is present; there is no `live trading` flag to enable.
