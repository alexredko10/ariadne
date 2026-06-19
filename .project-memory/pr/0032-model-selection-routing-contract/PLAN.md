## Implementation note

PR 0032 implemented:
- Created `.project-memory/model-routing.schema.yml` with ModelProfile, ContextStressProfile, ModelRouterScore, and ModelSelectionResult contract definitions, selection rules, safety rules, invalid cases list, and minimal valid example
- Added 14 `model-routing.*` contract entries to `.project-memory/project_contract.yml`
- Added 7 model-routing anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.10 with model-routing schema and ADR in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.12 with new `model-routing` label and schema/ADR references

The ADR (`docs/adr/0002-model-selection-methodology.md`) was already written by the planner and was not modified. No services/model_gateway/ changes. No agents/ changes. No model names hardcoded as contract values. No implementation of ModelRouter, ContextStressProfiler, or ModelProfile classes.# PR 0032: Model Selection and Routing Contract

## Goal

Formalise model selection methodology as ADR + schema + contracts.
Define ModelProfile, ContextStressProfile, ModelRouterScore as
machine-readable contract schemas.
Do not implement routing code in this PR.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "9c4e3403ad29376627fcd47dabfd081db48b5821"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.11"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "9c4e3403ad29376627fcd47dabfd081db48b5821"
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
- no implementation of ModelRouter, ContextStressProfiler, or ModelProfile classes
- no changes to services/model_gateway/
- no changes to agents/ configs
- no changes to Model Gateway JWT or routing code
- no runner code changes
- no .ariadne/** files
- no actual model capability profiles (those are runtime data, not contracts)
- no hardcoded model-to-role assignments
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
docs/adr/0002-model-selection-methodology.md
.project-memory/model-routing.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0032-model-selection-routing-contract/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify:

```text
services/**
agents/**
.ariadne/**
packages/**
apps/**
docs/** except docs/adr/0002-model-selection-methodology.md
.github/**
docker/**
Dockerfile*
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
```

## Required ADR

Create: `docs/adr/0002-model-selection-methodology.md`

ADR must include:

- title: ADR 0002: Model Selection Methodology
- status: Accepted
- date: 2026-06-19
- context: why model selection needs to be a platform concern, not ad-hoc
- decision: model selected by role + context stress profile + failure mode + cost + verification requirements, not by brand or leaderboard
- consequences:
  - model choice stays a configuration decision if substrate is owned
  - prevents platform lock-in
  - enables cost optimisation by role
  - requires maintaining model capability profiles (runtime data)
  - requires Context Stress Profiler component (future implementation)
- roles defined: architect, worker_coder, ui_frontend, backend_optimizer, reviewer, dataset_synth
- five selection rules from source document
- relationship to Model Gateway: _route_with_policy() must be extended to accept context_stress_profile
- future work: ModelRouter implementation, ContextStressProfiler, model performance feedback loop

## Required schema

Create: `.project-memory/model-routing.schema.yml`

Schema must define (as contract/comment structure, not Python):

ModelProfile fields:
- role
- frontend_ui_quality (0.0–1.0)
- backend_coding_quality (0.0–1.0)
- debugging_quality (0.0–1.0)
- long_repo_handling (0.0–1.0)
- exact_retrieval (0.0–1.0)
- aggregation_strength (0.0–1.0)
- graph_reasoning (0.0–1.0)
- tool_use_stability (0.0–1.0)
- hallucination_risk (0.0–1.0)
- icl_sensitivity (0.0–1.0)
- cost_per_token (float)
- latency_ms (int)
- interruptibility (0.0–1.0)
- safety_friction (0.0–1.0)

ContextStressProfile fields:
- retrieval_stress (low | medium | high)
- aggregation_stress (low | medium | high)
- graph_reasoning_stress (low | medium | high)
- long_code_stress (low | medium | high)
- icl_sensitivity (low | medium | high)

ModelRouterScore fields:
- role_fit (0.0–1.0)
- context_fit (0.0–1.0)
- risk_fit (0.0–1.0)
- cost_fit (0.0–1.0)
- latency_fit (0.0–1.0)
- historical_success (0.0–1.0)
- failure_penalty (0.0–1.0)
- availability (0.0–1.0)

ModelSelectionResult fields:
- role
- task_type
- risk_level
- context_stress (ContextStressProfile)
- recommended_model (provider:model string)
- reviewer_model (provider:model string, must differ from recommended_model when risk_level is high)
- reason (string)
- selection_rules_applied (list of rule ids)

Rules to document in schema:
- model_not_strongest_by_default
- strong_for_purpose_cheap_for_execution
- ui_routing_separate_from_backend
- long_context_profiled_by_subtask
- substrate_beats_model_loyalty
- reviewer_model_differs_from_coder_on_high_risk
- no_hardcoded_model_vendor_assignments
- profiles_updated_from_execution_history

Safety rules:
- ModelProfile scores are runtime data, not contract values
- no actual model names hardcoded as contract ids
- ModelSelectionResult is evidence, not an execution authorization
- ModelRouter must not bypass Model Gateway JWT contract
- ModelRouter must not bypass data_policy checks
- ModelRouter must not bypass apply-gate.schema.yml requirements

## Required contract ids

Add to `.project-memory/project_contract.yml`:

```text
model-routing.methodology.required
model-routing.methodology.adr-path
model-routing.methodology.schema-path
model-routing.role-based-selection.required
model-routing.context-stress-profile.required
model-routing.reviewer-differs-from-coder-on-high-risk
model-routing.no-hardcoded-vendor-assignments
model-routing.profiles-updated-from-execution-history
model-routing.substrate-beats-model-loyalty
model-routing.no-bypass-model-gateway-jwt
model-routing.no-bypass-data-policy
model-routing.no-bypass-apply-gate
model-routing.selection-result-evidence-only
model-routing.no-implementation-this-pr
```

## Required anchors

Add to `.project-memory/anchors.yml`:

```text
model-routing.methodology.required
model-routing.methodology.adr-path
model-routing.context-stress-profile.required
model-routing.reviewer-differs-from-coder-on-high-risk
model-routing.substrate-beats-model-loyalty
model-routing.no-bypass-model-gateway-jwt
model-routing.selection-result-evidence-only
```

## Required contracts bundle update

`.project-memory/context-bundles/contracts.yml`:

- add `.project-memory/model-routing.schema.yml` to read_first
- add `docs/adr/0002-model-selection-methodology.md` to read_first
- add model-routing anchors
- bump bundle version
- add note: model-routing is contract-only in PR 0032
- add note: ModelRouter implementation is future work

## Required memory index update

`.project-memory/memory_index.yml`:

- bump version from `"0.11"` to `"0.12"`
- add label: `model-routing`
- additional_files:
  - `.project-memory/model-routing.schema.yml`
  - `docs/adr/0002-model-selection-methodology.md`

## Relationship to existing contracts

```text
Model Gateway JWT contract (agents.context-snapshot.*) is preserved.
data_policy checks are preserved.
apply-gate.schema.yml is preserved.
_route_with_policy() will be extended in a future PR to accept
context_stress_profile — not in this PR.
Model capability profiles are runtime data stored outside contracts.
No model names are hardcoded as contract values.
```

## Stop conditions

Stop if:

- implementation modifies services/model_gateway/
- implementation modifies agents/ configs
- implementation hardcodes model names as contract ids
- implementation bypasses Model Gateway JWT or data_policy
- implementation creates `.ariadne/**` files
- implementation creates `run_record.yml` files
- implementation modifies forbidden schemas
- implementation adds non-stdlib dependencies

## Validation commands

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "model-routing\|0002-model-selection" .project-memory docs/adr
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
```

## Expected changed files

```text
docs/adr/0002-model-selection-methodology.md
.project-memory/model-routing.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0032-model-selection-routing-contract/PLAN.md
```

## Context receipt requirement

Every agent response for this PR must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- index_version:
- current_head:
- stale_snapshot:
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
