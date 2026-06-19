## Implementation note

PR 0031 implemented:
- Created `services/task_intake/src/task_intake/smoke.py` with `check_health`, `check_submit_accepted`, `check_blank_prompt_rejected` helpers and `main()` CLI entry point
- Created `services/task_intake/tests/test_task_intake_smoke.py` with monkeypatching-based tests (no running server required)
- Updated `services/task_intake/README.md` with Smoke demo section including command, curl equivalents, and limitations

No model routing implementation. No model switching. No model_capability_profile.json. No agent config changes. No runner invocation. No runner request creation. No task execution. No run_id. No run_record.yml. No .ariadne/** writes. No project-memory schema/contract changes. No memory_index changes. No Docker/workflow/root dependency changes.# PR 0031: Task Intake HTTP smoke/demo

## Goal

Add a lightweight smoke/demo command for the Task Intake HTTP endpoint.

The smoke command must:

- run against a locally running `uvicorn task_intake.server:app`
- call `GET /health`
- call `POST /submit` with a valid prompt
- call `POST /submit` with a blank prompt
- print human-readable output
- exit non-zero on failed checks
- use stdlib only
- require no Docker
- require no runner
- require no external service beyond local localhost HTTP server

## Context snapshot

```yaml
context_snapshot:
  base_sha: "94aaa1e6c8259f4890935ee9a9445c92ab6f4974"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.11"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "94aaa1e6c8259f4890935ee9a9445c92ab6f4974"
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
- no new contracts or schemas
- no project-memory contract changes
- no memory_index bump
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
- no root dependency changes
- no root Makefile changes
- no CI/workflow changes
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
services/task_intake/src/task_intake/smoke.py
services/task_intake/tests/test_task_intake_smoke.py
services/task_intake/README.md
.project-memory/pr/0031-task-intake-http-smoke-demo/PLAN.md
```

Optional only if strongly justified:

```text
services/task_intake/SMOKE.md
```

Implementation must not modify:

```text
services/task_intake/src/task_intake/server.py
services/task_intake/src/task_intake/app.py
services/task_intake/src/task_intake/models.py
services/task_intake/src/task_intake/doctor.py
services/task_intake/pyproject.toml
```

unless an existing bug is discovered and explicitly documented. Prefer no changes to those files.

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

## Required smoke module

Create:

```text
services/task_intake/src/task_intake/smoke.py
```

Required command:

```bash
python -m task_intake.smoke --base-url http://127.0.0.1:8001
```

Required behavior:

- use stdlib only
- use `urllib.request` or equivalent stdlib HTTP client
- accept `--base-url`
- default base URL may be `http://127.0.0.1:8001`
- call `GET /health`
- call `POST /submit` with `{"prompt": "Fix the login bug"}`
- call `POST /submit` with `{"prompt": ""}`
- validate JSON responses
- print readable progress lines
- return exit code 0 on success
- return non-zero exit code on failure
- not start uvicorn itself
- not use subprocess
- not invoke runner
- not create runner requests
- not orchestrate agents
- not create `run_record.yml`
- not write `.ariadne/**`
- not persist data

Expected successful output should be similar to:

```text
health: ok
submit accepted: task_...
blank prompt rejected: blank_prompt
smoke: ok
```

## Required tests

Create:

```text
services/task_intake/tests/test_task_intake_smoke.py
```

Tests must:

- not require a running HTTP server
- not require external network access
- not require Docker
- use stdlib only
- test smoke response validation helpers
- test success path formatting
- test failure/non-zero behavior for invalid responses
- confirm smoke module does not import runner
- confirm smoke module does not use subprocess/git/docker
- confirm smoke module does not write `.ariadne/**`
- confirm smoke module does not create `run_record.yml`

Recommended design:

- split smoke code into small pure helpers plus `main`
- test helpers without network
- mock or monkeypatch HTTP function with local fake responses

## Required README update

Update:

```text
services/task_intake/README.md
```

README must include a "Smoke demo" section with:

```bash
pip install -e services/task_intake
uvicorn task_intake.server:app --port 8001
python -m task_intake.smoke --base-url http://127.0.0.1:8001
```

README must also include the manual curl equivalent:

```bash
curl -X POST http://127.0.0.1:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the login bug"}'
```

README must state:

- smoke/demo is intake-only
- smoke/demo does not run tasks
- smoke/demo does not invoke runner
- smoke/demo does not create runner requests
- smoke/demo does not create `run_record.yml`
- smoke/demo does not write `.ariadne/**`
- smoke/demo requires a local uvicorn server
- smoke/demo does not require Docker

## Required validation

Implementation PR must run:

```bash
PYTHONPATH=services/task_intake/src python -m pytest services/task_intake/tests -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/task_intake/src python -m task_intake.smoke --help
PYTHONPATH=services/task_intake/src python -c "from task_intake.smoke import main; print(main)"
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
grep -R -n "from runner\|services.runner\|subprocess\|docker\|git \|run_record.yml\|\.ariadne" services/task_intake/src/task_intake/smoke.py services/task_intake/tests/test_task_intake_smoke.py services/task_intake/README.md || true
```

Expected:

- task_intake tests pass
- full pytest passes
- compileall passes
- runner doctor passes
- smoke help works
- smoke module import works
- import regression grep has no matches
- forbidden side-effect grep has no actionable matches except README/tests explicitly asserting forbidden behavior

## Manual smoke

Implementation final output must document whether this manual smoke was run:

```bash
pip install -e services/task_intake
uvicorn task_intake.server:app --port 8001
python -m task_intake.smoke --base-url http://127.0.0.1:8001
```

Manual smoke is preferred, but not required in CI.

If not run:

- state `manual smoke: not run`
- state that automated tests cover smoke helper behavior
- state README documents exact commands

If run:

- include sanitized output
- do not include secrets
- do not leave server running

## Relationship to existing contracts

```text
PR 0027 introduced Task Intake API skeleton.
PR 0028 defined Task Intake Request contract.
PR 0029 defined Task Intake → Runner Handoff contract.
PR 0030 added the externally runnable Task Intake HTTP interface.
PR 0031 adds a repeatable local smoke/demo path for the HTTP interface.
The smoke/demo is intake-only.
The smoke/demo does not execute tasks.
The smoke/demo does not invoke runner.
The smoke/demo does not create runner requests.
The smoke/demo does not orchestrate agents.
The smoke/demo does not create run_id.
The smoke/demo does not create run_record.yml.
The smoke/demo does not write .ariadne/**.
Run Record remains execution evidence.
Task Intake → Runner Handoff remains handoff eligibility evidence, not runtime execution.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
```

## Stop conditions

Stop if:

- implementation modifies project-memory contracts or schemas
- implementation modifies memory_index
- implementation modifies runner code
- implementation invokes runner
- implementation creates runner request
- implementation orchestrates agents
- implementation executes tasks
- implementation creates run_id
- implementation creates run_record.yml
- implementation writes `.ariadne/**`
- implementation creates Workspace Feature Records
- implementation modifies `.github/**`, Docker, root pyproject, root Makefile, packages, apps, docs
- implementation adds persistence/database/queue
- implementation adds auth/secrets
- implementation requires Docker to run
- implementation weakens existing Task Intake validation behavior

## Machine-checkable acceptance criteria

```text
task_intake_smoke_module: services/task_intake/src/task_intake/smoke.py
task_intake_smoke_tests: services/task_intake/tests/test_task_intake_smoke.py
readme_smoke_demo: services/task_intake/README.md
smoke_command: python -m task_intake.smoke --base-url http://127.0.0.1:8001
health_check: required
submit_accepted_check: required
blank_prompt_rejected_check: required
human_readable_output: required
nonzero_on_failure: required
stdlib_only: required
requires_local_uvicorn: documented
starts_server_itself: forbidden
subprocess_usage: forbidden
runner_invocation: forbidden
runner_request_creation: forbidden
agent_orchestration: forbidden
task_execution: forbidden
run_id_creation: forbidden
run_record_creation: forbidden
ariadne_writes: forbidden
feature_record_creation: forbidden
project_memory_schema_changes: forbidden
memory_index_changes: forbidden
runner_code_changes: forbidden
docker_workflow_changes: forbidden
persistence_database_queue: forbidden
validation_required: task_intake tests | full pytest | compileall | runner doctor | smoke help | smoke import
```

## Expected changed files

```text
services/task_intake/src/task_intake/smoke.py
services/task_intake/tests/test_task_intake_smoke.py
services/task_intake/README.md
.project-memory/pr/0031-task-intake-http-smoke-demo/PLAN.md
```

Optional only if justified:

```text
services/task_intake/SMOKE.md
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
