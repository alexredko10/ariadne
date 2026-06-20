# PR 0035: State-First Agent Architecture Contract

## Goal

Formalise State-First Agent Architecture as ADR + future schema/contract plan.

Define future artifacts:

```text
state_model.json
transition_graph.json
invariant_registry.json
state_trace.json
```

Define future contract schema:

```text
.project-memory/state-first.schema.yml
```

Extend `@ariadne-*` annotation system with state-oriented anchors.

Do not implement `state_core/` components in this PR.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "3edc38ba24d9ad0007b75725c4a8b878748453a2"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.12"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "3edc38ba24d9ad0007b75725c4a8b878748453a2"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review must report snapshot deltas but must not block
solely because current HEAD differs from PLAN.md base_sha, unless scope
evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no implementation of state_model_extractor
- no implementation of transition_graph_builder
- no implementation of invariant_registry
- no implementation of state_trace_builder
- no implementation of event_to_state_folder
- no implementation of state_verifier
- no services/ changes
- no agents/ config changes
- no actual state_model.json generation
- no actual transition_graph.json generation
- no actual invariant_registry.json generation
- no actual state_trace.json generation
- no changes to existing @ariadne-domain / @ariadne-risk / @ariadne-invariant semantics
- no replacement of existing annotation system
- no ban on event-driven architecture
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

## Commit structure

Document intended two-commit structure:

```text
commit 1:
  chore(memory): plan state-first architecture contract

  files:
  - .project-memory/pr/0035-state-first-architecture-contract/PLAN.md
  - docs/adr/0003-state-first-agent-architecture.md

commit 2:
  chore(memory): add state-first architecture contract

  files:
  - .project-memory/state-first.schema.yml
  - .project-memory/project_contract.yml
  - .project-memory/anchors.yml
  - .project-memory/context-bundles/contracts.yml
  - .project-memory/memory_index.yml
  - .project-memory/pr/0035-state-first-architecture-contract/PLAN.md
```

Plan-review is not saved as a file in this PR.
Plan-review approval will be recorded in PR body.

## Allowed write paths for future implementation commit 2

```text
.project-memory/state-first.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0035-state-first-architecture-contract/PLAN.md
```

ADR already written in commit 1:

```text
docs/adr/0003-state-first-agent-architecture.md
```

## Forbidden write paths for future implementation

```text
services/**
agents/**
.ariadne/**
packages/**
apps/**
docs/** except docs/adr/0003-state-first-agent-architecture.md
.github/**
docker/**
Dockerfile*
prompts/**
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/model-routing.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
```

## Required ADR

Create:

```text
docs/adr/0003-state-first-agent-architecture.md
```

ADR must include:

- title: ADR 0003: State-First Agent Architecture
- status: Accepted
- date: 2026-06-19
- context about why event-driven systems are difficult for AI agents, why state is easier to inspect/verify/replay/explain, and that UI/API/report should be derived from state (`View = F(State)`)
- decision: Ariadne adopts State-First as default architecture principle; events at boundary, state at core
- consequences (positive and negative)
- event exception policy
- annotation extensions (`@ariadne-state`, `@ariadne-transition`, `@ariadne-invariant`, `@ariadne-register`, `@ariadne-derived-view`)
- agent rules (all 7)
- relationship to existing contracts
- future work

## Future required schema

PLAN must specify that commit 2 will create:

```text
.project-memory/state-first.schema.yml
```

Schema must define/comment: StateEntity, Transition, InvariantEntry, StateTrace, StateFirstContextPack, annotation extensions, agent rules, event exception policy, safety rules, minimal valid Transition example, and invalid cases.

StateEntity required fields: `name`, `storage`, `table_or_key` (optional), `fields`, `description`.

Transition required fields: `id`, `input`, `reads`, `writes`, `preconditions`, `postconditions`, `invariants`, `transaction_boundary`, `idempotent`, `side_effects`, `rollback_behavior`.

InvariantEntry required fields: `id`, `description`, `severity`, `applies_to`, `verifiable_by`.

StateTrace required fields: `transition_id`, `timestamp`, `before_snapshot`, `after_snapshot`, `invariants_checked`, `invariants_passed`, `invariants_failed`, `outcome`.

StateFirstContextPack fields: `state_entities`, `transitions`, `invariants`, `derived_views`, `event_sources`, `side_effects`, `transaction_boundaries`, `state_traces`.

Safety rules: StateTrace is evidence only; transitions must not bypass apply-gate or Model Gateway JWT; state mutations outside named transitions are contract violations; invariant bypass is CRITICAL.

Invalid cases: state mutation outside named transition; transition without preconditions; transition without invariants on high-risk entity; event-driven subsystem with no state projection; StateTrace used to authorize canonical write.

## Future required contract ids

PLAN must list these future contract ids for commit 2:

```text
state-first.architecture.required
state-first.adr-path
state-first.schema-path
state-first.explicit-state-store.required
state-first.named-transitions.required
state-first.invariant-check.required
state-first.transaction-boundary.required
state-first.events-at-boundary-only
state-first.event-subsystem-high-risk
state-first.state-trace-evidence-only
state-first.no-bypass-apply-gate
state-first.no-bypass-model-gateway-jwt
state-first.annotation-extensions
state-first.no-implementation-this-pr
```

## Future required anchors

PLAN must list these future anchors for commit 2:

```text
state-first.architecture.required
state-first.adr-path
state-first.named-transitions.required
state-first.invariant-check.required
state-first.events-at-boundary-only
state-first.event-subsystem-high-risk
state-first.state-trace-evidence-only
state-first.no-bypass-apply-gate
```

## Future context bundle update

PLAN must specify commit 2 will update:

```text
.project-memory/context-bundles/contracts.yml
```

Required additions: state-first.schema.yml to read_first, docs/adr/0003-state-first-agent-architecture.md to read_first, state-first anchors, notes, and bundle version bump.

## Future memory index update

PLAN must specify commit 2 will update:

```text
.project-memory/memory_index.yml
```

Required: bump version, add label `state-first` with description and additional_files referencing the schema and ADR, preferred_agent: architect.

## Relationship to existing contracts

Model Gateway JWT contract preserved. apply-gate.schema.yml preserved. Existing `@ariadne-*` annotation system extended, not replaced. `state_first_context` will become part of future TaskSubgraph output. No `state_core/` implementation in this PR. Events are not banned. Events at boundary, state at core.

## Stop conditions

Stop if future implementation: modifies services/**, modifies agents/**, creates `.ariadne/**`, creates run_record.yml, bans event-driven architecture entirely, modifies forbidden schemas, adds non-stdlib dependencies, bypasses apply-gate, or bypasses Model Gateway JWT.

## Validation for commit 1

Planner must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "State-First\|state-first\|0003-state-first" .project-memory/pr/0035-state-first-architecture-contract docs/adr
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
```

## Expected changed files for commit 1

```text
.project-memory/pr/0035-state-first-architecture-contract/PLAN.md
docs/adr/0003-state-first-agent-architecture.md
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
