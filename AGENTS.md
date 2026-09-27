# Ops Reconciliation Copilot

Keep changes scoped to the admitted Issue/milestone. Read the exact Issue and candidate ref.

| Task | Shortest route |
| --- | --- |
| Jev research foundation (#21) | [Research contract](contracts/research-v1.md) -> `scripts/research.py`, `research/jev.py`, `tests/test_jev.py` |
| Existing reconciliation | `app/main.py` -> `scripts/verify_runtime.py` and independent `tests/fixtures/` |
| Existing mapping proposal | `app/llm.py` -> `tests/test_llm.py`, `scripts/verify_mapping.py` |

Prefer AGENTS -> relevant contract -> executable boundary (three document nodes).
This is navigation guidance, not a limit on necessary source/test reads.
Run `python -m unittest discover -s tests -p 'test_*.py' -v` and
`python scripts/verify_runtime.py`. Research also runs `python scripts/research.py`.
Preserve hand-authored fixtures as independent oracles. Never label mocked model
output, offline requests, or candidate self-tests as live model/trusted landing evidence.
Record runtime failures and inspect logs before changing assertions.

`docs/**` and [CONTEXT.md](CONTEXT.md) are N-class plans/history, not correctness
authority. This file guides Agent decisions (P); contracts specify intended
behavior but require executable evidence. Local checks (L) and provider readbacks
(R) only establish their exact tested claims. Do not claim required branch
protection or independent verification merely because Actions is green.

One Issue owns one causal correction, its producers/consumers and refusal controls.
Do not copy Soodles' scheduler, worktree manager, retry engine or lander here.
Soodles cross-repo delivery is not implemented; an owner-supplied next/request,
fresh target admission and exact-head evidence are required before using it.
Never replay an unknown write. Keep checkpoints and credentials outside candidate code.

This milestone changes no production route, database schema, authentication,
deployment, wallet or order execution. No live API calls by default. No merges,
auto-merge or Issue closure without user authorization. Issue #12 retains ownership
of hosted Google-login/live-model end-to-end verification.
