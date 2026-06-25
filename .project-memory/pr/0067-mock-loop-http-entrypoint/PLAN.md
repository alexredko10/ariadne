# PR 0067 — Mock Loop HTTP Entrypoint Plan

## Goal

Plan the smallest HTTP/app entrypoint that exposes the existing deterministic mock loop from PR 0066.

The desired visible behavior is:

```
POST /mock-loop
→ calls run_mock_loop(raw)
→ returns the same deterministic combined mock loop response
```

This PR should make the mock product loop callable through the existing task-intake service surface.

## Architectural Thesis

0063 introduced task-intake normalization.
0064 introduced context preview.
0065 introduced mock run creation and status.
0066 introduced pure deterministic mock loop composition.
0067 should expose that loop through the existing server/API pattern without changing the business logic.

This is an app-surface PR, not a runtime/runner PR.

It remains mock-only and substrate-safe:
- no real runner execution
- no Docker-agent execution
- no persistence
- no queue
- no model calls
- no GitHub automation
- no new framework

Docker agents remain future execution adapters after the mock loop is externally callable.

## Context Snapshot

- **current HEAD sha**: `b4dc67231633a572bab8ce9760316fba8fa5421f`
- **current branch**: `0067-mock-loop-http-entrypoint`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `b4dc672` (main after PR 0066 merge — no skew relative to main)
- **index_version**: `"0.33"` (from `.project-memory/context-bundles/contracts.yml` — PR 0066 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0066, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/pr/0066-minimal-mock-app-loop-surface/PLAN.md`
- `services/task_intake/src/task_intake/mock_loop.py`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_mock_loop.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/task_intake/src/task_intake/runs.py`

## Existing Server Surface Snapshot

### Current routes in `server.py`

| Route | Imported module | Status |
|---|---|---|
| `GET /health` | `doctor.py` | Present |
| `POST /submit` | `app.py` | Present |
| `POST /task-intake/submit` | `app.py` | Present |
| `POST /task-intake/normalize` | `normalize.py` | Present |
| `POST /context/preview` | `context_preview.py` | Present |
| `POST /runs` | `runs.py` | Present |
| **`POST /mock-loop`** | **`mock_loop.py`** | **NOT present** |

### Server pattern

All routes follow the same stdlib ASGI pattern:

```python
if method == "POST" and path == "/some-path":
    # Read body via ASGI receive events
    body_bytes = b""
    more_body = True
    while more_body:
        event = await receive()
        if event["type"] == "http.request":
            body_bytes += event.get("body", b"")
            more_body = event.get("more_body", False)

    # Parse JSON
    try:
        data = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        await _send_json(send, 400, error_body)
        return

    # Call module function
    result = module_function(data)

    # Respond based on ok field
    if result.get("ok") is True:
        await _send_json(send, 200, body)
    else:
        await _send_json(send, 400, body)
```

### Test pattern

`test_task_intake_http.py` uses a synchronous ASGI test harness via `asyncio.run()`:

```python
async def _asgi_request(method, path, body=None) -> tuple[int, dict]:
    ...

def _request(method, path, body=None) -> tuple[int, dict]:
    return asyncio.run(_asgi_request(method, path, body=body))
```

### Mock loop module (`mock_loop.py`)

- `run_mock_loop(raw: dict) -> dict` — pure function, no I/O.
- Accepts: `raw_task` (required), plus optional fields (`source`, `metadata`, `constraints`, `requested_output`, `include_sections`, `preview_options`, `run_options`).
- Or accepts pre-composed `task_intake`, `context_preview` dicts for caller-driven composition.
- Returns: deterministic combined response with `ok`, `loop_id`, `task_intake`, `context_preview`, `run`, `status`, `validation`, `evidence`, `next`.
- Side effects: none.

## Implementation Location Decision

**Decision: Two files to modify.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add route for `POST /mock-loop` following the existing ASGI pattern. Add import for `mock_loop.run_mock_loop`.

### Modified test file

2. **`services/task_intake/tests/test_task_intake_http.py`** — add `TestMockLoopHTTP` class with HTTP-level tests.

**Rationale for test location:** The existing HTTP tests for all other routes live in `test_task_intake_http.py`. Adding the mock-loop HTTP tests there keeps all HTTP-level tests in one file. This is consistent with the existing pattern.

**No new files.** This is the smallest possible change: one import + one route block in the server, one test class in the existing test file.

### Not modified (by default)

- `mock_loop.py` — no business logic changes.
- `test_mock_loop.py` — pure function tests remain untouched.
- `normalize.py`, `context_preview.py`, `runs.py` — unchanged.
- `pyproject.toml` — no dependency changes.
- `schemas/`, `.project-memory/`, `docs/` — unchanged.

## Entrypoint Contract

| Aspect | Decision |
|---|---|
| **Route path** | `POST /mock-loop` |
| **HTTP method** | `POST` |
| **Request shape** | Same as PR 0066 mock loop: `raw_task` (required), plus optional fields |
| **Success status** | `200` when `result["ok"] is True` |
| **Validation failure status** | `400` when `result["ok"] is False` |
| **Invalid JSON** | `400` with structured error (same pattern as other routes) |
| **Non-object body** | `400` — handled by `run_mock_loop` returning `ok: false` |
| **Unknown route** | `404` (existing catch-all) |
| **Unsupported method** | `404` (existing catch-all) |

## Route block in `server.py`

```python
from task_intake.mock_loop import run_mock_loop

# ... inside app() ...

if method == "POST" and path == "/mock-loop":
    # Read body
    body_bytes = b""
    more_body = True
    while more_body:
        event = await receive()
        if event["type"] == "http.request":
            body_bytes += event.get("body", b"")
            more_body = event.get("more_body", False)

    # Parse JSON
    try:
        data = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        await _send_json(
            send, 400,
            json.dumps({
                "ok": False,
                "validation": {
                    "valid": False,
                    "errors": ["Invalid JSON body."],
                    "warnings": [],
                },
            }, ensure_ascii=False).encode("utf-8"),
        )
        return

    result = run_mock_loop(data)

    if result.get("ok") is True:
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
    else:
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 400, body)
    return
```

This is a copy-paste of the same pattern used by `/task-intake/normalize`, `/context/preview`, and `/runs`.

## Tests

### Test class in `services/task_intake/tests/test_task_intake_http.py`

```python
class TestMockLoopHTTP:
    """HTTP-level tests for POST /mock-loop."""

    def test_valid_minimal_request_returns_200(self):
        body = json.dumps({"raw_task": "Implement JWT auth"}).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 200
        assert data["ok"] is True

    def test_valid_request_has_all_steps(self):
        body = json.dumps({"raw_task": "Implement JWT auth"}).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 200
        assert "task_intake" in data
        assert "context_preview" in data
        assert "run" in data

    def test_valid_request_has_loop_status(self):
        body = json.dumps({"raw_task": "Implement JWT auth"}).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 200
        assert data["status"]["state"] == "completed_mock_loop"
        assert data["status"]["is_terminal"] is True

    def test_valid_request_deterministic(self):
        body = json.dumps({"raw_task": "Implement JWT auth"}).encode("utf-8")
        s1, d1 = _request("POST", "/mock-loop", body=body)
        s2, d2 = _request("POST", "/mock-loop", body=body)
        assert s1 == 200 and s2 == 200
        assert d1 == d2

    def test_missing_raw_task_returns_400(self):
        body = json.dumps({}).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_invalid_json_returns_400(self):
        body = b"not json"
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_rich_options_pass_through(self):
        body = json.dumps({
            "raw_task": "Implement JWT auth",
            "source": "demo",
            "metadata": {"requester": "test"},
            "constraints": ["no_git_mutation"],
            "requested_output": "plan",
            "include_sections": ["task", "scope"],
            "run_options": {"priority": "normal"},
        }).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 200
        assert data["ok"] is True

    def test_unsupported_method_returns_404(self):
        status, data = _request("GET", "/mock-loop")
        assert status == 404
```

### Compatibility

- Existing `test_mock_loop.py` (pure function) tests pass.
- Existing `test_task_intake_http.py` tests pass (all existing test classes unaffected).
- Existing `test_normalize.py`, `test_context_preview.py`, `test_runs.py` tests pass.
- No changes to any existing test or implementation file except `server.py` and `test_task_intake_http.py`.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/task_intake/src/task_intake/server.py services/task_intake/tests/test_task_intake_http.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/task_intake/src/task_intake/server.py services/task_intake/tests/test_task_intake_http.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_task_intake_http.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0067-mock-loop-http-entrypoint/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0067-mock-loop-http-entrypoint/PLAN.md` (planner only)
- `.project-memory/pr/0067-mock-loop-http-entrypoint/reviews/plan-review.yml` (plan-review only)
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
- `services/task_intake/src/task_intake/mock_loop.py` (no business logic changes)
- `services/task_intake/src/task_intake/normalize.py`
- `services/task_intake/src/task_intake/context_preview.py`
- `services/task_intake/src/task_intake/runs.py`
- `services/task_intake/tests/test_mock_loop.py`
- `services/task_intake/tests/test_normalize.py`
- `services/task_intake/tests/test_context_preview.py`
- `services/task_intake/tests/test_runs.py`
- `package.json`
- `Makefile`
- `.project-memory/anchors.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/templates/**`
- `.grace/**`

## Non-goals

- no changes to mock-loop business logic
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
- no project-memory runtime writes
- no new files
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to add dependency/build config → stop
- about to add new web framework → stop
- about to change mock-loop business logic → stop
- about to add database/persistence → stop
- about to add queue behavior → stop
- about to add model/provider behavior → stop
- about to inspect Git/repository state from runtime code → stop
- about to scan repository files from runtime code → stop
- about to execute runs → stop
- about to implement real runner behavior → stop
- about to implement Docker-agent execution → stop
- about to modify `mock_loop.py` → stop
- about to modify runtime/core/runner/domain adapters → stop
- about to modify conductor → stop
- about to modify schemas → stop
- about to modify project-memory registry/templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the mock-loop route be added to `server.py` or a separate handler file?** **Decision:** `server.py`. All existing routes are in `server.py`. Adding one more route block follows the existing pattern exactly. A separate handler file would be inconsistent with the project convention.

2. **Should the HTTP tests go in the existing `test_task_intake_http.py` or a new file?** **Decision:** Existing `test_task_intake_http.py`. All HTTP-level tests for all routes live in this file. Adding a test class there is consistent with the existing pattern. The existing `test_mock_loop.py` tests the pure function; `test_task_intake_http.py` tests the HTTP integration.

3. **Should the route accept a pre-composed `task_intake` dict (bypassing normalize)?** **Decision:** Yes — the `run_mock_loop()` function already supports this. The route passes the raw body directly to `run_mock_loop()`, which handles both raw task strings and pre-composed dicts. No routing logic change needed.

## Decisions Made

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_task_intake_http.py (modify)
```

### optional_test_files

None — HTTP tests go in the existing test file.

### route_path

```
POST /mock-loop
```

### http_method

`POST` only. Other methods return 404 (existing catch-all).

### request_shape

Same as PR 0066 mock loop: `raw_task` (required), plus optional fields (`source`, `metadata`, `constraints`, `requested_output`, `include_sections`, `preview_options`, `run_options`). The route passes the raw body to `run_mock_loop()` which handles all shapes.

### response_shape

Same as PR 0066 mock loop output: deterministic dict with `ok`, `loop_id`, `task_intake`, `context_preview`, `run`, `status`, `validation`, `evidence`, `next`.

### status_mapping

| Condition | Status |
|---|---|
| `result["ok"] is True` | 200 |
| `result["ok"] is False` | 400 |
| Invalid JSON body | 400 |
| Unknown route | 404 |
| Unsupported method on /mock-loop | 404 |

### endpoint_strategy

Route `POST /mock-loop` in `server.py`. Same ASGI pattern as all other routes. Single import, single route block, no logic duplication.

### composition_strategy

The route calls `run_mock_loop(data)` and returns the result. No route-level business logic. No composition logic in the route handler.

### mock_loop_change_policy

Zero changes to `mock_loop.py`. The route imports and calls the existing function unchanged.

### docker_agent_boundary

No Docker. No runner. `evidence.execution_performed: false` is already in the mock loop output.

### deterministic_policy

- Route delegates to `run_mock_loop()` which is deterministic.
- No random ids, no timestamps, no current time in route handler.
- No absolute paths, no machine-specific values.
- No old names/examples, no shell placeholders.

### validation_strategy

```
HTTP-level tests in existing test file.
Pure function tests in existing mock_loop test file.
Compability tests for all slices.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes
