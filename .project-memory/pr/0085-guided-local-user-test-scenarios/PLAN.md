# PR 0085 — Guided Local User Test Scenarios Plan

## Goal

Plan guided local user-test scenarios for the existing Ariadne browser page.

PR 0084 added a local feedback panel. PR 0085 must make the first user test repeatable by adding visible in-page scenarios that guide testers through the same flow.

## Implementation Decision

**Decision: Add scenario panel to `_HTML_PAGE`. Client-side only. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add scenario panel between explanation and runner selection.

### New test file

2. **`services/task_intake/tests/test_guided_local_user_test_scenarios.py`** — tests for scenario panel.

## Scenario Panel Placement

The scenario panel appears between the explanation panel and the runner selection fieldset. It is always visible.

## Scenarios

| # | Label | Prefilled task | Runner selection | Auto-submit |
|---|---|---|---|---|
| 1 | Default local/no-op run | "Implement a JWT authentication middleware for FastAPI" | Sets runner to "noop" (no change from default) | No |
| 2 | Inspect summary and trace | "Add input validation to all API endpoints" | Sets runner to "noop" (no change from default) | No |
| 3 | Docker-agent opt-in boundary | "Run unit tests on the authentication module" | Sets runner to "docker-agent" | No |
| 4 | Generate user-test feedback | "Create a health check endpoint" | Sets runner to "noop" (no change from default) | No |

## Behavior

Each scenario is a clickable button or card. Clicking it:

1. Fills the task textarea with the prefilled task text.
2. Selects the corresponding runner radio button.
3. Does NOT auto-submit. The tester must click "Submit" manually.

This ensures the tester sees what the request looks like before submitting, and the flow is controlled.

## Per-Scenario Runner Selection

- Scenarios 1, 2, 4: Prefill task and set runner to `"noop"` (which is already the default — no visible change, but ensures consistency).
- Scenario 3: Prefill task and set runner to `"docker-agent"`. Tests the Docker opt-in boundary explicitly.

## Scenario Panel UI

```html
<fieldset id="scenarios">
  <legend>Guided scenarios</legend>
  <p>Click a scenario to prefill the task and runner, then click Submit.</p>
  <div id="scenario-buttons">
    <button onclick="fillScenario('noop', 'Implement a JWT authentication middleware for FastAPI')">
      Default local/no-op run
    </button>
    <button onclick="fillScenario('noop', 'Add input validation to all API endpoints')">
      Inspect summary and trace
    </button>
    <button onclick="fillScenario('docker-agent', 'Run unit tests on the authentication module')">
      Docker-agent opt-in boundary
    </button>
    <button onclick="fillScenario('noop', 'Create a health check endpoint')">
      Generate user-test feedback
    </button>
  </div>
</fieldset>
```

## Preservation

All existing UI elements preserved in order: explanation panel → scenario panel → runner selection → task input → submit → summary card → trace → structured result → raw JSON → feedback panel.

## Test Plan

**Test file:** `services/task_intake/tests/test_guided_local_user_test_scenarios.py`

| Test | Expectation |
|---|---|
| `test_page_contains_scenario_panel` | HTML includes "Guided scenarios" |
| `test_has_default_local_run_scenario` | Scenario 1 button present |
| `test_has_inspect_trace_scenario` | Scenario 2 button present |
| `test_has_docker_opt_in_scenario` | Scenario 3 button present |
| `test_has_generate_feedback_scenario` | Scenario 4 button present |
| `test_scenario_fills_task_textarea` | Scenario button onclick fills textarea |
| `test_scenario_selects_runner` | Scenario button onclick selects runner radio |
| `test_noop_remains_default` | Default runner is noop |
| `test_no_auto_submit` | No button calls submit automatically |
| `test_existing_ui_preserved` | Summary, trace, structured, raw JSON, runner, feedback all present |
| `test_no_external_assets` | No CDN/framework references |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
- `services/task_intake/tests/test_guided_local_user_test_scenarios.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0085-guided-local-user-test-scenarios/reviews/precommit-review.yml`

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/deps/build changes, no storage/telemetry.

## Stop Conditions

- docs/schema/smoke-only outcome
- no executable UI code planned
- no tests planned
- scenario requires backend/storage/telemetry
- existing UI sections hidden or removed
- runner selection removed
- Docker becomes default or runs
- deps/build change

## Decisions Made

### selected_strategy

Add scenario panel to `_HTML_PAGE`. Client-side only. Prefills task and runner, no auto-submit.

### implementation_files

`services/task_intake/src/task_intake/server.py` (modify)

### test_files

`services/task_intake/tests/test_guided_local_user_test_scenarios.py` (new)

### preservation

All existing UI preserved. Scenario panel added between explanation and runner selection.

### validation_strategy

11 tests + full compat + CLI checks.

### next_pr_notes

After PR 0085, the first controlled user test is repeatable. Run the test, collect feedback via the panel, and iterate.

---

PLAN written: yes
