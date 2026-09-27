# AI Engineer experiment templates

This directory turns curriculum concepts into bounded **Ops experiments**, not product backlog items.

```text
lesson / learning question
        ↓
choose a template
        ↓
inspect current Ops physical truth
        ↓
EXPERIMENT or NO_CHANGE
        ↓
tests / evals / runtime evidence
        ↓
human explanation
        ↓
optional article handoff
        ↓
PROMOTE is a separate product-owner decision
```

The five initial templates cover Prompt Engineering, Eval Scope, RAG need, Agent workflow,
and Fine-tuning/LoRA. They are intentionally small JSON contracts so another repo can render
cards without importing Ops code.

A template is **not** proof that an experiment ran. `catalog.json` may list historical examples,
but status and evidence identities must remain explicit.

Provider contract:
- canonical template bytes live in this repo;
- runtime code/tests/evals stay in this repo;
- medium-compiler may consume a pinned catalog snapshot for explanation/publishing;
- medium-compiler does not modify Ops runtime or promote an experiment.
