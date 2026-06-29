# PR 0084 — Local User Test Feedback Panel Plan

## Goal

Plan a minimal local user-test feedback panel for the existing Ariadne browser page.

Ariadne already runs locally and shows summary, trace, structured result, raw JSON, and runner selection. PR 0084 must make the app ready for the first controlled user test by adding an in-page way to capture what the tester understood or found confusing.

## Implementation Decision

**Decision: Add feedback panel to `_HTML_PAGE`. Client-side only. No backend routes, no storage, no telemetry.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update `_HTML_PAGE` to add feedback panel after the result area.

### New test file

2. **`services/task_intake/tests/test_local_user_test_feedback_panel.py`** — tests for feedback panel content.

## Feedback Panel Placement

The panel appears below the raw JSON section, at the bottom of the page. It is always visible (does not require a submission to be present).

## User-Test Questions (checkbox)

Six questions, each with a yes/no checkbox pair:

| # | Question | Field name |
|---|---|---|
| 1 | Did you understand what Ariadne does? | q_understood |
| 2 | Was runner selection clear? | q_runner_clear |
| 3 | Was the summary card clear? | q_summary_clear |
| 4 | Was the execution trace useful? | q_trace_useful |
| 5 | What was confusing? | q_confusing (textarea) |
| 6 | What would you expect Ariadne to do next? | q_expect_next (textarea) |

Each yes/no pair is a radio group with two options (Yes/No) and a default of neither selected.

Questions 5 and 6 are free-text textareas.

## Notes Field

A single notes textarea below the questions: "Additional notes (optional)".

## Generated Copyable Feedback Summary

A "Generate & copy feedback" button that builds a plain-text summary from:
- Latest run summary (if available): selected runner, runtime status, result status, review decision
- Question answers (Yes/No or text)
- Notes

The generated text is copied to the clipboard via `navigator.clipboard.writeText()`. If clipboard API is unavailable, the text is shown in a read-only textarea for manual copying.

**Generated feedback shape:**

```
=== Ariadne Local User Test Feedback ===

Run summary:
  Selected runner: noop
  Runtime status: completed
  Execution result: completed
  Review decision: completed

Questions:
  1. Did you understand what Ariadne does? Yes
  2. Was runner selection clear? Yes
  3. Was the summary card clear? Yes
  4. Was the execution trace useful? Yes
  5. What was confusing? (none)
  6. What would you expect Ariadne to do next? Run a real coder agent

Additional notes: (none)
```

If no run has been submitted yet, the "Run summary" section shows "No run submitted yet."

## Preservation

All existing UI elements are preserved in the same order: summary card → trace → structured result → raw JSON → feedback panel.

## No Persistence / No Telemetry

The feedback is never sent to any backend. It is only shown in the browser and copied via the clipboard API. This is explicitly documented in comments and enforced by code review.

No new backend route. No storage. No network calls.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_user_test_feedback_panel.py`

| Test | Expectation |
|---|---|
| `test_page_contains_feedback_panel` | HTML includes "Feedback" or "user test" |
| `test_feedback_has_understanding_question` | Question 1 present |
| `test_feedback_has_runner_clarity_question` | Question 2 present |
| `test_feedback_has_summary_clarity_question` | Question 3 present |
| `test_feedback_has_trace_question` | Question 4 present |
| `test_feedback_has_confusing_question` | Question 5 textarea present |
| `test_feedback_has_expectation_question` | Question 6 textarea present |
| `test_feedback_has_notes_field` | Notes textarea present |
| `test_feedback_has_generate_button` | Generate/copy button present |
| `test_feedback_no_backend_route` | No POST route for feedback |
| `test_summary_card_preserved` | Summary card section remains |
| `test_trace_preserved` | Trace section remains |
| `test_structured_view_preserved` | Structured view remains |
| `test_raw_json_preserved` | Raw JSON remains |
| `test_runner_selection_preserved` | Radio buttons remain |
| `test_runs_execute_preserved` | POST /runs/execute works |
| `test_no_external_assets` | No CDN/framework references |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_user_test_feedback_panel.py \
  services/task_intake/tests/test_local_run_summary_card.py \
  services/task_intake/tests/test_local_execution_trace.py \
  services/task_intake/tests/test_local_runner_selection.py \
  services/task_intake/tests/test_local_result_structured_view.py \
  services/task_intake/tests/test_local_interaction_page.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  services/task_intake/tests/test_task_intake_http.py \
  services/task_intake/tests/test_app_runtime.py \
  services/task_intake/tests/test_test_mode.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_docker_agent_adapter.py \
  -q
python -m compileall -f services/task_intake/src services/runner/src
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_user_test_feedback_panel.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0084-local-user-test-feedback-panel/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `services/runner/**`, `execution_handoff.py`, `app.py`, `test_mode.py`
- `schemas/**`, `docs/**`, `pyproject.toml`, `package.json`, `Makefile`
- `docker/**`, `Dockerfile*`
- `.ariadne/**`, `.grace/**`
- New backend routes, persistence, telemetry, external services

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- feedback requires backend route/storage/telemetry
- summary/trace/structured/raw JSON hidden
- runner selection removed
- local/noop not default
- Docker becomes default or runs
- real agent/model/provider/deps/build change

## Decisions Made

### selected_strategy

Add feedback panel to `_HTML_PAGE`. Client-side only. No backend, no persistence, no telemetry.

### implementation_files

`services/task_intake/src/task_intake/server.py` (modify)

### test_files

`services/task_intake/tests/test_local_user_test_feedback_panel.py` (new)

### preservation

All existing UI (summary card, trace, structured result, raw JSON, runner selection) preserved. Feedback panel added at bottom.

### validation_strategy

17 tests + full compat + CLI checks + no-backend-route verification.

### next_pr_notes

After PR 0084, Ariadne is ready for the first controlled user test. The next step is to run the test, collect feedback, and iterate on the UI based on what testers found confusing.

---

PLAN written: yes
