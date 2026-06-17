# PR 0017: Feature Workspace Run Record Contract

## Context snapshot verified at plan time

```text
Context snapshot verified at plan time:
- base_sha: 31951d15679025a7fa7182e0ad794457b070a172
- base_sha_source: ".project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md"
- index_version: "0.2"
- index_version_source: ".project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md"
- current_head: 31951d15679025a7fa7182e0ad794457b070a172
- stale_snapshot: false
- snapshot_verified: true
- snapshot_verified_by: git introspection
```

## Goal

Define a machine-readable run record schema for storing controlled-agent final outputs as future Feature Workspace Memory.

This PR standardizes where PR/run evidence should live, what fields are required, and how multiple agent runs per PR aggregate into a single per-PR record, without automating writes yet.

## Non-goals

- no runner code changes
- no service code changes
- no Dockerfile changes
- no workflow changes
- no GHCR changes
- no API server
- no frontend
- no task execution engine
- no real agent execution
- no LLM runtime integration
- no automatic memory writes
- no automatic team runner
- no canonical repo writes outside normal human-controlled git workflow
- no git mutation commands by agents
- no Docker commands by agents
- no secrets or credentials
- no change to patch/diff/worktree/normalize behavior

## Future implementation scope

Future implementation may modify/create only:

```text
.project-memory/run-record.schema.yml
.project-memory/context-bundles/contracts.yml
.project-memory/project_contract.yml
.project-memory/memory_index.yml
.project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md
```

Optional docs may be added only if PLAN justifies it, but default scope should remain memory/contract only.

This PR must not modify `.project-memory/context-bundles/agent-config.yml`.
Agent-config behavior was standardized in PR 0016.
PR 0017 defines the run-record schema/contract only.

## Required run record location

Define canonical per-PR run record path pattern:

```text
.project-memory/pr/<PR-ID>/run_record.yml
```

Examples:

```text
.project-memory/pr/0017-feature-workspace-run-record-contract/run_record.yml
.project-memory/pr/0015-runner-raw-diff-normalization-contract/run_record.yml
```

Clarify:

- this PR defines schema and contract only
- this PR does not require backfilling records for previous PRs
- this PR does not automate record creation
- human/agent final output can be manually copied into this structure until automation exists

## Base SHA source-of-truth policy

PLAN.md is the source of truth for `base_sha` and `index_version` after the PLAN is created.

Review and implementation prompts MUST NOT duplicate a literal `base_sha` as an independent expected value when reviewing or implementing an already-created PR plan.

Review and implementation prompts must:
- read `base_sha` from `.project-memory/pr/<PR-ID>/PLAN.md`
- read `index_version` from `.project-memory/pr/<PR-ID>/PLAN.md`
- run `git rev-parse --verify HEAD` as read-only introspection if available
- compare `current_head` to the PLAN.md `base_sha`
- stop with `STALE SNAPSHOT` if they differ

Prompt-level fields should use:
- `base_sha_source: .project-memory/pr/<PR-ID>/PLAN.md`
- `index_version_source: .project-memory/pr/<PR-ID>/PLAN.md`

Run records must store:
- `base_sha`: the value read from PLAN.md
- `base_sha_source`: `.project-memory/pr/<PR-ID>/PLAN.md`
- `index_version`: the value read from PLAN.md
- `index_version_source`: `.project-memory/pr/<PR-ID>/PLAN.md`
- `current_head`: the current HEAD observed during the run

## run_record.yml is a per-PR aggregate

`run_record.yml` is a per-PR aggregate containing an ordered `runs:` list.

Run order is authoritative and must be preserved.
Manual or future automated record creation should append new run entries rather than rewriting existing run entries, except for explicit human correction in a reviewed PR.

`created_at` is optional in schema v0.1.
If present, it must be ISO8601 UTC.
Absence of `created_at` must not make a run record invalid in schema v0.1.

Each agent/reviewer execution conceptually appends one run item. This PR does not automate appending. Ordering must be preserved.

Example structure:

```yaml
schema_version: "0.1"
pr_id: "0017"
pr_slug: "feature-workspace-run-record-contract"
runs:
  - run_id: "0017-plan-coder-001"
    agent: "coder"
    mode: "PLAN-only"
    created_at: "2026-06-17T00:00:00Z"
    base_sha: "31951d15679025a7fa7182e0ad794457b070a172"
    base_sha_source: ".project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md"
    index_version: "0.2"
    current_head: "31951d15679025a7fa7182e0ad794457b070a172"
    stale_snapshot: false
    snapshot_verified: true
    snapshot_verified_by: "git introspection"
    author_type: "agent"
    files_changed:
      - ".project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md"
    validation_results:
      - command: "python -m pytest -q"
        result: "passed"
        evidence: "<short sanitized evidence>"
    decisions_made:
      - decision: "None — followed PLAN.md exactly"
        reason: ""
    deviations_from_plan:
      - deviation: "None"
        reason: ""
        impact: ""
    confirmations:
      no_docker_commands_run: true
      no_git_mutation_commands_run: true
    context_used:
      labels:
        - architecture
        - contracts
        - agent-config
        - memory
      memory_files_read:
        - ".project-memory/memory_index.yml"
        - ".project-memory/project_contract.yml"
        - ".project-memory/anchors.yml"
      anchors_used:
        - "agents.context-snapshot.base-sha-guard"
      files_inspected:
        - ".project-memory/memory_index.yml"
        - ".project-memory/project_contract.yml"
        - ".project-memory/context-bundles/architecture.yml"
        - ".project-memory/context-bundles/contracts.yml"
        - ".project-memory/context-bundles/agent-config.yml"
        - ".project-memory/pr/0016-agent-context-snapshot-output-contract/PLAN.md"
        - "agents/architect.yml"
        - "agents/coder.yml"
        - "agents/plan-review.yml"
        - "agents/precommit-review.yml"
      files_modified:
        - ".project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md"
      files_intentionally_ignored:
        - "services/**"
        - "packages/**"
        - "apps/**"
        - ".github/**"
        - "Dockerfile*"
        - "docker/**"
```

## Required schema fields per run item

Each run item in the `runs:` list must contain:

`run_id` is required.
`run_id` must be unique within one PR `run_record.yml`.
Recommended format: `<PR-ID>-<phase>-<agent>-<sequence>`, for example `0017-plan-coder-001` or `0017-review-plan-review-001`.

`base_sha_source` is required.
`base_sha_source` must reference the PLAN.md file that was the source of `base_sha`.
Expected value: `.project-memory/pr/<PR-ID>/PLAN.md`.

`index_version_source` is required.
`index_version_source` must reference the PLAN.md file that was the source of `index_version`.
Expected value: `.project-memory/pr/<PR-ID>/PLAN.md`.

```yaml
schema_version: "0.1"
pr_id: "<string>"
pr_slug: "<string>"
run_id: "<string>"
agent: "coder | plan-review | precommit-review | architect | other"
mode: "PLAN-only | scoped implementation | read-only review | other"
author_type: "agent | human"
base_sha: "<sha>"
base_sha_source: ".project-memory/pr/<PR-ID>/PLAN.md"
index_version: "<version>"
current_head: "<sha>"
stale_snapshot: <boolean>
snapshot_verified: <boolean>
snapshot_verified_by: "<string>"
created_at: "<optional ISO8601 UTC>"  # optional in schema v0.1
files_changed:
  - "<repo-relative POSIX path>"
validation_results:
  - command: "<string>"
    result: "<enum>"
    evidence: "<short sanitized bounded evidence>"
decisions_made:
  - decision: "<string>"
    reason: "<string>"
deviations_from_plan:
  - deviation: "<string>"
    reason: "<string>"
    impact: "<string>"
confirmations:
  no_docker_commands_run: <boolean>
  no_git_mutation_commands_run: <boolean>
context_used:
  labels:
    - "<string>"
  memory_files_read:
    - "<path>"
  anchors_used:
    - "<string>"
  files_inspected:
    - "<repo-relative POSIX path>"
  files_modified:
    - "<repo-relative POSIX path>"
  files_intentionally_ignored:
    - "<repo-relative POSIX path or glob>"
```

All file path fields must use repo-relative POSIX paths (e.g. `services/runner/src/...`, not `/absolute/path` or `./relative`).

Validation evidence must be sanitized and bounded.
Schema v0.1 limit:
- `validation_results[].evidence` must be at most 2000 characters
- evidence must not contain secrets, credentials, tokens, full environment dumps, or full logs
- prefer short evidence such as `72 passed`, `compileall clean`, or `doctor passed`

`created_at` is optional in schema v0.1. If present, it must be ISO8601 UTC. Absence of `created_at` must not make a run record invalid in schema v0.1.

## Required enum values

Define machine-readable enums:

```yaml
snapshot_verified:
  - true
  - false
  - skipped

snapshot_verified_by:
  - git introspection
  - filesystem
  - not available

validation_result:
  - passed
  - failed
  - skipped
  - not run

stale_snapshot:
  - true
  - false
  - unknown
```

Clarify:

- if `git rev-parse --verify HEAD` ran and current_head == base_sha:
  - `snapshot_verified: true`
  - `snapshot_verified_by: git introspection`
  - `stale_snapshot: false`
- if `git rev-parse --verify HEAD` ran and current_head != base_sha:
  - `snapshot_verified: false`
  - `snapshot_verified_by: git introspection`
  - `stale_snapshot: true`
- if verification could not run:
  - `snapshot_verified: skipped`
  - `snapshot_verified_by: not available`
  - `stale_snapshot: unknown`

## Required behavior

Implementation must:

- add `.project-memory/run-record.schema.yml`
- document required fields and enum values
- define `run_record.yml` as per-PR aggregate with ordered `runs:` list
- require `run_id` (unique within PR)
- require `base_sha_source` referencing PLAN.md
- require repo-relative POSIX paths for all file path fields
- require sanitized and bounded validation evidence (max 2000 chars)
- require decisions/deviations to preserve order
- require `author_type` (`agent | human`) for each run item
- update `.project-memory/project_contract.yml` with a run-record contract
- update contracts context bundle to include the new run-record schema/contract

  Note: This PR must not modify `.project-memory/context-bundles/agent-config.yml`.
  Agent-config behavior was standardized in PR 0016.
  PR 0017 defines the run-record schema/contract only.

- bump `.project-memory/memory_index.yml` version from `"0.2"` to `"0.3"` if schema/contract metadata changes
- keep all changes memory/contract only
- not backfill previous PR run records
- not automate memory writes

## Safety invariants

- run records are evidence, not authority to mutate repo
- run records do not grant patch application rights
- run records must not contain secrets
- run records must contain sanitized validation evidence only
- validation evidence must be bounded; do not paste full logs
- run records must use repo-relative POSIX paths
- run record creation remains human-controlled/manual until automation is explicitly planned
- agents still cannot run git mutation commands
- agents still cannot run Docker commands unless explicitly human-approved in separate reviewed plan

## Machine-readable scope

```text
allowed_write_paths:
- .project-memory/run-record.schema.yml
- .project-memory/context-bundles/contracts.yml
- .project-memory/project_contract.yml
- .project-memory/memory_index.yml
- .project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md

forbidden_files:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/**
- docs/**
- packages/**
- apps/**
- services/**
- agents/**
- prompts/**
- pyproject.toml
- package.json
- Makefile
- docker-compose.yml
- .env
- .env.*
- .project-memory/context-bundles/agent-config.yml
- .project-memory/** except:
  - .project-memory/run-record.schema.yml
  - .project-memory/context-bundles/contracts.yml
  - .project-memory/project_contract.yml
  - .project-memory/memory_index.yml
  - .project-memory/pr/0017-feature-workspace-run-record-contract/PLAN.md
```

Note: `.project-memory/context-bundles/agent-config.yml` is explicitly forbidden — PR 0017 must not modify it.

## Tests / checks

No code tests are required beyond repository validation, but implementation must include grep-style checks proving:

- `run-record.schema.yml`
- `schema_version`
- `pr_id`
- `run_id`
- `run_id_unique_within_pr`
- `base_sha`
- `base_sha_source`
- `index_version`
- `index_version_source`
- `current_head`
- `snapshot_verified`
- `snapshot_verified_by`
- `runs:`
- `author_type`
- `validation_results`
- `decisions_made`
- `deviations_from_plan`
- `context_used`
- `no_docker_commands_run`
- `no_git_mutation_commands_run`
- `agents.run-record.required`
- `feature workspace memory`
- `sanitized`
- `bounded`
- `repo-relative POSIX`
- `validation_evidence_max_chars: 2000`

## Machine-checkable acceptance criteria

```text
run_record_schema: .project-memory/run-record.schema.yml
run_record_path_pattern: .project-memory/pr/<PR-ID>/run_record.yml
run_record_kind: per_pr_aggregate
runs_list: required
run_order_preserved: required
append_only_runs: required
run_id: required
run_id_unique_within_pr: required
base_sha_source: required
index_version_source: required
schema_version: "0.1"
required_fields: defined
snapshot_verified_enum: required
snapshot_verified_by_enum: required
validation_result_enum: required
stale_snapshot_enum: required
author_type: required
created_at: optional
created_at_format: ISO8601 UTC if present
repo_relative_posix_paths: required
sanitized_validation_evidence: required
bounded_validation_evidence: required
validation_evidence_max_chars: 2000
decisions_order_preserved: required
deviations_order_preserved: required
memory_index_bump: "0.3"
automatic_memory_writes: forbidden
backfill_previous_prs: forbidden
agent_config_changes: forbidden
runner_code_changes: forbidden
service_code_changes: forbidden
docker_required: false
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
secrets_in_run_records: forbidden
```

## Validation

Implementation PR must pass:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Do not run Docker commands.
Do not run git mutation commands.

Read-only git introspection allowed:

```bash
git rev-parse --verify HEAD
git status --short
```

## Stop / merge gates

Do not merge if:

- run record schema is missing
- schema lacks required fields
- schema lacks per-PR aggregate `runs:` list
- schema lacks run_id
- schema lacks run_id uniqueness requirement
- schema lacks base_sha_source field
- schema lacks index_version_source field
- schema lacks author_type
- schema lacks snapshot_verified enum
- schema lacks snapshot_verified_by enum
- schema lacks validation result enum
- schema lacks stale_snapshot enum
- schema lacks repo-relative POSIX path rule
- schema lacks bounded/sanitized validation evidence rule
- schema lacks evidence max length guidance (2000 chars)
- schema lacks decisions_order_preserved or deviations_order_preserved
- run record path pattern is not defined
- project_contract is not updated
- contracts context bundle is not updated
- memory_index version is not bumped to `"0.3"`
- implementation backfills previous PRs
- implementation automates memory writes
- implementation modifies agents
- implementation modifies runner/service code
- implementation modifies Dockerfile/workflow/GHCR files
- implementation modifies agent-config context bundle
- implementation permits secrets in run records
- implementation weakens no-git-mutation policy
- implementation weakens no-Docker-agent policy
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is weakened
- `agents.no-git-mutation` is weakened
- `agents.no-secrets` is weakened

## Context receipt requirement

Every agent response for this PR must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- index_version:
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

PR 0017 implemented:
- Created `.project-memory/run-record.schema.yml` with required fields, enums, path rules, evidence rules, and safety invariants
- Added 15 `agents.run-record.*` contract entries to `.project-memory/project_contract.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.2 with run-record schema reference, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.3 with new `run-record` label and `additional_files` reference

All changes are memory/contract only. No agent configs, runner code, services, packages, Dockerfiles, or workflows were modified. Agent-config context bundle was not modified.
