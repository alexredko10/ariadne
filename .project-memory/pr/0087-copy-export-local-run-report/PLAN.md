# PR 0087 — Copy/Export Local Run Report Plan

## Goal

Plan a frontend-only copy/export local run report feature for the existing Ariadne browser page.

PR 0086 added a local user-test session report. PR 0087 must add a general latest-run report that is useful outside a user-test session: copyable plain text and optional browser-local export generated from existing page state.

## Implementation Decision

**Decision: Add general run report panel to `_HTML_PAGE` near the summary card. Client-side only. Copy + optional Blob download. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — add run report panel below the summary card, above the trace.

### New test file

2. **`services/task_intake/tests/test_copy_export_local_run_report.py`** — tests for run report panel.

## Report Panel Placement

The run report panel is placed between the summary card and the execution trace. This makes it the second thing the user sees after a run (summary → run report → trace → structured view → raw JSON → feedback).

## Report Fields

```
=== Ariadne Local Run Report ===

Submitted task: <task text>
Selected runner: <noop | docker-agent>
Runtime status: <completed | blocked | ...>
Execution result: <completed | failed | ...>
Review decision: <completed | requires_review | ...>
Summary card: <deterministic run completed | Docker opt-in boundary | ...>

=== Execution Trace ===
1. Task received ✅
2. Execution request built ✅
3. Handoff prepared ✅
4. Local harness invoked ✅
5. Runner selected: <adapter>
6. Execution result returned: <status>
7. Execution envelope created: <envelope_id>
8. Review boundary derived: <decision>

=== Related feedback ===
<clipped from session report if present>

---

Generated in browser at: <client-side timestamp>
No data was sent to any server.
```

## Copy Behavior

A "Copy report" button copies the plain-text report to clipboard via `navigator.clipboard.writeText()`. A fallback selects the text in a read-only textarea if clipboard API is unavailable.

## Optional Export (Browser-Local Only)

An "Download report (.txt)" button creates a `Blob` with the report text and triggers a download via `URL.createObjectURL()` + `<a>` click. No server interaction — entirely browser-local.

## Source Data

Same pattern as session report:
- `window.__ariadne_last_run` for the latest `/runs/execute` response.
- `window.__ariadne_last_scenario` for scenario name.
- Feedback panel element values (by ID) if feedback panel exists and has answers.
- Task text, runner value from page elements.

## Empty-State Behavior

Before the first run, the report area shows: "Run a task to generate a run report." No generate button is visible until a run completes.

## Behavior After Successful Run

After each `/runs/execute` response:
1. The `Generate run report` button becomes visible.
2. Clicking it populates the report textarea and enables the copy/download buttons.

## Behavior When Feedback/Session Report Data Exists

If the feedback panel has answers, the report includes a "Related feedback" section with a brief summary of the tester's answers.

## Preservation

All existing UI preserved. Order: summary card → run report panel → execution trace → structured view → raw JSON → feedback panel.

## Test Plan

**Test file:** `services/task_intake/tests/test_copy_export_local_run_report.py`

| Test | Expectation |
|---|---|
| `test_page_contains_run_report_panel` | "Run report" section present |
| `test_run_report_contains_task` | Report includes submitted task |
| `test_run_report_contains_runner` | Report includes selected runner |
| `test_run_report_contains_runtime_status` | Report includes runtime_status |
| `test_run_report_contains_execution_result` | Report includes execution result |
| `test_run_report_contains_review_decision` | Report includes review decision |
| `test_run_report_includes_trace_steps` | Report includes trace steps |
| `test_run_report_has_copy_button` | Copy button present |
| `test_run_report_has_download_button` | Download button present |
| `test_run_report_hidden_before_submit` | Report area shows placeholder before first run |
| `test_existing_ui_preserved` | All existing sections present |
| `test_no_external_assets` | No CDN/framework references |
| `test_app_runtime_check_works` | `--check --json` works |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
- `services/task_intake/tests/test_copy_export_local_run_report.py` (new)

## Future Forbidden Write Paths

- `services/runner/**`, `execution_handoff.py`, `app.py`, `test_mode.py`
- `schemas/**`, `docs/**`, `pyproject.toml`, `package.json`, `Makefile`
- `docker/**`, `Dockerfile*`
- `.ariadne/**`, `.grace/**`
- New backend routes, storage, telemetry, external services

## Stop Conditions

- docs/schema/smoke/review-artifact-only outcome
- implementation requires backend route/storage/telemetry
- implementation requires frontend framework/CDN/npm/build
- implementation modifies files outside exact planned scope
- existing UI sections hidden or removed
- runner selection removed
- Docker becomes default or runs
- real agent/model/provider calls introduced
- old forbidden legacy names/examples introduced
- shell placeholders introduced

## Decisions Made

### implementation files

`services/task_intake/src/task_intake/server.py` (modify)

### test files

`services/task_intake/tests/test_copy_export_local_run_report.py` (new)

### validation strategy

Focused tests on new panel + existing local UI tests + app runtime check. No wide backend test discovery.

### behavior planned

General run report panel below summary card. Copy + download buttons. Client-side only. Empty-state placeholder before first run. Includes trace steps and optional feedback summary.

### boundaries

No backend/storage/telemetry. No framework/build/CDN. No existing UI changes. No runner/Docker/agent changes.

---

PLAN written: yes
