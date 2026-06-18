## Implementation note

PR 0027 implemented:
- Created `services/task_intake/src/task_intake/__init__.py` with all exports
- Updated `services/task_intake/src/task_intake/models.py` with TaskIntakeRequest, TaskIntakeAccepted, TaskIntakeRejected, TaskIntakeStatus, TaskIntakeError enums, MAX_PROMPT_LENGTH constant, and deterministic _make_task_id helper
- Created `services/task_intake/src/task_intake/app.py` with accept_task callable
- Created `services/task_intake/src/task_intake/doctor.py` with doctor health check
- Created `services/task_intake/tests/test_task_intake.py` with 16+ tests covering acceptance, blank/oversized rejection, doctor, import path, and no-side-effect guarantees

No runner invocation, no agent orchestration, no persistence, no .ariadne/** writes, no run_record.yml creation, no external dependencies added. All changes are stdlib-only and pure callable skeleton.# PR 0027: Task Intake API skeleton

## Goal

Add a minimal Task Intake API skeleton that defines the first service boundary for accepting task requests.

The skeleton must be intentionally small:

* request/response models
* in-memory validation behavior
* health/doctor-style endpoint or callable
* deterministic tests
* no persistence
* no runner invocation
* no agent orchestration
* no Docker/workflow changes

## Context snapshot

```yaml
context_snapshot:
  base_sha: "5a2b6591a9d9ce23fa3bc1a53536085ae4f55d1d"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.9"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "5a2b6591a9d9ce23fa3bc1a53536085ae4f55d1d"
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
- no real task execution
- no runner invocation
- no agent orchestration
- no model calls
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
services/task_intake/src/task_intake/__init__.py
services/task_intake/src/task_intake/models.py
services/task_intake/src/task_intake/app.py
services/task_intake/src/task_intake/doctor.py
services/task_intake/tests/test_task_intake.py
.project-memory/pr/0027-task-intake-api-skeleton/PLAN.md
```

Optional only if strictly required by existing repo conventions:

```text
services/task_intake/pyproject.toml
services/task_intake/README.md
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
services/runner/**
services/conductor/**
services/core/**
services/model_gateway/**
packages/**
apps/**
.github/**
docker/**
Dockerfile*
prompts/**
package.json
Makefile
docker-compose.yml
.env
.env.*
```

## Required API skeleton

Implementation should create:

```text
services/task_intake/src/task_intake/
```

Required concepts:

- `TaskIntakeRequest`
- `TaskIntakeAccepted`
- `TaskIntakeRejected`
- `TaskIntakeStatus`
- `TaskIntakeError`
- `accept_task`
- `doctor`

Required behavior:

- accepts a task title or prompt
- rejects empty/blank prompt
- rejects oversized prompt using a bounded max length
- generates deterministic or well-bounded task id format
- returns accepted response without invoking runner
- returns rejected response with structured reason
- has health/doctor callable returning service name and status
- stdlib-only unless existing repo already has an approved API dependency
- no network calls in tests
- no filesystem persistence
- no `.ariadne/**` writes
- no `run_record.yml` creation

## API surface decision

Prefer **Option A**: stdlib-only callable skeleton.

Option A:

- pure Python callable skeleton only
- no web framework dependency
- suitable since repo has no approved API framework dependency in task_intake

Option B (rejected for this PR):

- minimal FastAPI-style app only if FastAPI already exists in repo dependencies
- no new dependency added in this PR unless explicitly allowed by existing project conventions

## Required tests

Create:

```text
services/task_intake/tests/test_task_intake.py
```

Tests must cover:

- valid task is accepted
- accepted response has task_id
- blank prompt is rejected
- oversized prompt is rejected
- rejection includes structured reason
- doctor returns ok status
- no runner invocation
- no agent orchestration
- no `.ariadne/**` writes
- no `run_record.yml` creation
- deterministic import path works with `PYTHONPATH=services/task_intake/src`

## Required validation

Implementation PR must run:

```bash
PYTHONPATH=services/task_intake/src python -m pytest services/task_intake/tests -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/task_intake/src python -c "from task_intake.doctor import doctor; print(doctor())"
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "\.ariadne\|run_record.yml\|subprocess\|docker\|git " services/task_intake || true
```

Expected:

- task_intake tests pass
- full pytest passes
- compileall passes
- runner doctor still passes
- task_intake doctor import works
- import regression grep has no matches
- forbidden side-effect grep has no actionable matches except comments/tests explicitly asserting forbidden behavior

## Relationship to existing contracts

```text
Task Intake API skeleton is a service boundary only.
Task Intake does not execute tasks.
Task Intake does not invoke runner.
Task Intake does not orchestrate agents.
Task Intake does not write .ariadne/**.
Task Intake does not create run_record.yml.
Run Record remains execution evidence, not intake evidence.
Workspace Feature Record remains durable feature/workspace state.
Context Steward archival remains after-merge archival workflow.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Stop conditions

Stop if:

- implementation invokes runner
- implementation orchestrates agents
- implementation writes `.ariadne/**`
- implementation creates actual feature records
- implementation creates actual `run_record.yml`
- implementation modifies runner code
- implementation modifies Run Record schema
- implementation modifies Workspace Feature Record schema
- implementation modifies Context Steward archival schema
- implementation modifies Apply Gate schema
- implementation adds Docker/workflow files
- implementation adds persistence/database
- implementation adds external dependencies without explicit existing repo convention
- implementation modifies apps/packages/docs/.github/docker
- implementation weakens Run Record, Workspace Feature Record, Context Steward archival, Ariadne namespace, Apply Gate, Artifact Store, WorktreeManager, MockCoder, or patch safety invariants

## Machine-checkable acceptance criteria

```text
task_intake_service_path: services/task_intake/src/task_intake
task_intake_tests: services/task_intake/tests/test_task_intake.py
request_model: required
accepted_response_model: required
rejected_response_model: required
status_model: required
doctor_callable: required
accept_task_callable: required
blank_prompt_rejected: required
oversized_prompt_rejected: required
structured_rejection_reason: required
task_id_returned_for_acceptance: required
runner_invocation: forbidden
agent_orchestration: forbidden
ariadne_writes: forbidden
run_record_creation: forbidden
persistence_database: forbidden
docker_workflow_changes: forbidden
runner_code_changes: forbidden
schema_changes: forbidden
non_stdlib_dependencies_unless_existing_convention: forbidden
validation_required: task_intake tests | full pytest | compileall | runner doctor | task_intake doctor
```

## Expected changed files

```text
services/task_intake/src/task_intake/__init__.py
services/task_intake/src/task_intake/models.py
services/task_intake/src/task_intake/app.py
services/task_intake/src/task_intake/doctor.py
services/task_intake/tests/test_task_intake.py
.project-memory/pr/0027-task-intake-api-skeleton/PLAN.md
```

Optional only if justified:

```text
services/task_intake/pyproject.toml
services/task_intake/README.md
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
