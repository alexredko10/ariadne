# PR 0069 — Minimal No-op Runner Adapter Plan

## Goal

Plan executable behavior for a minimal deterministic no-op runner adapter.

This PR must add code and tests.
This PR must not be docs-only.
This PR must not be schemas-only.

The adapter must accept an execution request dict matching the PR 0068 contract shape and return a deterministic execution result dict.

## Product Direction

PR 0068 was the last standalone contract-only PR for this part of the project.

Starting with PR 0069, every PR must include executable/tested behavior unless explicitly blocked.

PR 0069 is the first runner-layer behavior PR.

## Architectural Thesis

The no-op adapter is the first concrete runner adapter boundary consumer.

It proves the execution contract can be consumed by code without introducing real execution.

The adapter is deterministic and safe:

- no Docker
- no subprocess
- no shell
- no network
- no filesystem writes
- no agent execution
- no persistence
- no queue
- no model/provider calls

The adapter returns evidence explicitly stating that no external work happened.

## Context Snapshot

- **current HEAD sha**: `f31e1badc5639d974d80da05436ac9d18b5fac02`
- **current branch**: `0069-minimal-noop-runner-adapter`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `f31e1ba` (main after PR 0068 merge — no skew relative to main)
- **index_version**: `"0.35"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0068, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.grace/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/pr/0068-runner-execution-contract/PLAN.md`
- `schemas/runner-execution-request.schema.yml`
- `schemas/runner-execution-result.schema.yml`
- `docs/RUNNER_EXECUTION_CONTRACT.md`
- `docs/adr/0010-runner-execution-contract-boundary.md`
- `schemas/agent-execution-contract.schema.yml`
- `.project-memory/pr/0065-runs-mock-status/PLAN.md`
- `.project-memory/pr/0066-minimal-mock-app-loop-surface/PLAN.md`
- `.project-memory/pr/0067-mock-loop-http-entrypoint/PLAN.md`
- `services/task_intake/src/task_intake/runs.py`
- `services/task_intake/src/task_intake/mock_loop.py`
- `services/runner/src/runner/__init__.py`
- `services/runner/src/runner/models.py`
- `services/runner/tests/__init__.py`
- `services/runner/tests/test_runner_models.py`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`

## Existing Surface Snapshot

### PR 0068 execution contract

**Request schema** (`schemas/runner-execution-request.schema.yml`):

Required: `execution_request_id`, `run_id`, `task_intake_id`, `context_preview_id`, `requested_adapter`, `execution_mode`, `inputs`, `constraints`.
Optional: `expected_outputs`, `metadata`, `approval`.

`requested_adapter` is a string identifier. `execution_mode` is one of `"dry_run"`, `"execute"`, `"preview"`.

**Result schema** (`schemas/runner-execution-result.schema.yml`):

Required: `execution_result_id`, `execution_request_id`, `run_id`, `status`, `adapter`, `artifacts` (list), `evidence` (list).
Optional: `started`, `completed`, `errors`, `warnings`, `review_required`, `next`.

Status values: `accepted`, `running`, `completed`, `failed`, `cancelled`, `blocked`, `requires_review`.

Artifact shape: `artifact_id`, `artifact_kind`, `relative_path`, `digest` (optional), `producing_step`, `summary`.
Evidence shape: `evidence_id`, `evidence_kind`, `summary`, `status`, `validation_ref` (optional), `artifact_ref` (optional).
Error shape: `code`, `message`, `details` (optional).

### Current runner service layout

```
services/runner/src/runner/
    __init__.py   — re-exports ApplyPatch, ArtifactStore, MockCoder
    __main__.py   — routes subcommands
    apply.py      — ApplyPatch
    artifacts.py  — ArtifactStore
    diff.py
    doctor.py
    mock_coder.py
    models.py     — runner-specific models
    normalize.py
    patch.py
    runtime_smoke.py
    worktree.py

services/runner/tests/
    __init__.py
    test_apply_gate.py
    test_artifact_store.py
    test_doctor_cli.py
    test_mock_coder_sandbox.py
    test_patch_normalizer.py
    test_raw_diff_normalization.py
    test_raw_diff.py
    test_runner_models.py     — uses dataclasses from models.py
    test_runner_smoke.py
    test_runtime_smoke.py
    test_sandbox_paths.py
    test_worktree_manager.py
```

No adapter module exists yet. The `models.py` contains runner-specific dataclasses (ApplyPatch, ValidationResult, etc.) but nothing adapter-related.

## Implementation Location Decision

**Decision: Two files in the existing runner service.**

### Implementation file

1. **`services/runner/src/runner/noop_adapter.py`** — the no-op runner adapter module.

### Test file

2. **`services/runner/tests/test_noop_adapter.py`** — focused tests.

**Rationale:**
- The runner service is the natural home for runner adapters.
- No `__init__.py` changes needed — the module is importable via `from runner.noop_adapter import run_noop_execution`.
- No changes to any existing runner files.
- No new packages or services.

**Not modified:**
- `services/task_intake/**` — no changes.
- `services/conductor/**`, `services/core/**`, `services/domain_adapters/**` — no changes.
- `schemas/**`, `docs/**` — no changes.
- PR 0068 schemas/docs — no changes.
- `pyproject.toml` — no dependency changes.

## Public Function/API Decision

```python
def run_noop_execution(execution_request: dict) -> dict:
    """Execute a deterministic no-op runner adapter response.

    Accepts a RunnerExecutionRequest dict (as defined in
    ``schemas/runner-execution-request.schema.yml``) and returns a
    deterministic RunnerExecutionResult dict without performing any
    real execution.

    Parameters
    ----------
    execution_request
        The execution request dict.

    Returns
    -------
    dict
        A deterministic execution result dict conforming to
        ``schemas/runner-execution-result.schema.yml``.
    """
```

- Accepts and returns plain dicts.
- No new dependencies.
- Pure function — no global state, no filesystem, no network, no subprocess.
- No classes — functions are sufficient for this scope.

## Behavior Requirements

### Case 1: Valid request → completed

A well-formed request with supported `requested_adapter` (e.g., `"noop"`, `"noop-v1"`) and supported `execution_mode` returns a `completed` result with evidence.

### Case 2: Approval required → blocked / requires_review

If `request.approval` indicates approval is pending (e.g., `{"required": true, "approved": false}`), return `blocked` status.

If `request.approval` indicates review-after-execution (e.g., `{"required": true, "after_execution": true}`), return `completed` status with `review_required: true` and `"status": "requires_review"`.

### Case 3: Invalid request → failed

Missing required fields return `failed` status with structured error records.

### Case 4: Unsupported adapter or mode → failed

If `requested_adapter` doesn't include `"noop"`, return `failed` with error indicating unsupported adapter.
If `execution_mode` is not `"dry_run"` or `"preview"`, return `failed` (the no-op adapter cannot execute — it can only dry-run or preview).

### Case 5: Determinism

Repeated calls with the same input return equal output dicts.

### Case 6: Evidence

Output includes evidence that no real execution happened.

## Input Contract Expectations

Minimum required fields based on PR 0068 schema:

- `execution_request_id` — non-empty string
- `run_id` — non-empty string
- `task_intake_id` — non-empty string
- `context_preview_id` — non-empty string
- `requested_adapter` — non-empty string
- `execution_mode` — non-empty string
- `inputs` — dict or empty dict
- `constraints` — list or empty list

Optional fields: `expected_outputs`, `metadata`, `approval`.

The adapter does NOT require absolute paths, Docker references, GitHub references, or provider-specific fields.

## Output Contract Expectations

All fields from PR 0068 `RunnerExecutionResult`:

- `execution_result_id` — deterministic, derived from request id: `f"{execution_request_id}-result"`
- `execution_request_id` — from the request
- `run_id` — from the request
- `status` — `"completed"`, `"blocked"`, `"requires_review"`, or `"failed"`
- `adapter` — `"noop-v1"`
- `artifacts` — empty list (no artifacts produced)
- `evidence` — list with one or more evidence records
- `errors` — list of error records (only present for `failed` status)
- `warnings` — empty list for success, may include warnings for edge cases
- `review_required` — True if approval indicates review-after-execution
- `next` — `"/runs/<run_id>/status"`

Timestamps (`started`, `completed`) are omitted — the contract marks them as optional and adapter-provided. For a no-op adapter that does nothing, timestamps are unnecessary.

## Status Semantics

| Condition | Status | review_required |
|---|---|---|
| Valid request, no approval | `completed` | False |
| Valid request, approval pending | `blocked` | False |
| Valid request, review-after-execution | `requires_review` | True |
| Missing required fields | `failed` | False |
| Unsupported adapter | `failed` | False |
| Unsupported mode | `failed` | False |

## Evidence Requirements

Each evidence record:

```python
{
    "evidence_id": "ev-noop-001",
    "evidence_kind": "execution_note",
    "summary": f"No-op adapter ({adapter_id}) completed. No real execution was performed. "
               "No Docker, no subprocess, no shell, no network, no filesystem writes, "
               "no model/provider calls, no agent execution.",
    "status": "passed",
}
```

The evidence explicitly states what was NOT done. This makes the adapter's safety guarantees auditable.

## Artifact Requirements

`artifacts: []` — no runtime artifacts are produced. The no-op adapter has nothing to report.

## Test Plan

**Test file:** `services/runner/tests/test_noop_adapter.py`

**Test cases:**

1. `test_valid_request_returns_completed` — well-formed request returns `completed` status.
2. `test_valid_request_has_deterministic_id` — `execution_result_id` derived from request id.
3. `test_valid_request_has_evidence` — evidence list is non-empty, states no execution.
4. `test_valid_request_has_empty_artifacts` — artifacts list is empty.
5. `test_valid_request_json_serializable` — output passes `json.dumps(sort_keys=True)`.
6. `test_deterministic` — repeated calls with same input return equal output.
7. `test_approval_pending_returns_blocked` — `approval.required: true, approved: false` returns `blocked`.
8. `test_approval_review_returns_requires_review` — `approval.after_execution: true` returns `requires_review` with `review_required: true`.
9. `test_missing_execution_request_id_returns_failed` — missing required field returns `failed`.
10. `test_missing_run_id_returns_failed` — missing required field returns `failed`.
11. `test_missing_task_intake_id_returns_failed` — missing required field returns `failed`.
12. `test_unsupported_adapter_returns_failed` — `requested_adapter: "docker-coder-v1"` returns `failed`.
13. `test_unsupported_execution_mode_returns_failed` — `execution_mode: "execute"` returns `failed`.
14. `test_dry_run_mode_succeeds` — `execution_mode: "dry_run"` returns `completed`.
15. `test_preview_mode_succeeds` — `execution_mode: "preview"` returns `completed`.
16. `test_no_side_effects` — module does not import subprocess, socket, os.system, etc.

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_noop_adapter.py -v
python -m compileall -f services/runner/src
grep -R -n "subprocess|os\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" services/runner/src/runner/noop_adapter.py services/runner/tests/test_noop_adapter.py || true
grep -R -n "\$(" services/runner/src/runner/noop_adapter.py services/runner/tests/test_noop_adapter.py || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/noop_adapter.py`
- `services/runner/tests/test_noop_adapter.py`

Precommit review may later write only:
- `.project-memory/pr/0069-minimal-noop-runner-adapter/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0069-minimal-noop-runner-adapter/PLAN.md` (planner only)
- `.project-memory/pr/0069-minimal-noop-runner-adapter/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/**`
- `services/conductor/**`
- `services/domain_adapters/**`
- `services/core/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.grace/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `services/runner/pyproject.toml`
- `services/runner/src/runner/__init__.py`
- `services/runner/src/runner/__main__.py`
- `services/runner/src/runner/models.py`
- `services/runner/tests/__init__.py`
- `services/runner/tests/test_runner_models.py`

## Non-goals

- no docs-only PR
- no schemas-only PR
- no real execution
- no runner adapter registry/dispatcher
- no task-intake to runner connection
- no HTTP endpoint for the adapter
- no Docker adapter
- no Docker files/commands
- no subprocess/shell execution
- no network/filesystem writes at runtime
- no repository scanner
- no artifact collection
- no queue/persistence/database
- no model calls/provider integration
- no approval UI/notifications
- no dependency/build changes
- no task-intake or mock-loop behavior changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only or schemas-only outcome → stop
- no executable `.py` implementation file selected → stop
- no test file selected → stop
- about to implement real runner execution → stop
- about to implement registry/dispatcher → stop
- about to connect mock-loop/task-intake to runner → stop
- about to add HTTP endpoint → stop
- about to implement Docker adapter → stop
- about to add Docker files → stop
- about to call subprocess/shell → stop
- about to use network libraries → stop
- about to write files at runtime → stop
- about to add persistence/queue/database → stop
- about to add dependencies → stop
- about to modify task-intake code → stop
- about to modify schemas/docs as primary output → stop
- about to modify existing runner files → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the no-op adapter support the `"execute"` mode?** **Decision:** No. The no-op adapter cannot execute anything. It supports `"dry_run"` and `"preview"` only. Requesting `"execute"` returns a `failed` status with an error explaining that the no-op adapter cannot execute. A real adapter would be needed for `"execute"`.

2. **Should the adapter use its own exception type or return structured error dicts?** **Decision:** Return structured error dicts. The contract defines an error shape. Using Python exceptions would require the caller to catch them. Returning structured errors in the result dict keeps the adapter pure and composable: callers check `result["status"]` rather than using try/except.

3. **Should `execution_result_id` be a deterministic derivation from `execution_request_id` or use the SHA-256 pattern?** **Decision:** Simple deterministic derivation: `f"{execution_request_id}-result"`. This is traceable and avoids unnecessary crypto computation. If the request id is `"er-001"`, the result id is `"er-001-result"`.

## Decisions Made

### selected_strategy

Executable Python code + tests. Not docs-only, not schemas-only.

### implementation_files

```
services/runner/src/runner/noop_adapter.py
```

### test_files

```
services/runner/tests/test_noop_adapter.py
```

### public_function

```python
run_noop_execution(execution_request: dict) -> dict
```

### request_minimum_shape

Required: `execution_request_id`, `run_id`, `task_intake_id`, `context_preview_id`, `requested_adapter`, `execution_mode`, `inputs`, `constraints`.
Optional: `expected_outputs`, `metadata`, `approval`.

### result_shape

All `RunnerExecutionResult` fields from PR 0068:
`execution_result_id`, `execution_request_id`, `run_id`, `status`, `adapter` (`"noop-v1"`), `artifacts` (`[]`), `evidence` (list), `errors` (list, only for failed), `warnings` (list), `review_required` (bool), `next` (str).
No timestamps.

### status_semantics

completed → valid request (dry_run/preview mode, no approval block).
blocked → approval pending.
requires_review → approval review-after-execution.
failed → missing fields or unsupported adapter/mode.

### evidence_shape

One evidence record per result with `evidence_id`, `evidence_kind` (`"execution_note"`), `summary` (states no execution), `status` (`"passed"`).

### artifact_behavior

`artifacts: []` — no runtime artifacts. Metadata-only.

### approval_behavior

`request.approval` controls status: `{"required": true, "approved": false}` → `blocked`. `{"required": true, "after_execution": true}` → `requires_review` + `review_required: true`. No approval dict → treat as not required.

### deterministic_id_strategy

`execution_result_id = f"{execution_request_id}-result"`. Simple, traceable, deterministic.

### validation_strategy

16 focused test cases. Side-effect import check. JSON serializability. Determinism across calls. Forbidden pattern grep for subprocess/Docker/network.

### next_pr_notes

The next PR should connect the mock loop to the no-op adapter through the task-intake service, so `POST /mock-loop` can produce a no-op execution result instead of a mock status. Alternatively, the next PR could add a second adapter type (e.g., a local-process scaffold) that does slightly more than no-op.

---

PLAN written: yes
