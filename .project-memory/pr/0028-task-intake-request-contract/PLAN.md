## Implementation note

PR 0028 implemented:
- Created `.project-memory/task-intake-request.schema.yml` with request contract, task_id rules, response contract, status/error enums, validation contract, handoff contract, forbidden actions, invalid cases list, and minimal valid accepted/rejected examples
- Added 15 `task-intake.request.*` contract entries to `.project-memory/project_contract.yml`
- Added 7 task-intake request anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.8 with task-intake-request schema in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.10 with new `task-intake` label and schema references

No Task Intake service code changed. No runner code changed. No existing schemas modified. No `.ariadne/**` files created.# PR 0028: Task Intake Request Contract

## Goal

Add a project-memory Task Intake Request schema and contract anchors.

The contract must define:

- accepted task intake request shape
- accepted/rejected response semantics
- status enum
- structured error codes
- task id contract
- validation boundaries
- relationship to future runner handoff
- relationship to run records and workspace feature records

## Context snapshot

```yaml
context_snapshot:
  base_sha: "9c1ccaa030c5e68dbf4801077657bc568d6bd675"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.9"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "9c1ccaa030c5e68dbf4801077657bc568d6bd675"
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
- no Task Intake service code changes
- no runner invocation
- no runner handoff implementation
- no agent orchestration
- no task execution
- no persistence/database
- no authentication/authorization
- no frontend
- no Docker commands
- no Dockerfile changes
- no GHCR/workflow changes
- no ApplyPatch changes
- no Artifact Store changes
- no WorktreeManager changes
- no Run Record schema changes
- no Workspace Feature Record schema changes
- no Context Steward archival schema changes
- no .ariadne/** writes
- no actual feature records
- no run_record.yml creation
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
.project-memory/task-intake-request.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0028-task-intake-request-contract/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
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
.project-memory/task-intake-request.schema.yml
```

Schema must define Task Intake Request as a contract artifact, not runtime implementation.

Required top-level fields:

```text
schema_version
task_id
request
response
validation
status
error
handoff
forbidden_actions
```

Required `request` contract:

```yaml
request:
  prompt: "<task prompt>"
  title: "<optional short title>"
  source: "<human | agent | system>"
  metadata: {}
```

Rules:

- `prompt` is required
- `prompt` must be non-blank
- `prompt` must have bounded max length
- `title` is optional
- `metadata` is optional and bounded
- request must not include secrets
- request must not include executable instructions for shell/git/docker
- request does not authorize execution

Required `task_id` contract:

```yaml
task_id:
  format: "task_<bounded-id>"
  deterministic_or_well_bounded: true
  source: "intake validation result"
```

Rules:

- accepted task returns a task_id
- task_id is not a run_id
- task_id is not a feature_workspace_id
- task_id does not imply execution
- future runner handoff may link task_id to run_id
- future workspace feature may link task_id to feature_workspace_id

Required `response` contract:

```yaml
response:
  accepted:
    status: "accepted"
    task_id: "<task_id>"
  rejected:
    status: "rejected"
    reason: "<structured reason>"
    error_code: "<error code>"
```

Required `status` enum:

```text
accepted
rejected
```

Required `error` enum:

```text
blank_prompt
oversized_prompt
invalid_metadata
forbidden_secret
forbidden_execution_instruction
unsupported_request
```

Required `validation` contract:

```yaml
validation:
  blank_prompt_rejected: true
  oversized_prompt_rejected: true
  structured_rejection_reason_required: true
  no_execution_authorization: true
```

Required `handoff` contract:

```yaml
handoff:
  runner_handoff_allowed: false
  runner_handoff_contract_required: true
  future_contract: "Task Intake → Runner Handoff Contract"
```

Rules:

- PR 0028 does not define runner handoff
- runner handoff remains future PR
- accepted intake request does not invoke runner
- accepted intake request does not create run_record.yml

Required `forbidden_actions` contract:

```text
- invoke runner
- orchestrate agents
- execute task
- write .ariadne/**
- create run_record.yml
- create feature records
- modify runner code
- modify Run Record schema
- modify Workspace Feature Record schema
- modify Context Steward archival schema
- modify Apply Gate schema
- add persistence/database
- add Docker/workflow files
```

Schema must include:

- commented minimal valid accepted example
- commented minimal rejected example
- invalid cases list

Invalid cases must include:

- blank prompt
- oversized prompt
- missing prompt
- unsupported metadata shape
- request containing secret-like fields
- request containing shell/git/docker execution instruction
- response accepted without task_id
- rejected response without structured reason
- task_id confused with run_id
- task_id confused with feature_workspace_id
- request implying runner execution
- request implying `.ariadne/**` write
- request implying `run_record.yml` creation

## Required contract ids

Update `.project-memory/project_contract.yml` with contract ids equivalent to:

```text
task-intake.request.required
task-intake.request.schema-path
task-intake.request.prompt-required
task-intake.request.prompt-bounded
task-intake.request.status-enum
task-intake.request.error-enum
task-intake.request.task-id-required-on-acceptance
task-intake.request.task-id-not-run-id
task-intake.request.task-id-not-feature-workspace-id
task-intake.request.no-runner-invocation
task-intake.request.no-agent-orchestration
task-intake.request.no-execution-authorization
task-intake.request.no-run-record-creation
task-intake.request.no-ariadne-writes
task-intake.request.runner-handoff-future-contract
```

Contract semantics:

- schema path is `.project-memory/task-intake-request.schema.yml`
- prompt is required and bounded
- accepted response requires task_id
- rejected response requires structured reason and error_code
- task_id is intake identity only
- task_id is not run_id
- task_id is not feature_workspace_id
- intake does not invoke runner
- intake does not orchestrate agents
- intake does not authorize execution
- intake does not create run_record.yml
- intake does not write `.ariadne/**`
- runner handoff requires future contract

## Required anchors

Update `.project-memory/anchors.yml` with anchors equivalent to:

```text
task-intake.request.required
task-intake.request.schema-path
task-intake.request.task-id-required-on-acceptance
task-intake.request.no-runner-invocation
task-intake.request.no-run-record-creation
task-intake.request.no-ariadne-writes
task-intake.request.runner-handoff-future-contract
```

Preserve existing anchor structure and add these anchors consistently.

## Required contracts bundle update

Update `.project-memory/context-bundles/contracts.yml`:

- include `.project-memory/task-intake-request.schema.yml` in `read_first` or equivalent
- include task-intake request anchors
- add note that Task Intake Request Contract is contract-only in PR 0028
- add note that runner handoff remains future contract
- add note that intake acceptance does not create run records or `.ariadne/**` writes
- bump bundle version according to existing convention

## Required memory index update

Update `.project-memory/memory_index.yml`:

- bump version by one minor step: `"0.9"` → `"0.10"`
- add or update `task-intake` label
- ensure contracts label references `.project-memory/task-intake-request.schema.yml`
- include schema in relevant additional files
- ensure future agents can discover task-intake contract from contracts bundle

## Relationship to existing contracts

```text
PR 0027 introduced Task Intake API skeleton as a service boundary.
PR 0028 defines the Task Intake Request contract.
Task Intake Request is intake evidence, not execution evidence.
Run Record remains execution evidence.
Workspace Feature Record remains durable feature/workspace state.
Context Steward archival remains after-merge archival workflow.
Accepted task_id is not run_id and not feature_workspace_id.
Future Task Intake → Runner Handoff Contract may link task_id to run_id.
Future workspace workflow may link task_id to feature_workspace_id.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "task-intake.request\|task-intake-request.schema.yml\|task_id\|runner-handoff" .project-memory
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- import regression grep has no matches
- task-intake grep shows schema, contract ids, anchors, contracts bundle, and memory index references

## Stop conditions

Stop if:

- implementation modifies services/task_intake/**
- implementation modifies runner code
- implementation invokes runner
- implementation orchestrates agents
- implementation writes `.ariadne/**`
- implementation creates actual feature records
- implementation creates actual `run_record.yml`
- implementation modifies Run Record schema
- implementation modifies Workspace Feature Record schema
- implementation modifies Context Steward archival schema
- implementation modifies Apply Gate schema
- implementation adds Docker/workflow files
- implementation adds persistence/database
- implementation adds external dependencies
- implementation modifies apps/packages/docs/.github/docker/services
- implementation weakens Run Record, Workspace Feature Record, Context Steward archival, Ariadne namespace, Apply Gate, Artifact Store, WorktreeManager, MockCoder, or patch safety invariants

## Machine-checkable acceptance criteria

```text
task_intake_request_schema: .project-memory/task-intake-request.schema.yml
project_contract_ids: required
anchors: required
contracts_bundle_reference: required
memory_index_bump: required
memory_index_expected_version_if_current_0_9: "0.10"
prompt_required: required
prompt_bounded: required
accepted_status: accepted
rejected_status: rejected
error_enum: required
task_id_required_on_acceptance: required
task_id_not_run_id: required
task_id_not_feature_workspace_id: required
structured_rejection_reason: required
runner_invocation: forbidden
agent_orchestration: forbidden
execution_authorization: forbidden
ariadne_writes: forbidden
run_record_creation: forbidden
feature_record_creation: forbidden
runner_handoff_this_pr: forbidden
runner_handoff_future_contract: required
task_intake_code_changes: forbidden
runner_code_changes: forbidden
schema_changes_except_task_intake_request: forbidden
non_stdlib_dependencies: forbidden
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
.project-memory/task-intake-request.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0028-task-intake-request-contract/PLAN.md
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
