# Ops research roadmap — N-class, not completion evidence

## Decision: Ops owns the domain; Soodles may later own delivery

Keep experiments with the reconciliation inputs, independent fixtures and real
consumer in this repository. Do not build a second automation platform here.
Reuse Python/FastAPI, existing storage and Actions. No new cloud resource is
required for the first experiment. A second model implementation must earn its
place by reducing measured cost/latency without unacceptable decision errors.

Inspected Ops base: `24a56d18661630b0dba97dcb0b057dce07b0ab32`.
Soodles reference: `defc5f41153837f4db5ee0858fd03c9029523c6c` (read-only inspection).
Its landing implementation explicitly fixes the
repository to `ed3c/soodles`, including provider identity/CI checks. Its existing
prepared/offered/unknown-outcome handling is a design reference, not a capability
already available to Ops. Do not turn that constant into an unrestricted flag.

## Minimal causal stages

| Stage / owner | Smallest deliverable | Evidence needed to advance | Explicitly excluded |
| --- | --- | --- | --- |
| 1 / Ops #21 | Isolated header-only Jev request/consumer, offline evidence, document route | Prior runtime stays green; positive/refusal controls; no-network default; exact-head CI | Production switch, new DB, trading |
| 2 / Ops new atom | Controlled Jev vs current OpenRouter header mapping experiment | Same labeled inputs, recorded versions, ambiguous/adversarial/held-out cases, accepted-answer precision + abstention coverage + failures + latency + cost; choose thresholds on separate calibration split | Calling 4/4 smoke enterprise accuracy; automatic promotion |
| 3 / Soodles new atom | One explicitly admitted Ops Issue -> Draft PR -> target CI; separately approved landing | Target repo/Issue/PR/head/tree/base/run/attempt binding; foreign repo and stale evidence RED; candidate correction GREEN; same-repo non-case GREEN; interruption/readback without duplicate write | Repo wildcard, second scheduler, autonomous trading |
| 4 / Ops new atom | Read-only normalization and reconciliation of one selected provider's fills/positions against chain events | Proven source IDs/times, asset identity, units/precision, fees, duplicates, stale data and reorg controls; no signer exists | Buy/sell advice, generic broker framework |
| 5 / Ops new atom | Paper execution with one operation owner and deterministic risk checks | Stable operation ID; side effect -> process kill -> missing checkpoint; restart reconciles observed outcome rather than blindly resubmitting; duplicate/partial fill controls | Real funds, claiming remote exactly-once |
| 6 / separately authorized project boundary | Consider tightly scoped live pilot only after legal/product/provider review | Venue eligibility, instrument rights, key custody, explicit budgets/limits, manual approval/kill switch, incident recovery, independent review | Any automatic live enablement from prior green tests |

Stages 3 and 4 do not require inventing a full platform. Stage 3 becomes necessary
when automated delivery is the measured bottleneck; it is not a dependency of
local research. Create later Issues only when their concrete failing seam, owner,
inputs and rollback are known. Never split one cause across helper/test/checkpoint
Issues. Each atom specifies baseline failure, correction, legal non-case, exact
checks, side effects, and next readback. Wrong tests may be corrected with the
implementation; fixture truth must not be rewritten merely to obtain green.

## What to reuse from Soodles

- A supervisor admits exact identities; the candidate cannot choose its judge.
- Provider transport stays outside untrusted candidate code.
- Persist intent before an external write; unknown response means readback, not retry.
- Consume the actual owner's next/request instead of reconstructing commands.
- Noodle retains worktree lifecycle ownership if that path is selected.
- Merge, Issue closure and cleanup are distinct observed facts; a green test is none of them.

For cross-repo work, keep the target's verifier command and required job identities
in supervisor-controlled admission. Bind both controller and target versions;
do not run arbitrary candidate-supplied verifier commands with controller secrets.
First prove two repositories cannot borrow each other's green runs/checkpoints or
write requests. After one safe target delivery, prove A -> cleanup -> B with one
actual interruption. No fleet scheduler, reusable-workflow migration or central
database is required merely to pass the first atom.

## Where Jev fits

Use Jev for an uncertain semantic mapping or triage proposal. Use deterministic
code for amounts, evidence identity, data freshness, permissions and state
transitions. Low confidence or missing evidence escalates; high confidence does
not certify correctness. An evidence classifier must never attest that its own
trade succeeded. Trace/provider readback and ledger facts own that conclusion.

The first experiment uses the direct Python HTTP API to avoid introducing Node
and an experimental SDK into this Python repository. Native TypeSafe uses
`choice`/`noul`/`score`; Vercel's evaluation surface has a distinct adapter contract.
Gateway integration is optional later, not a model ID substituted into the
existing OpenRouter Chat Completions transport.

## On-chain US-equity boundary

Tokenized exposure is not automatically identical to direct share ownership.
Before choosing a provider, establish jurisdiction/account eligibility, issuer
and redemption rights, custody, exchange hours vs token transfer hours, settlement
and corporate-action handling with authoritative provider/legal sources. No
provider, chain, asset contract or signing authority is selected by this plan.

Current reconciliation accepts two-decimal monetary values and 3-letter
currencies. It cannot represent arbitrary token quantity precision, share
fractions or on-chain asset IDs. Keep raw integer base units + declared decimals
or explicitly scaled Decimal; bind chain ID/contract/token ID, block hash/height,
transaction hash/log index, source event time and ingestion time. A symbol alone
is not asset identity. Reorged/unfinalized observations cannot silently become
settled fills. Asset quantity, cash, fees and FX are distinct dimensions; don't
patch token units into the old money column. Add only the selected provider's
required shape after a real read-only fixture demonstrates the mismatch.

## Environment / authority checklist

- Stage 1: Python 3.12 + existing requirements; disposable local SQLite. Existing
  CI supplies PostgreSQL. No cloud DB migration or hosted settings changed.
- Stage 2: narrowly scoped TypeSafe key + fixed model; synthetic inputs first.
  Explicit bounded invocation, provider usage/cost capture, no automatic retries.
- Hosted browser prerequisite remains Issue #12; local research does not prove
  real Google owner login or hosted live-model behavior.
- Stage 3: separately verify GitHub installation scopes for both repositories.
  Read/write capability is not permission to bypass target checks or merge approval.
- Stage 4: read-only market/chain credentials if required; no wallet private key.
- Stages 5/6: different authorization boundaries; never reuse development CI or
  model credentials as financial execution authority.

## Primary references, checked 2026-09-17

- [TypeSafe API](https://docs.typesafe.ai/api): state/questions and typed answers.
- [TypeSafe models](https://docs.typesafe.ai/models): version IDs and moving aliases.
- [TypeSafe confidence](https://docs.typesafe.ai/confidence): domain-specific calibration.
- [TypeSafe workflow evals](https://evals.typesafe.ai/): model-consensus labels, not business ground truth.
- [Vercel evaluation](https://vercel.com/docs/ai-gateway/modalities/evaluation): separate evaluation interface.

These vendor claims do not demonstrate this repository's accuracy or latency.
