# PR 0072 — Run Execution HTTP Mock Endpoint Plan

## Goal

Plan executable behavior for a thin HTTP endpoint that exposes the PR 0071 deterministic execution handoff.

This PR must add code and tests.
This PR must not be docs-only.
This PR must not be schemas-only.

The endpoint must accept a JSON request body, call `run_mock_execution_handoff(raw)`, and return the handoff response.

## Product Direction

PR 0071 connected mock-run flow to runner dispatcher in Python code.
PR 0072 exposes that existing behavior over HTTP without adding new business logic.

This is the first HTTP surface for the mock-to-runner execution path.

## Implementation Location Decision

**Decision: Modify server.py, add HTTP test file.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add import + route block.

### New test file

2. **`services/task_intake/tests/test_execution_handoff_http.py`** — HTTP-level tests.

**Not modified:**
- `execution_handoff.py`, `mock_loop.py`, `runs.py` — no changes.
- `adapter_registry.py`, `noop_adapter.py` — no changes.
- `schemas/`, `docs/` — no changes.

## Route Decision

**Route:** `POST /runs/execute`

**Rationale:** The path `/runs/execute` follows the existing convention of noun-based paths (`/runs`, `/mock-loop`, `/context/preview`, `/task-intake/normalize`). The verb `execute` distinguishes this from the mock `/runs` endpoint (which creates a mock run object). This is clearer than `/execution-requests` — the endpoint runs an execution, not just creates a request.

### Request body handling

Same pattern as all other routes in `server.py`:
1. Read body via ASGI `receive()` events.
2. Parse JSON — return 400 on parse failure.
3. Call `run_mock_execution_handoff(data)`.

### Response body shape

Same shape as `run_mock_execution_handoff()` return value:
```json
{
  "ok": true,
  "handoff_id": "handoff_...",
  "mock_loop_result": {...},
  "execution_request": {...},
  "execution_result": {...},
  "errors": [],
  "warnings": [],
  "next": "/runs/.../status"
}
```

### HTTP status policy

| Condition | Status |
|---|---|
| Valid JSON, handoff succeeds (`ok: true`) | 200 |
| Valid JSON, handoff returns error (`ok: false`) | 400 |
| Invalid JSON body | 400 |
| Unknown route | 404 |

This matches the pattern used by all other routes in `server.py`: call the function, check `ok`, respond 200 or 400.

### Relationship to `/mock-loop`

The existing `/mock-loop` endpoint calls `run_mock_loop()` and returns mock loop results including a mock run object. The new `/runs/execute` endpoint calls `run_mock_execution_handoff()` which internally calls `run_mock_loop()` and then dispatches through the runner adapter. The `/mock-loop` endpoint is unchanged.

## Route block in `server.py`

```python
from task_intake.execution_handoff import run_mock_execution_handoff

# Add to existing imports.
```

Route block (follows the exact same pattern as `/mock-loop`):

```python
if method == "POST" and path == "/runs/execute":
    body_bytes = b""
    more_body = True
    while more_body:
        event = await receive()
        if event["type"] == "http.request":
            body_bytes += event.get("body", b"")
            more_body = event.get("more_body", False)

    try:
        data = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        await _send_json(
            send, 400,
            json.dumps({
                "ok": False,
                "errors": [{"code": "invalid_json", "message": "Invalid JSON body."}],
            }, ensure_ascii=False).encode("utf-8"),
        )
        return

    result = run_mock_execution_handoff(data)

    if result.get("ok") is True:
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
    else:
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 400, body)
    return
```

## Behavior Requirements

| Aspect | Behavior |
|---|---|
| Valid body | Returns 200 with handoff result containing execution_result from no-op adapter |
| Invalid JSON | Returns 400 with structured error |
| Missing raw_task | Returns 400 with handoff failure (mock loop fails → handoff returns ok: false) |
| Determinism | Repeated calls with same body return equal response bodies |
| Delegation | Calls `run_mock_execution_handoff`, not lower-level functions |
| `/mock-loop` | Unchanged — still calls `run_mock_loop` only |
| `/runs` | Unchanged — still calls `create_mock_run` only |

## Test Plan

**Test file:** `services/task_intake/tests/test_execution_handoff_http.py`

Using the same ASGI test harness pattern as existing HTTP tests (`_request()` wrapper via `asyncio.run()`).

| Test | Expectation |
|---|---|
| `test_valid_request_returns_200` | POST /runs/execute with valid body → 200 |
| `test_response_contains_handoff_id` | response has `handoff_id` |
| `test_response_contains_execution_request` | response has `execution_request` |
| `test_response_contains_execution_result` | response has `execution_result` with `status: "completed"` |
| `test_response_contains_mock_loop_result` | response has `mock_loop_result` |
| `test_deterministic` | repeated calls return equal JSON |
| `test_invalid_json_returns_400` | non-JSON body → 400 |
| `test_missing_raw_task_returns_400` | empty JSON → 400 with error |
| `test_mock_loop_unchanged` | POST /mock-loop still returns mock loop result |
| `test_runs_unchanged` | POST /runs still returns mock run result |
| `test_no_direct_adapter_call` | server source does not import `noop_adapter` |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_execution_handoff.py services/runner/tests/test_adapter_registry.py services/runner/tests/test_noop_adapter.py -q
python -m compileall -f services/task_intake/src services/runner/src
grep -R -n "run_noop_execution|noop_adapter|subprocess|os\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |open(\\|write(\\|Path(\\|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" services/task_intake/src/task_intake/server.py services/task_intake/tests/test_execution_handoff_http.py || true
grep -R -n "\$(" services/task_intake/src/task_intake/server.py services/task_intake/tests/test_execution_handoff_http.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_execution_handoff_http.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0072-run-execution-http-endpoint/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0072-run-execution-http-endpoint/PLAN.md` (planner only)
- `.project-memory/pr/0072-run-execution-http-endpoint/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/task_intake/src/task_intake/mock_loop.py`
- `services/task_intake/src/task_intake/runs.py`
- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/noop_adapter.py`
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
- no new execution contract
- no handoff business logic changes
- no mock-loop business logic changes
- no runner dispatcher changes
- no no-op adapter changes
- no real execution
- no Docker adapter
- no subprocess/shell/network
- no filesystem writes at runtime
- no plugin discovery/dynamic imports
- no queue/persistence/database
- no model calls/provider integration
- no dependency/build changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only/schemas-only → stop
- no executable `.py` file selected → stop
- no test file selected → stop
- about to duplicate handoff logic in server.py → stop
- about to bypass PR 0071 handoff → stop
- about to call no-op adapter directly from HTTP route → stop
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

## Decisions Made

### selected_strategy

Executable Python code + HTTP tests.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_execution_handoff_http.py (new)
```

### route

`POST /runs/execute`

### request_body_policy

Same as all other routes: read ASGI body, parse JSON, call function.

### response_body_shape

Same as `run_mock_execution_handoff()` return value.

### http_status_policy

| Condition | Status |
|---|---|
| `ok: true` | 200 |
| `ok: false` | 400 |
| Invalid JSON | 400 |
| Unknown route | 404 |

### delegation_semantics

Calls `run_mock_execution_handoff(data)`. Does NOT call `dispatch_execution`, `run_mock_loop`, or `run_noop_execution` directly.

### invalid_input_semantics

Invalid JSON → 400. Missing required fields → handoff returns `ok: false` → 400.

### validation_strategy

11 HTTP-level tests + existing handoff/adapter/dispatcher tests. PYTHONPATH includes task_intake and runner sources.

### next_pr_notes

After PR 0072, the mock-to-runner execution path is HTTP-accessible through `POST /runs/execute`. The next step could be adding a lightweight integration test that starts the server via uvicorn and runs the handoff end-to-end, or moving toward real execution by adding a local-process adapter as an alternative to no-op.

---

PLAN written: yes
