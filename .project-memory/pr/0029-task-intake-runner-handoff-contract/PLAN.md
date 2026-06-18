## Implementation note

PR 0029 implemented:
- Created `.project-memory/task-intake-runner-handoff.schema.yml` with source, input/output contracts, preconditions, runner_boundary, run_record_boundary, workspace_boundary, validation, status/error enums, forbidden_actions, invalid cases list, and minimal accepted/rejected examples
- Added 14 `task-intake.runner-handoff.*` contract entries to `.project-memory/project_contract.yml`
- Added 7 task-intake runner-handoff anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.9 with runner-handoff schema in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.11 with new `task-intake-runner-handoff` label and schema references

No services/** files changed. No runner code changed. No Task Intake Request schema changed. No existing schemas modified. No .ariadne/** files created.# PR 0029: Task Intake → Runner Handoff Contract

## Goal

Add a project-memory schema and contract anchors defining how a future accepted Task Intake request may be handed off to the runner layer.

The contract must define:

- handoff input shape
- handoff output shape
- preconditions
- task_id → future run_id relationship
- runner invocation boundary
- run record boundary
- workspace feature relationship
- validation and refusal rules
- forbidden actions
- future implementation requirements

## Context snapshot

```yaml
context_snapshot:
  base_sha: "6c931ec10d3f272c205f74587f736487f333141e"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.10"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "6c931ec10d3f272c205f74587f736487f333141e"
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
- no runner code changes
- no actual runner invocation
- no actual handoff runtime implementation
- no agent orchestration
- no task execution
- no run_record.yml creation
- no .ariadne/** writes
- no actual feature records
- no persistence/database
- no queue implementation
- no authentication/authorization
- no frontend
- no Docker commands
- no Dockerfile changes
- no GHCR/workflow changes
- no ApplyPatch changes
- no Artifact Store changes
- no WorktreeManager changes
- no Run Record schema changes
- no Task Intake Request schema changes
- no Workspace Feature Record schema changes
- no Context Steward archival schema changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0029-task-intake-runner-handoff-contract/PLAN.md
```

## Future implementation forbidden_write_paths

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/task-intake-request.schema.yml
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
.project-memory/task-intake-runner-handoff.schema.yml
```

Schema must define Task Intake → Runner Handoff as a contract artifact, not runtime implementation.

Required top-level fields:

```text
schema_version
handoff_id
source
input
output
preconditions
runner_boundary
run_record_boundary
workspace_boundary
validation
status
error
forbidden_actions
future_implementation
```

Required `source` contract:

```yaml
source:
  task_intake_request_schema: ".project-memory/task-intake-request.schema.yml"
  run_record_schema: ".project-memory/run-record.schema.yml"
  apply_gate_schema: ".project-memory/apply-gate.schema.yml"
```

Required `input` contract:

```yaml
input:
  task_id: "<task_id from accepted intake request>"
  prompt: "<validated prompt>"
  title: "<optional title>"
  source: "<human | agent | system>"
  metadata: {}
```

Rules:

- `task_id` is required.
- `task_id` must come from accepted Task Intake Request.
- `task_id` is not `run_id`.
- `task_id` is not `feature_workspace_id`.
- `prompt` must already satisfy Task Intake Request validation.
- handoff input does not authorize execution by itself.
- handoff input must not contain secrets.
- handoff input must not contain shell/git/docker execution instructions.

Required `output` contract:

```yaml
output:
  accepted_for_runner:
    status: "accepted_for_runner"
    task_id: "<task_id>"
    handoff_id: "<handoff_id>"
  rejected_for_runner:
    status: "rejected_for_runner"
    task_id: "<task_id>"
    reason: "<structured reason>"
    error_code: "<error code>"
```

Required `preconditions`:

- task intake request is valid and accepted
- task_id is present
- prompt is validated and bounded
- no secrets detected
- no executable shell/git/docker instructions
- runner handoff contract exists
- human-approved future runtime policy exists before any actual execution
- run record must not exist before actual runner execution
- `.ariadne/**` writes are forbidden in this handoff contract

Required `runner_boundary`:

```yaml
runner_boundary:
  runner_invocation_allowed_this_pr: false
  runner_invocation_future_contract_required: true
  runner_request_creation_allowed_this_pr: false
  orchestration_allowed_this_pr: false
```

Rules:

- PR 0029 does not invoke runner.
- PR 0029 does not create runner requests.
- PR 0029 does not implement orchestration.
- Future runtime may create runner request only under a later implementation contract.
- Runner execution remains separate from intake and handoff contracts.

Required `run_record_boundary`:

```yaml
run_record_boundary:
  run_record_creation_allowed_this_pr: false
  run_id_creation_allowed_this_pr: false
  future_runner_execution_may_create_run_id: true
  future_runner_execution_may_link_task_id_to_run_id: true
```

Rules:

- `task_id` may be linked to future `run_id`.
- `task_id` is never itself a `run_id`.
- no `run_record.yml` may be created in PR 0029.
- run record remains execution evidence, not intake/handoff evidence.

Required `workspace_boundary`:

```yaml
workspace_boundary:
  feature_workspace_creation_allowed_this_pr: false
  future_workspace_flow_may_link_task_id: true
```

Rules:

- PR 0029 does not create Workspace Feature Records.
- PR 0029 does not write `.ariadne/**`.
- future workspace flow may link `task_id` to `feature_workspace_id` under separate contract.

Required `status` enum:

```text
accepted_for_runner
rejected_for_runner
```

Required `error` enum:

```text
missing_task_id
invalid_task_id
invalid_intake_reference
invalid_prompt
forbidden_secret
forbidden_execution_instruction
runner_contract_missing
unsupported_handoff
```

Required `validation` contract:

```yaml
validation:
  task_id_required: true
  task_id_must_not_be_run_id: true
  task_id_must_not_be_feature_workspace_id: true
  accepted_intake_required: true
  prompt_already_validated: true
  no_execution_authorization: true
  no_runner_invocation: true
  no_run_record_creation: true
  no_ariadne_writes: true
```

Required `forbidden_actions`:

- invoke runner
- create runner request
- orchestrate agents
- execute task
- create run_id
- create run_record.yml
- write `.ariadne/**`
- create feature records
- modify Task Intake service code
- modify runner code
- modify Run Record schema
- modify Task Intake Request schema
- modify Workspace Feature Record schema
- modify Context Steward archival schema
- modify Apply Gate schema
- add persistence/database
- add Docker/workflow files

Schema must include:

- commented minimal accepted_for_runner example
- commented rejected_for_runner example
- invalid cases list

Invalid cases must include:

- missing task_id
- task_id confused with run_id
- task_id confused with feature_workspace_id
- task_id not linked to accepted intake request
- invalid prompt
- secret-like fields
- shell/git/docker execution instruction
- request implying immediate runner execution
- request implying run_record.yml creation
- request implying `.ariadne/**` write
- handoff accepted without handoff_id
- rejected handoff without structured reason

## Required contract ids

Update `.project-memory/project_contract.yml` with contract ids equivalent to:

```text
task-intake.runner-handoff.required
task-intake.runner-handoff.schema-path
task-intake.runner-handoff.input-task-id-required
task-intake.runner-handoff.task-id-not-run-id
task-intake.runner-handoff.task-id-not-feature-workspace-id
task-intake.runner-handoff.accepted-intake-required
task-intake.runner-handoff.no-runner-invocation-this-pr
task-intake.runner-handoff.no-runner-request-this-pr
task-intake.runner-handoff.no-agent-orchestration
task-intake.runner-handoff.no-run-id-creation
task-intake.runner-handoff.no-run-record-creation
task-intake.runner-handoff.no-ariadne-writes
task-intake.runner-handoff.no-feature-record-creation
task-intake.runner-handoff.future-runtime-contract-required
```

Contract semantics:

- schema path is `.project-memory/task-intake-runner-handoff.schema.yml`
- handoff requires accepted intake task_id
- task_id is not run_id
- task_id is not feature_workspace_id
- this PR does not invoke runner
- this PR does not create runner requests
- this PR does not create run_id
- this PR does not create run_record.yml
- this PR does not write `.ariadne/**`
- future runtime implementation requires a separate contract

## Required anchors

Update `.project-memory/anchors.yml` with anchors equivalent to:

```text
task-intake.runner-handoff.required
task-intake.runner-handoff.schema-path
task-intake.runner-handoff.input-task-id-required
task-intake.runner-handoff.no-runner-invocation-this-pr
task-intake.runner-handoff.no-run-record-creation
task-intake.runner-handoff.no-ariadne-writes
task-intake.runner-handoff.future-runtime-contract-required
```

Preserve existing anchor structure and add these anchors consistently.

## Required contracts bundle update

Update `.project-memory/context-bundles/contracts.yml`:

- include `.project-memory/task-intake-runner-handoff.schema.yml` in `read_first` or equivalent
- include task-intake runner handoff anchors
- include `.project-memory/task-intake-request.schema.yml` as required prior context
- add note that PR 0029 is contract-only
- add note that runner invocation remains forbidden in PR 0029
- add note that run record creation remains forbidden in PR 0029
- add note that `.ariadne/**` writes remain forbidden in PR 0029
- bump bundle version according to existing convention

## Required memory index update

Update `.project-memory/memory_index.yml`:

- bump version by one minor step: `"0.10"` → `"0.11"`
- update `task-intake` label
- ensure contracts label references `.project-memory/task-intake-runner-handoff.schema.yml`
- include schema in relevant additional files
- ensure future agents can discover task-intake runner handoff contract from contracts bundle

## Relationship to existing contracts

```text
PR 0027 introduced Task Intake API skeleton as a service boundary.
PR 0028 defined Task Intake Request contract.
PR 0029 defines Task Intake → Runner Handoff contract.
Task Intake Request is intake evidence, not execution evidence.
Task Intake → Runner Handoff is handoff eligibility evidence, not execution evidence.
Run Record remains execution evidence.
Workspace Feature Record remains durable feature/workspace state.
Context Steward archival remains after-merge archival workflow.
Accepted task_id is not run_id and not feature_workspace_id.
Future runner runtime may link task_id to run_id only under a separate implementation contract.
Future workspace workflow may link task_id to feature_workspace_id only under a separate implementation contract.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "task-intake.runner-handoff\|task-intake-runner-handoff.schema.yml\|task_id\|run_id\|run_record.yml\|\.ariadne" .project-memory
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- import regression grep has no matches
- handoff grep shows schema, contract ids, anchors, contracts bundle, memory index, and PLAN references
- references to `run_record.yml` and `.ariadne/**` are forbidden-boundary references only

## Stop conditions

Stop if:

- implementation modifies services/**
- implementation modifies runner code
- implementation invokes runner
- implementation creates runner requests
- implementation orchestrates agents
- implementation writes `.ariadne/**`
- implementation creates actual feature records
- implementation creates actual `run_record.yml`
- implementation creates run_id
- implementation modifies Run Record schema
- implementation modifies Task Intake Request schema
- implementation modifies Workspace Feature Record schema
- implementation modifies Context Steward archival schema
- implementation modifies Apply Gate schema
- implementation adds Docker/workflow files
- implementation adds persistence/database
- implementation adds external dependencies
- implementation modifies apps/packages/docs/.github/docker/services
- implementation weakens Run Record, Task Intake Request, Workspace Feature Record, Context Steward archival, Ariadne namespace, Apply Gate, Artifact Store, WorktreeManager, MockCoder, or patch safety invariants

## Machine-checkable acceptance criteria

```text
task_intake_runner_handoff_schema: .project-memory/task-intake-runner-handoff.schema.yml
project_contract_ids: required
anchors: required
contracts_bundle_reference: required
memory_index_bump: required
memory_index_expected_version_if_current_0_10: "0.11"
accepted_intake_required: required
task_id_required: required
task_id_not_run_id: required
task_id_not_feature_workspace_id: required
handoff_id_required_on_acceptance: required
accepted_for_runner_status: accepted_for_runner
rejected_for_runner_status: rejected_for_runner
error_enum: required
structured_rejection_reason: required
runner_invocation_this_pr: forbidden
runner_request_creation_this_pr: forbidden
agent_orchestration: forbidden
execution_authorization: forbidden
run_id_creation: forbidden
run_record_creation: forbidden
ariadne_writes: forbidden
feature_record_creation: forbidden
task_intake_code_changes: forbidden
runner_code_changes: forbidden
schema_changes_except_runner_handoff: forbidden
future_runtime_contract_required: required
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0029-task-intake-runner-handoff-contract/PLAN.md
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
