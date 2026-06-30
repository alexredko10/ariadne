# PR 0090 — First-Time User Onboarding Panel Plan

## Goal

Plan a frontend-only first-time user onboarding panel for the existing Ariadne browser page.

PR 0089 improved empty, loading, validation, and error states. PR 0090 must help a first-time tester understand what Ariadne is, what the local/noop runner means, what docker-agent opt-in means, and what to do next on the page.

## Implementation Decision

**Decision: Add onboarding panel to `_HTML_PAGE`. Client-side only. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add onboarding panel at the top of the page, above the explanation panel. Add dismiss behavior via in-memory flag (no persistence).

### New test file

2. **`services/task_intake/tests/test_first_time_user_onboarding_panel.py`** — tests for onboarding panel.

## Onboarding Panel Placement

At the very top of the page, above the existing explanation panel. Prominent but dismissible.

## First-Time Explanation Text

The panel is a prominent box with:

**Header:** "Welcome to Ariadne"

**Content:**
- Ariadne is a local execution substrate for agentic software development.
- It accepts a task, builds an execution request, dispatches it through a selected runner, and returns a deterministic result with an execution envelope and review boundary.
- **Local/no-op runner (default):** A deterministic simulation that returns results without executing any real work. No Docker daemon, no process spawning, no network calls.
- **Docker agent runner (opt-in):** A boundary that runs tasks in a Docker container. Must be explicitly selected. Selecting it returns a structured blocked result without running Docker — enabling real execution requires additional configuration.
- After submitting a task, inspect the summary card, execution trace, structured result, and raw JSON.
- Use the feedback panel to capture your observations.

## Step-by-Step Local Flow

A compact numbered list below the explanation:

1. Select a guided scenario or type your own task.
2. Choose a runner (local/no-op default, docker-agent opt-in).
3. Click Submit.
4. Inspect the summary card, execution trace, and structured result.
5. Use the feedback panel to record observations.
6. Generate and copy a run report.

## Dismiss Behavior

The panel has a "Dismiss" button. Clicking it hides the panel for the current page session via an in-memory JS flag. No cookies, no localStorage, no backend — it reappears on page refresh.

## Preservation

All existing UI sections preserved below the onboarding panel: explanation → scenarios → runner selection → task input → submit → summary card → run report → run history → trace → structured view → raw JSON → feedback.

## Test Plan

**Test file:** `services/task_intake/tests/test_first_time_user_onboarding_panel.py`

| Test | Expectation |
|---|---|
| `test_page_contains_onboarding_panel` | "Welcome to Ariadne" or "onboarding" present |
| `test_onboarding_explains_local_noop` | "Local/no-op" explained |
| `test_onboarding_explains_docker_opt_in` | "Docker agent" and "opt-in" explained |
| `test_onboarding_has_step_by_step` | Numbered steps present |
| `test_onboarding_has_dismiss_button` | Dismiss button present |
| `test_dismiss_hides_panel` | Clicking dismiss hides the panel |
| `test_dismiss_in_memory_only` | Panel reappears on page refresh (no storage) |
| `test_explanation_panel_preserved` | Existing explanation panel below onboarding |
| `test_existing_ui_preserved` | All existing sections present |
| `test_no_external_assets` | No CDN/framework references |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_first_time_user_onboarding_panel.py` (new)

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/deps/build changes, no storage/telemetry.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- onboarding requires backend/storage/telemetry
- existing UI hidden or removed
- Docker becomes default or runs
- deps/build change

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_first_time_user_onboarding_panel.py` (new)

### validation strategy

Focused tests for panel presence, content, dismiss behavior, and existing UI preservation.

### behavior planned

Prominent onboarding panel at top of page. Explains Ariadne, local/noop default, docker-agent opt-in. Numbered step-by-step flow. Dismiss via in-memory flag (reappears on refresh). No persistence.

### boundaries

No backend/storage/telemetry. No framework/build/CDN. No existing UI changes. No runner/Docker/agent changes.

---

PLAN written: yes
