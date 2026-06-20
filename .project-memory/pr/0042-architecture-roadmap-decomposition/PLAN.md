# PR 0042 — Architecture Roadmap Decomposition Plan

## Goal

Produce a precise decomposition of Ariadne Phase 0 (Architecture Contracts) into concrete follow-up PRs, commit order, acceptance criteria, and implementation boundaries.

This PR receives the architecture blueprint and roadmap from PR 0041 (assumed merged) and answers: *what PRs actually need to be written next, in what order, and who should write each one?*

The future implementation agent must produce:

- `PHASE_0_DECOMPOSITION.md` — detailed Phase 0 breakdown
- `ROADMAP_PHASE_0_PR_PLAN.md` — executable PR-by-PR plan

The future implementation may update `ROADMAP.md` only if the plan explicitly justifies why a roadmap patch is necessary. Prefer separate decomposition artifacts over rewriting the canonical roadmap.

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
- ROADMAP.md — 10-phase roadmap (Phase 0 labeled "Architecture Contracts")
- schemas/purpose.schema.yml
- schemas/pbs.schema.yml
- schemas/context-pack.schema.yml
- schemas/state-model.schema.yml
- schemas/transition-graph.schema.yml
- schemas/rubric-pack.schema.yml
- schemas/rubric-judge-result.schema.yml
- schemas/model-capability-profile.schema.yml
- schemas/agent-execution-contract.schema.yml
- schemas/run-state.schema.yml
- schemas/checkpoint.schema.yml
- schemas/long-context-stress-profile.schema.yml
- schemas/final-report.schema.yml
- docs/adr/0005-rubrics-as-runtime-contracts.md
- docs/adr/0006-model-replaceability.md
- docs/adr/0007-cached-repository-understanding.md
- docs/adr/0004-ariadne-is-domain-agnostic.md (present, referenced)
- .project-memory/project_contract.yml (version "0.1", heavily populated with contract IDs)
- .project-memory/anchors.yml (version "0.1")
- .project-memory/context-bundles/contracts.yml (version "0.16")
- .project-memory/memory_index.yml (version "0.18")
- .project-memory/pr/0041-architecture-blueprint/PLAN.md (present)
- .project-memory/pr/0041-architecture-blueprint/reviews/plan-review.yml (present)
- .project-memory/pr/0041-architecture-blueprint/reviews/precommit-review.yml (present)

## Phase 0 Interpretation

ROADMAP.md defines Phase 0 as **"Architecture Contracts"** with status "Complete in PR 0041":

- 13 schemas under `schemas/*.yml`
- ADRs 0005, 0006, 0007
- `ARIADNE_ARCHITECTURE.md` and `ROADMAP.md`

**However**, Phase 0 according to the PR 0041 plan and the architecture document is a *blueprint phase* — it defines what should exist but does not:

- Integrate these schemas into the operational `.project-memory/**` contract layer
- Create any runtime implementation (even stubs)
- Define the `\.ariadne/` runtime workspace structure
- Write machine-readable anchor instances in code
- Write data model Python classes or dataclasses
- Write any importable code

Therefore Phase 0 is **not complete** for the purpose of enabling Phase 1 implementation. A proper Phase 0 must include a **contracts integration sub-phase** that:

1. Evaluates which blueprint schemas should be promoted to operational `.project-memory/**` schemas
2. Creates a clear mapping from `schemas/*.yml` to `.project-memory/*.schema.yml` or documents intentional divergence
3. Integrates anchor contracts and context-pack contracts into the active `.project-memory/contracts` bundle
4. Creates a `\.ariadne/` namespace structure definition (even if empty/contract-only)
5. Updates the memory index to cover new labels

## Already Completed Phase 0 / Pre-Phase-0 Contracts

These contracts exist and are operationally active in `.project-memory/**`:

| Contract | Status | Location |
|---|---|---|
| Conductor Prompt Contract | Operational | `.project-memory/conductor-prompt-contract.schema.yml` |
| Prompt Artifact Schema | Operational | `.project-memory/prompt-artifact.schema.yml` |
| Domain Adapter Contract | Operational | `.project-memory/domain-adapter.schema.yml` |
| Context Pack Schema | Operational | `.project-memory/context-pack.schema.yml` |
| Ariadne Anchor Schema | Operational | `.project-memory/ariadne-anchor.schema.yml` |
| State-First Schema | Operational | `.project-memory/state-first.schema.yml` |
| Model Routing Schema | Operational | `.project-memory/model-routing.schema.yml` |
| Review Artifact Schema | Operational | `.project-memory/review-artifact.schema.yml` |
| Run Record Schema | Operational | `.project-memory/run-record.schema.yml` |
| Apply Gate Schema | Operational | `.project-memory/apply-gate.schema.yml` |
| Ariadne Architecture Blueprint | Blueprint-only | `ARIADNE_ARCHITECTURE.md` |
| Roadmap | Blueprint-only | `ROADMAP.md` |
| ADR 0005 (Rubrics as Runtime Contracts) | Blueprint-only | `docs/adr/0005-rubrics-as-runtime-contracts.md` |
| ADR 0006 (Model Replaceability) | Blueprint-only | `docs/adr/0006-model-replaceability.md` |
| ADR 0007 (Cached Repository Understanding) | Blueprint-only | `docs/adr/0007-cached-repository-understanding.md` |

## Existing Blueprint Schemas

All 13 schemas under `schemas/**` are blueprint-only. None is operationally integrated into `.project-memory/**` yet.

| Schema | Status | Relationship to Operational Schemas |
|---|---|---|
| `schemas/purpose.schema.yml` | Blueprint-only | No operational equivalent exists. Needs integration. |
| `schemas/pbs.schema.yml` | Blueprint-only | No operational equivalent exists. Needs integration. |
| `schemas/context-pack.schema.yml` | Blueprint-only | Operational equivalent at `.project-memory/context-pack.schema.yml`. Diverges — blueprint has `repo_id`, `task`, `task_subgraph`; operational has `purpose`, `pbs_node`, `rubric_context`, `domain_adapter_context`. Needs reconciliation. |
| `schemas/state-model.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/transition-graph.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/rubric-pack.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/rubric-judge-result.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/model-capability-profile.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/agent-execution-contract.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/run-state.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/checkpoint.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/long-context-stress-profile.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |
| `schemas/final-report.schema.yml` | Blueprint-only | No operational equivalent. Needs integration. |

Key observation: The blueprint `schemas/context-pack.schema.yml` diverges from the operational `.project-memory/context-pack.schema.yml`. This intentional divergence must be resolved in Phase 0 contracts integration.

## Decomposition Strategy

Divide Phase 0 work into four categories:

1. **Docs-only** — documentation that defines but does not operationalize
2. **Contract integration** — promoting or aligning blueprint schemas into the operational `.project-memory/**` contract layer
3. **Runtime substrate skeleton** — minimal importable code (dataclasses, stubs) needed by Phase 1 but safe to create in Phase 0
4. **Validation** — PRs that only validate existing contracts

The strategy is:

- PR 0043 — Integrate Purpose and PBS schemas into operational contracts
- PR 0044 — Reconcile and integrate Context Pack schema
- PR 0045 — Integrate State Model and Transition Graph schemas
- PR 0046 — Integrate Rubric Pack and Rubric Judge Result schemas
- PR 0047 — Integrate Model Capability Profile and Long-Context Stress Profile schemas
- PR 0048 — Integrate Agent Execution Contract schema
- PR 0049 — Integrate Run State, Checkpoint, and Final Report schemas
- PR 0050 — Integrate Ariadne namespace structure definition
- PR 0051 — Update memory index, contracts bundle, and anchors for all Phase 0 integrations

## Proposed Follow-up PR Sequence

### PR 0043 — Purpose and PBS Contracts Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schemas for Purpose (PCAM) and PBS in `.project-memory/`, update contracts bundle, update memory index |
| **Allowed write paths** | `.project-memory/purpose.schema.yml`, `.project-memory/pbs.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md`, `.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/plan-review.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/precommit-review.yml` |
| **Forbidden write paths** | `services/**`, `agents/**`, `packages/**`, `apps/**`, `src/**`, `\.ariadne/**`, `Dockerfile*`, `.github/**` |
| **Inputs** | `schemas/purpose.schema.yml`, `schemas/pbs.schema.yml`, `docs/adr/0004-ariadne-is-domain-agnostic.md` |
| **Expected outputs** | `.project-memory/purpose.schema.yml`, `.project-memory/pbs.schema.yml`, updated `.project-memory/context-bundles/contracts.yml`, updated `.project-memory/memory_index.yml` |
| **Acceptance criteria** | Schemas parse as YAML, contracts bundle lists new schemas, memory index has new labels |
| **Risk level** | Low |
| **Reviewer requirements** | architect |

### PR 0044 — Context Pack Schema Reconciliation

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Reconcile `schemas/context-pack.schema.yml` with `.project-memory/context-pack.schema.yml`. Document divergence rationale. Update operational schema to support Phase 0 concepts (purpose_id, task_subgraph) while preserving existing contracts. |
| **Allowed write paths** | `.project-memory/context-pack.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Forbidden write paths** | Same as PR 0043 |
| **Inputs** | `schemas/context-pack.schema.yml`, `.project-memory/context-pack.schema.yml`, `docs/CONTEXT_COMPILER.md` |
| **Expected outputs** | Updated `.project-memory/context-pack.schema.yml` |
| **Acceptance criteria** | No existing contract IDs broken. New fields added without removing old ones. Schema version bumped. |
| **Risk level** | Medium — existing contracts depend on current shape |
| **Reviewer requirements** | architect, precommit-review |

### PR 0045 — State Model and Transition Graph Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schemas for State Model and Transition Graph in `.project-memory/` |
| **Allowed write paths** | `.project-memory/state-model.schema.yml`, `.project-memory/transition-graph.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `schemas/state-model.schema.yml`, `schemas/transition-graph.schema.yml`, `.project-memory/state-first.schema.yml`, `docs/adr/0003-state-first-agent-architecture.md` |
| **Risk level** | Low |
| **Reviewer** | architect |

### PR 0046 — Rubric Pack and Rubric Judge Result Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schemas for Rubric Pack and Rubric Judge Result in `.project-memory/` |
| **Allowed write paths** | `.project-memory/rubric-pack.schema.yml`, `.project-memory/rubric-judge-result.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `schemas/rubric-pack.schema.yml`, `schemas/rubric-judge-result.schema.yml`, `docs/adr/0005-rubrics-as-runtime-contracts.md` |
| **Risk level** | Low |
| **Reviewer** | architect |

### PR 0047 — Model Capability Profile and Long-Context Stress Profile Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schemas for Model Capability Profile and Long-Context Stress Profile in `.project-memory/` |
| **Allowed write paths** | `.project-memory/model-capability-profile.schema.yml`, `.project-memory/long-context-stress-profile.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `schemas/model-capability-profile.schema.yml`, `schemas/long-context-stress-profile.schema.yml`, `.project-memory/model-routing.schema.yml`, `docs/adr/0002-model-selection-methodology.md`, `docs/adr/0006-model-replaceability.md` |
| **Risk level** | Low |
| **Reviewer** | architect |

### PR 0048 — Agent Execution Contract Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schema for Agent Execution Contract in `.project-memory/` |
| **Allowed write paths** | `.project-memory/agent-execution-contract.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `schemas/agent-execution-contract.schema.yml`, `.project-memory/conductor-prompt-contract.schema.yml`, `.project-memory/domain-adapter.schema.yml`, `docs/CONDUCTOR_PROMPT_CONTRACT.md` |
| **Risk level** | Medium — execution contract touches many existing contracts |
| **Reviewer** | architect, precommit-review |

### PR 0049 — Run State, Checkpoint, and Final Report Integration

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Create operational schemas for Run State, Checkpoint, and Final Report in `.project-memory/` |
| **Allowed write paths** | `.project-memory/run-state.schema.yml`, `.project-memory/checkpoint.schema.yml`, `.project-memory/final-report.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `schemas/run-state.schema.yml`, `schemas/checkpoint.schema.yml`, `schemas/final-report.schema.yml`, `.project-memory/run-record.schema.yml`, `.project-memory/state-first.schema.yml` |
| **Risk level** | Medium — run state and checkpoints relate to existing run-record and apply-gate contracts |
| **Reviewer** | architect, precommit-review |

### PR 0050 — Ariadne Namespace Structure Definition

| Field | Value |
|---|---|
| **Type** | contract-integration |
| **Purpose** | Define `\.ariadne/` namespace directory structure, file conventions, and storage policies. Create operational schema for the namespace layout. Update ADR 0001 references if needed. |
| **Allowed write paths** | `.project-memory/ariadne-namespace.schema.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/memory_index.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md` |
| **Inputs** | `docs/adr/0001-ariadne-namespace.md`, `.project-memory/workspace-feature-record.schema.yml`, `.project-memory/context-steward-archival.schema.yml` |
| **Expected outputs** | `.project-memory/ariadne-namespace.schema.yml` |
| **Acceptance criteria** | Namespace structure can be validated against this schema. No files are actually created in `\.ariadne/`. |
| **Risk level** | Low |
| **Reviewer** | architect |

### PR 0051 — Phase 0 Final Memory and Contracts Bundle Update

| Field | Value |
|---|---|
| **Type** | migration |
| **Purpose** | Update `.project-memory/memory_index.yml` version, add all new operational labels, update `.project-memory/context-bundles/contracts.yml` to version 0.17+, add all new anchors, update `.project-memory/anchors.yml`. |
| **Allowed write paths** | `.project-memory/memory_index.yml`, `.project-memory/anchors.yml`, `.project-memory/context-bundles/contracts.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/PHASE_0_DECOMPOSITION.md`, `.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/plan-review.yml`, `.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/precommit-review.yml` |
| **Inputs** | All `.project-memory/*.schema.yml` files created in PRs 0043–0050 |
| **Risk level** | Low — mechanical updates only |
| **Reviewer** | precommit-review |
| **Note** | This is the last Phase 0 PR. After this, Phase 1 (Runtime Substrate) can begin. |

## Docs-only vs Operational vs Runtime Split

| Category | PRs | Description |
|---|---|---|
| **Docs-only** | None in this sequence (documentation already written in PR 0041) | No new docs-only PRs needed for Phase 0 |
| **Contract integration** | 0043, 0044, 0045, 0046, 0047, 0048, 0049, 0050 | Promote blueprint schemas to operational `.project-memory/**` |
| **Migration** | 0051 | Update memory index, contracts bundle, anchors |
| **Runtime-substrate** | None in Phase 0 (these are Phase 1+ work) | Phase 1 begins after PR 0051 |
| **Validation** | None separate (validation is built into each PR's acceptance criteria) | |

## Exact Commit Order

1. PR 0043 — Purpose and PBS contracts
2. PR 0044 — Context Pack reconciliation
3. PR 0045 — State Model and Transition Graph
4. PR 0046 — Rubric Pack and Rubric Judge Result
5. PR 0047 — Model Capability Profile and Long-Context Stress Profile
6. PR 0048 — Agent Execution Contract
7. PR 0049 — Run State, Checkpoint, Final Report
8. PR 0050 — Ariadne namespace structure definition
9. PR 0051 — Phase 0 final memory and contracts bundle update

## First Coder-Executable PR After 0042

**PR 0043** — Purpose and PBS Contracts Integration is the first PR a coder agent can execute.

Rationale:
- It is contract-only (YAML schemas, bundle updates)
- No runtime code required
- No services/agents/Docker changes
- Clear inputs and outputs
- Low risk
- Directly follows from the blueprint

## Non-goals

```text
- no production runtime implementation in PR 0042
- no services/packages/apps changes in PR 0042
- no Docker/CI/dependency changes in PR 0042
- no .ariadne namespace creation in PR 0042
- no model-provider hardcoding
- no old .grace namespace
- no old water_meter / broken_clock examples
```

## Future Allowed Write Paths

For the future implementation phase of PR 0042:

```text
PHASE_0_DECOMPOSITION.md
ROADMAP_PHASE_0_PR_PLAN.md
ROADMAP.md (only if explicit justification for a roadmap patch is provided)
.project-memory/pr/0042-architecture-roadmap-decomposition/PLAN.md
.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/plan-review.yml
.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/precommit-review.yml
```

## Future Forbidden Write Paths

For the future implementation phase of PR 0042:

```text
ARIADNE_ARCHITECTURE.md
schemas/**
docs/adr/**
docs/CONTEXT_COMPILER.md
docs/ARIADNE_ANCHORS.md
docs/CONDUCTOR_PROMPT_CONTRACT.md
docs/DOMAIN_ADAPTER_CONTRACT.md
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
.project-memory/** (except PR 0042's own PLAN.md and review artifacts)
```

## Validation Commands

Safe for architecture/documentation PRs:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
git status --short
git diff --name-only
```

`python -m pytest -q` and `python -m compileall -f services packages` are expected to pass but may be skipped if the PR contains no Python code changes — in which case the skip must be documented with reason in the review artifact.

`PYTHONPATH=services/runner/src python -m runner doctor` should be skipped if no runner code changes are made. The review artifact must explain why.

## Expected Changed Files

For the future implementation phase of PR 0042:

```text
PHASE_0_DECOMPOSITION.md
ROADMAP_PHASE_0_PR_PLAN.md
.project-memory/pr/0042-architecture-roadmap-decomposition/PLAN.md
.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/plan-review.yml
.project-memory/pr/0042-architecture-roadmap-decomposition/reviews/precommit-review.yml
```

Conditional:

- `ROADMAP.md` — only if explicit justification for a roadmap patch is provided

## Review Requirements

- **Architect review** — required for all PRs that modify contracts, schemas, or memory index
- **Precommit review** — required for PRs that modify `.project-memory/**` contracts
- **Human approval** — required for root purpose changes, agent permission changes, and any deviation from the decomposition plan

## Stop Conditions

Stop if future implementation:

- modifies services/agents/packages/apps
- creates `\.ariadne/**` files (namespace structures defined in contracts are fine)
- writes runtime implementation code
- introduces model-provider hardcoding
- uses old project names or examples (water_meter, broken_clock, .grace, @grace-*)
- modifies `ARIADNE_ARCHITECTURE.md` or existing `docs/adr/**` (ADRs 0005–0007 are blueprint-only and should not be touched by this PR)
- creates review artifacts for PRs other than 0042

## Open Questions

1. Should the `schemas/context-pack.schema.yml` divergence be resolved by updating the blueprint, updating the operational schema, or both with explicit documentation?
   → Decision for PR 0044 implementation. This PLAN recommends updating `.project-memory/context-pack.schema.yml` to reconcile, keeping `schemas/context-pack.schema.yml` as the canonical blueprint reference.

2. Should PR 0050 define `\.ariadne/` as a contract-only schema, or should it also create the directory structure?
   → Decision for PR 0050 implementation. This PLAN recommends contract-only (no directory creation) — consistent with the existing policy that `\.ariadne/**` is not created in contract PRs.

3. Can Phase 1 (Runtime Substrate) start in parallel with later Phase 0 integration PRs?
   → No — Phase 1 depends on operational run-state and checkpoint schemas (PR 0049). Phase 1 should begin only after PR 0051 is merged and the full Phase 0 contract layer is operational.

4. Should `ROADMAP.md` be updated to reflect the Phase 0 sub-PRs?
   → This PLAN recommends against rewriting ROADMAP.md. The decomposition artifacts (`PHASE_0_DECOMPOSITION.md`, `ROADMAP_PHASE_0_PR_PLAN.md`) should describe the sub-PRs. ROADMAP.md should stay as canonical high-level phase definitions.

## Decisions Made

- **Phase 0 is not complete.** PR 0041 created the blueprint but not the operational contract integration. Nine follow-up PRs (0043–0051) are needed.
- **All 13 blueprint schemas need operational equivalents** in `.project-memory/**`.
- **`schemas/context-pack.schema.yml` diverges from `.project-memory/context-pack.schema.yml`** — this needs reconciliation in PR 0044.
- **`ROADMAP.md` should not be rewritten** — decomposition artifacts are sufficient.
- **No runtime code** — all Phase 0 follow-up PRs are contract-integration only.
- **First coder-executable PR: 0043** — Purpose and PBS Contracts Integration.

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
- Phase 0 is a blueprint, not operational — 9 follow-up PRs needed
- `ROADMAP.md` stays canonical high-level, decomposition artifacts describe sub-PRs
- First coder-executable PR: 0043 (Purpose and PBS Contracts Integration)
- No runtime code in any Phase 0 follow-up PR
- `schemas/context-pack.schema.yml` divergence must be reconciled in PR 0044

CONTEXT USED:
- labels: architecture, contracts, development-order, sprint-0, sprint-1, context-pack, ariadne-anchors, state-first, model-routing, domain-adapter
- memory files read: memory_index.yml, project_contract.yml, anchors.yml, context-bundles/contracts.yml
- ADRs inspected: 0004 (domain-agnostic), 0005 (rubrics as runtime contracts), 0006 (model replaceability), 0007 (cached repository understanding)
- implementation files inspected: ARIADNE_ARCHITECTURE.md, ROADMAP.md, all 13 schemas, 0041 PLAN.md and review artifacts
- files modified: .project-memory/pr/0042-architecture-roadmap-decomposition/PLAN.md
- files intentionally ignored: services/, agents/, packages/, apps/, .git/, .venv/, node_modules/
