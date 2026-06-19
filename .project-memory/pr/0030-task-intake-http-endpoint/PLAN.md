## Implementation note

PR 0030 implemented:
- Created `services/task_intake/src/task_intake/server.py` with stdlib-only ASGI app (no FastAPI), GET /health, POST /submit, and POST /task-intake/submit alias
- Created `services/task_intake/tests/test_task_intake_http.py` with ASGI test harness and 20+ tests
- Created `services/task_intake/pyproject.toml` with uvicorn dependency only (no fastapi, no pytest-asyncio)

HTTP tests use stdlib ``asyncio.run()`` and do not require async pytest plugins. Root ``python -m pytest -q`` passes without service-local dev extras.
- Updated `services/task_intake/README.md` with install instructions, endpoint table, curl examples, and non-goal disclaimers

The implementation uses a minimal stdlib ASGI app so root `python -m pytest -q` does not require FastAPI for test collection. No root dependencies changed. No CI/workflow changes. No Docker changes. No project-memory schemas/contracts modified.# PR 0030: Task Intake HTTP endpoint

## Goal

Add a minimal HTTP interface for Task Intake.

The endpoint must:

* expose a runnable HTTP app
* reuse existing `task_intake.accept_task`
* accept JSON prompt input
* return accepted/rejected JSON responses
* provide a health endpoint
* include local run instructions
* include tests
* remain strictly isolated from runner/orchestration/runtime execution

## Context snapshot

```yaml
context_snapshot:
  base_sha: "b22ea41d21c97e94448acdb19f3f4bb24fecc95b"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.11"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "b22ea41d21c97e94448acdb19f3f4bb24fecc95b"
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
- no runner invocation
- no runner request creation
- no runner handoff runtime implementation
- no agent orchestration
- no task execution
- no run_id creation
- no run_record.yml creation
- no .ariadne/** writes
- no Workspace Feature Record creation
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
- no Task Intake Runner Handoff schema changes
- no Workspace Feature Record schema changes
- no Context Steward archival schema changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
services/task_intake/src/task_intake/server.py
services/task_intake/tests/test_task_intake_http.py
services/task_intake/pyproject.toml
services/task_intake/README.md
.project-memory/pr/0030-task-intake-http-endpoint/PLAN.md
```

Implementation may modify `services/task_intake/src/task_intake/__init__.py` only if needed to export the HTTP app in a minimal way. Prefer not to modify it unless tests or package conventions require it.

Implementation must not modify existing intake core behavior unless a bug is discovered and documented:

- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/models.py`
- `services/task_intake/src/task_intake/doctor.py`

## Future implementation forbidden_write_paths

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/run-record.schema.yml
.project-memory/apply-gate.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
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
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
```

## Required HTTP implementation

Create:

```text
services/task_intake/src/task_intake/server.py
```

Required app object:

```text
app
```

Required routes:

```text
GET /health
POST /submit
POST /task-intake/submit
```

Route behavior:

### GET /health

Must return JSON equivalent to:

```json
{"service":"task_intake","status":"ok"}
```

It should reuse `task_intake.doctor.doctor` if possible.

### POST /submit

Must:

- accept JSON body with `prompt`
- optionally accept `title`
- call existing `accept_task(TaskIntakeRequest(prompt=...))`
- return JSON with status and either `task_id` or structured rejection details
- not invoke runner
- not create runner request
- not orchestrate agents
- not write `.ariadne/**`
- not create `run_record.yml`
- not persist data
- not call subprocess/git/docker/network internally

### POST /task-intake/submit

Must be an alias of `/submit` or call the same handler.

Accepted response must include:

```json
{"status":"accepted","task_id":"task_..."}
```

Rejected response must include:

```json
{"status":"rejected","reason":"...","error_code":"..."}
```

## Dependency decision

PLAN must inspect existing repo conventions and decide dependency approach.

Preferred approach:

- Use FastAPI + Uvicorn if adding service-local dependencies is acceptable.
- Dependencies must be scoped to `services/task_intake/pyproject.toml`.
- Do not modify root `pyproject.toml`.
- Do not modify root dependency files.
- Do not add Docker/workflow files.

Expected `services/task_intake/pyproject.toml` should allow:

```bash
pip install -e services/task_intake
uvicorn task_intake.server:app --port 8001
```

If `services/task_intake/pyproject.toml` already exists:

- preserve existing package metadata
- add only required HTTP dependencies if missing

If it does not exist:

- create a minimal service-local pyproject
- include package discovery for `src`
- include only minimal dependencies required for endpoint runtime and tests

Recommended dependencies:

- `fastapi`
- `uvicorn`
- test client dependency only if required by chosen framework/test strategy

Do not add broad unrelated dependencies.

## Required README / runbook

Create or update:

```text
services/task_intake/README.md
```

README must include:

- install command
- server command
- curl accepted example
- curl rejected blank prompt example
- note that endpoint does not run tasks
- note that endpoint does not invoke runner
- note that endpoint does not create `run_record.yml`
- note that endpoint does not write `.ariadne/**`

Required run commands:

```bash
pip install -e services/task_intake
uvicorn task_intake.server:app --port 8001
curl -X POST http://localhost:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the login bug"}'
```

## Required tests

Create:

```text
services/task_intake/tests/test_task_intake_http.py
```

Tests must cover:

- `GET /health` returns service and ok status
- `POST /submit` accepts valid prompt
- accepted response has `status: accepted`
- accepted response has `task_id`
- `POST /task-intake/submit` behaves the same as `/submit`
- blank prompt is rejected
- rejected response has `status: rejected`
- rejected response has `reason`
- rejected response has `error_code`
- malformed JSON or missing prompt is rejected predictably
- endpoint uses existing `accept_task` behavior
- endpoint does not invoke runner
- endpoint does not create runner request
- endpoint does not orchestrate agents
- endpoint does not create `run_record.yml`
- endpoint does not write `.ariadne/**`

Tests must not require Docker.
Tests must not require an external network service.

## Required validation

Implementation PR must run:

```bash
PYTHONPATH=services/task_intake/src python -m pytest services/task_intake/tests -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/task_intake/src python -c "from task_intake.server import app; print(app)"
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "runner\|run_record.yml\|\.ariadne\|subprocess\|docker\|git " services/task_intake/src/task_intake services/task_intake/tests || true
```

Expected:

- Task Intake tests pass
- full pytest passes
- compileall passes
- runner doctor passes
- server app import works
- import regression grep has no matches
- forbidden side-effect grep has no actionable matches except tests/README/comments explicitly asserting forbidden behavior

## Manual smoke test

Manual smoke test for documentation:

```bash
pip install -e services/task_intake
uvicorn task_intake.server:app --port 8001
curl -X POST http://localhost:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the login bug"}'
```

Expected response:

```json
{"status":"accepted","task_id":"task_..."}
```

Manual smoke may be documented but should not require Docker.

## Relationship to existing contracts

```text
PR 0027 introduced Task Intake API skeleton as a service boundary.
PR 0028 defined Task Intake Request contract.
PR 0029 defined Task Intake → Runner Handoff contract.
PR 0030 adds the first externally runnable Task Intake HTTP interface.
The HTTP endpoint is intake-only.
The HTTP endpoint does not execute tasks.
The HTTP endpoint does not invoke runner.
The HTTP endpoint does not create runner requests.
The HTTP endpoint does not orchestrate agents.
The HTTP endpoint does not create run_id.
The HTTP endpoint does not create run_record.yml.
The HTTP endpoint does not write .ariadne/**.
Run Record remains execution evidence.
Task Intake → Runner Handoff remains handoff eligibility evidence, not runtime execution.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Stop conditions

Stop if:

- implementation invokes runner
- implementation creates runner request
- implementation orchestrates agents
- implementation executes tasks
- implementation creates run_id
- implementation creates run_record.yml
- implementation writes `.ariadne/**`
- implementation creates Workspace Feature Records
- implementation modifies runner code
- implementation modifies project-memory contracts or schemas
- implementation modifies `.github/**`, Docker, root pyproject, root Makefile, packages, apps, docs
- implementation adds persistence/database/queue
- implementation adds auth/secrets
- implementation requires Docker to run
- implementation weakens existing Task Intake validation behavior

## Machine-checkable acceptance criteria

```text
task_intake_http_server: services/task_intake/src/task_intake/server.py
task_intake_http_tests: services/task_intake/tests/test_task_intake_http.py
service_local_pyproject: services/task_intake/pyproject.toml
readme_runbook: services/task_intake/README.md
health_endpoint: GET /health
submit_endpoint: POST /submit
submit_alias_endpoint: POST /task-intake/submit
accepted_response_status: accepted
accepted_response_task_id: required
rejected_response_status: rejected
rejected_response_reason: required
rejected_response_error_code: required
uses_existing_accept_task: required
pip_install_editable: required
uvicorn_run_command: required
curl_smoke_example: required
runner_invocation: forbidden
runner_request_creation: forbidden
agent_orchestration: forbidden
task_execution: forbidden
run_id_creation: forbidden
run_record_creation: forbidden
ariadne_writes: forbidden
feature_record_creation: forbidden
project_memory_schema_changes: forbidden
runner_code_changes: forbidden
docker_workflow_changes: forbidden
persistence_database_queue: forbidden
validation_required: task_intake tests | full pytest | compileall | runner doctor | server import
```

## Expected changed files

```text
services/task_intake/src/task_intake/server.py
services/task_intake/tests/test_task_intake_http.py
services/task_intake/pyproject.toml
services/task_intake/README.md
.project-memory/pr/0030-task-intake-http-endpoint/PLAN.md
```

Optional only if justified:

```text
services/task_intake/src/task_intake/__init__.py
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
