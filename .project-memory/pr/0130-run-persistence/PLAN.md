# PR 0130 — Run Persistence Plan

## Summary

Plan the third Stage 2 Closed Loop PR after PR 0129: minimal local Run Persistence so `ariadne task` runs leave durable, inspectable run state before the PR 0131 dogfood milestone. Persists pipeline result, git boundary result, command plan, and artifact hashes as deterministic `run.json` and `manifest.json` under `.ariadne/runs/<run_id>/`. Supports readback by `run_id`. No dashboard, no control plane, no retry loop.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 24aa5dced54f29c59800cd754ed681edc80c3fdb |
| current_branch | 0130-run-persistence |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line ACTIVE; L329 "0130 — Run Persistence: run state/artifacts/proofs in .ariadne/runs/"; L327 DOGFOOD MILESTONE |
| pr_0127_pipeline_runner_evidence | `pipeline_runner.py` + tests present; `run_pr_pipeline()` → `PipelineRunnerResult` |
| pr_0128_git_boundary_evidence | `git_boundary.py` + tests present; `prepare_git_boundary_plan()`, `execute_git_boundary_plan()` |
| pr_0129_ariadne_task_cli_evidence | `ariadne_task_cli.py` + tests present; `run_ariadne_task(request, pipeline_runner_fn, git_boundary_planner_fn, git_boundary_executor_fn, clock_provider)` with 4 injectable boundaries |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 2 Closed Loop
* expected PR slot: 0130 — Run Persistence
* why this PR is next: PR 0127 added Pipeline Runner, PR 0128 added Git Boundary, and PR 0129 added the minimal ariadne task CLI; the next required capability is durable local run evidence so PR 0131 can dogfood a real Ariadne-created PR and leave inspectable run state
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime/file-captured artifacts are evidence; persisted run records are local proof, not a dashboard or control plane

## PR 0127 Pipeline Runner verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/pipeline_runner.py` exists | PRESENT ✓ |
| `run_pr_pipeline()` → `PipelineRunnerResult` with `status`, `final_action`, `has_blockers`, `artifact_hashes`, `step_results`, `gate_results` | CONFIRMED ✓ |

## PR 0128 Git Boundary verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/git_boundary.py` exists | PRESENT ✓ |
| `prepare_git_boundary_plan()` + `execute_git_boundary_plan()` → `GitBoundaryResult` | CONFIRMED ✓ |

## PR 0129 ariadne task CLI verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/ariadne_task_cli.py` exists | PRESENT ✓ |
| `.project-memory/pr/0129-ariadne-task-cli/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `run_ariadne_task(request, pipeline_runner_fn, git_boundary_planner_fn, git_boundary_executor_fn, clock_provider)` with 4 injectable boundaries | CONFIRMED ✓ |
| CLI uses `AriadneTaskCliResult` with `task_description_hash`, `pipeline_status`, `git_boundary_status`, `command_plan`, `execution_results`, `artifact_hashes` (via pipeline) | CONFIRMED ✓ |

## Anti-stall / no-drift constraint

Do not respond to external agent-system prompts by expanding scope. PR 0130 must remain Run Persistence only. No roadmap changes. No ADR. No dashboard. No control plane. No retry loop. No model health. No run report. No parallel queue. No decision core. No context warehouse. No eval harness. No frontend. No new capability stream.

## Run Persistence contract

### New module

`services/runner/src/runner/run_persistence.py`

Contains:
- `RunPersistenceRequest` — input dataclass
- `PersistedRunRecord` — stored record model
- `RunPersistenceResult` — write result
- `RunPersistenceReadResult` — read result
- `RunPersistenceStatus` — status enum: `persisted`, `read_ok`, `rejected`, `not_found`
- `persist_run_record(request)` — main write function
- `load_run_record(runs_root, run_id)` — read function
- `_build_run_manifest()` — manifest generation
- `_write_json_atomically()` — atomic JSON write helper
- Stable reason codes

### `RunPersistenceStatus` (enum)

```python
class RunPersistenceStatus(str, enum.Enum):
    PERSISTED = "persisted"
    READ_OK = "read_ok"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
```

### `RunPersistenceRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class RunPersistenceRequest:
    runs_root: str                         # e.g., ".ariadne/runs"
    run_id: str                            # deterministic filesystem-safe identifier
    task_description_hash: str
    task_description_redacted: str         # first 80 chars or hash placeholder
    branch: str
    base_branch: str
    status: str                            # overall CLI status
    reason_codes: tuple[str, ...]
    pipeline_status: str | None
    pipeline_final_action: str | None
    pipeline_has_blockers: bool | None
    pipeline_step_summary: tuple[dict, ...]      # serialized step results
    pipeline_gate_summary: tuple[dict, ...]      # serialized gate results
    git_boundary_status: str | None
    command_plan_summary: tuple[dict, ...]        # serialized command plan
    execution_attempted: bool
    execution_results_summary: tuple[dict, ...]   # serialized execution results
    approval_summary: str
    artifact_hashes: dict[str, str]
    warnings: tuple[str, ...]
    next_action: str
    started_at: str | None
    finished_at: str | None
    clock_provider: Callable | None = None
```

### `PersistedRunRecord` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PersistedRunRecord:
    schema_version: str
    run_id: str
    run_json_hash: str                     # SHA256[:16] of run.json content
    task_description_hash: str
    task_description_redacted: str
    branch: str
    base_branch: str
    status: str
    reason_codes: tuple[str, ...]
    pipeline_status: str | None
    pipeline_final_action: str | None
    pipeline_has_blockers: bool | None
    git_boundary_status: str | None
    command_plan_summary: tuple[dict, ...]
    execution_attempted: bool
    execution_results_summary: tuple[dict, ...]
    approval_summary: str
    artifact_hashes: dict[str, str]
    warnings: tuple[str, ...]
    next_action: str
    started_at: str | None
    finished_at: str | None
```

### `RunPersistenceResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class RunPersistenceResult:
    status: str
    reason_codes: tuple[str, ...]
    run_id: str
    run_dir: str
    files_written: tuple[str, ...]
    manifest_path: str
    run_json_path: str
    run_json_hash: str
    bytes_written: int
    readback_ok: bool
    started_at: str | None
    finished_at: str | None
    details: str | None
```

### `RunPersistenceReadResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class RunPersistenceReadResult:
    status: str
    reason_codes: tuple[str, ...]
    run_id: str
    record: PersistedRunRecord | None
    stored_hash: str | None
    recomputed_hash: str | None
    hash_match: bool
    details: str | None
```

## Run directory layout

```
.ariadne/runs/<run_id>/
├── run.json           # Run record with all fields (deterministic JSON)
└── manifest.json      # Manifest with schema_version, run_id, run_json_hash, file list
```

Tests use a temp `runs_root` (e.g., `tmp_path / "runs"`), never the repo `.ariadne/`.

## Run ID and hashing contract

- `run_id` must be filesystem-safe: matches `^[a-zA-Z0-9_\-]{1,64}$`
- Non-conforming `run_id` is rejected with reason code `invalid_run_id`
- `task_description_hash` is SHA256[:16] of full task description text
- `run.json` hash is SHA256[:16] of the canonical JSON content
- Output JSON uses `sort_keys=True` for deterministic ordering
- Timestamps are injectable via `clock_provider`

## Persisted data contract

`run.json` includes:

```json
{
  "schema_version": "1",
  "run_id": "...",
  "task_description_hash": "...",
  "task_description_redacted": "...",
  "branch": "...",
  "base_branch": "...",
  "status": "completed",
  "reason_codes": [],
  "pipeline_status": "completed",
  "pipeline_final_action": "continue",
  "pipeline_has_blockers": false,
  "git_boundary_status": "approved",
  "command_plan_summary": [...],
  "execution_attempted": true,
  "execution_results_summary": [...],
  "approval_summary": "Approved by ...",
  "artifact_hashes": {"path/to/artifact": "abc123..."},
  "warnings": [],
  "next_action": "continue",
  "started_at": null,
  "finished_at": null
}
```

`manifest.json` includes:

```json
{
  "schema_version": "1",
  "run_id": "...",
  "run_json_hash": "...",
  "files": ["run.json"]
}
```

Do NOT persist:
- Raw agent stdout/stderr as canonical proof
- Secrets
- Full unredacted task text (use hash + 80-char redacted summary)
- `.ariadne/` in test runs

## Readback contract

- `load_run_record(runs_root, run_id)` reads `run.json` from the run directory
- Verifies `run_id` consistency (stored run_id matches requested run_id)
- Returns `RunPersistenceReadResult` with stored hash and recomputed hash for integrity check
- Missing directory → `NOT_FOUND`
- Malformed JSON → `REJECTED` with reason code

## CLI integration contract

Narrow integration into `ariadne_task_cli.py` (and only `ariadne_task_cli.py`):

- `run_ariadne_task()` accepts optional `--runs-root` and `--run-id` CLI arguments
- After `run_ariadne_task()` produces a result, CLI persists via `persist_run_record()` through an injectable boundary (default: the new `persist_run_record` function; injectable for tests)
- CLI output includes `run_id` and `run_record_path` in both human-readable and JSON output
- CLI tests use temp `runs_root` — never write to repo `.ariadne/runs`
- Persistence failure surfaces as blocked/failed CLI result (non-zero exit)
- Persistence does not bypass Pipeline Runner or Git Boundary
- Persistence does not execute git/gh
- The persistence boundary is injected via a `persistence_fn` parameter in `run_ariadne_task()` — similar to the existing `pipeline_runner_fn`, `git_boundary_planner_fn`, etc.

## Atomic/local file write contract

- Create run directory under the selected `runs_root` (`os.makedirs(exist_ok=True)`)
- Write `run.json` with `sort_keys=True`
- Write `manifest.json` with `sort_keys=True`
- Write using file → replace (write to `.tmp` then `os.rename()` for atomicity)
- No network, no Docker, no git mutation, no dependency install
- No `chmod`/`chown` requirement

## Safety and mutation boundaries

Run Persistence must not:
- Grant agents unattended git mutation rights
- Mutate git
- Invoke GitHub CLI
- Invoke Docker
- Install dependencies
- Modify agent configs
- Bypass Pipeline Runner
- Bypass Git Boundary
- Implement retry
- Implement dashboard/control plane
- Start frozen streams

## Non-goals

PR 0130 does not implement:
- Dogfood PR itself (PR 0131)
- Full run report (PR 0134)
- Dashboard
- Control plane
- Retry/failure recovery loop (PR 0132)
- Automatic prompt refinement (PR 0132)
- Model health live fallback (PR 0133)
- Parallel-safe queue (PR 0135)
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/run_persistence.py` | NEW |
| `services/runner/tests/test_run_persistence.py` | NEW |
| `services/runner/src/runner/ariadne_task_cli.py` | MODIFIED — add `--runs-root`, `--run-id`, persistence injection, output fields |
| `services/runner/tests/test_ariadne_task_cli.py` | MODIFIED — add persistence test cases |

Default — not modified:
- `services/runner/src/runner/pipeline_runner.py` — NOT modified
- `services/runner/src/runner/git_boundary.py` — NOT modified
- `services/runner/src/runner/prompt_composer.py` — NOT modified
- `services/runner/src/runner/verdict_parser.py` — NOT modified
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `services/runner/src/runner/docker_agent_adapter.py` — NOT modified
- `agents/*.yml` — NOT modified
- `ROADMAP.md`, `docs/**` — NOT modified
- `pyproject.toml` — NOT modified

## Forbidden files

- `services/task_intake/**`
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0129-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `run_persistence.py` with:
   - All dataclass shapes (request, record, write/read results, status)
   - `persist_run_record()` — create dir, write run.json, write manifest.json
   - `load_run_record()` — read run.json, verify run_id, compute hash
   - `_write_json_atomically()` — atomic JSON write helper
   - Stable reason codes: `invalid_run_id`, `write_failed`, `read_failed`, `hash_mismatch`
   - No subprocess.run/os.system/shell=True, no Docker, no git

2. Create `test_run_persistence.py` with focused tests.

3. Modify `ariadne_task_cli.py`:
   - Add `--runs-root` and `--run-id` CLI arguments
   - Add `persistence_fn` injectable parameter to `run_ariadne_task()`
   - After result is final, call `persist_run_record()` through injected boundary
   - Include `run_id` and `run_record_path` in output
   - Default no persistence (`persistence_fn=None`) → no-op if no runs_root

4. Modify `test_ariadne_task_cli.py`:
   - Add tests for persistence integration
   - Use temp runs_root, fake persistence boundary

## Test plan

### `test_run_persistence.py`

| Class | Focus |
|-------|-------|
| `TestPersistMinimalRecord` | Writes run.json and manifest.json |
| `TestRunDirectoryCreated` | `.ariadne/runs/<run_id>/` created under runs_root |
| `TestDeterministicJsonOrdering` | sort_keys=True in output |
| `TestRunJsonHash` | Hash recorded in manifest |
| `TestLoadRunRecord` | Full round-trip readback |
| `TestLoadRunRecordNotFound` | Missing run → `not_found` |
| `TestLoadRunRecordMalformedJson` | Corrupt run.json → `rejected` |
| `TestRunIdValidation` | Invalid run_id → rejected |
| `TestTaskDescriptionHash` | Hash recorded in run.json |
| `TestRedactedSummary` | 80-char or hash redacted summary |
| `TestArtifactHashesPreserved` | Pipeline artifact_hashes persisted |
| `TestPipelineStepSummary` | Step results serialized |
| `TestPipelineGateSummary` | Gate results serialized |
| `TestCommandPlanSummary` | Command plan serialized |
| `TestApprovalSummary` | Approval metadata persisted |
| `TestExecutionAttemptedFlag` | execution_attempted persisted |
| `TestInjectedClock` | Deterministic timestamps |
| `TestNoAriadneResidue` | Temp runs_root, no repo `.ariadne/` residue |
| `TestNoSubprocessDockerGit` | No forbidden commands |
| `TestNoPipelineModified` | pipeline_runner.py not changed |
| `TestNoGitBoundaryModified` | git_boundary.py not changed |

### `test_ariadne_task_cli.py` (additional persistence tests)

| Class | Focus |
|-------|-------|
| `TestCliPersistWithFakeBoundary` | CLI with fake persistence boundary → result includes run_id |
| `TestCliPersistWithTempRunsRoot` | CLI with temp runs_root → no `.ariadne/` residue |
| `TestCliPersistFailure` | Fake persistence failure → CLI status blocked/failed |
| `TestCliOutputIncludesRunId` | CLI output contains run_id field |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_persistence.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "RunPersistence|run_persistence|persist_run_record|load_run_record|RunPersistenceRequest|RunPersistenceResult|run_id|runs_root|run.json|manifest.json|run_record_path" services/runner/src services/runner/tests .project-memory/pr/0130-run-persistence 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|os.system|shell=True|docker compose|docker run|pip install|python -m pip install|git commit|git push|git add|gh pr create" services/runner/src/runner/run_persistence.py services/runner/tests/test_run_persistence.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `run_persistence.py` (new), `test_run_persistence.py` (new); `ariadne_task_cli.py` and `test_ariadne_task_cli.py` (modified for narrow integration)
- **behavior drift**: `persist_run_record()` writes local files; no git/gh/Docker
- **persistence API drift**: input/output shapes match PLAN.md definitions
- **run directory layout drift**: matches `.ariadne/runs/<run_id>/run.json` + manifest.json
- **CLI integration drift**: narrow wiring of `--runs-root`, `--run-id`, injectable `persistence_fn`
- **readback drift**: `load_run_record()` verifies run_id + hash integrity
- **pipeline/boundary drift**: `pipeline_runner.py` and `git_boundary.py` NOT modified
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no dashboard, no control plane, no retry, no run report
- **dirty-tree residue drift**: no `.ariadne/` residue after validation (tmp_path)

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- third Stage 2 Closed Loop PR after PR 0129 ✓
- minimal Run Persistence planned ✓
- local file evidence only, no dashboard/control plane ✓
- readback by run_id supported ✓
- CLI persistence integration via injectable boundary ✓
- no unattended git mutation rights ✓
- no git/gh execution ✓
- temp runs_root in tests; no repo `.ariadne/` residue ✓
- no predecessor module mutation (pipeline_runner.py, git_boundary.py) ✓
- no dashboard/retry/run-report/model-health/parallel-queue scope ✓
- no frozen stream capability started ✓
- no `.ariadne/` residue after validation ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test `runs_root`. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0130-run-persistence`
- Block if PR 0127 `pipeline_runner.py` is missing — PASS: present
- Block if PR 0128 `git_boundary.py` is missing — PASS: present
- Block if PR 0129 `ariadne_task_cli.py` is missing — PASS: present
- Block if ROADMAP evidence for PR 0130 is missing — PASS: L329 confirmed
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan modifies Pipeline Runner or Git Boundary — PASS: not modified
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if persistence can execute git/gh — PASS: no git/gh in persistence module
- Block if tests write repo `.ariadne/runs` — PASS: tmp_path only
- Block if the plan implements dogfood PR itself — PASS: deferred to PR 0131
- Block if the plan implements full run report, retry/failure recovery, model health, parallel queue, dashboard, or control plane — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
