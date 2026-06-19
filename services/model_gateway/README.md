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

Expected output:

```json
{"error": "reviewer_model (provider:same-model) must differ from recommended_model (provider:same-model) when risk_level is high"}
```

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
