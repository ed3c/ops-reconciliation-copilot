# Evidence scope checkpoint — Issue #23

**State: candidate; human judgment pending.** This is one Ops Reconciliation Copilot learning atom. Do not use it as a medium-compiler completion receipt yet.

## Predict before revealing

The [historical live report](evidence/2026-09-15-luna-medium.json) says 4/4. The [dataset](../evals/cases.jsonl) contains two mapping cases and two clarification cases.

1. Does 4/4 establish that the current reconciliation product is correct? State the strongest claim you would make.
2. Which of the four cases evaluates the *quality* of a clarification question? What observation would falsify your answer?
3. Would your judgment change if the reported checkout differs from the current checkout? Why?

Record the human's prediction and reason before running the reveal. No response has been recorded for this atom; reading this page or passing tests does not mark learning complete.

## Reveal and compare

Run `python evals/audit.py` from this repository. It re-scores actual outputs against the hand-authored cases, verifies dataset and prompt hashes, checks recorded provider/model metadata, and compares the historical checkout with the current one. It does not call a model.

The historical report supports **2/2 exact mappings** and **2/2 clarification statuses** for four fixed header-only cases on checkout `78ea5882fa996cf9ef4c900bcc53cd79911b7a7a`. Clarification question quality was not scored. The report metadata says the provider was live; the [original Actions run](https://github.com/ed3c/ops-reconciliation-copilot/actions/runs/34948675162/attempts/2) is the external execution receipt. A JSON field alone cannot independently prove that a provider call occurred.

The planted controls in `tests/test_eval_audit.py` test two different boundaries: a corrupted mapping with stored `passed=true` is rejected; an irrelevant question still passes the existing *status* criterion, while question quality remains `not_assessed` and product correctness remains unsupported. The latter is an intentional visible limitation, not evidence that the question is good.

## Source and authority

- Ops anchors: `evals/run.py`, `evals/cases.jsonl`, `app/llm.py`, and the historical report above.
- Installed learning source: [rohitg00/ai-engineering-from-scratch at `8bc378c`](https://github.com/rohitg00/ai-engineering-from-scratch/tree/8bc378c2e07777899322ae77cd0dde94cb12fab3), with its [MIT notice](third-party/ai-engineering-from-scratch-LICENSE) retained for the copied skills. `skills/course-guide/SKILL.md` routes this barrier to [Phase 11, Lesson 10: Evaluation & Testing](https://github.com/rohitg00/ai-engineering-from-scratch/blob/8bc378c2e07777899322ae77cd0dde94cb12fab3/phases/11-llm-engineering/10-evaluation/docs/en.md).
- `npx skills add rohitg00/ai-engineering-from-scratch` resolved the `skills` installer to 1.5.18 and initially copied nine skills. All were inspected as text/YAML with no executable files or symlinks and compared with the source tree. The eight unrelated tutors/certification skills were removed using the installer; only `course-guide` remains in `.agents/skills/`. The remove command left stale lock entries, so `skills-lock.json` was reduced to the one remaining skill and checked against `npx skills list --agent codex`. The lock does not pin the upstream commit, so this receipt records it explicitly.
- The curriculum's example prices, sample-size thresholds, and judge-correlation figures are not Ops measurements or release gates. Only the audited Ops cases and runtime checks support claims here.

## Pending gate

Record a human prediction, the evidence they used, their revised judgment after the reveal, and whether they can apply that rule to a new Ops failure. Until then, `DONE` for human learning is not established. Do not update medium-compiler from this candidate.
