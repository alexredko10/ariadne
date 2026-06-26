# PR 0071 — Mock Run to Runner Dispatcher Handoff Plan

## Goal

Plan executable behavior for connecting the existing mock run / mock loop flow to the runner dispatcher.

This PR must add code and tests.
This PR must not be docs-only.
This PR must not be schemas-only.

The handoff must build an execution request from existing mock app/run data, call the runner dispatcher, and return a deterministic combined response.

## Product Direction

PR 0069 proved that a runner adapter can return a deterministic execution result.
PR 0070 proved that runner adapter selection can happen through a deterministic dispatcher.
PR 0071 connects the app/mock-run layer to the runner dispatcher without adding HTTP or real execution.

This is the first app-to-runner bridge.

## Implementation Location Decision

**Decision: New handoff module in task_intake, new test file.**

### Implementation file

1. **`services/task_intake/src/task_intake/execution_handoff.py`** — handoff function.

### Test file

2. **`services/task_intake/tests/test_execution_handoff.py`** — focused tests.

**Rationale:** The handoff belongs in `task_intake` because it consumes the mock loop output (which is a task_intake concern) and produces a combined response. The runner dispatcher is imported as a dependency — no changes to runner code.

**Not modified (by default):**
- `services/task_intake/src/task_intake/mock_loop.py` — imported and called, not modified.
- `services/task_intake/src/task_intake/server.py` — no HTTP route changes.
- `services/task_intake/src/task_intake/runs.py` — not used directly (handoff goes through mock_loop).
- `services/runner/src/runner/adapter_registry.py` — imported and called, not modified.
- `services/runner/src/runner/noop_adapter.py` — not imported directly (goes through dispatcher).
- `schemas/`, `docs/` — no changes.

## Public Function

```python
def run_mock_execution_handoff(raw: object) -> dict:
    """Run the mock app loop then dispatch execution through the runner adapter.

    Parameters
    ----------
    raw
        The raw task request (same shape as ``run_mock_loop`` input).

    Returns
    -------
    dict
        A combined handoff response with keys:
        ok, handoff_id, mock_loop_result, execution_request,
        execution_result, errors, warnings, next.
    """
```

## Input Surface

Accepts the same raw request as `run_mock_loop`:
`raw_task` (required), plus optional fields (`source`, `metadata`, `constraints`, `requested_output`, `include_sections`, `preview_options`, `run_options`).

Additionally accepts optional execution-specific overrides:
- `requested_adapter` — override the adapter id (default `"noop"`)
- `execution_mode` — override the execution mode (default `"dry_run"`)
- `execution_approval` — override the approval dict (default `None`)

These are nested inside the same request dict, alongside the mock loop fields.

## Execution Request Builder

From the mock loop result, build a `RunnerExecutionRequest` dict:

```python
def _build_execution_request(
    mock_result: dict,
    raw: dict,
) -> dict:
    """Build a RunnerExecutionRequest from mock loop result and raw input."""
    task_intake = mock_result.get("task_intake", {})
    normalized = task_intake.get("normalized", {})
    context_preview = mock_result.get("context_preview", {})
    run = mock_result.get("run", {})

    # Generate a deterministic execution request ID
    task_goal = normalized.get("task_goal", "")
    cp_id = context_preview.get("context_preview_id", "")
    loop_id = mock_result.get("loop_id", "")
    digest = hashlib.sha256(
        f"{task_goal}{cp_id}{loop_id}".encode("utf-8")
    ).hexdigest()

    return {
        "execution_request_id": f"er_{digest[:12]}",
        "run_id": run.get("run_id", "") or mock_result.get("loop_id", ""),
        "task_intake_id": task_intake.get("task_intake_id", ""),
        "context_preview_id": cp_id,
        "requested_adapter": raw.get("requested_adapter", "noop"),
        "execution_mode": raw.get("execution_mode", "dry_run"),
        "inputs": {
            "task_goal": task_goal,
            "source": normalized.get("source", "manual"),
            "inferred_mode": normalized.get("inferred_mode", "unknown"),
            "inferred_domains": normalized.get("inferred_domains", []),
            "context_sections_included": list(
                context_preview.get("preview", {})
                .get("context_sections", {})
                .keys()
            ),
        },
        "constraints": normalized.get("constraints", []),
        "expected_outputs": [normalized.get("requested_output", "plan")],
        "approval": raw.get("execution_approval"),
        "metadata": {
            "source": "mock-execution-handoff",
            "handoff_via": "run_mock_execution_handoff",
        },
    }
```

## Handoff Result Shape

```python
{
    "ok": True,
    "handoff_id": "handoff_<sha256>",
    "mock_loop_result": mock_result,
    "execution_request": execution_request,
    "execution_result": execution_result,
    "errors": [],
    "warnings": [],
    "next": f"/runs/{run_id}/status",
}
```

For failures (mock loop fails, or dispatcher returns failed):

```python
{
    "ok": False,
    "handoff_id": "<deterministic or empty>",
    "mock_loop_result": <mock_result or None>,
    "execution_request": <request or None>,
    "execution_result": <result or None>,
    "errors": [error_dicts],
    "warnings": [],
    "next": "",
}
```

## Behavior Requirements

| Case | Behavior |
|---|---|
| Valid raw request | Call run_mock_loop, build execution request, call dispatch_execution, return combined response |
| Approval-gated | `execution_approval: {"required": true, "approved": false}` → execution_result has `status: "blocked"` |
| Invalid raw input (no raw_task) | Mock loop returns failure. Handoff returns error without calling dispatcher. |
| Mock loop non-dict failure | Propagation: mock_loop returns structured error, handoff captures it. |
| Unsupported adapter | `requested_adapter: "docker-coder-v1"` → dispatch returns `failed`. Handoff includes error. |
| Unsupported execution mode | Delegated to adapter; dispatcher passes through. |
| Determinism | Repeated calls with same input return equal output. |
| JSON serializable | All output fields are plain Python types. |

## Test Plan

**Test file:** `services/task_intake/tests/test_execution_handoff.py`

| Test | Expectation |
|---|---|
| `test_valid_handoff_returns_ok` | valid input → ok: true |
| `test_valid_handoff_has_execution_result` | valid input → execution_result present with completed status |
| `test_valid_handoff_has_execution_request` | valid input → execution_request present with all required fields |
| `test_valid_handoff_has_mock_loop_result` | valid input → mock_loop_result present with completed_mock_loop status |
| `test_handoff_deterministic` | repeated calls return equal output |
| `test_handoff_json_serializable` | passes json.dumps(sort_keys=True) |
| `test_invalid_raw_input_handoff_fails` | missing raw_task → ok: false, no dispatcher call |
| `test_approval_pending_returns_blocked` | execution_approval with pending → blocked in execution_result |
| `test_unsupported_adapter_returns_error` | requested_adapter: "docker-coder-v1" → failed in execution_result |
| `test_no_side_effects` | no subprocess/Docker/network imports |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_execution_handoff.py services/runner/tests/test_adapter_registry.py services/runner/tests/test_noop_adapter.py -q
python -m compileall -f services/task_intake/src services/runner/src
grep -R -n "subprocess|os\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |open(\\|write(\\|Path(\\|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" services/task_intake/src/task_intake/execution_handoff.py services/task_intake/tests/test_execution_handoff.py || true
grep -R -n "\$(" services/task_intake/src/task_intake/execution_handoff.py services/task_intake/tests/test_execution_handoff.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/task_intake/tests/test_execution_handoff.py`

Precommit review may later write only:
- `.project-memory/pr/0071-mock-run-runner-handoff/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0071-mock-run-runner-handoff/PLAN.md` (planner only)
- `.project-memory/pr/0071-mock-run-runner-handoff/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/src/task_intake/mock_loop.py`
- `services/task_intake/src/task_intake/runs.py`
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/**` (except no changes at all)
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
- `pyproject.toml`
- `package.json`
- `Makefile`

## Non-goals

- no docs-only or schemas-only PR
- no HTTP endpoint
- no route changes
- no mock-loop business logic changes
- no runner adapter logic changes
- no real execution
- no Docker adapter
- no subprocess/shell/network
- no filesystem writes at runtime
- no plugin discovery/dynamic imports
- no artifact collection
- no queue/persistence/database
- no model calls/provider integration
- no dependency/build changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only/schemas-only → stop
- no executable `.py` file → stop
- no test file → stop
- about to add HTTP endpoint → stop
- about to modify task-intake route behavior → stop
- about to modify mock_loop.py → stop
- about to modify adapter_registry.py → stop
- about to implement real runner execution → stop
- about to implement Docker adapter → stop
- about to call subprocess/shell → stop
- about to use network libraries → stop
- about to write files at runtime → stop
- about to add plugin discovery/dynamic imports → stop
- about to add persistence/queue/database → stop
- about to add dependencies → stop
- about to modify schemas/docs as primary output → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples → stop
- shell placeholders → stop

## Open Questions

1. **Should the handoff module be in `task_intake` or `runner`?** **Decision:** `task_intake`. The handoff consumes mock loop output (task_intake concern) and produces a combined response. Importing the dispatcher from runner is a clean dependency — runner has no dependency on task_intake. Placing the handoff in runner would create a reverse dependency (runner → task_intake), which is architecturally worse.

2. **Should the handoff function accept raw input like `run_mock_loop`, or a pre-computed mock loop result?** **Decision:** Both. The signature accepts `raw` (same as `run_mock_loop`). Internally, it calls `run_mock_loop(raw)`. Callers who already have a mock loop result can call `run_mock_loop` themselves and build execution requests manually. The public function is the convenience entry point.

3. **Should `handoff_id` be derived from the raw input or the mock loop result?** **Decision:** From the mock loop result (task_goal + context_preview_id + loop_id). This ensures the handoff ID is consistent with the IDs generated by the individual slices. If the raw input produces the same mock loop result, it produces the same handoff ID.

## Decisions Made

### selected_strategy

Executable Python code + tests in `task_intake` package.

### implementation_files

```
services/task_intake/src/task_intake/execution_handoff.py
```

### test_files

```
services/task_intake/tests/test_execution_handoff.py
```

### public_functions

```python
run_mock_execution_handoff(raw: object) -> dict
```

### input_surface

Same as `run_mock_loop` input: `raw_task` (required), plus optional fields and execution overrides (`requested_adapter`, `execution_mode`, `execution_approval`).

### execution_request_shape

Full `RunnerExecutionRequest` with deterministic IDs derived from mock loop output. `requested_adapter` defaults to `"noop"`, `execution_mode` defaults to `"dry_run"`.

### handoff_result_shape

```python
{
    "ok": bool,
    "handoff_id": str,
    "mock_loop_result": dict,
    "execution_request": dict,
    "execution_result": dict,
    "errors": list,
    "warnings": list,
    "next": str,
}
```

### dispatcher_call_semantics

Call `run_mock_loop(raw)` first. If mock loop fails, return error without calling dispatcher. If mock loop succeeds, build execution request, call `dispatch_execution(request)`. Combine both into handoff result.

### error_semantics

Mock loop failure → handoff returns `ok: false` with mock loop errors, no dispatcher call. Dispatcher returns `failed` → handoff returns `ok: true` (handoff itself succeeded) but includes the failed execution_result for caller inspection.

### deterministic_id_strategy

`handoff_id`: `handoff_<sha256(task_goal + context_preview_id + loop_id)[:12]>`. Execution request ID: `er_<sha256(...)[:12]>`.

### validation_strategy

10 tests covering valid flow, determinism, serialization, invalid input, approval blocking, unsupported adapter, and side-effect safety. PYTHONPATH must include both task_intake and runner.

### next_pr_notes

The next PR should wire the handoff into an HTTP endpoint, either as a new route in task_intake (`POST /execute`) or by extending `POST /mock-loop` to return execution results alongside mock loop results.

---

PLAN written: yes
