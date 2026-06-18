## Implementation note

PR 0024 implemented:
- Created `.project-memory/workspace-feature-record.schema.yml` with all required fields, enums, run_record_links contract, context_steward contract, scope/artifacts/decisions/handoff fields, invalid cases list, and minimal valid example
- Added 13 `workspace-feature.record.*` contract entries to `.project-memory/project_contract.yml`
- Added 6 workspace-feature anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.5 with workspace-feature-record schema in read_first, new anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.7 with new `workspace-feature` label and schema references

No .ariadne/** namespace, no feature instance files, no runner code, no run-record/apply-gate schema modifications, and no Python dataclasses were introduced.# PR 0024: Workspace Feature Record Contract

## Goal

Add a project-memory Workspace Feature Record schema and contract anchors so future workspaces/features can be recorded, linked to run records, and archived by Context Steward after merge.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "8a47ecbf3dbbf3f99f096d475b86591f4b8a11d3"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.6"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "8a47ecbf3dbbf3f99f096d475b86591f4b8a11d3"
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
- no .ariadne/** namespace introduction
- no actual feature record instances
- no .ariadne/features/{id}.yml files
- no project-memory feature instance files
- no runner Python dataclass
- no services/runner implementation
- no API server
- no frontend
- no automatic team runner
- no ApplyPatch changes
- no artifact store changes
- no WorktreeManager changes
- no Docker commands
- no git mutation commands by agents
- no workflow/GHCR/Dockerfile changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
.project-memory/workspace-feature-record.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0024-workspace-feature-record-contract/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify:

```text
.ariadne/**
agents/**
services/**
packages/**
apps/**
docs/**
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
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
.project-memory/features/**
.project-memory/pr/*/feature*.yml
```

## Required schema

Create:

```text
.project-memory/workspace-feature-record.schema.yml
```

Schema must define a Workspace Feature Record as a contract artifact, not a runtime implementation.

Required top-level fields:

```text
schema_version
feature_workspace_id
title
status
created_at
created_by
source_pr
run_record_links
context_steward
scope
artifacts
decisions
open_questions
handoff
```

Required `feature_workspace_id` rules:

```text
- required
- stable string id
- repo-unique
- lowercase kebab-case recommended
- must not contain path separators
- must not imply current physical storage under .ariadne/**
```

Required `status` enum:

```text
planned
active
merged
archived
superseded
abandoned
```

Required `run_record_links` contract:

```text
run_record_links:
  - run_record_path: ".project-memory/pr/<PR-ID>/run_record.yml"
    run_id: "<run_id>"
    feature_workspace_id: "<feature_workspace_id>"
```

Rules:

- each link must include `run_record_path`
- each link must include `run_id`
- each link must include `feature_workspace_id`
- `run_id → feature_workspace_id` relationship must be explicit
- `run_record_path` must follow `.project-memory/pr/<PR-ID>/run_record.yml`
- this PR must not create actual `run_record.yml` files
- this PR must not modify `.project-memory/run-record.schema.yml`

Required `context_steward` contract:

```text
context_steward:
  archival_required_after_merge: true
  archival_status: "pending | archived | not_required"
  archival_note: "<short text>"
```

Rules:

- Context Steward archival after merge must be explicitly represented.
- A merged feature should not silently disappear into chat history.
- Archival means preserving final feature state as project memory.
- This PR defines the contract only; it does not implement an archival runner.

Required `scope` fields:

```text
scope:
  summary: "<short text>"
  allowed_paths: []
  forbidden_paths: []
  changed_paths: []
```

Required `artifacts` fields:

```text
artifacts:
  normalized_patch_sha256: "<optional>"
  raw_diff_sha256: "<optional>"
  apply_request_sha256: "<optional>"
  notes: []
```

Rules:

- artifact sha256 references are optional in this PR
- artifact references do not authorize canonical mutation
- Artifact Store remains evidence storage only

Required `decisions` and `handoff`:

```text
decisions:
  - decision: "<text>"
    reason: "<text>"

handoff:
  next_action: "<text>"
  owner: "<human | agent | context-steward>"
  notes: []
```

Required examples:

- include a commented minimal valid example
- include an invalid example or invalid cases list

Invalid cases must include:

- missing `feature_workspace_id`
- duplicate `feature_workspace_id`
- invalid status
- missing run_id in run_record_links
- missing feature_workspace_id in run_record_links
- run_record_path outside `.project-memory/pr/<PR-ID>/run_record.yml`
- archival_required_after_merge missing
- artifact sha malformed if present
- paths using absolute paths or backslashes
- references to `.ariadne/**` as current storage

## Required contract ids

Update `.project-memory/project_contract.yml` with contract ids equivalent to:

```text
workspace-feature.record.required
workspace-feature.record.schema-path
workspace-feature.record.id-required
workspace-feature.record.id-unique
workspace-feature.record.status-enum
workspace-feature.record.run-record-link-required
workspace-feature.record.run-id-to-feature-workspace-id
workspace-feature.record.context-steward-archival-required
workspace-feature.record.no-ariadne-storage-yet
workspace-feature.record.no-runtime-dataclass-yet
workspace-feature.record.artifact-references-evidence-only
workspace-feature.record.repo-relative-posix-paths
workspace-feature.record.no-feature-instance-files-this-pr
```

Contract semantics:

- schema path is `.project-memory/workspace-feature-record.schema.yml`
- actual feature instances are future work
- `.ariadne/**` remains forbidden until separately introduced by contract/ADR
- runner dataclass/runtime implementation is future work
- run record links must explicitly connect `run_id` to `feature_workspace_id`
- Context Steward archival after merge is required by contract

## Required anchors

Update `.project-memory/anchors.yml` with anchors equivalent to:

```text
workspace-feature.record.required
workspace-feature.record.schema-path
workspace-feature.record.run-id-to-feature-workspace-id
workspace-feature.record.context-steward-archival-required
workspace-feature.record.no-ariadne-storage-yet
workspace-feature.record.artifact-references-evidence-only
```

Preserve existing anchor structure and add these anchors consistently.

## Required contracts bundle update

Update `.project-memory/context-bundles/contracts.yml`:

- include `.project-memory/workspace-feature-record.schema.yml` in `read_first` or equivalent
- include workspace-feature anchors in `anchors` or equivalent
- add note that Workspace Feature Record is contract-only in PR 0024
- add note that `.ariadne/features/{id}.yml` is future work and not introduced here
- bump bundle version according to existing convention

## Required memory index update

Update `.project-memory/memory_index.yml`:

- bump version by one minor step: `"0.6"` → `"0.7"`
- add a `workspace-feature` label
- include `.project-memory/workspace-feature-record.schema.yml` in relevant additional_files
- ensure contracts label references the new schema

## Relationship to existing contracts

```text
Workspace Feature Record complements Run Record but does not replace it.
Run Record captures execution evidence.
Workspace Feature Record captures durable feature/workspace state.
run_id → feature_workspace_id is required for traceability.
Context Steward archival after merge is required for durable project memory.
Artifact Store references are evidence only and do not authorize writes.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
This PR does not introduce .ariadne/** or runtime runner dataclasses.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
```

Expected grep result:

- no matches

Additional grep checks:

```bash
grep -R -n "workspace-feature-record.schema.yml\|workspace-feature.record\|feature_workspace_id\|context_steward\|run_id" .project-memory
```

Expected:

- schema, contract ids, anchors, contracts bundle, and memory index references are present

## Stop conditions

Stop if:

- implementation introduces `.ariadne/**`
- implementation creates actual feature instance files
- implementation creates actual run_record.yml files
- implementation modifies `.project-memory/run-record.schema.yml`
- implementation modifies `.project-memory/apply-gate.schema.yml`
- implementation modifies runner code
- implementation adds Python dataclasses
- implementation modifies services/packages/apps/docs/.github/docker
- implementation adds non-stdlib dependencies
- implementation weakens Run Record, Apply Gate, Artifact Store, WorktreeManager, or MockCoder safety invariants

## Machine-checkable acceptance criteria

```text
workspace_feature_schema: .project-memory/workspace-feature-record.schema.yml
project_contract_ids: required
anchors: required
contracts_bundle_reference: required
memory_index_bump: required
memory_index_expected_version_if_current_0_6: "0.7"
feature_workspace_id: required
feature_workspace_id_unique: required
status_enum: planned | active | merged | archived | superseded | abandoned
run_record_links: required
run_id_to_feature_workspace_id: required
context_steward_archival_after_merge: required
artifact_references_evidence_only: required
repo_relative_posix_paths: required
actual_feature_instances: forbidden
ariadne_namespace_changes: forbidden
runner_dataclass: forbidden
runner_code_changes: forbidden
apply_gate_schema_changes: forbidden
run_record_schema_changes: forbidden
actual_run_record_files: forbidden
non_stdlib_dependencies: forbidden
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
.project-memory/workspace-feature-record.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0024-workspace-feature-record-contract/PLAN.md
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
