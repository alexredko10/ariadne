## Implementation note

PR 0033 implemented:
- Created `services/model_gateway/src/model_gateway/model_selection_dry_run.py` with CLI argument parsing, role/risk/stress enum validation, reviewer independence check on high/critical risk, deterministic ModelSelectionResult JSON output, selection_rules_applied, and human-readable reason
- Created `services/model_gateway/tests/test_model_selection_dry_run.py` with 20+ tests covering valid output shape, invalid role/risk/stress rejection, reviewer independence, selection_rules content, and no-side-effect guarantees
- Updated `services/model_gateway/README.md` with usage examples, failure example, and evidence-only boundary disclaimers

No provider calls. No live routing. No automatic model switching. No secrets. No Model Gateway JWT bypass. No data_policy bypass. No apply-gate bypass. No runner invocation. No .ariadne/** writes. No run_record.yml. No project-memory schema/contract changes. No memory_index changes.# PR 0033: Model Selection Dry-Run Decision Record

## Goal

Add a deterministic local dry-run path that produces an evidence-only `ModelSelectionResult` from explicit input.

The dry-run should make model-selection decisions explainable without calling any model provider and without routing live agent execution.

Core principle:

```text
ModelSelectionResult is evidence only.
It does not authorize execution, canonical writes, provider calls, or agent actions.
```

## Context snapshot

```yaml
context_snapshot:
  base_sha: "e3a71f739a718ff81e57680af7fde45ab3622182"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.12"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "e3a71f739a718ff81e57680af7fde45ab3622182"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review should report snapshot deltas but must not block
solely because current HEAD differs from PLAN.md base_sha, unless scope
evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no live model routing
- no automatic model switching
- no provider API calls
- no real model invocation
- no secrets or credentials
- no Model Gateway JWT bypass
- no data_policy bypass
- no apply-gate bypass
- no agent execution
- no task execution
- no runner invocation
- no runner request creation
- no run_id creation
- no run_record.yml creation
- no .ariadne/** writes
- no agent config changes
- no model vendor hardcoded as contract id
- no actual runtime model capability profile data
- no database or persistence implementation
- no telemetry implementation
- no Docker / CI / workflow changes
- no root dependency changes
- no changes to existing schemas except PR PLAN
```

## Implementation allowed_write_paths

Implementation may modify/create only:

```text
services/model_gateway/src/model_gateway/model_selection_dry_run.py
services/model_gateway/tests/test_model_selection_dry_run.py
services/model_gateway/README.md
.project-memory/pr/0033-model-selection-dry-run/PLAN.md
```

Optional only if strongly justified:

```text
services/model_gateway/src/model_gateway/__init__.py
```

## Implementation forbidden_write_paths

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/model-routing.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/run-record.schema.yml
.project-memory/apply-gate.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/context-bundles/agent-config.yml
docs/**
agents/**
prompts/**
services/runner/**
services/conductor/**
services/core/**
services/task_intake/**
packages/**
apps/**
.github/**
docker/**
Dockerfile*
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
```

## Required dry-run module

Create:

```text
services/model_gateway/src/model_gateway/model_selection_dry_run.py
```

Required behavior:

- use stdlib only
- expose `main`
- support `python -m model_gateway.model_selection_dry_run --help`
- accept explicit CLI arguments:

  - `--role`
  - `--task-type`
  - `--risk-level`
  - `--retrieval-stress`
  - `--aggregation-stress`
  - `--graph-reasoning-stress`
  - `--long-code-stress`
  - `--icl-sensitivity`
  - `--recommended-model`
  - `--reviewer-model`

- output JSON to stdout
- output a shape compatible with `ModelSelectionResult` from `.project-memory/model-routing.schema.yml`
- validate allowed enum values
- reject missing context stress fields
- reject invalid risk level
- reject invalid role
- reject high/critical risk if `reviewer_model == recommended_model`
- include `selection_rules_applied`
- include human-readable `reason`
- return exit code 0 on valid input
- return non-zero on invalid input
- not call any provider
- not call Model Gateway runtime routing
- not import runner
- not use subprocess
- not call git/docker
- not write files
- not write `.ariadne/**`
- not create `run_record.yml`

Recommended command example:

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
  --recommended-model provider:coder-model \
  --reviewer-model provider:reviewer-model
```

Expected output example:

```json
{
  "role": "reviewer",
  "task_type": "verification",
  "risk_level": "high",
  "context_stress": {
    "retrieval_stress": "high",
    "aggregation_stress": "high",
    "graph_reasoning_stress": "medium",
    "long_code_stress": "high",
    "icl_sensitivity": "medium"
  },
  "recommended_model": "provider:coder-model",
  "reviewer_model": "provider:reviewer-model",
  "reason": "...",
  "selection_rules_applied": [
    "reviewer_model_differs_from_coder_on_high_risk",
    "long_context_profiled_by_subtask"
  ]
}
```

The placeholder string `provider:model` style is allowed as data format. Do not hardcode real vendor assignments as contract ids or policy.

## Required tests

Create:

```text
services/model_gateway/tests/test_model_selection_dry_run.py
```

Tests must cover:

- valid dry-run output shape
- all context stress fields are required
- invalid role rejected
- invalid risk level rejected
- high risk requires reviewer_model different from recommended_model
- critical risk requires reviewer_model different from recommended_model
- low/medium risk may use same reviewer_model if explicitly allowed by code
- output is valid JSON
- `selection_rules_applied` is present
- `reason` is present
- no provider/API call
- no runner import
- no subprocess/git/docker
- no `.ariadne/**`
- no `run_record.yml`
- stdlib-only implementation

Tests must not:

- require network
- require secrets
- require provider credentials
- require Docker
- require pytest-asyncio
- require FastAPI/Starlette/HTTPX

## README update

Update:

```text
services/model_gateway/README.md
```

If the README does not exist, PLAN may allow creating it.

README must document:

- dry-run command
- example valid command
- example failure: high risk with same recommended/reviewer model
- evidence-only boundary
- no provider calls
- no live routing
- no execution authorization
- no apply-gate bypass
- no data_policy bypass
- no Model Gateway JWT bypass
- no runner invocation
- no `.ariadne/**`
- no `run_record.yml`

## Relationship to PR 0032

```text
PR 0032 added the model selection/routing contract and ADR.
PR 0033 is the first local dry-run implementation of the contract shape.
PR 0033 does not implement live routing.
PR 0033 does not call providers.
PR 0033 does not switch models in live execution.
PR 0033 only emits ModelSelectionResult-like evidence from explicit input.
```

## Required validation

Implementation PR must run:

```bash
PYTHONPATH=services/model_gateway/src python -m pytest services/model_gateway/tests -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run --help
PYTHONPATH=services/model_gateway/src python -c "from model_gateway.model_selection_dry_run import main; print(main)"
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "subprocess\|docker\|git \|run_record.yml\|\.ariadne\|api key\|secret" services/model_gateway/src/model_gateway/model_selection_dry_run.py services/model_gateway/tests/test_model_selection_dry_run.py services/model_gateway/README.md || true
```

Expected:

- model_gateway tests pass
- full pytest passes
- compileall passes
- runner doctor passes
- dry-run help works
- dry-run main import works
- import regression grep has no matches
- forbidden side-effect grep has no actionable matches except tests/README boundary assertions

## Stop conditions

Stop if implementation:

- adds provider integration
- calls provider APIs
- touches secrets
- modifies agents/**
- modifies runner/**
- modifies task_intake/**
- modifies project-memory schemas/contracts
- modifies memory_index
- modifies `.github/**`
- modifies Docker/root deps
- writes `.ariadne/**`
- creates run_record.yml
- treats ModelSelectionResult as execution authorization
- bypasses Model Gateway JWT, data_policy, or apply-gate boundaries

## Expected changed files

```text
services/model_gateway/src/model_gateway/model_selection_dry_run.py
services/model_gateway/tests/test_model_selection_dry_run.py
services/model_gateway/README.md
.project-memory/pr/0033-model-selection-dry-run/PLAN.md
```

Optional only if justified:

```text
services/model_gateway/src/model_gateway/__init__.py
```

## Context receipt requirement

Every agent response for this PR must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- base_sha_source:
- index_version:
- index_version_source:
- current_head:
- stale_snapshot:
- snapshot_verified:
- snapshot_verified_by:

DECISIONS MADE:
- None — followed PLAN.md exactly
- or <decision> — <reason>

CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files modified:
- files intentionally ignored:
```
