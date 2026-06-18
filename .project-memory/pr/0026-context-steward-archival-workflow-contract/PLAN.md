## Implementation note

PR 0026 implemented:
- Created `.project-memory/context-steward-archival.schema.yml` with trigger, preconditions, source, destination, required_evidence, archival_action, postconditions, forbidden_actions, invalid cases list, and minimal valid example
- Added 13 `context-steward.archival.*` contract entries to `.project-memory/project_contract.yml`
- Added 7 context-steward archival anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.7 with context-steward-archival schema in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.9 with new `context-steward` label and schema references

No `.ariadne/**` files created. No actual feature records. No schema modifications to workspace-feature-record, run-record, or apply-gate. No runner code changed.# PR 0026: Context Steward archival workflow contract

## Goal

Add a project-memory Context Steward archival workflow schema and contract anchors.

The workflow contract must define:

```text
when archival is required
what evidence is required before archival
where the final Workspace Feature Record is written
how run_record evidence links to feature_workspace_id
what Context Steward may and may not mutate
```

## Context snapshot

```yaml
context_snapshot:
  base_sha: "430272cdcfc0feb430efccc46e52fd961a3b2fd4"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.8"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "430272cdcfc0feb430efccc46e52fd961a3b2fd4"
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
- no actual .ariadne/** files
- no actual .ariadne/features/{id}.yml records
- no actual feature record instances
- no runtime Context Steward implementation
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
- no Workspace Feature Record schema changes
- no Apply Gate schema changes
- no Docker commands
- no git mutation commands by agents
- no workflow/GHCR/Dockerfile changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
.project-memory/context-steward-archival.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0026-context-steward-archival-workflow-contract/PLAN.md
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
docs/**
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

## Required schema

Create:

```text
.project-memory/context-steward-archival.schema.yml
```

Schema must define Context Steward archival workflow as a contract artifact, not runtime implementation.

Required top-level fields:

```text
schema_version
workflow_id
workflow_name
trigger
preconditions
source
destination
required_evidence
archival_action
postconditions
forbidden_actions
handoff
```

Required `trigger` contract:

```yaml
trigger:
  event: "after_merge"
  source_pr: "<PR-ID>"
  required_status: "merged"
```

Rules:

- archival starts only after merge
- archival must not run for unmerged PRs
- archival must not run from chat-only state
- source PR must be explicit

Required `preconditions` contract:

```yaml
preconditions:
  workspace_feature_record_exists: true
  workspace_feature_record_status: "merged"
  run_record_links_present: true
  human_review_complete: true
  validation_evidence_present: true
  storage_namespace_contract_present: true
```

Rules:

- Workspace Feature Record must exist as valid data before archival
- `run_record_links` must include `run_id` and `feature_workspace_id`
- `.ariadne/` namespace ADR must be present
- archival must not invent missing evidence

Required `source` contract:

```yaml
source:
  workspace_feature_schema: ".project-memory/workspace-feature-record.schema.yml"
  run_record_schema: ".project-memory/run-record.schema.yml"
  namespace_adr: "docs/adr/0001-ariadne-namespace.md"
```

Required `destination` contract:

```yaml
destination:
  path_template: ".ariadne/features/{feature_workspace_id}.yml"
  path_rules:
    repo_relative_posix: true
    no_absolute_paths: true
    no_path_traversal: true
    lowercase_kebab_case_id: true
```

Rules:

- destination path is `.ariadne/features/{feature_workspace_id}.yml`
- this PR defines destination only; it does not create destination files
- future writer must enforce repo-relative POSIX paths
- feature id must not contain path separators

Required `required_evidence` contract:

```yaml
required_evidence:
  - source_pr
  - feature_workspace_id
  - run_record_links
  - validation_summary
  - review_summary
  - final_decisions
  - open_questions
  - handoff
```

Required `archival_action` contract:

```yaml
archival_action:
  actor: "context-steward"
  writes:
    - ".ariadne/features/{feature_workspace_id}.yml"
  reads:
    - ".project-memory/workspace-feature-record.schema.yml"
    - ".project-memory/run-record.schema.yml"
    - "docs/adr/0001-ariadne-namespace.md"
  mutates_project_memory: false
  mutates_runner_code: false
  mutates_contract_schemas: false
```

Rules:

- Context Steward may write only the final feature record path in future workflow
- Context Steward must not modify schemas while archiving
- Context Steward must not modify runner code
- Context Steward must not create run records
- Context Steward archival is not canonical code mutation authorization

Required `postconditions` contract:

```yaml
postconditions:
  feature_record_status: "archived"
  archival_status: "archived"
  destination_exists: true
  run_id_to_feature_workspace_id_preserved: true
```

Required `forbidden_actions` contract:

```text
- modify .project-memory/workspace-feature-record.schema.yml
- modify .project-memory/run-record.schema.yml
- modify .project-memory/apply-gate.schema.yml
- create .project-memory/pr/*/run_record.yml
- write outside .ariadne/features/{feature_workspace_id}.yml
- write feature records before merge
- write feature records without run_id links
- invent validation evidence
- use Docker
- use git mutation commands
- modify runner code
- create Python dataclasses
```

Schema must include:

- commented minimal valid example
- invalid cases list

Invalid cases must include:

- archival before merge
- missing feature_workspace_id
- missing run_record_links
- missing run_id
- destination outside `.ariadne/features/{feature_workspace_id}.yml`
- destination with absolute path
- destination with `../`
- Context Steward modifying schemas
- Context Steward writing run_record.yml
- Context Steward inventing validation evidence
- `.ariadne/` ADR missing

## Required contract ids

Update `.project-memory/project_contract.yml` with contract ids equivalent to:

```text
context-steward.archival.required
context-steward.archival.schema-path
context-steward.archival.after-merge-only
context-steward.archival.destination-path
context-steward.archival.requires-workspace-feature-record
context-steward.archival.requires-run-record-links
context-steward.archival.run-id-to-feature-workspace-id-preserved
context-steward.archival.requires-ariadne-namespace-contract
context-steward.archival.no-evidence-invention
context-steward.archival.no-schema-mutation
context-steward.archival.no-run-record-creation
context-steward.archival.no-runner-code
context-steward.archival.no-actual-records-this-pr
```

Contract semantics:

- schema path is `.project-memory/context-steward-archival.schema.yml`
- archival is after-merge only
- destination path is `.ariadne/features/{feature_workspace_id}.yml`
- Workspace Feature Record is required as source state
- run record links are required
- `run_id → feature_workspace_id` must be preserved
- `.ariadne/` namespace ADR is required
- Context Steward must not invent missing evidence
- Context Steward must not mutate schemas during archival
- Context Steward must not create run records
- Context Steward must not modify runner code
- PR 0026 creates no actual archived records

## Required anchors

Update `.project-memory/anchors.yml` with anchors equivalent to:

```text
context-steward.archival.required
context-steward.archival.schema-path
context-steward.archival.after-merge-only
context-steward.archival.destination-path
context-steward.archival.requires-run-record-links
context-steward.archival.no-evidence-invention
context-steward.archival.no-actual-records-this-pr
```

Preserve existing anchor structure and add these anchors consistently.

## Required contracts bundle update

Update `.project-memory/context-bundles/contracts.yml`:

- include `.project-memory/context-steward-archival.schema.yml` in `read_first` or equivalent
- include `.project-memory/workspace-feature-record.schema.yml`
- include `docs/adr/0001-ariadne-namespace.md`
- include context-steward archival anchors
- add note that Context Steward archival is contract-only in PR 0026
- add note that future destination is `.ariadne/features/{feature_workspace_id}.yml`
- add note that PR 0026 creates no actual `.ariadne/**` files
- bump bundle version according to existing convention

## Required memory index update

Update `.project-memory/memory_index.yml`:

- bump version by one minor step: `"0.8"` → `"0.9"`
- add or update a `context-steward` label
- ensure contracts label references `.project-memory/context-steward-archival.schema.yml`
- ensure ariadne-namespace and workspace-feature labels can discover the archival schema
- include schema in relevant additional files

## Relationship to existing contracts

```text
PR 0024 defined the Workspace Feature Record schema and contract.
PR 0025 defined the .ariadne/ namespace and future physical feature storage.
PR 0026 defines the Context Steward archival workflow contract.
Workspace Feature Records remain governed by .project-memory/workspace-feature-record.schema.yml.
Future archived feature records may live at .ariadne/features/{feature_workspace_id}.yml.
Context Steward archival must preserve run_id → feature_workspace_id traceability.
Run Record captures execution evidence.
Workspace Feature Record captures durable feature/workspace state.
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
grep -R -n "context-steward.archival\|context-steward-archival.schema.yml\|.ariadne/features/{feature_workspace_id}.yml\|context-steward" .project-memory docs/adr
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- import regression grep has no matches
- context-steward grep shows schema, contract ids, anchors, contracts bundle, and memory index references

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
- implementation modifies services/packages/apps/.github/docker/docs
- implementation adds non-stdlib dependencies
- implementation weakens Run Record, Workspace Feature Record, Ariadne namespace, Apply Gate, Artifact Store, WorktreeManager, MockCoder, or patch safety invariants

## Machine-checkable acceptance criteria

```text
context_steward_archival_schema: .project-memory/context-steward-archival.schema.yml
project_contract_ids: required
anchors: required
contracts_bundle_reference: required
memory_index_bump: required
memory_index_expected_version_if_current_0_8: "0.9"
trigger_after_merge_only: required
destination_path_template: .ariadne/features/{feature_workspace_id}.yml
workspace_feature_record_required: required
run_record_links_required: required
run_id_to_feature_workspace_id_preserved: required
ariadne_namespace_contract_required: required
context_steward_no_evidence_invention: required
context_steward_no_schema_mutation: required
context_steward_no_run_record_creation: required
context_steward_no_runner_code: required
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
.project-memory/context-steward-archival.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0026-context-steward-archival-workflow-contract/PLAN.md
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
