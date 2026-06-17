# PR 0019: Run Record Schema Hardening

## Goal

```text
Harden the existing `.project-memory/run-record.schema.yml` so ApplyRequest references to `run_record_path` and `run_id` are strict, unique, and machine-checkable.
```

## Context snapshot verified at plan time

```yaml
context_snapshot:
  base_sha: "7e527bef2c57a68605a75831e081ef30511bc310"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.4"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "7e527bef2c57a68605a75831e081ef30511bc310"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

Historical PLAN base_sha deltas (informational — do not stop):

- PR 0017 base_sha: `31951d15679025a7fa7182e0ad794457b070a172` (current HEAD `7e527bef...` — delta, no action required)
- PR 0018 base_sha: `babf76b6303ab327be2af7566daf7e13e042903f` (current HEAD `7e527bef...` — delta, no action required)

Previous PLAN snapshots are historical evidence. Base SHA source of truth for this PR is this file only.

## Base SHA source-of-truth policy

```text
After PLAN.md is created, PLAN.md is the source of truth for `base_sha` and `index_version`.

Review and implementation prompts must:
- read `base_sha` from `.project-memory/pr/0019-run-record-schema-hardening/PLAN.md`
- read `index_version` from `.project-memory/pr/0019-run-record-schema-hardening/PLAN.md`
- run `git rev-parse --verify HEAD` as read-only introspection if available
- compare `current_head` to PLAN.md `base_sha`
- stop with `STALE SNAPSHOT` if they differ
```

## Non-goals

```text
- no new run record implementation
- no actual `.project-memory/pr/*/run_record.yml` files
- no backfilling previous PR run records
- no ApplyRequest schema changes
- no `.project-memory/apply-gate.schema.yml` changes
- no `.ariadne/**` namespace introduction
- no runner/service code changes
- no package/app/frontend changes
- no Dockerfile/workflow/GHCR changes
- no agent config changes
- no automatic memory writes
- no git mutation commands by agents
- no Docker commands by agents
- no secrets or credentials
```

## Future implementation allowed_write_paths

The implementation PR may modify/create only:

```text
.project-memory/run-record.schema.yml
.project-memory/context-bundles/contracts.yml
.project-memory/project_contract.yml
.project-memory/memory_index.yml
.project-memory/pr/0019-run-record-schema-hardening/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify:

```text
.project-memory/apply-gate.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
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
```

## Read-only context

Implementation and review may read:

```text
.project-memory/apply-gate.schema.yml
.project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md
.project-memory/pr/0018-apply-gate-contract/PLAN.md
```

## Required hardening

### Existing schema target

```text
`.project-memory/run-record.schema.yml` already exists from PR 0017.
PR 0019 must harden the existing file rather than replace it with an unrelated schema.
```

### run_record_reference semantics

The schema must define:

```yaml
run_record_reference:
  run_record_path: ".project-memory/pr/<PR-ID>/run_record.yml"
  run_id: "<string>"
  required: true
  uniqueness_scope: "within one run_record.yml"
  resolution_rule: "runs[] must contain exactly one item with matching run_id"
```

Rules:

```text
- `run_record_path` must be a repo-relative POSIX path.
- `run_record_path` must match `.project-memory/pr/<PR-ID>/run_record.yml`.
- `run_id` must be present and non-empty.
- `run_id` must be unique within `runs[]` of that file.
- `runs[]` must contain exactly one item matching `run_id`.
- ApplyRequest reference is invalid if `run_record_path` is missing or empty.
- ApplyRequest reference is invalid if `run_id` is missing or empty.
- ApplyRequest reference is invalid if `run_id` appears more than once in `runs[]`.
- ApplyRequest reference is invalid if `runs[]` is missing or empty.
- ApplyRequest reference is invalid if `run_id` is not found in `runs[]`.
```

### Top-level required fields

The schema must explicitly require:

```yaml
schema_version: "<string>"
runs:
  - "<ordered run item>"
```

### Per-run required fields

The schema must explicitly require:

```yaml
run_id: "<string>"
base_sha: "<sha>"
base_sha_source: "<source>"
index_version: "<version>"
index_version_source: "<source>"
current_head: "<sha>"
snapshot_verified: true | false | skipped
snapshot_verified_by: "git introspection | filesystem | not available"
validation_results:
  - command: "<string>"
    result: "passed | failed | skipped | waived"
    status: "passed | failed | skipped | waived"
decisions:
  - "<ordered decision>"
deviations:
  - "<ordered deviation>"
confirmations:
  no_docker_commands_run: true | false
  no_git_mutation_commands_run: true | false
context_used:
  labels:
    - "<label>"
  memory_files_read:
    - "<repo-relative POSIX path>"
  anchors_used:
    - "<anchor id>"
  files_inspected:
    - "<repo-relative POSIX path>"
  files_modified:
    - "<repo-relative POSIX path>"
  files_intentionally_ignored:
    - "<repo-relative POSIX path or glob>"
```

### Backward compatibility with PR 0017 field names

The current schema uses `decisions_made` and `deviations_from_plan` as field names.
This PR introduces canonical fields `decisions` and `deviations`.

Decision: use canonical fields `decisions` and `deviations` while preserving backward-compatible aliases `decisions_made` and `deviations_from_plan` in schema v0.1.

Implementation must:

- add canonical `decisions` as the canonical name
- add canonical `deviations` as the canonical name
- document `decisions_made` as a backward-compatible alias for `decisions`
- document `deviations_from_plan` as a backward-compatible alias for `deviations`
- both names are valid in schema v0.1
- future schema versions may drop aliases

### Ordering rules

```text
- `runs[]` ordered newest-last
```

Rationale:

```text
Append-only records are easier to review in git diffs when newest entries are appended at the end.
```

Also require:

```text
- decisions are ordered
- deviations are ordered
- append-only run entries are preferred
- rewriting existing run entries is forbidden except explicit human correction in a reviewed PR
```

### Path rules

Require:

```text
All paths in `run_record.yml` must be repo-relative POSIX paths.
Absolute paths are forbidden.
Backslash Windows-style paths are forbidden.
Paths escaping the repository root are forbidden.
```

### validation_results

Require:

```yaml
validation_results:
  - command: "<string>"
    result: "passed | failed | skipped | waived"
    status: "passed | failed | skipped | waived"
    evidence: "<short sanitized bounded evidence>"
```

Rules:

```text
- each validation entry must have `command`
- each validation entry must have `result`
- each validation entry must have `status`
- allowed status values: passed | failed | skipped | waived
- waived requires:
  - human_waiver: true
  - waiver_reason: "<string>"
  - waived_by: "<human identifier>"
- evidence must be sanitized
- evidence must be bounded
- evidence max 2000 characters
- evidence must not contain secrets, credentials, tokens, full environment dumps, or full logs
```

### schema_version

```text
schema_version remains "0.1" if changes are additive and backward-compatible.
schema_version must bump to "0.2" if required fields are renamed, removed, or existing valid records would become invalid.
PR 0019 should prefer additive hardening and keep schema_version "0.1" unless the current schema requires a breaking correction.
```

### Minimal valid example

PLAN must require `.project-memory/run-record.schema.yml` to include a commented minimal valid example:

```yaml
# Minimal valid run_record.yml example:
schema_version: "0.1"
pr_id: "0019"
pr_slug: "run-record-schema-hardening"
runs:
  - run_id: "0019-plan-coder-001"
    base_sha: "<sha>"
    base_sha_source: ".project-memory/pr/0019-run-record-schema-hardening/PLAN.md"
    index_version: "0.4"
    index_version_source: ".project-memory/pr/0019-run-record-schema-hardening/PLAN.md"
    current_head: "<sha>"
    snapshot_verified: true
    snapshot_verified_by: "git introspection"
    validation_results:
      - command: "python -m pytest -q"
        result: "passed"
        status: "passed"
        evidence: "159 passed"
    decisions:
      - "None — followed PLAN.md exactly"
    deviations:
      - "None"
    confirmations:
      no_docker_commands_run: true
      no_git_mutation_commands_run: true
    context_used:
      labels:
        - contracts
      memory_files_read:
        - ".project-memory/memory_index.yml"
      anchors_used: []
      files_inspected:
        - ".project-memory/run-record.schema.yml"
      files_modified:
        - ".project-memory/run-record.schema.yml"
      files_intentionally_ignored: []
```

### Invalid reference cases

The schema must document at minimum:

```text
- missing run_record_path
- empty run_record_path
- malformed run_record_path
- missing run_id
- empty run_id
- duplicate run_id
- empty runs[]
- missing runs[]
- run_id not found in runs[]
- run_record_path points outside `.project-memory/pr/<PR-ID>/run_record.yml`
```

## project_contract updates

Future implementation must add or strengthen contract ids:

```text
agents.run-record.path-required
agents.run-record.path-pattern
agents.run-record.run-id-required
agents.run-record.run-id-unique
agents.run-record.runs-required
agents.run-record.reference-resolution
agents.run-record.invalid-reference-cases
agents.run-record.repo-relative-posix-paths
agents.run-record.validation-waiver-fields
agents.run-record.evidence-bounded
agents.run-record.evidence-sanitized
```

Preserve all existing contract ids unchanged, especially:

```text
repo.canonical-write.single-gate
agents.no-git-mutation
agents.no-secrets
agents.context-snapshot.*
agents.run-record.*
agents.apply-gate.*
```

## contracts_bundle updates

Future implementation must:

```text
- add `.project-memory/run-record.schema.yml` to read_first if not present
- add new agents.run-record.* anchor ids to anchors list
- bump contracts bundle version
- reference run-record hardening as Apply Gate dependency
```

## memory_index updates

Future implementation must:

```text
- bump memory index version
- preserve existing labels
- ensure run-record label exists
- ensure run-record label references `.project-memory/run-record.schema.yml`
- ensure contracts label references `.project-memory/run-record.schema.yml`
```

Target version:

```text
memory_index_bump: "0.5"
```

## Stop conditions

```text
Stop if:
- `.project-memory/run-record.schema.yml` is missing
- `.project-memory/apply-gate.schema.yml` is missing
- PR 0017 PLAN.md is missing
- PR 0018 PLAN.md is missing
- implementation attempts to modify `.project-memory/apply-gate.schema.yml`
- implementation attempts to create or modify `.project-memory/pr/*/run_record.yml`
- implementation attempts to modify `.ariadne/**`
- implementation attempts to modify services/apps/packages/agents/docs/.github/docker/Dockerfile/prompts
```

Historical PLAN base_sha deltas:

```text
If current HEAD differs from base_sha values in PR 0017 or PR 0018 PLAN.md, note this as historical delta only. Do not stop. Previous PLAN snapshots are historical evidence.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Do not run Docker commands.
Do not run git mutation commands.

## Post-change checks

Implementation must run:

```bash
grep -n "run_record_path\|run_id\|uniqueness\|invalid\|reference-resolution\|newest-last\|validation_waiver\|repo-relative POSIX" .project-memory/run-record.schema.yml
grep -n "agents.run-record" .project-memory/project_contract.yml
grep -n "run-record.schema.yml" .project-memory/memory_index.yml
git status --short
```

## Expected changed files

```text
.project-memory/run-record.schema.yml
.project-memory/project_contract.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0019-run-record-schema-hardening/PLAN.md
```

## Decisions required

```text
runs_order: newest-last
schema_version_policy: keep 0.1 for additive hardening; bump to 0.2 only for breaking changes
canonical_decision_fields: use canonical fields `decisions` and `deviations`, while preserving backward-compatible aliases `decisions_made` and `deviations_from_plan` in schema v0.1
memory_index_target_version: "0.5"
```

## Machine-checkable acceptance criteria

```text
run_record_schema_exists: required
run_record_reference: required
run_record_path_required: required
run_record_path_pattern: .project-memory/pr/<PR-ID>/run_record.yml
run_id_required: required
run_id_unique_within_runs: required
runs_required: required
runs_order: newest-last
reference_resolution_exactly_one_match: required
invalid_reference_cases: required
repo_relative_posix_paths: required
validation_result_status_enum: passed | failed | skipped | waived
validation_waiver_fields: required
validation_evidence_max_chars: 2000
minimal_valid_example: required
apply_gate_schema_changes: forbidden
actual_run_record_files: forbidden
ariadne_namespace_changes: forbidden
agent_config_changes: forbidden
runner_code_changes: forbidden
service_code_changes: forbidden
docker_required: false
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
memory_index_bump: "0.5"
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

## Implementation note

PR 0019 implemented:
- Hardened `.project-memory/run-record.schema.yml` with:
  - `run_record_reference` section defining run_record_path, run_id, uniqueness scope, and resolution rule
  - 10 invalid reference cases documented
  - `runs[]` ordering: newest-last
  - Canonical fields `decisions` and `deviations` with backward-compatible aliases `decisions_made` and `deviations_from_plan`
  - Enhanced validation_results with `status` enum (passed | failed | skipped | waived) and waiver fields
  - Explicit path rules (repo-relative POSIX only, absolute and Windows paths forbidden)
  - Minimal valid example at end of file
  - schema_version preserved as "0.1" (additive backward-compatible hardening)
- Added 8 new `agents.run-record.*` contract entries to `.project-memory/project_contract.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.4 with run-record.schema.yml in read_first, new anchors, and hardened reference note
- Bumped `.project-memory/memory_index.yml` to version 0.5

All changes are memory/contract only. No agent configs, runner code, services, packages, Dockerfiles, workflows, apply-gate schema, or agent-config context bundle were modified.
