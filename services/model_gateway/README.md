# Model Gateway Service

Placeholder service for the platform repository skeleton.

## Model Selection Dry-Run

A local, deterministic, evidence-only CLI tool that emits a
`ModelSelectionResult`-like JSON object from explicit input.

This is **not** live model routing.
This is **not** provider integration.
This is **not** automatic model switching.

### Usage

```bash
# Run a valid dry-run
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run \
  --role reviewer \
  --task-type verification \
  --risk-level high \
  --retrieval-stress high \
  --aggregation-stress high \
  --graph-reasoning-stress medium \
  --long-code-stress high \
  --icl-sensitivity medium \
  --recommended-model provider:coder-model \
  --reviewer-model provider:reviewer-model
```

### Failure example: same model on high-risk task

```bash
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run \
  --role reviewer \
  --task-type verification \
  --risk-level high \
  --retrieval-stress high \
  --aggregation-stress high \
  --graph-reasoning-stress medium \
  --long-code-stress high \
  --icl-sensitivity medium \
  --recommended-model provider:same-model \
  --reviewer-model provider:same-model
```

### Model Selection Dry-Run CLI (simplified smoke)

A simplified CLI smoke interface for quick demos:

```bash
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run \
  --role coder \
  --task-type long-context-code-review \
  --context-stress high \
  --failure-mode hallucinated-diff \
  --cost-sensitivity medium \
  --verification required
```

Expected output shape (abbreviated):

```json
{
  "role": "worker_coder",
  "task_type": "long-context-code-review",
  "risk_level": "critical",
  "context_stress": { ... },
  "recommended_model": "provider:worker_coder-recommended",
  "reviewer_model": "provider:worker_coder-reviewer-independent",
  "failure_mode": "hallucinated-diff",
  "reason": "...",
  "selection_rules_applied": [
    "reviewer_model_differs_from_coder_on_high_risk",
    "strong_for_purpose_cheap_for_execution",
    "long_context_profiled_by_subtask",
    "substrate_beats_model_loyalty"
  ]
}
```

The simplified CLI maps `--role` values like `coder`, `architect`, `reviewer`,
`ui`, `backend`, `dataset` to the detailed role identifiers from PR 0033.

This is a **PR 0034** addition on top of the **PR 0033** detailed decision record.

### Evidence-only boundary

- The dry-run output is evidence only.
- It does **not** authorize execution.
- It does **not** authorize canonical writes.
- It does **not** bypass the Model Gateway JWT contract.
- It does **not** bypass `data_policy` checks.
- It does **not** bypass `apply-gate.schema.yml` requirements.
- It does **not** invoke the runner.
- It does **not** create `run_record.yml`.
- It does **not** write to `.ariadne/**`.
