# PR 0075 — First Local Execution Harness Plan

## Goal

Plan a bounded vertical deterministic runtime slice:

```
runner local harness
→ dispatcher
→ no-op execution result
→ execution envelope
→ human review boundary
→ task-intake handoff response
→ existing HTTP endpoint response becomes richer through handoff
```

This PR must be code + tests.
Docs-only is invalid.
Schemas-only is invalid.

This PR may be slightly larger than previous PRs, but only as one vertical deterministic slice.

## Implementation Decision

**Decision: New harness module in runner, update handoff in task_intake.**

### New files

1. **`services/runner/src/runner/local_harness.py`** — local execution harness.
2. **`services/runner/tests/test_local_harness.py`** — harness tests.

### Modified files

3. **`services/task_intake/src/task_intake/execution_handoff.py`** — delegate to harness.
4. **`services/task_intake/tests/test_execution_handoff.py`** — update for richer response.
5. **`services/task_intake/tests/test_execution_handoff_http.py`** — update for richer response.

**Not modified:**
- `server.py` — no changes. The existing `/runs/execute` route calls `run_mock_execution_handoff` which will now produce richer output.
- `noop_adapter.py`, `adapter_registry.py`, `execution_envelope.py`, `review_boundary.py` — no changes.

## Public API

```python
# services/runner/src/runner/local_harness.py

def run_local_execution_harness(execution_request: dict) -> dict:
    """Run a local execution harness:
    dispatcher → execution result → envelope → review boundary.

    Parameters
    ----------
    execution_request
        A RunnerExecutionRequest dict.

    Returns
    -------
    dict
        A deterministic harness result dict.
    """
```

The harness:
1. Validates input (must be a dict).
2. Calls `dispatch_execution(execution_request)` from `adapter_registry`.
3. Calls `build_execution_envelope(execution_request, execution_result)` from `execution_envelope`.
4. Calls `derive_review_boundary(execution_request, execution_result)` from `review_boundary`.
5. Returns combined response.

## Response Shape

```python
{
    "ok": True,
    "runtime_status": "completed",    # from review boundary decision
    "execution_request": {...},       # original request
    "execution_result": {...},        # from dispatcher
    "execution_envelope": {...},      # from envelope builder
    "review_boundary": {...},         # from review boundary
    "errors": [],
    "warnings": [],
    "metadata": {
        "harness": "local",
        "harness_version": "0.1",
    },
}
```

For failure (non-dict input or dispatcher/envelope/boundary error):
```python
{
    "ok": False,
    "runtime_status": "error",
    "execution_request": {...} or None,
    "execution_result": {...} or None,
    "execution_envelope": {...} or None,
    "review_boundary": {...} or None,
    "errors": [...],
    "warnings": [],
    "metadata": {"harness": "local", "harness_version": "0.1"},
}
```

## Handoff Integration

The `run_mock_execution_handoff()` function in `execution_handoff.py` is updated to:

1. Build execution request (same as before).
2. Call `run_local_execution_harness(execution_request)` instead of calling `dispatch_execution` directly.
3. Include the harness result in the handoff response alongside existing fields.

The handoff response gains these new fields:
- `execution_envelope` — from the harness
- `review_boundary` — from the harness
- `runtime_status` — the harness runtime_status (which comes from the review boundary decision)

The handoff response keeps backward-compatible fields:
- `ok` — unchanged
- `handoff_id` — unchanged
- `mock_loop_result` — unchanged
- `execution_request` — unchanged
- `execution_result` — unchanged
- `errors` — unchanged
- `warnings` — unchanged
- `next` — unchanged

## HTTP Effect

The existing `POST /runs/execute` endpoint calls `run_mock_execution_handoff(raw)`. No changes to `server.py`. The response shape expands automatically because the handoff function returns more fields.

Existing HTTP tests that assert specific fields (like `test_response_contains_execution_result` and `test_response_contains_execution_request`) continue to pass. New tests verify the additional fields.

## Status Semantics

`runtime_status` is the `decision` from `derive_review_boundary`. Values:
- `completed` — no approval gates, result completed.
- `requires_review` — approval pending or after_execution with completed result.
- `blocked` — approval denied or result blocked.
- `failed` — result failed or error.
- `error` — input validation failure.

## Test Plan

### New tests: `services/runner/tests/test_local_harness.py`

| Test | Expectation |
|---|---|
| `test_valid_request_returns_ok` | valid input → ok: true |
| `test_contains_execution_request` | response has execution_request |
| `test_contains_execution_result` | response has execution_result with completed status |
| `test_contains_execution_envelope` | response has execution_envelope |
| `test_contains_review_boundary` | response has review_boundary with decision |
| `test_runtime_status_matches_boundary` | runtime_status == review_boundary.decision |
| `test_uses_dispatcher_not_direct_adapter` | harness does not import noop_adapter directly |
| `test_deterministic` | repeated calls return equal output |
| `test_json_serializable` | passes json.dumps(sort_keys=True) |
| `test_invalid_request_not_dict` | non-dict → ok: false |
| `test_no_side_effects` | no filesystem/Docker/subprocess imports |

### Updated tests: `services/task_intake/tests/test_execution_handoff.py`

Add test methods to verify:
- `test_handoff_contains_execution_envelope`
- `test_handoff_contains_review_boundary`
- `test_handoff_runtime_status`
- Existing tests continue to pass (handoff_id, mock_loop_result, execution_request, execution_result all still present).

### Updated tests: `services/task_intake/tests/test_execution_handoff_http.py`

Add test methods:
- `test_response_contains_execution_envelope`
- `test_response_contains_review_boundary`
- `test_response_runtime_status`
- Existing tests remain unchanged.

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_review_boundary.py \
  services/runner/tests/test_execution_envelope.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_noop_adapter.py \
  services/task_intake/tests/test_execution_handoff.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  -q
python -m compileall -f services/runner/src services/task_intake/src
grep -R -n "run_noop_execution\|noop_adapter\|open(\\|write(\\|Path(\\|read_text(\\|write_text(\\|subprocess|os\\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |uuid|datetime\\.now|time\\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\\.grace|@grace-\|old Flask" \
  services/runner/src/runner/local_harness.py \
  services/runner/tests/test_local_harness.py \
  services/task_intake/src/task_intake/execution_handoff.py \
  services/task_intake/tests/test_execution_handoff.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  || true
grep -R -n "\\$(" \
  services/runner/src/runner/local_harness.py \
  services/runner/tests/test_local_harness.py \
  services/task_intake/src/task_intake/execution_handoff.py \
  services/task_intake/tests/test_execution_handoff.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/local_harness.py` (new)
- `services/runner/tests/test_local_harness.py` (new)
- `services/task_intake/src/task_intake/execution_handoff.py` (modify)
- `services/task_intake/tests/test_execution_handoff.py` (modify)
- `services/task_intake/tests/test_execution_handoff_http.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0075-first-local-execution-harness/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0075-first-local-execution-harness/PLAN.md` (planner only)
- `.project-memory/pr/0075-first-local-execution-harness/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/server.py`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/execution_envelope.py`
- `services/runner/src/runner/review_boundary.py`
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

## Stop Conditions

- docs-only or schemas-only outcome
- no Python implementation file selected
- no test file selected
- broad write paths
- new HTTP route
- server.py change without narrow justification
- direct no-op adapter call from local harness
- bypassing dispatcher
- modifying dispatcher/noop/envelope/review_boundary without narrow compatibility blocker
- Docker/subprocess/network/filesystem IO
- real agent execution
- model/provider calls
- persistence/queue/database
- dependency/build changes
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Executable Python + tests. New harness module in runner. Update handoff in task_intake. No server.py changes.

### implementation_files

```
services/runner/src/runner/local_harness.py
services/task_intake/src/task_intake/execution_handoff.py (modify)
```

### test_files

```
services/runner/tests/test_local_harness.py
services/task_intake/tests/test_execution_handoff.py (modify)
services/task_intake/tests/test_execution_handoff_http.py (modify)
```

### public_api

```python
run_local_execution_harness(execution_request: dict) -> dict
```

### response_shape

`ok`, `runtime_status`, `execution_request`, `execution_result`, `execution_envelope`, `review_boundary`, `errors`, `warnings`, `metadata` (harness + version).

### handoff_integration

`run_mock_execution_handoff()` calls `run_local_execution_harness()` instead of `dispatch_execution()` directly. Handoff response gains `execution_envelope`, `review_boundary`, `runtime_status`. Existing fields preserved.

### http_effect

No changes to `server.py`. The existing `POST /runs/execute` route automatically returns richer responses because the handoff function returns more fields.

### status_semantics

`runtime_status` = review boundary decision: completed, requires_review, blocked, failed, error.

### validation_strategy

11 new harness tests + updated handoff HTTP tests + full compatibility run across all 5 runner modules and 2 task_intake modules.

### next_pr_notes

After PR 0075, the vertical runtime slice is complete: harness → dispatcher → envelope → review boundary → handoff → HTTP. The next step could be adding a non-noop adapter (e.g., a `local_coder` adapter that performs simple file operations) or wiring the review boundary decision into a human-notification path.

---

PLAN written: yes
