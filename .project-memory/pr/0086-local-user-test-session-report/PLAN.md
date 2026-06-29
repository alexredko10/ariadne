# PR 0086 — Local User Test Session Report Plan

## Goal

Plan a local user-test session report panel for the existing Ariadne browser page.

PR 0084 added feedback capture. PR 0085 added guided scenarios. PR 0086 must make the first user test actionable by generating one local plain-text session report from the current scenario, latest run, and tester feedback.

## Implementation Decision

**Decision: Add session report panel to `_HTML_PAGE`. Client-side only. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add session report panel in the feedback section, with a "Generate session report" button and a read-only textarea showing the generated report.

### New test file

2. **`services/task_intake/tests/test_local_user_test_session_report.py`** — tests for session report panel.

## Session Report Panel Placement

The session report panel is placed within the feedback section, below the questions/notes and "Copy feedback" button, adding a "Generate session report" button and a read-only report output area.

## Report Fields

The generated plain-text report includes:

```
=== Ariadne User Test Session Report ===

Scenario: <scenario name or "Manual">
Submitted task: <task text>
Selected runner: <noop | docker-agent>
Runtime status: <completed | blocked | ...>
Execution result: <completed | failed | ...>
Review decision: <completed | requires_review | ...>

Tester feedback:
  Understood: Yes/No
  Runner clear: Yes/No
  Summary clear: Yes/No
  Trace useful: Yes/No
  Confusing: <tester text>
  Expected next: <tester text>
  Additional notes: <tester text>

Session generated locally in browser at: <client-side timestamp>
No data was sent to any server.
```

## Report Generation Trigger

A "Generate session report" button. When clicked:
1. Reads the current/demo data from `window.__ariadne_last_run` (a new variable set after each `/runs/execute` response).
2. Reads the feedback panel answers.
3. Reads the scenario name if a scenario button was clicked (tracked via a `window.__ariadne_last_scenario` variable set by `fillScenario`).
4. Generates the plain-text report.
5. Displays it in a read-only textarea below the button.

A "Copy report" button next to the textarea copies it via clipboard API.

## Report Source Data

- Scenario name: from `window.__ariadne_last_scenario` (set by `fillScenario()`, defaults to `"Manual"`).
- Task text: from `document.getElementById("task").value`.
- Runner: from `document.querySelector('input[name="runner"]:checked').value`.
- Run data: from `window.__ariadne_last_run` which contains the full `/runs/execute` response JSON.
- Feedback answers: read from the feedback panel's radio buttons and textareas by ID.

## No Persistence / No Telemetry

Same as feedback panel: generated client-side, shown in-browser, copyable. Never sent to any backend.

## Preservation

All existing UI preserved in the current order: explanation → scenarios → runner selection → task input → submit → summary card → trace → structured result → raw JSON → feedback panel (questions + notes + copy feedback + session report).

## Test Plan

**Test file:** `services/task_intake/tests/test_local_user_test_session_report.py`

| Test | Expectation |
|---|---|
| `test_page_contains_session_report_button` | "Generate session report" button present |
| `test_report_contains_scenario` | Report includes scenario field |
| `test_report_contains_task` | Report includes submitted task |
| `test_report_contains_runner` | Report includes selected runner |
| `test_report_contains_runtime_status` | Report includes runtime_status |
| `test_report_contains_execution_result` | Report includes execution result status |
| `test_report_contains_review_decision` | Report includes review decision |
| `test_report_contains_feedback_answers` | Report includes tester answers |
| `test_report_includes_timestamp` | Report includes client-side timestamp |
| `test_report_no_backend` | No POST route for report |
| `test_existing_ui_preserved` | All existing UI sections present |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_user_test_session_report.py \
  services/task_intake/tests/test_guided_local_user_test_scenarios.py \
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
- `services/task_intake/tests/test_local_user_test_session_report.py` (new)

## Future Forbidden Write Paths

Same as previous PRs.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- session report requires backend/storage/telemetry
- existing UI sections hidden
- runner selection removed
- Docker becomes default or runs
- frontend framework/dependency/build change
- real agent/model/provider change

## Decisions Made

### selected_strategy

Add session report panel to `_HTML_PAGE`. Client-side only. "Generate session report" builds plain-text report from latest run + feedback. Copy button via clipboard API.

### implementation_files

`services/task_intake/src/task_intake/server.py` (modify)

### test_files

`services/task_intake/tests/test_local_user_test_session_report.py` (new)

### preservation

All existing UI preserved.

### validation_strategy

11 tests + full compat + CLI checks.

### next_pr_notes

After PR 0086, the first user test is fully instrumented. Run the test with the guided scenarios, collect feedback and session reports, and iterate on the UI and flow based on findings.

---

PLAN written: yes
