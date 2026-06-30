# PR 0091 — Manual Acceptance Checklist Plan

## Goal

Plan a frontend-only manual acceptance checklist for the existing Ariadne browser page.

PR 0090 added first-time user onboarding. PR 0091 must give testers and operators a visible checklist for manually confirming that the local Ariadne flow works before or during a user-test session.

## Implementation Decision

**Decision: Add checklist panel to `_HTML_PAGE`. Client-side only. In-memory checkboxes, no persistence.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add manual acceptance checklist panel near the feedback section, with checkboxes and a reset button.

### New test file

2. **`services/task_intake/tests/test_manual_acceptance_checklist.py`** — tests for checklist panel.

## Checklist Panel Placement

At the top of the feedback section, before the questions. The panel has a header: "Manual Acceptance Checklist" and a "Reset all" button.

## Checklist Items

15 items, each with a checkbox and label:

| # | Label |
|---|---|
| 1 | First-time onboarding is visible and understandable |
| 2 | Scenario can be selected (task prefilled, runner set) |
| 3 | Task can be submitted |
| 4 | Local/no-op remains default |
| 5 | Docker-agent remains opt-in and non-default |
| 6 | Summary card is visible after run |
| 7 | Execution trace is visible after run |
| 8 | Structured result is visible after run |
| 9 | Raw JSON remains available |
| 10 | Feedback can be captured |
| 11 | Session report can be generated |
| 12 | Run report can be copied/exported |
| 13 | Local run history updates |
| 14 | Empty task validation works (inline message shown) |
| 15 | Error state preserves previous run and history |

## Checkbox Behavior

- Each checkbox is a standard `<input type="checkbox">`.
- State is in-memory only (tied to the DOM — lost on page refresh).
- No localStorage, sessionStorage, or backend calls.

## Progress/Count

A small counter below the header: "0/15 checked" that updates as checkboxes are toggled. When all 15 are checked, the text changes to "15/15 — All checks passed."

## Reset Behavior

A "Reset all" button unchecks all checkboxes and resets the counter to "0/15".

## Preservation

All existing UI preserved. The checklist panel is added at the top of the feedback section.

## Test Plan

**Test file:** `services/task_intake/tests/test_manual_acceptance_checklist.py`

| Test | Expectation |
|---|---|
| `test_page_contains_checklist` | "Manual Acceptance Checklist" present |
| `test_checklist_has_15_items` | 15 checkbox items present |
| `test_checklist_item_has_label` | Each item has a text label |
| `test_item_1_onboarding` | Item 1: onboarding |
| `test_item_4_local_noop_default` | Item 4: local/noop default |
| `test_item_5_docker_opt_in` | Item 5: docker-agent opt-in |
| `test_item_14_empty_validation` | Item 14: empty task validation |
| `test_item_15_error_preserves` | Item 15: error preserves previous |
| `test_progress_counter_updates` | Counter shows correct count |
| `test_reset_button` | Reset unchecks all and resets counter |
| `test_no_storage` | No localStorage/sessionStorage used |
| `test_existing_ui_preserved` | All existing sections present |
| `test_no_external_assets` | No CDN/framework references |
| `test_no_forbidden_source_strings` | grep guard for forbidden patterns |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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

# Safety guard for forbidden source strings
grep -R -n "water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_manual_acceptance_checklist.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_manual_acceptance_checklist.py` (new)

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/deps/build changes, no storage/telemetry, no localStorage/sessionStorage.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- checklist requires backend/storage/localStorage/telemetry
- existing UI hidden or removed
- Docker becomes default or runs
- deps/build change

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_manual_acceptance_checklist.py` (new)

### validation strategy

Focused tests for checklist panel, 15 items, progress counter, reset, no-storage guard, existing UI preservation, and forbidden source string guard.

### behavior planned

15-item manual acceptance checklist at top of feedback section. Progress counter. Reset button. In-memory only, no persistence. All existing UI preserved.

### boundaries

No backend/storage/localStorage/telemetry. No framework/build/CDN. No existing UI changes. No runner/Docker/agent changes.

---

PLAN written: yes
