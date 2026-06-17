# PR 0018: Apply Gate / Canonical Write Contract

## Context snapshot verified at plan time

```text
Context snapshot verified at plan time:
- base_sha: babf76b6303ab327be2af7566daf7e13e042903f
- base_sha_source: git rev-parse --verify HEAD at PLAN creation time
- index_version: "0.3"
- index_version_source: .project-memory/memory_index.yml
- current_head: babf76b6303ab327be2af7566daf7e13e042903f
- stale_snapshot: false
- snapshot_verified: true
- snapshot_verified_by: git introspection
```

## Base SHA source-of-truth policy

After PLAN.md is created, PLAN.md is the source of truth for `base_sha` and `index_version`.

Review and implementation prompts MUST NOT duplicate a literal `base_sha` as an independent expected value.

Review and implementation prompts must:
- read `base_sha` from `.project-memory/pr/0018-apply-gate-contract/PLAN.md`
- read `index_version` from `.project-memory/pr/0018-apply-gate-contract/PLAN.md`
- run `git rev-parse --verify HEAD` as read-only introspection if available
- compare `current_head` to the PLAN.md `base_sha`
- stop with `STALE SNAPSHOT` if they differ

## Goal

Define the Apply Gate contract.

The Apply Gate controls when a `NormalizedPatch` may be transformed into a canonical repository write.

The core invariant:

```text
sandbox/raw diff/normalized patch evidence does not grant repository mutation authority.
```

Only a human/HITL-approved Apply Gate may authorize canonical writes.

## Non-goals

- no runner apply implementation
- no patch application engine
- no `git apply`
- no canonical repository writes
- no service code changes
- no Dockerfile changes
- no workflow changes
- no GHCR changes
- no API server
- no frontend
- no automatic team runner
- no automatic memory writes
- no direct agent writes to canonical repo
- no backfilling previous PRs
- no secrets or credentials
- no Docker commands by agents
- no git mutation commands by agents
- no change to existing raw diff / normalization behavior

## Future implementation scope

Future implementation may modify/create only:

```text
.project-memory/apply-gate.schema.yml
.project-memory/context-bundles/contracts.yml
.project-memory/project_contract.yml
.project-memory/memory_index.yml
.project-memory/pr/0018-apply-gate-contract/PLAN.md
```

Do not modify:

```text
.project-memory/context-bundles/agent-config.yml
agents/**
services/**
packages/**
apps/**
docs/**
.github/**
docker/**
Dockerfile*
prompts/**
```

## Required ApplyRequest schema

Define a future schema file:

```text
.project-memory/apply-gate.schema.yml
```

The schema must define an `ApplyRequest` with required fields:

```yaml
schema_version: "0.1"
apply_request_id: "<string>"
apply_request_kind: "normalized_patch_apply_request"
normalized_patch_id: "<string>"
normalized_patch_source: "<path or run record reference>"
run_record_path: ".project-memory/pr/<PR-ID>/run_record.yml"
run_id: "<string>"
base_sha: "<sha>"
base_sha_source: ".project-memory/pr/<PR-ID>/PLAN.md"
current_head: "<sha>"
snapshot_verified: true
snapshot_verified_by: "git introspection"
patch_normalized: true
scope_approved: true
allowed_paths:
  - "<repo-relative POSIX path or glob>"
forbidden_paths:
  - "<repo-relative POSIX path or glob>"
validation_results:
  - command: "<string>"
    result: "passed | failed | skipped | not run"
    evidence: "<short sanitized bounded evidence>"
human_approval:
  required: true
  status: "approved | rejected | changes_requested | waived_validation"
  approved_by: "<human identifier>"
  approval_reason: "<string>"
  approved_at: "<ISO8601 UTC>"
apply_decision:
  apply_status: "approved | rejected | applied | failed | skipped"
  applied_by: "<human or controlled apply process identifier>"
  applied_at: "<ISO8601 UTC or null>"
  failure_reason: "<string or null>"
post_apply_validation:
  - command: "<string>"
    result: "passed | failed | skipped | not run"
    evidence: "<short sanitized bounded evidence>"
confirmations:
  no_forbidden_paths: true
  no_secrets: true
  no_agent_git_mutation: true
  no_agent_docker_commands: true
  canonical_write_human_approved: true
```

## Required enum values

```yaml
human_approval.status:
  - approved
  - rejected
  - changes_requested
  - waived_validation

apply_status:
  - approved
  - rejected
  - applied
  - failed
  - skipped

validation_result:
  - passed
  - failed
  - skipped
  - not run

snapshot_verified_by:
  - git introspection
  - filesystem
  - not available
```

## Apply allowed only if

```text
Apply may be approved only if:
- base_sha == current_head
- snapshot_verified == true
- patch_normalized == true
- scope_approved == true
- no forbidden paths are present
- no secrets are present
- human approval is present
- validation passed, or validation was explicitly waived by a human with reason
- allowed_paths and forbidden_paths are recorded
- ApplyRequest references the originating run_record
- ApplyRequest references the normalized_patch_id
```

## Apply must stop / reject if

```text
Apply must stop or be rejected if:
- base_sha != current_head
- snapshot verification is false or skipped without explicit human handling
- patch is not normalized
- forbidden paths are present
- secrets are detected
- human approval is missing
- validation failed and no explicit human waiver exists
- allowed_paths are absent
- forbidden_paths are absent
- originating run_record is missing
- normalized_patch_id is missing
```

## Agent prohibitions

```text
Agents must not run:
- git apply
- git add
- git commit
- git push
- git reset
- git checkout
- git switch
- git merge
- git rebase
- git clean

Agents must not:
- directly mutate the canonical repository
- apply patches to the canonical repository
- perform Docker apply side effects
- bypass human/HITL approval
```

## Human/HITL decisions

```text
Human/HITL may:
- approve
- reject
- request changes
- approve with validation waiver
```

Validation waiver must include:

- human approver
- reason
- timestamp
- which validation was waived
- risk note

## Run record apply outcome

Define required future run record apply outcome fields:

```yaml
apply_outcome:
  apply_request_id: "<string>"
  apply_status: "approved | rejected | applied | failed | skipped"
  approved_by: "<human identifier>"
  approval_reason: "<string>"
  applied_by: "<human or controlled apply process identifier>"
  applied_at: "<ISO8601 UTC or null>"
  post_apply_validation:
    - command: "<string>"
      result: "passed | failed | skipped | not run"
      evidence: "<short sanitized bounded evidence>"
```

Clarify:

- PR 0018 defines the contract only
- PR 0018 does not modify existing run records
- PR 0018 does not backfill apply outcomes
- PR 0018 does not automate run record updates

## Safety invariants

- ApplyRequest is evidence and authorization request, not execution by itself
- Apply approval does not imply git commit/push by agents
- canonical repo write remains human/HITL gated
- ApplyRequest must not contain secrets
- validation evidence must be sanitized and bounded
- file paths must be repo-relative POSIX paths
- forbidden path checks must be explicit
- allowed path checks must be explicit
- Docker side effects are forbidden for agents
- git mutation is forbidden for agents

## Machine-readable scope

```text
allowed_write_paths:
- .project-memory/apply-gate.schema.yml
- .project-memory/context-bundles/contracts.yml
- .project-memory/project_contract.yml
- .project-memory/memory_index.yml
- .project-memory/pr/0018-apply-gate-contract/PLAN.md

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
- .project-memory/run-record.schema.yml
- .project-memory/** except:
  - .project-memory/apply-gate.schema.yml
  - .project-memory/context-bundles/contracts.yml
  - .project-memory/project_contract.yml
  - .project-memory/memory_index.yml
  - .project-memory/pr/0018-apply-gate-contract/PLAN.md
```

## Required project contract ids

Future implementation must add contract ids such as:

```text
agents.apply-gate.required
agents.apply-gate.apply-request-schema
agents.apply-gate.normalized-patch-reference
agents.apply-gate.run-record-reference
agents.apply-gate.base-sha-match
agents.apply-gate.snapshot-verified
agents.apply-gate.human-approval-required
agents.apply-gate.validation-required-or-waived
agents.apply-gate.validation-waiver-human-only
agents.apply-gate.no-forbidden-paths
agents.apply-gate.no-secrets
agents.apply-gate.allowed-paths-required
agents.apply-gate.forbidden-paths-required
agents.apply-gate.evidence-not-execution
agents.apply-gate.no-agent-git-apply
agents.apply-gate.no-agent-canonical-write
agents.apply-gate.no-docker-side-effects
agents.apply-gate.run-record-apply-outcome
```

Must preserve:

- repo.canonical-write.single-gate
- agents.no-git-mutation
- agents.no-secrets
- agents.context-snapshot.*
- agents.run-record.*
- agents.git.read-only-introspection

## Machine-checkable acceptance criteria

```text
apply_gate_schema: .project-memory/apply-gate.schema.yml
schema_version: "0.1"
apply_request_id: required
normalized_patch_id: required
run_record_path: required
run_id: required
base_sha: required
base_sha_source: required
current_head: required
snapshot_verified: required
snapshot_verified_by: required
patch_normalized: required
scope_approved: required
allowed_paths: required
forbidden_paths: required
human_approval: required
validation_required_or_human_waived: required
apply_status_enum: required
human_approval_status_enum: required
validation_result_enum: required
run_record_apply_outcome: required
post_apply_validation: required
repo_relative_posix_paths: required
sanitized_validation_evidence: required
bounded_validation_evidence: required
validation_evidence_max_chars: 2000
automatic_apply: forbidden
agent_git_apply: forbidden
agent_git_mutation: forbidden
agent_canonical_write: forbidden
docker_side_effects_by_agents: forbidden
secrets_in_apply_request: forbidden
memory_index_bump: "0.4"
runner_code_changes: forbidden
service_code_changes: forbidden
agent_config_changes: forbidden
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

- apply gate schema is missing
- ApplyRequest fields are missing
- normalized_patch_id is missing
- run_record_path is missing
- base_sha/current_head match requirement is missing
- human approval requirement is missing
- validation required-or-waived rule is missing
- validation waiver lacks human reason
- forbidden paths rule is missing
- allowed paths rule is missing
- no secrets rule is missing
- agent `git apply` prohibition is missing
- agent canonical write prohibition is missing
- Docker side-effect prohibition is missing
- project_contract is not updated
- contracts bundle is not updated
- memory_index is not bumped to `"0.4"`
- implementation modifies runner/service code
- implementation modifies agent configs
- implementation modifies Dockerfiles/workflows/GHCR
- implementation modifies run-record schema
- implementation automates apply
- implementation performs canonical repo writes
- repo.canonical-write.single-gate is weakened
- agents.no-git-mutation is weakened
- agents.no-secrets is weakened

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

PR 0018 implemented:
- Created `.project-memory/apply-gate.schema.yml` with ApplyRequest schema, required fields, enums, validation waiver fields, run record apply outcome fields, apply allowed/stop conditions, agent prohibitions, and safety rules
- Added 18 `agents.apply-gate.*` contract entries to `.project-memory/project_contract.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.3 with apply-gate schema reference, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.4 with new `apply-gate` label and additional_files references

All changes are memory/contract only. No agent configs, runner code, services, packages, Dockerfiles, workflows, run-record schema, or agent-config context bundle were modified.
