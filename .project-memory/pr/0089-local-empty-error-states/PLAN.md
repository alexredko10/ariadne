# PR 0089 — Local Empty and Error States Plan

## Goal

Plan frontend-only empty, loading, validation, and error states for the existing Ariadne browser page.

PR 0088 added in-page local run history. PR 0089 must make the local page clearer when there is no run yet, when task input is empty, when a request is running, and when `/runs/execute` fails or returns an unexpected response.

## Implementation Decision

**Decision: Update JS and HTML in `_HTML_PAGE`. Client-side only. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update existing JS to add empty state, validation, loading state, and error handling. Add error panel element.

### New test file

2. **`services/task_intake/tests/test_local_empty_error_states.py`** — tests for all states.

## States

### 1. Empty State (before first run)

The result area below the submit button shows:
- Summary card: hidden or shows "Submit a task to see the run summary."
- Run report: hidden or shows "Run a task to generate a run report."
- Run history: shows "No runs yet. Submit a task to see your run history."
- Execution trace, structured view, raw JSON: hidden or show placeholders.

This is already partially implemented (history shows empty state). PR 0089 makes all result sections show clear empty-state text when no run has completed.

### 2. Inline Task Validation (client-side)

The "Submit" button click handler:
- Checks if the task textarea is empty or whitespace-only.
- If empty: shows an inline validation message below the textarea ("Task text is required.") and does NOT call `/runs/execute`.
- If non-empty: clears the validation message and proceeds.
- The validation message is styled as a small red text.

### 3. Loading/Running State

During the fetch to `/runs/execute`:
- The "Submit" button text changes to "Running…" and the button is disabled.
- A visible loading indicator (a "Running…" message or a CSS animation) appears in the status bar area.
- The button re-enables after the request completes (success or failure).

### 4. Request Failure State

If the fetch fails (network error, non-200 status, or malformed JSON response):
- The status bar shows a red error message: "Request failed: <error message>" or "Unexpected response status: <status>".
- An error panel appears below the status bar with details.
- The previous successful run data (summary card, trace, structured view, raw JSON) **remains visible** — it is NOT cleared by a failed request.
- The local run history is **not** modified by a failed request — only successful responses append to history.
- The error panel includes a "Dismiss" button to hide it.

### 5. Unexpected Response Fallback

If the response JSON is missing expected fields (no `runtime_status`, no `ok`):
- The status bar shows "Unexpected response format."
- The raw JSON `<pre>` is still populated with the full response for debugging.
- A safe fallback message is shown in place of structured sections.

## Previous Data Preservation

- Successful run data remains visible after a failed subsequent request.
- Local run history is not modified by failed requests.
- Only successful responses (fetch ok, JSON parseable, has basic expected fields) trigger state updates.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_empty_error_states.py`

| Test | Expectation |
|---|---|
| `test_empty_state_before_first_run` | Result sections show empty state placeholders |
| `test_empty_task_validated` | Empty task shows inline validation message |
| `test_whitespace_task_validated` | Whitespace-only task shows validation |
| `test_validation_blocks_submit` | No fetch for empty task |
| `test_loading_state_during_submit` | Button shows "Running…" during fetch |
| `test_network_error_preserves_previous` | Failed fetch doesn't clear previous result |
| `test_error_panel_dismissible` | Error panel has dismiss button |
| `test_history_not_modified_on_failure` | Failed request doesn't add to history |
| `test_missing_fields_fallback` | Response without runtime_status shows fallback |
| `test_existing_ui_preserved` | All existing sections present |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_empty_error_states.py \
  services/task_intake/tests/test_local_run_history_in_page.py \
  services/task_intake/tests/test_copy_export_local_run_report.py \
  services/task_intake/tests/test_local_user_test_session_report.py \
  services/task_intake/tests/test_guided_local_user_test_scenarios.py \
  services/task_intake/tests/test_local_user_test_feedback_panel.py \
  services/task_intake/tests/test_local_run_summary_card.py \
  services/task_intake/tests/test_local_execution_trace.py \
  services/task_intake/tests/test_local_runner_selection.py \
  services/task_intake/tests/test_local_result_structured_view.py \
  services/task_intake/tests/test_local_interaction_page.py \
  -q
python -m compileall -f services/task_intake/src services/runner/src
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_empty_error_states.py` (new)

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/deps/build changes, no storage/telemetry.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- states require backend route/storage/telemetry
- existing UI sections hidden or removed
- runner selection removed
- Docker becomes default or runs
- deps/build change

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_local_empty_error_states.py` (new)

### validation strategy

Focused tests for all five states + existing UI preservation + `--check --json`.

### behavior planned

Empty-state placeholders. Inline task validation (blocks submit). Loading indicator (button text + disabled). Error panel (dismissible, preserves previous success). No history modification on failure. Missing-fields fallback.

### boundaries

No backend/storage/telemetry. No framework/build/CDN. No existing UI hidden. No runner/Docker/agent changes.

---

PLAN written: yes
