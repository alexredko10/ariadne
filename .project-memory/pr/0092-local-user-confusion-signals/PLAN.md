# PR 0092 — Local User Confusion Signals Plan

## Goal

Plan frontend-only visible user confusion signals for the existing Ariadne browser page.

PR 0091 added a manual acceptance checklist. PR 0092 must let a local tester mark moments of confusion during a user-test session so the existing local report/feedback flow becomes more actionable.

## Implementation Decision

**Decision: Add confusion signals panel to `_HTML_PAGE`. Client-side in-memory signals. No backend/persistence.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add confusion signals panel with category buttons, optional note, signal list display, and clear button.

### New test file

2. **`services/task_intake/tests/test_local_user_confusion_signals.py`** — tests for confusion signals panel.

## Confusion Signals Panel Placement

Below the manual acceptance checklist, inside the feedback section. Order: checklist → confusion signals → feedback questions → session report → run report (existing).

## Signal Categories

Four buttons, each recording a signal with a timestamp:

| Category | Button label | Signal recorded |
|---|---|---|
| Unclear next step | "Unclear next step" | `{type: "unclear_next_step", note: "..."}` |
| Unexpected result | "Unexpected result" | `{type: "unexpected_result", note: "..."}` |
| Runner confusion | "Runner confusion" | `{type: "runner_confusion", note: "..."}` |
| Report/export confusion | "Report/export confusion" | `{type: "report_export_confusion", note: "..."}` |

## Button/Input Behavior

- Clicking a category button appends a signal to an in-memory array.
- Each button click opens a small inline textarea for an optional note (or the note field appears below the buttons after clicking).
- A line per signal is added to a visible list below the buttons, showing type and note text.
- If the existing session report is generated, it includes the confusion signals with their notes.

## In-Memory Signal List

Signals are stored in `window.__ariadne_confusion_signals` — a plain JS array. Each entry: `{type: string, note: string, timestamp: string}`. Lost on page refresh.

## Clear/Remove

A "Clear all signals" button empties the array and re-renders the list.

## Integration with Session Report

The existing "Generate session report" button (PR 0086) should include confusion signals if present. The session report textarea's content is extended with a "=== Confusion Signals ===" section listing each signal.

This requires a small update to the existing session report generation JS — no backend changes.

## Preservation

All existing UI preserved. Confusion signals panel placed in the feedback section.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_user_confusion_signals.py`

| Test | Expectation |
|---|---|
| `test_page_contains_confusion_panel` | "Confusion signals" or similar label present |
| `test_has_unclear_next_step_button` | "Unclear next step" button present |
| `test_has_unexpected_result_button` | "Unexpected result" button present |
| `test_has_runner_confusion_button` | "Runner confusion" button present |
| `test_has_report_export_confusion_button` | "Report/export confusion" button present |
| `test_clicking_button_adds_signal` | Signal appears in list after click |
| `test_note_field_available` | Optional note textarea present |
| `test_signal_list_visible` | Signal list is rendered |
| `test_clear_all_button` | Clear removes all signals |
| `test_signals_in_memory_only` | No localStorage/sessionStorage used |
| `test_session_report_includes_signals` | Session report includes confusion signals section |
| `test_existing_ui_preserved` | All existing sections present |
| `test_no_forbidden_source_strings` | grep guard for forbidden patterns |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_user_confusion_signals.py \
  services/task_intake/tests/test_manual_acceptance_checklist.py \
  services/task_intake/tests/test_first_time_user_onboarding_panel.py \
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

# Safety guard
grep -R -n "water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_user_confusion_signals.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_user_confusion_signals.py` (new)

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/deps/build changes, no storage/localStorage/telemetry.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- signals require backend/storage/telemetry
- existing UI hidden or removed
- Docker becomes default or runs
- deps/build change

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_local_user_confusion_signals.py` (new)

### validation strategy

Focused tests for signal panel, 4 category buttons, note, list, clear, session report integration, in-memory guard, existing UI preservation, forbidden source string guard.

### behavior planned

4 confusion signal category buttons with optional notes. In-memory array. Clear button. Session report includes signals section. All existing UI preserved.

### boundaries

No backend/storage/localStorage/telemetry. No framework/build/CDN. No existing UI changes. No runner/Docker/agent changes.

---

PLAN written: yes
