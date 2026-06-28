# PR 0080 — Local Result Structured View Plan

## Goal

Plan a minimal structured result view for Ariadne's local browser page.

PR 0079 added the first local interaction page. PR 0080 must improve that page so the user can understand the `/runs/execute` result without reading only raw JSON.

This PR must keep raw JSON visible and add structured sections for the existing response.

## Implementation Decision

**Decision: Update the inline HTML in `server.py` to parse and render structured result sections.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update `_HTML_PAGE` to add structured section rendering.

### New test file

2. **`services/task_intake/tests/test_local_result_structured_view.py`** — tests for structured view content.

**Not modified:**
- Any backend logic, routes, or APIs.
- `execution_handoff.py`, `local_harness.py`, `adapter_registry.py`, `noop_adapter.py` — no changes.
- `app.py` — no changes (routes are unchanged).
- `services/runner/**` — no changes.
- No new files, no new assets, no new dependencies.

## Structured Sections

The updated page renders these sections after a successful `/runs/execute` response:

### 1. Status Summary (always visible)

| Section | HTML Element | Source field |
|---|---|---|
| OK status | `<span>` with green/red | `data.ok` |
| Runtime status | `<span>` with color class | `data.runtime_status` |

### 2. Execution Request (collapsible)

| Field | Source |
|---|---|
| Execution request ID | `data.execution_request.execution_request_id` |
| Run ID | `data.execution_request.run_id` |
| Requested adapter | `data.execution_request.requested_adapter` |
| Execution mode | `data.execution_request.execution_mode` |
| Task goal | `data.execution_request.inputs.task_goal` (when present) |

### 3. Execution Result (collapsible)

| Field | Source |
|---|---|
| Result ID | `data.execution_result.execution_result_id` |
| Status | `data.execution_result.status` |
| Adapter | `data.execution_result.adapter` |
| Review required | `data.execution_result.review_required` |
| Evidence count | `data.execution_result.evidence.length` |

### 4. Execution Envelope (collapsible)

| Field | Source |
|---|---|
| Envelope ID | `data.execution_envelope.envelope_id` |
| Status | `data.execution_envelope.status` |
| Schema version | `data.execution_envelope.schema_version` |
| Artifact count | `data.execution_envelope.artifacts.length` |
| Evidence count | `data.execution_envelope.evidence.length` |

### 5. Review Boundary (collapsible)

| Field | Source |
|---|---|
| Decision | `data.review_boundary.decision` |
| Completed | `data.review_boundary.completed` |
| Requires review | `data.review_boundary.requires_review` |
| Blocked | `data.review_boundary.blocked` |
| Failed | `data.review_boundary.failed` |
| Reason code | `data.review_boundary.reason_code` |
| Reasons | `data.review_boundary.reasons` (list, each on its own line) |

### 6. Warnings and Errors (collapsible, only if non-empty)

| Field | Source |
|---|---|
| Warnings | `data.warnings` (list items) |
| Errors | `data.errors` (list items with code + message) |

### 7. Raw JSON (always visible)

The full JSON response rendered in a `<pre>` block, same as PR 0079. Preserved exactly.

## Raw JSON Preservation

The `<pre id="json">` block remains in the page. After each submission, it is populated with `JSON.stringify(data, null, 2)` — the complete response. This ensures that even with structured sections, the raw JSON is always available for inspection.

## Page Behavior

The page works the same way as PR 0079:
1. User types a task in the textarea.
2. User clicks Submit.
3. Page POSTs to `/runs/execute`.
4. Page renders structured sections AND raw JSON.
5. No new backend route.
6. No `/runs/execute` response changes.

The only change is the JavaScript rendering logic: instead of just showing the status and raw JSON, it now also renders the six structured sections described above.

## Execute API Usage

Same as PR 0079: `POST /runs/execute` with `{"task": taskText}`. No change.

## API Preservation

- `POST /runs/execute` unchanged. Same request/response shape, same code path.
- All existing HTTP tests pass without modification.
- No new backend routes.

## Runtime Preservation

- App runtime from PR 0078 unchanged.
- Same `python -m task_intake.app --host 127.0.0.1 --port 8000` command.
- Same `--check --json` non-blocking mode.
- `_ROUTES` list in `app.py` unchanged (no new routes).

## Test Plan

**Test file:** `services/task_intake/tests/test_local_result_structured_view.py`

Tests use the same ASGI test harness pattern as `test_local_interaction_page.py`.

| Test | Expectation |
|---|---|
| `test_page_returns_200` | GET / → 200 |
| `test_page_contains_status_summary_area` | HTML includes element for runtime status display |
| `test_page_contains_execution_request_section` | HTML includes section label for execution request |
| `test_page_contains_execution_result_section` | HTML includes section label for execution result |
| `test_page_contains_execution_envelope_section` | HTML includes section label for execution envelope |
| `test_page_contains_review_boundary_section` | HTML includes section label for review boundary |
| `test_page_contains_warnings_errors_section` | HTML includes section label for warnings/errors |
| `test_page_contains_raw_json_area` | HTML includes `<pre` or raw JSON container |
| `test_page_references_runs_execute` | HTML includes `/runs/execute` |
| `test_page_has_no_external_assets` | No CDN/framework references |
| `test_runs_execute_preserved` | Existing POST /runs/execute still returns runtime_status |
| `test_runs_execute_preserves_envelope` | Response includes execution_envelope |
| `test_runs_execute_preserves_boundary` | Response includes review_boundary |
| `test_app_runtime_check_works` | `build_runtime_config(["--check"])` works |
| `test_test_mode_cli_works` | `test_mode.main(["--task", "test"])` returns 0 |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_result_structured_view.py \
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
grep -R -n "subprocess|os\.system|popen|docker compose|Dockerfile|requests|httpx|urllib|redis|sqlite|import docker|from docker|docker\.from_env|uuid|datetime\.now|time\.time|random|cdn|unpkg|jsdelivr|react|vue|svelte|vite|webpack|npm|yarn|pnpm|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_result_structured_view.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_result_structured_view.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_result_structured_view.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0080-local-result-structured-view/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0080-local-result-structured-view/PLAN.md` (planner only)
- `.project-memory/pr/0080-local-result-structured-view/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/task_intake/src/task_intake/test_mode.py`
- `services/task_intake/tests/test_local_interaction_page.py`
- `services/task_intake/tests/test_execution_handoff_http.py`
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
- backend-only outcome
- no structured result view selected
- raw JSON hidden or removed
- no executable implementation file selected
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

Update inline `_HTML_PAGE` in `server.py` to parse JSON response and render structured sections alongside raw JSON.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_local_result_structured_view.py (new)
```

### structured_sections

1. Status summary (ok, runtime_status)
2. Execution request (collapsible)
3. Execution result (collapsible)
4. Execution envelope (collapsible)
5. Review boundary (collapsible)
6. Warnings/errors (collapsible, only if non-empty)
7. Raw JSON (always visible)

### raw_json_preservation

`<pre id="json">` preserved. `JSON.stringify(data, null, 2)` after every submission.

### page_behavior

Same as PR 0079: textarea + submit button → POST /runs/execute → render sections + raw JSON. No polling, no streaming.

### execute_api_usage

Same as PR 0079: `POST /runs/execute` with `{"task": taskText}`. No change.

### api_preservation

`/runs/execute` unchanged. All HTTP tests pass as-is.

### runtime_preservation

App runtime unchanged. `_ROUTES` unchanged (no new routes).

### validation_strategy

15 tests + full compatibility across all test modules + check command + test-mode CLI + forbidden guards.

### next_pr_notes

After PR 0080, the local page shows structured results. The next PR could add loading state animations, error state display for network failures, or a "copy JSON" button for the raw output.

---

PLAN written: yes
