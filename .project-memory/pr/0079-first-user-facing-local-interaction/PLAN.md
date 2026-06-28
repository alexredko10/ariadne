# PR 0079 — First User-Facing Local Interaction Path Plan

## Goal

Plan the first user-facing local interaction path for Ariadne.

This PR must add a minimal local browser-facing interaction surface on top of the existing app runtime from PR 0078.

The user should be able to start the local app runtime, open a local page in the browser, submit a task, and receive the existing `/runs/execute` JSON result.

## Implementation Decision

**Decision: Add `GET /` HTML route to server.py, add HTTP test.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add `GET /` route serving inline HTML.

### New test file

2. **`services/task_intake/tests/test_local_interaction_page.py`** — focused tests.

**Not modified:**
- `app.py` — no runtime config changes. The user starts the same runtime as PR 0078.
- `execution_handoff.py` — no changes.
- `test_mode.py` — no changes.
- `services/runner/**` — no changes.
- `schemas/`, `docs/` — no changes.

## User-Facing Route

**Route:** `GET /`

**Rationale:** `/` is unoccupied (all current routes are either `GET /health` or `POST /...` paths). This is the simplest URL for a developer to open: `http://127.0.0.1:8000/`.

**Route location in server.py:** Inserted before the 404 catch-all, after all existing route blocks. Follows the same ASGI pattern:

```python
if method == "GET" and path == "/":
    html = _HTML_PAGE.encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            (b"content-type", b"text/html; charset=utf-8"),
            (b"content-length", str(len(html)).encode("utf-8")),
        ],
    })
    await send({"type": "http.response.body", "body": html})
    return
```

## HTML Behavior

The page is a single inline HTML string (no template engine, no separate file, no external assets):

- **Title:** "Ariadne — Local Interaction"
- **Task input:** `<textarea>` or `<input>` for task text
- **Submit button:** `<button>` that sends a POST to `/runs/execute`
- **Result area:** `<pre>` or `<div>` that displays the JSON response
- **Status indicator:** Shows the `runtime_status` from the response

**Design constraints:**
- Zero external dependencies — no CDN, no `<script src="...">`, no `<link href="...">`
- No frontend framework (no React, Vue, Svelte, etc.)
- No build step
- All CSS is inline `<style>` block
- All JS is inline `<script>` block
- No images, icons, fonts, or external assets
- Accessible at `http://127.0.0.1:8000/` without any path prefix

**JavaScript behavior:**
1. On submit, call `fetch("/runs/execute", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({task: taskText})})`
2. Parse response JSON
3. Display the key fields: `runtime_status`, `ok`, and a formatted JSON view of the full response in a `<pre>` block
4. Color-code `runtime_status` (green for completed, yellow for requires_review/blocked, red for failed/error)

**The page does NOT:**
- Add a new execution backend route
- Bypass `/runs/execute`
- Add authentication
- Add user management
- Add persistence
- Add real agent execution
- Call model/provider APIs
- Make Docker the default
- Modify the deterministic local/no-op path

## Execute API Usage

The page calls the **existing** `POST /runs/execute` endpoint. No new route is created for execution.

The request body:
```json
{"task": "Implement JWT authentication middleware"}
```

The response is the existing `/runs/execute` response, which includes:
`ok`, `runtime_status`, `execution_request`, `execution_result`, `execution_envelope`, `review_boundary`, `errors`, `warnings`, `metadata`.

## Visible Result Behavior

After submission, the page shows:
1. The `runtime_status` value (color-coded)
2. A formatted JSON view of the full response

No polling, no streaming, no WebSockets — the result appears after the single POST completes.

## API Preservation

The `POST /runs/execute` endpoint is unchanged:
- Same request shape (`{"task": "..."}`)
- Same response shape
- Same deterministic behavior
- Same code path (execution_handoff → local_harness → dispatcher → noop_adapter)
- All existing HTTP tests continue to pass

## Runtime Preservation

The app runtime from PR 0078 is unchanged:
- Same `python -m task_intake.app --host 127.0.0.1 --port 8000` command
- Same `--check --json` non-blocking mode
- Same route list (includes `GET /`)

The `_ROUTES` list in `app.py` should be updated to include `"/"` since a new route was added.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_interaction_page.py`

Tests use the same ASGI test harness pattern as `test_execution_handoff_http.py`.

| Test | Expectation |
|---|---|
| `test_get_root_returns_200` | GET / → 200 |
| `test_response_is_html` | content-type is text/html |
| `test_page_contains_task_input` | HTML includes `<textarea` or `<input` |
| `test_page_contains_submit_button` | HTML includes `<button` or `submit` |
| `test_page_references_runs_execute` | HTML includes `/runs/execute` |
| `test_page_has_no_external_assets` | HTML has no `src="http` or CDN references |
| `test_page_has_no_cdn` | HTML has no unpkg/jsdelivr/CDN |
| `test_runs_execute_preserved` | POST /runs/execute still returns runtime_status |
| `test_runs_execute_preserves_envelope` | Response still includes execution_envelope |
| `test_runs_execute_preserves_boundary` | Response still includes review_boundary |
| `test_no_new_execution_route` | No POST /execute path added |
| `test_app_runtime_check_works` | `build_runtime_config(["--check"])` works |
| `test_mode_cli_works` | `test_mode.main(["--task", "test"])` returns 0 |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_interaction_page.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  services/task_intake/tests/test_app_runtime.py \
  services/task_intake/tests/test_test_mode.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_docker_agent_adapter.py \
  -q
python -m compileall -f services/task_intake/src services/runner/src
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json
grep -R -n "subprocess|os\.system|popen|docker compose|Dockerfile|requests|httpx|urllib|redis|sqlite|import docker|from docker|docker\.from_env|uuid|datetime\.now|time\.time|random|cdn|unpkg|jsdelivr|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_interaction_page.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_interaction_page.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/src/task_intake/app.py` (modify — add `"/"` to `_ROUTES`)
- `services/task_intake/tests/test_local_interaction_page.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0079-first-user-facing-local-interaction/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0079-first-user-facing-local-interaction/PLAN.md` (planner only)
- `.project-memory/pr/0079-first-user-facing-local-interaction/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/task_intake/src/task_intake/test_mode.py`
- `services/runner/**`
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
- smoke-test-only outcome
- no user-facing local page selected
- no executable Python implementation file selected
- no test file selected
- frontend framework/build system required
- external assets/CDN required
- new execution backend route required
- `/runs/execute` behavior change required
- execution_handoff/local_harness bypass required
- Docker adapter becomes default
- Docker daemon required
- real agent execution required
- model/provider call required
- dependency/build change required
- persistence/auth/users required
- broad write paths
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Add `GET /` route to server.py serving inline HTML. No frameworks, no CDN, no build step. Calls existing `POST /runs/execute`.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
services/task_intake/src/task_intake/app.py (modify — add "/" to _ROUTES)
```

### test_files

```
services/task_intake/tests/test_local_interaction_page.py (new)
```

### user_facing_route

`GET /`

### route_behavior

Serves inline HTML (no template engine, no separate file). Route inserted before 404 catch-all. Follows existing ASGI pattern.

### html_behavior

Single inline HTML string with embedded `<style>` and `<script>`. No external assets. Text input + submit button + formatted JSON result display.

### execute_api_usage

Calls existing `POST /runs/execute` via `fetch()` with `{"task": taskText}`. No new backend route.

### visible_result_behavior

Color-coded `runtime_status` + formatted JSON in `<pre>` block. Single POST, no polling/streaming/WebSockets.

### api_preservation

`POST /runs/execute` unchanged. Same request/response shape, same code path. All HTTP tests pass.

### runtime_preservation

App runtime from PR 0078 unchanged. `_ROUTES` list updated to include `"/"`.

### validation_strategy

13 tests + full compatibility across all test modules + check command + test-mode CLI + forbidden pattern guards.

### next_pr_notes

After PR 0079, Ariadne has a functioning local app with a browser UI. The next PR could add error display, loading state, or a richer task result view.

---

PLAN written: yes
