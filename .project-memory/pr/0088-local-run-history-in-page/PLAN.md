# PR 0088 — Local Run History In Page Plan

## Goal

Plan a frontend-only in-page local run history for the existing Ariadne browser page.

PR 0087 added copy/export local run report. PR 0088 must let a tester compare the latest few runs during one browser page session without backend persistence.

## Implementation Decision

**Decision: Add run history panel to `_HTML_PAGE`. Client-side in-memory array. No persistence, no storage, no backend.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add run history panel between the run report and the execution trace. Add JS to push each `/runs/execute` response into a history array.

### New test file

2. **`services/task_intake/tests/test_local_run_history_in_page.py`** — tests for history panel.

## History Panel Placement

Between the run report (PR 0087) and the execution trace (PR 0082). Order after a run: summary card → run report → run history → execution trace → structured view → raw JSON → feedback.

## Max History Entries

10 entries maximum. When the 11th run completes, the oldest entry is removed.

## Source Data

Each entry is built from:
- `window.__ariadne_last_run` (the latest `/runs/execute` response).
- `document.getElementById("task").value` at the time of submission.
- `document.querySelector('input[name="runner"]:checked').value`.
- `window.__ariadne_last_scenario` (if a scenario button was used).
- A local `Date()` generated client-side when the push happens.

## When an Entry Is Added

After each successful `/runs/execute` response (after setting `window.__ariadne_last_run`), the JS pushes an entry to `window.__ariadne_run_history` — a plain JS array.

## Empty State

Before the first run: "No runs yet. Submit a task to see your run history."

## Behavior After Multiple Runs

Each new run appends to the top of the list (newest first). The list shows:

```
#3 — completed — "Implement JWT auth" — noop — 2026-06-30T12:00:00
#2 — completed — "Add validation" — noop — 2026-06-30T11:55:00
#1 — blocked — "Run tests" — docker-agent — 2026-06-30T11:50:00
```

Each entry shows: index, runtime status (color-coded), task text (truncated to 60 chars), selected runner, and local timestamp.

Entries are not individually copyable (the run report covers that). They serve as a visual comparison of the session's runs.

## Clear History

A "Clear history" button removes all entries from the in-memory array and re-renders the empty state.

## No Persistence

The history is a plain JS array in memory. It is lost on page refresh. No `localStorage`, `sessionStorage`, cookies, or backend storage.

## Behavior When Feedback/Session Data Exists

No change — history is independent of feedback. Feedback is captured in the feedback panel and session report.

## Preservation

All existing UI preserved. Order: summary card → run report → **run history** → execution trace → structured view → raw JSON → feedback.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_run_history_in_page.py`

| Test | Expectation |
|---|---|
| `test_page_contains_run_history_panel` | "Run history" section present |
| `test_history_empty_before_submit` | Shows "No runs yet" before any run |
| `test_history_appends_after_submit` | History has entries after run |
| `test_history_max_entries` | Array capped at 10 entries |
| `test_history_clear_button` | Clear button removes all entries |
| `test_history_no_persistence` | No localStorage/sessionStorage used |
| `test_existing_ui_preserved` | All existing sections present |
| `test_no_external_assets` | No CDN/framework references |
| `test_app_runtime_check_works` | `--check --json` works |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
- `services/task_intake/tests/test_local_run_history_in_page.py` (new)

## Future Forbidden Write Paths

- `services/runner/**`, `execution_handoff.py`, `app.py`, `test_mode.py`
- `schemas/**`, `docs/**`, `pyproject.toml`, `package.json`, `Makefile`
- `docker/**`, `Dockerfile*`
- `.ariadne/**`, `.grace/**`
- New backend routes, storage/persistence, telemetry

## Stop Conditions

- docs/schema/smoke/review-artifact-only outcome
- implementation requires backend/storage/telemetry
- implementation requires frontend framework/CDN/npm/build
- implementation modifies files outside exact planned scope
- existing UI sections hidden or removed
- runner selection removed
- Docker becomes default or runs
- real agent/model/provider calls
- old forbidden legacy names/examples
- shell placeholders

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_local_run_history_in_page.py` (new)

### validation strategy

Focused tests on history panel + existing local UI tests + `--check --json`.

### behavior planned

In-memory array capped at 10 entries. Newest first. Appends after each /runs/execute response. Clear history button. No persistence (lost on refresh).

### boundaries

No backend/storage/telemetry. No framework/build/CDN. No existing UI changes. No runner/Docker/agent changes.

---

PLAN written: yes
