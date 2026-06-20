# PR 0043 — Phase 0 Contracts Integration Plan

## Goal

Integrate the Ariadne Phase 0 blueprint/platform schemas (from PR 0041) into the operational `.project-memory/**` contract layer.

This PR does **not** create new schemas, write `\.ariadne/**` files, implement runtime code, or modify `services/**`, `agents/**`, `packages/**`, or `apps/**`.

The implementation must update four operational files so that Ariadne's contract discovery, anchor reasoning, bundle loading, and memory index can discover and reason about the Phase 0 contracts as part of the execution substrate.

## Architectural Thesis

```text
Ariadne is not a chatbot wrapper.
Ariadne is not a model-centered agent framework.
Ariadne is an execution substrate for agentic software production.

The model is replaceable.
The substrate is the product.
```

## Context Snapshot

```yaml
context_snapshot:
  base_sha: "adb8747fe6d5b955fa3365151d389ba1f9582253"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.18"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "adb8747fe6d5b955fa3365151d389ba1f9582253"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Inputs Read

- ARIADNE_ARCHITECTURE.md — full 19-section architecture document
- ROADMAP.md — 10-phase roadmap (Phase 0 status: "Complete in PR 0041" — blueprint only)
- .project-memory/project_contract.yml — version "0.1", heavily populated with contract IDs for existing operational contracts
- .project-memory/anchors.yml — version "0.1", contains anchors for existing operational contracts
- .project-memory/context-bundles/contracts.yml — version "0.16", contains read_first references and anchored contract IDs
- .project-memory/memory_index.yml — version "0.18", contains labels for existing operational contracts
- .project-memory/review-artifact.schema.yml — schema version "0.1", includes example review artifacts
- .project-memory/pr/0042-architecture-roadmap-decomposition/PLAN.md
- .project-memory/pr/0042-architecture-roadmap-decomposition/reviews/plan-review.yml
- All 13 blueprint schemas under schemas/ (purpose, pbs, context-pack, state-model, transition-graph, rubric-pack, rubric-judge-result, model-capability-profile, agent-execution-contract, run-state, checkpoint, long-context-stress-profile, final-report)
- docs/adr/0004-ariadne-is-domain-agnostic.md
- docs/adr/0005-rubrics-as-runtime-contracts.md
- docs/adr/0006-model-replaceability.md
- docs/adr/0007-cached-repository-understanding.md

## Current Operational Contract Layer

### `.project-memory/project_contract.yml`

Role: Global machine-readable contract registry for the entire platform. Contains `protected_behaviors`, `validation_commands`, `forbidden_generated_files`, and `human_approval_required_for`. The `protected_behaviors` list is the primary contract ID registry.

Current state: Contains contract IDs for all pre-Phase-0 operational contracts (run-record, apply-gate, workspace-feature, task-intake, model-routing, state-first, review-artifact, conductor-prompt, domain-adapter, context-pack, ariadne-anchor). Does **not** contain contract IDs for Phase 0 blueprint schemas: purpose, pbs, state-model, transition-graph, rubric-pack, rubric-judge-result, model-capability-profile, agent-execution-contract, run-state, checkpoint, final-report, long-context-stress-profile.

### `.project-memory/anchors.yml`

Role: Stable anchors for quick context retrieval. Each anchor references contract_ids and paths.

Current state: Contains anchors for all operational contracts. Does **not** contain anchors for any Phase 0 blueprint schemas.

### `.project-memory/context-bundles/contracts.yml`

Role: The shared "contracts" context bundle that all agents read first. Contains `read_first`, `anchors` (list of anchor IDs), and `notes`.

Current state: Version "0.16". Contains read_first references and anchors for all operational contracts. Does **not** contain references to Phase 0 blueprint schemas.

### `.project-memory/memory_index.yml`

Role: Shared memory index that agents read first to select context bundles by task labels.

Current state: Version "0.18". Contains labels for operational contracts. Does **not** contain labels for Phase 0 schemas: purpose, pbs, state-model, transition-graph, rubric-pack, rubric-judge-result, model-capability-profile, agent-execution-contract, run-state, checkpoint, long-context-stress-profile, final-report.

## Phase 0 Contract Inventory

| Contract/Schema | Status | Location |
|---|---|---|
| `.project-memory/conductor-prompt-contract.schema.yml` | Already operational | `.project-memory/` |
| `.project-memory/prompt-artifact.schema.yml` | Already operational | `.project-memory/` |
| `.project-memory/domain-adapter.schema.yml` | Already operational | `.project-memory/` |
| `.project-memory/context-pack.schema.yml` | Already operational | `.project-memory/` |
| `.project-memory/ariadne-anchor.schema.yml` | Already operational | `.project-memory/` |
| `schemas/purpose.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/pbs.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/context-pack.schema.yml` | Duplicate/overlap risk with `.project-memory/context-pack.schema.yml` | `schemas/` |
| `schemas/state-model.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/transition-graph.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/rubric-pack.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/rubric-judge-result.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/model-capability-profile.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/agent-execution-contract.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/run-state.schema.yml` | Blueprint-only — deferred to runtime PR | `schemas/` |
| `schemas/checkpoint.schema.yml` | Blueprint-only — deferred to runtime PR | `schemas/` |
| `schemas/long-context-stress-profile.schema.yml` | Blueprint-only | `schemas/` |
| `schemas/final-report.schema.yml` | Blueprint-only — deferred to runtime PR | `schemas/` |

### Classification rationale

- **Already operational**: These schemas already have contract IDs, anchors, bundle entries, and memory index labels.
- **Blueprint-only**: These schemas exist in `schemas/` but are not referenced in any operational `.project-memory/**` file. They are discoverable via code search but not via contract discovery (anchors, bundles, memory index).
- **Duplicate/overlap risk**: `schemas/context-pack.schema.yml` exists alongside `.project-memory/context-pack.schema.yml`. The two diverge — blueprint has `repo_id`, `task_subgraph`, `stable_prompt_blocks`; operational has `purpose`, `pbs_node`, `rubric_context`, `domain_adapter_context`, `state_first_context`.
- **Deferred to runtime PR**: `run-state`, `checkpoint`, and `final-report` are execution runtime schemas. Registering them as operational contracts is premature before runtime substrate exists. They should be registered in `project_contract.yml` as future/deferred with a note.

## Integration Decisions

For each of the four operational files, the implementation must make the following changes:

### 1. `.project-memory/project_contract.yml`

**Purpose of change**: Register Phase 0 blueprint schemas as discoverable contract IDs.

**Entries to add** (each as a `contract_id` entry under `protected_behaviors`):

```text
purpose.schema-path:
  text: "Schema path for Purpose (PCAM) record: schemas/purpose.schema.yml"
  severity: "medium"

pbs.schema-path:
  text: "Schema path for Purpose Breakdown Structure: schemas/pbs.schema.yml"
  severity: "medium"

state-model.schema-path:
  text: "Schema path for State Model: schemas/state-model.schema.yml"
  severity: "medium"

transition-graph.schema-path:
  text: "Schema path for Transition Graph: schemas/transition-graph.schema.yml"
  severity: "medium"

rubric-pack.schema-path:
  text: "Schema path for Rubric Pack: schemas/rubric-pack.schema.yml"
  severity: "medium"

rubric-judge-result.schema-path:
  text: "Schema path for Rubric Judge Result: schemas/rubric-judge-result.schema.yml"
  severity: "medium"

model-capability-profile.schema-path:
  text: "Schema path for Model Capability Profile: schemas/model-capability-profile.schema.yml"
  severity: "medium"

agent-execution-contract.schema-path:
  text: "Schema path for Agent Execution Contract: schemas/agent-execution-contract.schema.yml"
  severity: "medium"

long-context-stress-profile.schema-path:
  text: "Schema path for Long-Context Stress Profile: schemas/long-context-stress-profile.schema.yml"
  severity: "medium"

run-state.schema-path:
  text: "Schema path for Run State: schemas/run-state.schema.yml. Deferred to runtime substrate PR."
  severity: "low"

checkpoint.schema-path:
  text: "Schema path for Checkpoint: schemas/checkpoint.schema.yml. Deferred to runtime substrate PR."
  severity: "low"

final-report.schema-path:
  text: "Schema path for Final Report: schemas/final-report.schema.yml. Deferred to runtime substrate PR."
  severity: "low"
```

**Entries NOT to touch**:

- All existing `protected_behaviors` entries (run-record, apply-gate, workspace-feature, task-intake, model-routing, state-first, review-artifact, conductor-prompt, domain-adapter, context-pack, ariadne-anchor) must remain unchanged.
- `validation_commands`, `forbidden_generated_files`, `human_approval_required_for` must remain unchanged.

**Ordering policy**: Append new entries at the end of `protected_behaviors`. Do not reorder existing entries.

**Duplication policy**: Check each contract_id does not already exist. If it does, skip (do not duplicate).

### 2. `.project-memory/anchors.yml`

**Purpose of change**: Register stable context-retrieval anchors for Phase 0 contracts.

**Entries to add**:

```text
purpose.schema-path:
  type: "contract"
  labels: ["contracts", "purpose"]
  description: "Schema path for Purpose (PCAM) record: schemas/purpose.schema.yml"
  contract_ids:
    - "purpose.schema-path"

pbs.schema-path:
  type: "contract"
  labels: ["contracts", "pbs"]
  description: "Schema path for Purpose Breakdown Structure: schemas/pbs.schema.yml"
  contract_ids:
    - "pbs.schema-path"

state-model.schema-path:
  type: "contract"
  labels: ["contracts", "state-model"]
  description: "Schema path for State Model: schemas/state-model.schema.yml"
  contract_ids:
    - "state-model.schema-path"

transition-graph.schema-path:
  type: "contract"
  labels: ["contracts", "transition-graph"]
  description: "Schema path for Transition Graph: schemas/transition-graph.schema.yml"
  contract_ids:
    - "transition-graph.schema-path"

rubric-pack.schema-path:
  type: "contract"
  labels: ["contracts", "rubric"]
  description: "Schema path for Rubric Pack: schemas/rubric-pack.schema.yml"
  contract_ids:
    - "rubric-pack.schema-path"

rubric-judge-result.schema-path:
  type: "contract"
  labels: ["contracts", "rubric"]
  description: "Schema path for Rubric Judge Result: schemas/rubric-judge-result.schema.yml"
  contract_ids:
    - "rubric-judge-result.schema-path"

model-capability-profile.schema-path:
  type: "contract"
  labels: ["contracts", "model-routing"]
  description: "Schema path for Model Capability Profile: schemas/model-capability-profile.schema.yml"
  contract_ids:
    - "model-capability-profile.schema-path"

agent-execution-contract.schema-path:
  type: "contract"
  labels: ["contracts", "agent-runtime"]
  description: "Schema path for Agent Execution Contract: schemas/agent-execution-contract.schema.yml"
  contract_ids:
    - "agent-execution-contract.schema-path"

long-context-stress-profile.schema-path:
  type: "contract"
  labels: ["contracts", "model-routing"]
  description: "Schema path for Long-Context Stress Profile: schemas/long-context-stress-profile.schema.yml"
  contract_ids:
    - "long-context-stress-profile.schema-path"
```

**Entries NOT to touch**: All existing anchors must remain unchanged.

**Deferred schemas** (run-state, checkpoint, final-report): Add anchors only when runtime substrate PR is initiated. Skip in PR 0043.

### 3. `.project-memory/context-bundles/contracts.yml`

**Purpose of change**: Add Phase 0 blueprint schemas to the `read_first` list and registered anchors to the `anchors` list.

**Version**: Bump from `0.16` to `0.17`.

**read_first additions** (append at end):

```text
- "schemas/purpose.schema.yml"
- "schemas/pbs.schema.yml"
- "schemas/state-model.schema.yml"
- "schemas/transition-graph.schema.yml"
- "schemas/rubric-pack.schema.yml"
- "schemas/rubric-judge-result.schema.yml"
- "schemas/model-capability-profile.schema.yml"
- "schemas/agent-execution-contract.schema.yml"
- "schemas/long-context-stress-profile.schema.yml"
```

**Do NOT add**: `schemas/run-state.schema.yml`, `schemas/checkpoint.schema.yml`, `schemas/final-report.schema.yml` — deferred to runtime PR.

**Do NOT add**: `schemas/context-pack.schema.yml` — only the operational `.project-memory/context-pack.schema.yml` belongs in the bundle. The blueprint schema is a reference document, not an operational contract.

**anchors additions** (append at end):

```text
- "purpose.schema-path"
- "pbs.schema-path"
- "state-model.schema-path"
- "transition-graph.schema-path"
- "rubric-pack.schema-path"
- "rubric-judge-result.schema-path"
- "model-capability-profile.schema-path"
- "agent-execution-contract.schema-path"
- "long-context-stress-profile.schema-path"
```

**notes additions**: Add the following at end:

```text
- "PR 0043 integrates Phase 0 blueprint schemas into operational contract discovery."
- "Phase 0 schemas under schemas/ are blueprint-only references. Operational schemas under .project-memory/*.schema.yml are created in follow-up integration PRs."
- "Purpose (PCAM) and PBS schemas are defined in schemas/purpose.schema.yml and schemas/pbs.schema.yml."
- "State Model and Transition Graph schemas are blueprint-only. Operational state-model and transition-graph schemas will be created in PR 0045."
- "Rubric Pack and Rubric Judge Result schemas are blueprint-only. Operational equivalents will be created in PR 0046."
- "Model Capability Profile and Long-Context Stress Profile are referenced by model-routing contracts."
- "Run State, Checkpoint, and Final Report are deferred to runtime substrate PRs."
- "schemas/context-pack.schema.yml diverges from .project-memory/context-pack.schema.yml and is excluded from the bundle to avoid confusion. Reconciled in PR 0044."
```

### 4. `.project-memory/memory_index.yml`

**Purpose of change**: Add labels for Phase 0 contract domains.

**Version**: Bump from `0.18` to `0.19`.

**New labels to add**:

```text
purpose:
  description: "Purpose (PCAM) schema and contract for agent task purpose decomposition."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/purpose.schema.yml"
  preferred_agent: "architect"

pbs:
  description: "Purpose Breakdown Structure schema and contract for decomposing root purpose into agent-executable nodes."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/pbs.schema.yml"
  preferred_agent: "architect"

state-model:
  description: "State Model schema and State-First contract extension for durable state entities and derived views."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/state-model.schema.yml"
  preferred_agent: "architect"

transition-graph:
  description: "Transition Graph schema for named state transitions with preconditions, postconditions, and invariants."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/transition-graph.schema.yml"
  preferred_agent: "architect"

rubric:
  description: "Rubric Pack and Rubric Judge Result schemas for runtime contract evaluation."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/rubric-pack.schema.yml"
    - "schemas/rubric-judge-result.schema.yml"
  preferred_agent: "architect"

agent-runtime:
  description: "Agent Execution Contract schema defining what agents receive and must return."
  bundles:
    - ".project-memory/context-bundles/contracts.yml"
  additional_files:
    - "schemas/agent-execution-contract.schema.yml"
  preferred_agent: "architect"
```

**Entries NOT to touch**: All existing labels (architecture, context-pack, ariadne-anchors, domain-adapter, sprint-0, sprint-1, task-intake, contracts, agent-config, run-record, apply-gate, workspace-feature, ariadne-namespace, context-steward, task-intake-runner-handoff, model-routing, state-first, conductor-prompt, review-artifacts) must remain unchanged.

**Anchors used** — no change to existing anchors. New anchors from `.project-memory/anchors.yml` become discoverable through the normal anchor lookup mechanism.

### 5. Optional: `.project-memory/phase-0-contracts.yml`

**Decision**: NOT necessary for PR 0043. The existing four operational files (project_contract.yml, anchors.yml, context-bundles/contracts.yml, memory_index.yml) are sufficient to register and discover Phase 0 contracts. A separate phase-0-contracts.yml would duplicate content already present in the bundle and anchors registry.

## Context-Pack Schema Overlap Policy

The blueprint `schemas/context-pack.schema.yml` and operational `.project-memory/context-pack.schema.yml` diverge:

| Aspect | Blueprint (`schemas/`) | Operational (`.project-memory/`) |
|---|---|---|
| Primary fields | repo_id, task, purpose_id, task_subgraph | schema_version, context_pack_id, purpose, pbs_node, repository_context, semantic_context, state_first_context, rubric_context, domain_adapter_context, validation_context, source_trace |
| Version concept | base_sha + index_version | created_at + explicit source_trace array |
| Context sections | Implicit in field list | Explicit typed sections |

**Policy for PR 0043**: Neither schema is modified. The blueprint schema is **excluded** from the contracts bundle read_first list to prevent lookup ambiguity. The operational `.project-memory/context-pack.schema.yml` remains the authoritative contract for runtime context pack structure. The reconciliation is explicitly deferred to PR 0044 as defined in the PR 0042 decomposition.

**Policy for context-bundles/contracts.yml**: Add a note explaining the divergence and deferral.

## Model Capability Profile Integration

The `schemas/model-capability-profile.schema.yml` and `schemas/long-context-stress-profile.schema.yml` must become discoverable operational contracts without hardcoding any provider ideology.

**Policy for PR 0043**:

1. Register contract IDs in `project_contract.yml` (`model-capability-profile.schema-path`, `long-context-stress-profile.schema-path`).
2. Register anchors in `anchors.yml` under `labels: ["contracts", "model-routing"]`.
3. Add to `context-bundles/contracts.yml` read_first and anchors lists.
4. Do NOT add a separate memory index label — the existing `model-routing` label already covers routing contracts. The additional_files in the model-routing label can be extended to include these schemas, but PR 0043 defers that to PR 0047 (Model Capability Profile and Long-Context Stress Profile Integration).

**Preserving ADR 0006**: Contract IDs must not contain provider names. Model capability profiles are runtime data, not contract values. The contract ID `model-capability-profile.schema-path` only points to the schema location.

## Rubric Contract Integration

The `schemas/rubric-pack.schema.yml` and `schemas/rubric-judge-result.schema.yml` must be registered consistently with ADR 0005.

**Policy for PR 0043**:

1. Register contract IDs in `project_contract.yml` (`rubric-pack.schema-path`, `rubric-judge-result.schema-path`).
2. Register anchors in `anchors.yml` under `labels: ["contracts", "rubric"]`.
3. Add to `context-bundles/contracts.yml` read_first and anchors lists.
4. Add a new `rubric` label in `memory_index.yml` with additional_files referencing both schema files.
5. Adr 0005 notes: Add a note in `context-bundles/contracts.yml` notes section referencing ADR 0005.

**Preserving ADR 0005**: Rubrics are runtime contracts, not docs. The schema registration in the operational contract layer ensures discoverability by agents reading the contracts bundle. The runtime Rubric Generator and Rubric Judge are future work (Phases 5+ in the roadmap).

## State / Runtime Contract Integration

The `schemas/state-model.schema.yml`, `schemas/transition-graph.schema.yml`, `schemas/agent-execution-contract.schema.yml`, `schemas/run-state.schema.yml`, `schemas/checkpoint.schema.yml`, and `schemas/final-report.schema.yml` are registered as contracts while deferring runtime implementation.

**Policy for PR 0043**:

- **Register now** (contract IDs, anchors, bundles): state-model, transition-graph, agent-execution-contract
- **Defer** (register with "deferred" note only, no bundle inclusion): run-state, checkpoint, final-report

State-model and transition-graph extend the existing State-First contracts. agent-execution-contract bridges context packs, domain adapters, and agent roles.

Preserving ADR 0003 (State-First): State Model and Transition Graph schemas are consistent with state-first principles. State entities, named transitions, preconditions/postconditions, invariants, and transaction boundaries are all present in the schemas.

## Domain-Agnostic Boundary Check

The implementation must preserve ADR 0004 (Ariadne Is Domain-Agnostic).

**Policy**:

1. All new contract IDs and anchors use generic labels (e.g., `purpose`, `pbs`, `rubric`) — not domain-specific labels like `python-purpose` or `coding-pbs`.
2. The `domain` field in blueprint schemas is a runtime field, not a contract identity.
3. No contract ID references a specific programming language, model provider, or application domain.
4. The existing `domain-adapter.adr-path` anchor in `anchors.yml` already references ADR 0004. No new domain-agnostic policy contract is needed.
5. The `agent-execution-contract.schema-path` anchor uses `labels: ["contracts", "agent-runtime"]` — domain-neutral.

## Future Allowed Write Paths

For the implementation phase of PR 0043:

```text
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0043-phase-0-contracts-integration/PLAN.md
.project-memory/pr/0043-phase-0-contracts-integration/reviews/precommit-review.yml
```

Optional, only if justified: none (phase-0-contracts.yml not needed).

## Future Forbidden Write Paths

```text
.project-memory/pr/0043-phase-0-contracts-integration/PLAN.md (already written)
.project-memory/pr/0043-phase-0-contracts-integration/reviews/plan-review.yml
schemas/**
docs/**
agents/**
services/**
packages/**
apps/**
.ariadne/**
.github/**
docker/**
Dockerfile*
pyproject.toml
package.json
Makefile
PHASE_0_DECOMPOSITION.md
ROADMAP_PHASE_0_PR_PLAN.md
ARIADNE_ARCHITECTURE.md
ROADMAP.md
```

## Contract Registration Plan (Summary Table)

| Operational File | Action | New Entries | Version Bump |
|---|---|---|---|
| `.project-memory/project_contract.yml` | Append contract IDs | 12 new entries | No (version "0.1" is stable by convention) |
| `.project-memory/anchors.yml` | Append anchors | 9 new anchors | No |
| `.project-memory/context-bundles/contracts.yml` | Append read_first, anchors, notes | 9 read_first + 9 anchors + ~7 notes | 0.16 → 0.17 |
| `.project-memory/memory_index.yml` | Append labels | 6 new labels | 0.18 → 0.19 |

## Non-goals

```text
- no runtime implementation
- no agents/services/packages/apps changes
- no schema rewrites
- no docs/ADR rewrites
- no Docker/CI/dependency changes
- no .ariadne namespace creation
- no model-provider hardcoding
- no old .grace namespace
- no water_meter / broken_clock / old Flask examples
- no creation of .project-memory/phase-0-contracts.yml
- no modification of schemas/context-pack.schema.yml
- no creation of operational .project-memory/*.schema.yml files (Purpose, PBS, etc.)
- no modification of existing operational schemas (context-pack, ariadne-anchor, etc.)
```

## Validation Commands

Safe for operational contract update PRs:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
python - <<'PY'
from pathlib import Path
import yaml

paths = [
    ".project-memory/project_contract.yml",
    ".project-memory/anchors.yml",
    ".project-memory/context-bundles/contracts.yml",
    ".project-memory/memory_index.yml",
]
for path in paths:
    data = yaml.safe_load(Path(path).read_text())
    assert data, f"{path} is empty or invalid YAML"
print("operational contract yaml parse: ok")
PY
git status --short
git diff --name-only
```

**Skip policy**: `python -m pytest -q`, `python -m compileall -f services packages`, and `python -m runner doctor` may be skipped if no Python code changes are made. The review artifact must document the skip with reason (e.g., "no Python code changed in this PR — only YAML configuration updates."). The YAML parse check and git status/diff must always run.

## Expected Changed Files

For future implementation:

```text
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0043-phase-0-contracts-integration/PLAN.md
.project-memory/pr/0043-phase-0-contracts-integration/reviews/precommit-review.yml
```

## Review Requirements

- **Architect review** — required (all four operational files are contract/architecture-critical)
- **Precommit review** — required (`.project-memory/**` modifications)
- **Human approval** — required before merge (changes to contract registry and memory index affect all agents)

## Stop Conditions

Stop if implementation:

- duplicates existing contract IDs without checking
- modifies or rewrites `schemas/**` files
- creates or modifies `docs/**` files
- creates or modifies `agents/**`, `services/**`, `packages/**`, `apps/**` files
- creates `\.ariadne/**` files or directories
- creates `.project-memory/phase-0-contracts.yml` without explicit justification in this PLAN.md
- includes provider-specific model routing values in any contract description
- introduces old project names (water_meter, broken_clock, daily-consumption, .grace, @grace-*)
- produces YAML parse errors or invalid YAML in any updated file
- modifies existing operational schemas (`.project-memory/context-pack.schema.yml`, `.project-memory/ariadne-anchor.schema.yml`, etc.)
- rewrites existing anchors/bundles/memory entries instead of appending
- changes `human_approval_required_for`, `validation_commands`, or `forbidden_generated_files` in `project_contract.yml`

## Open Questions

1. Memory index version — should this be 0.19 or 0.18 → 0.19? Given that this is the first Phase 0 integration, 0.19 is appropriate.
2. Should the `domain-adapter` label in memory_index.yml be updated to include `schemas/agent-execution-contract.schema.yml` or kept separate? → This plan recommends a separate label for `agent-runtime` to avoid conflating domain adapter contracts with agent execution contracts.
3. Should `schemas/long-context-stress-profile.schema.yml` be registered under `model-routing` label or a separate label? → This plan recommends adding to the bundle (read_first + anchors) but keeping it under the existing `model-routing` label rather than creating a separate label. PR 0047 will decide if a dedicated label is needed.

## Decisions Made

- **PR 0043 scope**: Register Phase 0 blueprint schemas into operational `.project-memory/**` files only. No new operational schemas created.
- **No `.project-memory/phase-0-contracts.yml`**: Existing four files sufficient.
- **Context-pack schema overlap**: Explictly deferred to PR 0044. Neither schema modified. Blueprint version excluded from bundle.
- **Run-state, checkpoint, final-report**: Registered as "deferred" contract IDs only. No bundle or anchor registration.
- **Memory index version**: 0.18 → 0.19.
- **Contracts bundle version**: 0.16 → 0.17.
- **Domain-agnostic**: All new labels and contract IDs use neutral terms. No domain-specific coding tag.
- **Model replaceability**: No provider names in contract IDs. Model capability profile schema is referenced as runtime data contract.
- **Rubrics as runtime contracts**: Rubric schemas registered as contract-level entities, not documentation.

CONTEXT SNAPSHOT:
- base_sha: adb8747fe6d5b955fa3365151d389ba1f9582253
- base_sha_source: git rev-parse --verify HEAD at PLAN creation time
- index_version: "0.18"
- index_version_source: .project-memory/memory_index.yml
- current_head: adb8747fe6d5b955fa3365151d389ba1f9582253
- stale_snapshot: false
- snapshot_verified: true
- snapshot_verified_by: git introspection

DECISIONS MADE:
- scope: Register Phase 0 schemas into operational discovery. No new operational schemas, no runtime code.
- no phase-0-contracts.yml: existing four files sufficient
- context-pack divergence deferred to PR 0044
- run-state/checkpoint/final-report deferred (runtime-only)
- memory_index: 0.18→0.19, contracts bundle: 0.16→0.17
- domain-agnostic labels and contract IDs preserved
- model replaceability preserved
- rubrics as runtime contracts preserved

CONTEXT USED:
- labels: architecture, contracts, context-pack, ariadne-anchors, domain-adapter, state-first, model-routing, conductor-prompt, review-artifacts
- memory files read: memory_index.yml, project_contract.yml, anchors.yml, context-bundles/contracts.yml, review-artifact.schema.yml
- ADRs inspected: 0004 (domain-agnostic), 0005 (rubrics as runtime contracts), 0006 (model replaceability), 0007 (cached repository understanding)
- files inspected: ARIADNE_ARCHITECTURE.md, ROADMAP.md, all 13 schemas, PR 0042 PLAN.md and plan-review
- files modified: .project-memory/pr/0043-phase-0-contracts-integration/PLAN.md
- files intentionally ignored: services/, agents/, packages/, apps/, .git/, .venv/, node_modules/, pyproject.toml, Makefile
