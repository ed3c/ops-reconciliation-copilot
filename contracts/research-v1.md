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
wrong option sets, impossible sums, non-maximal choices, invalid usage, duplicate mapped
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

Explicit live experiment, limited to the four synthetic cases:

```sh
# Set AI_GATEWAY_API_KEY through your secret manager, never in Git or chat.
python scripts/research.py live
# Optional separately billed direct provider, no automatic fallback:
python scripts/research.py live --provider typesafe
```

Vercel is the default provider, including offline request validation. It uses
`https://ai-gateway.vercel.sh/typesafe/v1/systemone` and `typesafe-ai/jev`.
The Gateway slug is an alias, NOT an immutable upstream model version; receipts
explicitly record `immutable_model_version=false`. Require matching response
model identity, preserve raw provider metadata/usage/cost when supplied, and do
not fabricate the underlying version or zero billing. No OIDC token extraction
or new Node service is needed: this stdlib client uses `AI_GATEWAY_API_KEY`.

The official model page checked 2026-09-21 says promotional pricing ends
2026-09-25 without an exact time/timezone. The Gateway catalog simultaneously
reports the regular $0.042/M input rate. Treat that as catalog list price, not
a proof of promotional billing. This research client conservatively refuses
Vercel live calls starting 2026-09-25 00:00 UTC (`promotion_review_required`),
pending a reviewed pricing decision. That cutoff is our policy, not a claim
about the provider's exact billing switch. Avoid provider BYOK for this trial;
it may bill the provider directly. Offline remains usable after the cutoff.

Explicit `--provider typesafe` retains the fixed direct endpoint
`https://api.typesafe.ai/v1/systemone`, separate `TYPESAFE_API_KEY`, and pinned
`TYPESAFE_MODEL` (default `jev-1.13.0`). Provider/model mismatches fail before
transport. No retries, redirects, automatic paid fallback or key sharing.

`--provider openrouter` reserves the adapter boundary and exits 2/not_run with
`openrouter_jev_not_supported`, even if an OpenRouter key exists. No verified
Jev entry was found in its public catalog on 2026-09-21. Do not substitute a
Jev slug into Chat Completions. The existing production `app.llm` OpenRouter
mapping path is unchanged and is not a Jev fallback.

Gateway documents probabilities rounded to two decimal places. Its validation
accepts a sum only if per-option rounding intervals could contain a normalized
distribution; it never renormalizes or overwrites the returned probabilities.
Direct TypeSafe retains the existing exact-sum tolerance. Confidence measures
distribution concentration; the thresholds do not establish domain calibration.

At most four calls, six questions per call, 64 KiB request/response caps, 45-second
socket timeout, no application retry. Socket timeout is not a total wall-clock SLA;
the CI job has a separate time bound. This is not a global spending cap. Missing
key, unsupported provider, expired trial or invalid model exits 2/not_run before transport. Transport/validation
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

## Gateway sources (checked 2026-09-21)

- [Jev promotion](https://vercel.com/ai-gateway/models/jev)
- [TypeSafe-compatible API](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe)
- [Evaluation semantics and rounding](https://vercel.com/kb/guide/typesafe-jev-and-ai-sdk)
- [OpenRouter catalog](https://openrouter.ai/api/v1/models)
