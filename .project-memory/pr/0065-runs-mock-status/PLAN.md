# PR 0065 — Runs Mock + Status Object Plan

## Goal

Plan the third visible application-loop endpoint:

```
POST /runs
```

The endpoint should accept normalized task intake and context preview data and return a deterministic mock run object with a simple status object.

This is a mock run creation/status slice, not real execution.

## Architectural Thesis

0063 introduced deterministic task intake normalization.

0064 introduced deterministic context preview.

0065 should let a caller create a mock run from those two prior outputs and receive a stable run status object.

Application loop:

```
raw task request
→ normalized task intake
→ context preview
→ mock run creation
→ run status object
```

This PR should not execute runs, call models, invoke Docker agents, use queues, or persist state.

Docker agents remain future runner adapters. They must not be introduced in this PR.

## Context Snapshot

- **current HEAD sha**: `5b0c860c35e0bfd6dd3e15b17d5f524b2e45c42e`
- **current branch**: `0065-runs-mock-status`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `5b0c860` (main after PR 0064 merge — no skew relative to main)
- **index_version**: `"0.31"` (from `.project-memory/context-bundles/contracts.yml` — PR 0064 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0064, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/pr/0063-task-intake-normalize-mock/PLAN.md`
- `.project-memory/pr/0064-context-preview-mock/PLAN.md`
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_normalize.py`
- `services/task_intake/tests/test_context_preview.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`

## Existing Application Surface Snapshot

### Current product loop endpoints

All wired in `services/task_intake/src/task_intake/server.py`:

| Route | Module | Purpose |
|---|---|---|
| `GET /health` | `doctor.py` | Health check |
| `POST /submit` | `app.py` | Submit task (existing Sprint 0) |
| `POST /task-intake/submit` | `app.py` | Submit task alias |
| `POST /task-intake/normalize` | `normalize.py` | Normalize raw task (PR 0063) |
| `POST /context/preview` | `context_preview.py` | Preview context (PR 0064) |

### Request/response flow patterns

- All new endpoints follow: read body → parse JSON → call pure function → check `"ok"` → respond 200 or 400.
- The `normalize.py` output has `normalized_task` with `task_intake_id`.
- The `context_preview.py` output has `preview` with `context_sections`.
- Both outputs include `validation` and `next`.

### Current server route registration pattern

```python
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
```

Each route follows the same ASGI pattern with `body_bytes`, `json.loads`, `_send_json`.

## Implementation Location Decision

**Decision: Add runs module to task_intake, route in server.py.**

### New module

1. **`services/task_intake/src/task_intake/runs.py`** — pure deterministic mock run creation function.

### Modified file

2. **`services/task_intake/src/task_intake/server.py`** — add route for `POST /runs`.

### New test file

3. **`services/task_intake/tests/test_runs.py`** — focused tests.

**Rationale:** Same pattern as PR 0063 and 0064. The product loop (normalize → preview → runs) lives in task_intake. The runs mock is self-contained — no imports from conductor, runner, or core.

### Not modified

- `normalize.py`, `context_preview.py` — untouched.
- `pyproject.toml` — no dependency changes.
- `app.py`, `models.py`, `normalizer.py` — untouched.
- `services/conductor/`, `services/core/`, `services/runner/`, `services/domain_adapters/` — untouched.
- `schemas/`, `.project-memory/` — untouched.

## Runs Request Contract

```json
{
  "task_intake": {
    "raw_task": "Implement JWT authentication middleware",
    "task_goal": "Implement JWT authentication middleware",
    "source": "manual",
    "metadata": {"requester": "demo"},
    "constraints": ["no_git_mutation"],
    "requested_output": "plan",
    "inferred_mode": "feature",
    "inferred_domains": ["auth"],
    "warnings": []
  },
  "context_preview": {
    "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
    "preview": {
      "task_summary": "Implement JWT authentication middleware",
      "inferred_mode": "feature",
      "inferred_domains": ["auth"],
      "context_sections": { ... }
    }
  },
  "run_options": {
    "priority": "normal",
    "target_agent": "worker_coder"
  },
  "metadata": {
    "created_by": "demo"
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `task_intake` | dict | Yes | Normalized task intake structure (from `/task-intake/normalize`) |
| `context_preview` | dict | Yes | Context preview structure (from `/context/preview`) |
| `run_options` | dict | No | Run creation options |
| `metadata` | dict | No | Request metadata |

## Runs Response Contract

```json
{
  "ok": true,
  "run_id": "run_a1b2c3d4e5f6",
  "status": {
    "state": "created",
    "phase": "mock_run",
    "message": "Mock run created — no execution was performed. Submit to runner adapter for real execution.",
    "is_terminal": false,
    "progress": 0,
    "updated_by": "task-intake-api"
  },
  "task_intake_id": "task_e5b71a2f3c4d",
  "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
  "run": {
    "run_id": "run_a1b2c3d4e5f6",
    "task_intake_id": "task_e5b71a2f3c4d",
    "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
    "requested_mode": "feature",
    "constraints": ["no_git_mutation"],
    "requested_output": "plan",
    "run_options": {
      "priority": "normal",
      "target_agent": "worker_coder"
    },
    "execution_plan_placeholder": {
      "note": "Real execution plan would be generated by conductor",
      "suggested_next_phase": "orchestrate"
    },
    "evidence": {
      "mock_run": true,
      "execution_performed": false,
      "runner_adapter_required": true
    }
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": ["No real execution was performed. This is a mock run object."]
  },
  "next": "/runs/<run_id>/status"
}
```

## Status Object Contract

**Fields:**

| Field | Type | Description |
|---|---|---|
| `state` | string | Run state (`"created"` for mock, real statuses added by runner adapter) |
| `phase` | string | Current phase (`"mock_run"` for mock) |
| `message` | string | Human-readable status message |
| `is_terminal` | bool | Whether this state is terminal |
| `progress` | int | Progress percentage (0–100) |
| `updated_by` | string | Who last updated the status |

**Status values (mock only):**

| State | Description |
|---|---|
| `created` | Run object created in mock state |
| `validation_failed` | Input validation failed |

**Status values NOT included:** `running`, `paused`, `completed`, `failed`, `cancelled`, `blocked` — these are real execution lifecycle statuses that belong to the runner adapter, not the mock loop.

## ID Strategy

`run_<first 12 hex chars of sha256(task_goal + context_preview_id)>` — deterministic, stdlib-only SHA-256. Reuses the same `hashlib.sha256` pattern as `normalize.py` and `context_preview.py`.

## Validation Behavior

| Input condition | Response |
|---|---|
| Missing `task_intake` | `ok: false`, 400 |
| `task_intake` not a dict | `ok: false`, 400 |
| Missing `task_goal` in `task_intake` | `ok: false`, 400 |
| Missing `context_preview` | `ok: false`, 400 |
| `context_preview` not a dict | `ok: false`, 400 |
| Missing `context_preview_id` in `context_preview` | `ok: false`, 400 (cross-validation) |
| `task_intake_id` in `task_intake` doesn't match `task_intake_id` referenced in `context_preview` | `ok: false`, 400 (mismatch) |
| `run_options` not a dict if provided | `ok: false`, 400 |
| Valid input | `ok: true`, 200 |

## Endpoint Strategy

**Route:** `POST /runs` in `server.py`.

**Pattern:** Same ASGI pattern as `/task-intake/normalize` and `/context/preview`.

**Behavior:**
1. Read body via ASGI `receive()` events.
2. Parse JSON.
3. Call `create_mock_run(data)` from the new `runs.py`.
4. If `ok: false`, return 400.
5. If `ok: true`, return 200.

## Docker Agent Boundary

- Docker agents are future execution adapters, not part of this PR.
- PR 0065 creates only a mock run/status object that could later be handed to a runner adapter.
- The `evidence` field explicitly states `execution_performed: false` and `runner_adapter_required: true`.
- No Docker, no subprocess, no runner invocation.
- No `services/runner/` or `services/core/` or `services/conductor/` imports.

## Tests

### Test module: `services/task_intake/tests/test_runs.py`

```python
class TestRunsEndpoint:
    # Endpoint behavior
    def test_valid_request_returns_200(self): ...
    def test_valid_request_has_ok_true(self): ...
    def test_valid_request_has_run_id(self): ...
    def test_valid_request_has_status(self): ...
    def test_valid_request_has_next(self): ...

    # Status object
    def test_status_state_is_created(self): ...
    def test_status_is_not_terminal(self): ...
    def test_status_progress_is_zero(self): ...
    def test_status_message_indicates_mock(self): ...

    # Run object
    def test_run_has_task_intake_id(self): ...
    def test_run_has_context_preview_id(self): ...
    def test_run_has_execution_plan_placeholder(self): ...
    def test_run_evidence_indicates_mock(self): ...

    # Validation
    def test_missing_task_intake_returns_400(self): ...
    def test_missing_context_preview_returns_400(self): ...
    def test_missing_task_goal_returns_400(self): ...
    def test_non_dict_task_intake_returns_400(self): ...
    def test_mismatched_ids_returns_400(self): ...

    # Determinism
    def test_deterministic(self): ...
    def test_json_serializable(self): ...

    # Safety
    def test_no_forbidden_source_strings(self): ...
    def test_no_old_names(self): ...
```

### Compatibility

- Existing `test_normalize.py` tests pass.
- Existing `test_context_preview.py` tests pass.
- Existing `test_task_intake_http.py` tests pass.
- Existing `test_task_intake.py` tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/task_intake/src/task_intake/runs.py services/task_intake/tests/test_runs.py services/task_intake/src/task_intake/server.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/task_intake/src/task_intake/runs.py services/task_intake/tests/test_runs.py services/task_intake/src/task_intake/server.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/runs.py` (new)
- `services/task_intake/tests/test_runs.py` (new)
- `services/task_intake/src/task_intake/server.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0065-runs-mock-status/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0065-runs-mock-status/PLAN.md` (planner only)
- `.project-memory/pr/0065-runs-mock-status/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `services/core/**`
- `services/conductor/**`
- `services/runner/**`
- `services/domain_adapters/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `services/task_intake/pyproject.toml`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/models.py`
- `services/task_intake/src/task_intake/normalizer.py`
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/task_intake/tests/test_normalize.py`
- `services/task_intake/tests/test_context_preview.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `services/task_intake/tests/test_task_intake.py`
- `package.json`
- `Makefile`
- `.project-memory/anchors.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/templates/**`
- `.grace/**`

## Non-goals

- no model calls
- no provider integration
- no repository scanner
- no repository graph computation
- no RAG/vector search
- no cache backend
- no distributed cache
- no database
- no persistence
- no queue
- no real run execution
- no runner execution
- no Docker-agent execution
- no Docker behavior
- no subprocess
- no authentication
- no UI
- no full API surface
- no GitHub integration
- no dependency changes
- no schema changes
- no changes to normalize or context_preview modules
- no imports from conductor, runner, or core
- no project-memory runtime writes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to add dependency/build config → stop
- about to add new web framework → stop
- about to add database/persistence → stop
- about to add queue behavior → stop
- about to add model/provider behavior → stop
- about to inspect Git/repository state → stop
- about to scan repository files → stop
- about to execute runs → stop
- about to implement real runner behavior → stop
- about to implement Docker-agent execution → stop
- about to implement full API surface → stop
- about to modify runtime/core/runner/domain adapters → stop
- about to modify conductor → stop
- about to modify normalize or context_preview → stop
- about to modify schemas → stop
- about to modify project-memory registry/templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the mock run status include real execution lifecycle statuses like `running` or `completed`?** **Decision:** No. The mock status is `"created"`. Real execution statuses belong to the runner adapter. Including them in the mock would suggest the API performs execution, which it explicitly does not. The `evidence.execution_performed: false` field makes this unambiguous.

2. **Should the endpoint cross-validate `task_intake_id` between `task_intake` and `context_preview`?** **Decision:** Yes. If `task_intake` has a `task_intake_id` and `context_preview` has a `task_intake_id`, they must match. This ensures the caller is creating a run from a consistent pipeline state.

3. **Should the status object include `updated_by`?** **Decision:** Yes — set to `"task-intake-api"` for the mock. This establishes the provenance pattern for future runner adapter status updates.

## Decisions Made

### implementation_files

```
services/task_intake/src/task_intake/runs.py (new)
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_runs.py (new)
```

### optional_route_files

None — route added to existing server.py.

### request_shape

```
{
    "task_intake": dict,       # required, normalized task intake
    "context_preview": dict,   # required, context preview output
    "run_options": dict,       # optional
    "metadata": dict,          # optional
}
```

### response_shape

```
{
    "ok": bool,
    "run_id": str,
    "status": dict with 6 fields,
    "task_intake_id": str,
    "context_preview_id": str,
    "run": dict with 9 fields,
    "validation": dict,
    "next": str,
}
```

### status_shape

```
{
    "state": str,
    "phase": str,
    "message": str,
    "is_terminal": bool,
    "progress": int,
    "updated_by": str,
}
```

### status_values

Mock: `"created"`, `"validation_failed"`.
**Not included:** `running`, `paused`, `completed`, `failed`, `cancelled`, `blocked`.

### id_strategy

`run_<first 12 hex chars of sha256(task_goal + context_preview_id)>`.

### validation_rules

- Missing/non-dict task_intake → 400.
- Missing `task_goal` in task_intake → 400.
- Missing/non-dict context_preview → 400.
- Missing `context_preview_id` in context_preview → 400.
- Mismatched task_intake_id → 400.
- Non-dict run_options → 400.
- Deterministic across calls.

### endpoint_strategy

Route `POST /runs` in server.py. Same ASGI pattern. 400 for invalid, 200 for valid.

### docker_agent_boundary

No Docker, no subprocess, no runner. Evidence field explicitly states `execution_performed: false`, `runner_adapter_required: true`.

### deterministic_policy

- Run ID from SHA-256 (deterministic).
- All content from explicit request fields.
- No random ids, no timestamps, no current time.
- No absolute paths, no machine-specific values.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused endpoint tests via ASGI test harness.
Compatibility tests for existing task_intake tests.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes
