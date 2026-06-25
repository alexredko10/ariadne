# PR 0066 — Minimal Mock App Loop Surface Plan

## Goal

Plan the first minimal end-to-end mock application loop surface.

The flow should accept a raw task request and return a deterministic combined response containing:

1. normalized task intake
2. context preview
3. mock run
4. mock run status
5. evidence that this was a mock deterministic loop

The loop should compose existing PR 0063, 0064, and 0065 behavior.

## Architectural Thesis

0063 introduced task intake normalization.
0064 introduced context preview.
0065 introduced mock run creation and status.
0066 should make these slices usable as one coherent application-facing loop.

This is the first working product-loop pass.

It remains mock-only and substrate-safe:
- no real runner execution
- no Docker-agent execution
- no persistence
- no queue
- no model calls
- no GitHub automation

Docker agents remain future execution adapters after the mock loop is complete.

## Context Snapshot

- **current HEAD sha**: `336bc584cc7ac0975e4619d6be71c6db8d3c160f`
- **current branch**: `0066-minimal-mock-app-loop-surface`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `336bc58` (main after PR 0065 merge — no skew relative to main)
- **index_version**: `"0.32"` (from `.project-memory/context-bundles/contracts.yml` — PR 0065 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0065, no pending changes
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
- `.project-memory/pr/0065-runs-mock-status/PLAN.md`
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/task_intake/src/task_intake/runs.py`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_normalize.py`
- `services/task_intake/tests/test_context_preview.py`
- `services/task_intake/tests/test_runs.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`

## Existing Product Loop Snapshot

### Current endpoints wired in `server.py`

| Route | Module | PR |
|---|---|---|
| `GET /health` | `doctor.py` | Sprint 0 |
| `POST /submit` | `app.py` | Sprint 0 |
| `POST /task-intake/submit` | `app.py` | Sprint 0 |
| `POST /task-intake/normalize` | `normalize.py` | PR 0063 |
| `POST /context/preview` | `context_preview.py` | PR 0064 |
| `POST /runs` | `runs.py` | PR 0065 |

### Individual slice interfaces

**`normalize_task_intake(raw: dict) -> dict`**
- Accepts: `raw_task` (required), `source`, `metadata`, `constraints`, `requested_output` (optional)
- Returns: `ok`, `task_intake_id`, `normalized_task`, `validation`, `next` → `/context/preview`

**`generate_context_preview(raw: dict) -> dict`**
- Accepts: `task_intake` (required), `include_sections`, `preview_options` (optional)
- Returns: `ok`, `context_preview_id`, `task_intake_id`, `preview`, `validation`, `next` → `/runs`

**`create_mock_run(raw: dict) -> dict`**
- Accepts: `task_intake` (required), `context_preview` (required), `run_options` (optional)
- Returns: `ok`, `run_id`, `status`, `task_intake_id`, `context_preview_id`, `run`, `validation`, `next` → `/runs/<run_id>/status`

## Implementation Location Decision

**Decision: One new module, one route in existing server.py.**

### New module

1. **`services/task_intake/src/task_intake/mock_loop.py`** — pure deterministic mock loop composition function.

### Modified file

2. **`services/task_intake/src/task_intake/server.py`** — add route for `POST /mock-loop`.

### New test file

3. **`services/task_intake/tests/test_mock_loop.py`** — focused tests.

**Rationale:** The mock loop module composes the three existing functions. It doesn't modify them — it calls them sequentially. The route follows the same pattern as all other routes in server.py.

**Not modified:**
- `normalize.py`, `context_preview.py`, `runs.py` — untouched. The loop imports and calls them.
- `pyproject.toml` — no dependency changes.
- `app.py`, `models.py`, `normalizer.py` — untouched.
- `services/conductor/`, `services/core/`, `services/runner/`, `services/domain_adapters/` — untouched.
- `schemas/`, `.project-memory/` — untouched.

## Mock Loop Request Contract

```json
{
  "raw_task": "Implement JWT authentication middleware",
  "source": "manual",
  "metadata": {"requester": "demo"},
  "constraints": ["no_git_mutation"],
  "requested_output": "plan",
  "include_sections": ["task", "scope", "risks"],
  "preview_options": {"format": "compact"},
  "run_options": {"priority": "normal"}
}
```

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `raw_task` | string | Yes | Raw task description text |
| `source` | string | No | Source (default `"manual"`) |
| `metadata` | dict | No | Request metadata |
| `constraints` | list[string] | No | Task constraints |
| `requested_output` | string | No | Expected output (default `"plan"`) |
| `include_sections` | list[string] | No | Context sections to include (default: `["task", "scope", "risks"]`) |
| `preview_options` | dict | No | Context preview options |
| `run_options` | dict | No | Run creation options |

This is the union of the individual slice request fields, flattened into a single request.

## Mock Loop Response Contract

```json
{
  "ok": true,
  "loop_id": "loop_a1b2c3d4e5f6",
  "status": {
    "state": "completed_mock_loop",
    "phase": "mock_loop_complete",
    "message": "Mock application loop completed. No real execution was performed.",
    "is_terminal": true,
    "progress": 100,
    "updated_by": "task-intake-api"
  },
  "steps": {
    "normalize": {
      "ok": true,
      "task_intake_id": "task_e5b71a2f3c4d",
      "normalized_task": { ... },
      "validation": { ... }
    },
    "context_preview": {
      "ok": true,
      "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
      "preview": { ... },
      "validation": { ... }
    },
    "run": {
      "ok": true,
      "run_id": "run_a1b2c3d4e5f6",
      "status": { ... },
      "run": { ... },
      "validation": { ... }
    }
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": ["No real execution was performed. This is a mock application loop."]
  },
  "evidence": {
    "mock_loop": true,
    "execution_performed": false,
    "runner_adapter_required": true,
    "step_count": 3
  },
  "next": "/runs/<run_id>/status"
}
```

## Composition Strategy

The `run_mock_loop(raw: dict) -> dict` function composes the three existing modules:

```python
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
from task_intake.runs import create_mock_run


def run_mock_loop(raw: dict) -> dict:
    # 1. Normalize
    normalize_input = {
        "raw_task": raw.get("raw_task"),
        "source": raw.get("source", "manual"),
        "metadata": raw.get("metadata", {}),
        "constraints": raw.get("constraints", []),
        "requested_output": raw.get("requested_output", "plan"),
    }
    normalize_result = normalize_task_intake(normalize_input)
    if not normalize_result.get("ok"):
        return _loop_failure("normalize", normalize_result)

    # 2. Context preview
    preview_input = {
        "task_intake": normalize_result.get("normalized_task", {}),
        "include_sections": raw.get("include_sections"),
        "preview_options": raw.get("preview_options"),
    }
    preview_result = generate_context_preview(preview_input)
    if not preview_result.get("ok"):
        return _loop_failure("context_preview", preview_result)

    # 3. Mock run
    run_input = {
        "task_intake": normalize_result.get("normalized_task", {}),
        "context_preview": preview_result,
        "run_options": raw.get("run_options", {}),
    }
    run_result = create_mock_run(run_input)
    if not run_result.get("ok"):
        return _loop_failure("run", run_result)

    # 4. Compose final response
    return _loop_success(normalize_result, preview_result, run_result)
```

**Key rules:**
- The loop does NOT duplicate validation logic from the individual slices.
- Each slice validates its own input.
- If any slice returns `ok: false`, the loop returns `ok: false` with step evidence and the validation errors from the failing step.
- The loop uses the existing slice outputs directly (no re-serialization, no transformation beyond selecting the relevant sub-fields).

## Loop Status Shape

```python
{
    "state": str,         # "completed_mock_loop" or "validation_failed"
    "phase": str,         # "mock_loop_complete" or failing step name
    "message": str,       # Human-readable status
    "is_terminal": bool,  # True for both success and failure
    "progress": int,      # 100 for success, step_progress for failure
    "updated_by": str,    # "task-intake-api"
}
```

**Status values:**
- `completed_mock_loop` — all three steps succeeded.
- `validation_failed` — one or more steps failed validation.

## ID Strategy

`loop_<first 12 hex chars of sha256(raw_task)>` — deterministic, stdlib-only SHA-256, matching the pattern used by normalize, context_preview, and runs.

## Endpoint Strategy

**Route:** `POST /mock-loop` in `server.py`.

**Pattern:** Same ASGI pattern as all other routes.

**Behavior:**
1. Read body via ASGI `receive()` events.
2. Parse JSON.
3. Call `run_mock_loop(data)` from `mock_loop.py`.
4. If `ok: false`, return 400.
5. If `ok: true`, return 200.

## Docker Agent Boundary

- Docker agents are future execution adapters.
- PR 0066 does not introduce Docker behavior.
- PR 0066 composes the mock app loop only.
- The `evidence` field explicitly states `execution_performed: false` and `runner_adapter_required: true`.
- No `services/runner/`, `services/conductor/`, or `services/core/` imports.

## Validation Behavior

| Condition | Response |
|---|---|
| Missing `raw_task` | `ok: false`, 400 (from normalize step) |
| Empty `raw_task` | `ok: false`, 400 (from normalize step) |
| Rich valid input | `ok: true`, 200 with all three step outputs |
| The loop does not add its own validation — it delegates to each slice. |

## Tests

### Test module: `services/task_intake/tests/test_mock_loop.py`

```python
class TestMockLoop:
    # Endpoint behavior
    def test_valid_loop_returns_200(self): ...
    def test_valid_loop_has_ok_true(self): ...
    def test_valid_loop_has_loop_id(self): ...
    def test_valid_loop_has_three_steps(self): ...
    def test_valid_loop_has_status(self): ...

    # Step presence
    def test_loop_has_normalize_step(self): ...
    def test_loop_has_context_preview_step(self): ...
    def test_loop_has_run_step(self): ...

    # Status
    def test_loop_status_completed_mock_loop(self): ...
    def test_loop_status_is_terminal(self): ...
    def test_loop_status_progress_is_100(self): ...

    # Validation failure at normalize step
    def test_missing_raw_task_fails_at_normalize(self): ...

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
- Existing `test_runs.py` tests pass.
- Existing `test_task_intake_http.py` tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/task_intake/src/task_intake/mock_loop.py services/task_intake/tests/test_mock_loop.py services/task_intake/src/task_intake/server.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/task_intake/src/task_intake/mock_loop.py services/task_intake/tests/test_mock_loop.py services/task_intake/src/task_intake/server.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/mock_loop.py` (new)
- `services/task_intake/tests/test_mock_loop.py` (new)
- `services/task_intake/src/task_intake/server.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0066-minimal-mock-app-loop-surface/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0066-minimal-mock-app-loop-surface/PLAN.md` (planner only)
- `.project-memory/pr/0066-minimal-mock-app-loop-surface/reviews/plan-review.yml` (plan-review only)
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
- `services/task_intake/src/task_intake/runs.py`
- `services/task_intake/tests/test_normalize.py`
- `services/task_intake/tests/test_context_preview.py`
- `services/task_intake/tests/test_runs.py`
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
- no authentication
- no UI
- no GitHub integration
- no dependency changes
- no schema changes
- no changes to normalize, context_preview, or runs modules
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
- about to modify normalize, context_preview, or runs modules → stop
- about to modify runtime/core/runner/domain adapters → stop
- about to modify conductor → stop
- about to modify schemas → stop
- about to modify project-memory registry/templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the mock loop be a separate module or a thin route handler that calls the three slices?** **Decision:** Separate module (`mock_loop.py`). The composition logic is non-trivial (step ordering, failure aggregation, final status computation, loop ID generation). A separate module keeps the route handler thin and testable independently of the ASGI server.

2. **Should each step's full response be preserved in the loop output or summarized?** **Decision:** Preserved as `steps.normalize`, `steps.context_preview`, `steps.run`. This gives callers full access to each step's response for debugging and integration. The loop output is already deterministic, so the size is predictable.

3. **Should the loop ID be derived from the raw_task?** **Decision:** Yes — `loop_<first 12 hex chars of sha256(raw_task)>`. Consistent with the ID strategy used by all three slices. Makes the loop ID traceable back to the input.

## Decisions Made

### implementation_files

```
services/task_intake/src/task_intake/mock_loop.py (new)
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_mock_loop.py (new)
```

### optional_route_files

None — route added to existing server.py.

### request_shape

```
{
    "raw_task": str,              # required
    "source": str,                # optional, default "manual"
    "metadata": dict,             # optional
    "constraints": list[str],     # optional
    "requested_output": str,      # optional, default "plan"
    "include_sections": list[str],# optional
    "preview_options": dict,      # optional
    "run_options": dict,          # optional
}
```

### response_shape

```
{
    "ok": bool,
    "loop_id": str,
    "status": dict with 6 fields,
    "steps": {
        "normalize": dict,        # full normalize output
        "context_preview": dict,  # full context preview output
        "run": dict,              # full run output
    },
    "validation": dict,
    "evidence": dict with 4 fields,
    "next": str,
}
```

### loop_status_shape

```
{
    "state": str,         # "completed_mock_loop" | "validation_failed"
    "phase": str,         # "mock_loop_complete" | failing step name
    "message": str,       # Human-readable
    "is_terminal": bool,  # True
    "progress": int,      # 100 | step index * 33
    "updated_by": str,    # "task-intake-api"
}
```

### loop_status_values

- `completed_mock_loop` — all steps succeeded.
- `validation_failed` — one or more steps failed.

### id_strategy

`loop_<first 12 hex chars of sha256(raw_task)>`.

### validation_rules

- Delegates to each slice. No loop-level validation.
- Missing `raw_task` fails at normalize step.
- Empty `raw_task` fails at normalize step.
- All downstream failures propagate deterministically.

### endpoint_strategy

Route `POST /mock-loop` in server.py. Same ASGI pattern. 400 for invalid, 200 for valid.

### composition_strategy

Call normalize → context_preview → runs in sequence. If any fails, return failure with failing step's validation errors. On success, compose all three step outputs. No duplicate validation.

### docker_agent_boundary

No Docker. `evidence.execution_performed: false`, `evidence.runner_adapter_required: true`.

### deterministic_policy

- Loop ID from SHA-256. All content from deterministic slice outputs.
- No random ids, no timestamps, no current time.
- No absolute paths, no machine-specific values.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused mock loop composition tests.
Compatibility tests for individual slices.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes
