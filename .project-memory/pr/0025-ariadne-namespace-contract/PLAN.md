## Implementation note

PR 0025 implemented:
- Created `docs/adr/0001-ariadne-namespace.md` with namespace roles, safety rules, consequences, and relationship to Workspace Feature Record / Context Steward archival
- Added 11 `ariadne.namespace.*` contract entries to `.project-memory/project_contract.yml`
- Added 6 ariadne-namespace anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.6 with ADR in read_first, workspace-feature-record schema reference, ariadne anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.8 with new `ariadne-namespace` label and ADR references

No `.ariadne/**` files created. No feature instances. No schema modifications to workspace-feature-record, run-record, or apply-gate. No runner code changed.# PR 0025: `.ariadne/` namespace ADR + contract

## Goal

Introduce an ADR and project-memory contracts for the `.ariadne/` namespace.

The ADR must define:

```text
.ariadne/ is repository-local runtime/workspace state.
.project-memory/ is durable contracts/history/project memory.
```

This PR must define `.ariadne/features/{id}.yml` as the future physical storage location for Workspace Feature Records, without creating actual feature record instances in this PR.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "701150f2074a44c5ecd33018a63f183d16fef76a"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.7"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "701150f2074a44c5ecd33018a63f183d16fef76a"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review should report snapshot deltas but must not block solely because current HEAD differs from PLAN.md base_sha, unless scope evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no actual .ariadne/features/{id}.yml records
- no actual feature record instances
- no Context Steward archival workflow implementation
- no context-steward schema yet
- no runner Python dataclass
- no runner implementation
- no API server
- no frontend
- no automatic team runner
- no ApplyPatch changes
- no Artifact Store changes
- no WorktreeManager changes
- no run_record.yml creation
- no Run Record schema changes
- no Apply Gate schema changes
- no Docker commands
- no git mutation commands by agents
- no workflow/GHCR/Dockerfile changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
docs/adr/0001-ariadne-namespace.md
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0025-ariadne-namespace-contract/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/run-record.schema.yml
.project-memory/apply-gate.schema.yml
.project-memory/context-bundles/agent-config.yml
agents/**
services/**
packages/**
apps/**
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
```

Docs allowed exception:

- `docs/adr/0001-ariadne-namespace.md` only

## Required ADR

Create:

```text
docs/adr/0001-ariadne-namespace.md
```

ADR must include:

- title: `ADR 0001: .ariadne namespace`
- status: `Accepted`
- date or placeholder date
- context
- decision
- consequences
- non-goals
- relationship to `.project-memory/`
- relationship to Workspace Feature Record
- relationship to Context Steward archival
- forbidden current behavior
- future work

ADR decision must state:

```text
.ariadne/ is reserved for repository-local runtime/workspace state.
.project-memory/ remains the durable home for contracts, schemas, historical plans, anchors, and durable project memory.
.ariadne/features/{id}.yml is the future physical storage path for Workspace Feature Records.
PR 0025 defines the namespace only and does not create feature records.
```

ADR must define namespace roles:

```text
.project-memory/
- contracts
- schemas
- anchors
- historical PR plans
- durable project memory
- validation and governance evidence

.ariadne/
- workspace state
- feature records
- archival outputs produced by future Context Steward workflow
- runtime/workspace metadata that should not be mixed into contract schemas
```

ADR must include safety rules:

- `.ariadne/**` may be introduced only by this ADR/contract.
- No agents may write `.ariadne/**` unless a future contract explicitly permits it.
- `.ariadne/features/{id}.yml` records must conform to `.project-memory/workspace-feature-record.schema.yml`.
- Feature record ids must be stable, repo-unique, lowercase kebab-case, and must not contain path separators.
- Context Steward archival may write `.ariadne/features/{id}.yml` only after a future archival workflow contract exists.
- Artifact references remain evidence-only and do not authorize canonical mutation.
- ApplyPatch HITL gate remains the only path toward future canonical mutation.

ADR must explicitly say:

- Storage decision is made now.
- Actual writer workflow is future PR 0026.
- Actual records are not created in PR 0025.
- `.project-memory/workspace-feature-record.schema.yml` remains the schema source of truth.

## Required contract ids

Update `.project-memory/project_contract.yml` with contract ids equivalent to:

```text
ariadne.namespace.required
ariadne.namespace.adr-path
ariadne.namespace.role-runtime-workspace-state
ariadne.namespace.project-memory-role-durable-contracts
ariadne.namespace.features-storage-path
ariadne.namespace.no-feature-instances-this-pr
ariadne.namespace.feature-records-must-match-schema
ariadne.namespace.context-steward-writer-future-contract
ariadne.namespace.no-agent-writes-without-contract
ariadne.namespace.apply-gate-remains-canonical-mutation-gate
ariadne.namespace.artifact-references-evidence-only
```

Contract semantics:

- ADR path is `docs/adr/0001-ariadne-namespace.md`
- `.ariadne/` is runtime/workspace state
- `.project-memory/` is durable contracts/history/project memory
- future Workspace Feature Record physical storage path is `.ariadne/features/{id}.yml`
- no actual feature instances are created in PR 0025
- feature records must conform to `.project-memory/workspace-feature-record.schema.yml`
- future Context Steward writer requires separate workflow contract
- agents may not write `.ariadne/**` without explicit future contract
- ApplyPatch/HITL remains canonical mutation gate
- artifact references remain evidence-only

## Required anchors

Update `.project-memory/anchors.yml` with anchors equivalent to:

```text
ariadne.namespace.required
ariadne.namespace.adr-path
ariadne.namespace.features-storage-path
ariadne.namespace.no-feature-instances-this-pr
ariadne.namespace.context-steward-writer-future-contract
ariadne.namespace.no-agent-writes-without-contract
```

Preserve existing anchor structure and add these anchors consistently.

## Required contracts bundle update

Update `.project-memory/context-bundles/contracts.yml`:

- include `docs/adr/0001-ariadne-namespace.md` in `read_first` or equivalent
- include `.project-memory/workspace-feature-record.schema.yml`
- include ariadne namespace anchors
- add note that `.ariadne/features/{id}.yml` is future physical storage for Workspace Feature Records
- add note that PR 0025 creates no actual `.ariadne/**` files
- add note that Context Steward archival writer remains future PR 0026
- bump bundle version according to existing convention

## Required memory index update

Update `.project-memory/memory_index.yml`:

- bump version by one minor step: `"0.7"` → `"0.8"`
- add or update an `ariadne-namespace` label
- ensure contracts label references `docs/adr/0001-ariadne-namespace.md`
- ensure workspace-feature label or contracts bundle can discover the ADR
- include ADR in relevant additional files

## Relationship to existing contracts

```text
PR 0024 defined the Workspace Feature Record schema and contract, but intentionally did not define .ariadne/** storage.
PR 0025 defines the .ariadne/ namespace and physical future storage path.
Workspace Feature Records remain governed by .project-memory/workspace-feature-record.schema.yml.
Future physical records may live at .ariadne/features/{id}.yml.
Context Steward archival workflow remains future PR 0026.
Run Record captures execution evidence.
Workspace Feature Record captures durable feature/workspace state.
run_id → feature_workspace_id remains required for traceability.
Artifact Store references are evidence only and do not authorize writes.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "ariadne.namespace\|0001-ariadne-namespace\|.ariadne/features\|ariadne-namespace" .project-memory docs/adr
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- import regression grep has no matches
- ariadne namespace grep shows ADR, contract ids, anchors, contracts bundle, and memory index references

## Stop conditions

Stop if:

- implementation creates `.ariadne/**` files
- implementation creates actual feature records
- implementation creates actual `run_record.yml` files
- implementation modifies `.project-memory/workspace-feature-record.schema.yml`
- implementation modifies `.project-memory/run-record.schema.yml`
- implementation modifies `.project-memory/apply-gate.schema.yml`
- implementation modifies runner code
- implementation adds Python dataclasses
- implementation modifies services/packages/apps/.github/docker
- implementation modifies docs outside `docs/adr/0001-ariadne-namespace.md`
- implementation adds non-stdlib dependencies
- implementation weakens Run Record, Workspace Feature Record, Apply Gate, Artifact Store, WorktreeManager, MockCoder, or patch safety invariants

## Machine-checkable acceptance criteria

```text
adr_path: docs/adr/0001-ariadne-namespace.md
project_contract_ids: required
anchors: required
contracts_bundle_reference: required
memory_index_bump: required
memory_index_expected_version_if_current_0_7: "0.8"
ariadne_namespace_role: runtime_workspace_state
project_memory_role: durable_contracts_history_project_memory
feature_record_future_storage_path: .ariadne/features/{id}.yml
feature_record_schema_source: .project-memory/workspace-feature-record.schema.yml
context_steward_writer_future_contract: required
actual_ariadne_files_this_pr: forbidden
actual_feature_instances: forbidden
actual_run_record_files: forbidden
runner_dataclass: forbidden
runner_code_changes: forbidden
workspace_feature_schema_changes: forbidden
apply_gate_schema_changes: forbidden
run_record_schema_changes: forbidden
non_stdlib_dependencies: forbidden
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
docs/adr/0001-ariadne-namespace.md
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0025-ariadne-namespace-contract/PLAN.md
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
