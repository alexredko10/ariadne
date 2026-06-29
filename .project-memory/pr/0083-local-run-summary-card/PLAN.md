# PR 0083 — Local Run Summary Card Plan

## Goal

Plan a minimal local run summary card for the existing Ariadne browser page.

The app now shows runner selection, structured result, raw JSON, and execution trace. The next step is to make the result immediately understandable at a glance.

The page should show a concise summary after submit:

- what happened
- selected/requested runner
- runtime status
- execution result status
- review boundary outcome
- whether this was deterministic/no-op or Docker opt-in boundary
- what the user can inspect next

## Implementation Decision

**Decision: Add a summary card section to `_HTML_PAGE` in `server.py`. Derived from existing `/runs/execute` response. No backend changes.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update `_HTML_PAGE` to add summary card section at the top of the result area.

### New test file

2. **`services/task_intake/tests/test_local_run_summary_card.py`** — tests for summary card content.

**No backend changes.** The summary card is rendered client-side from the existing JSON response.

## Summary Card Sections

The summary card appears at the top of the result area, before the trace, structured view, and raw JSON. It contains:

### Header

```
Ariadne Local Run Summary
```

### Fields

| Field | Source | Example |
|---|---|---|
| Selected runner | `execution_request.requested_adapter` | "noop" or "docker-agent" |
| What happened | Derived from `runtime_status` + runner | "Deterministic local/no-op run completed." or "Docker opt-in boundary — blocked. Enable Docker to execute." |
| Runtime status | `runtime_status` | "completed" (color-coded) |
| Execution result | `execution_result.status` | "completed" |
| Review decision | `review_boundary.decision` | "completed" |
| Evidence | `execution_envelope.evidence.length` | "1 evidence record" |
| Next step | Static text derived from status | "Inspect structured sections below." or "Approve or rerun with different parameters." |

### What happened — derived text

| Condition | Text |
|---|---|
| `runtime_status == "completed"` and adapter contains `"noop"` | "Deterministic local/no-op run completed. No real execution was performed." |
| `runtime_status == "completed"` and adapter contains `"docker"` | "Docker opt-in boundary — completed without Docker. Enable Docker with allow_docker=True to execute." |
| `runtime_status == "blocked"` | "Execution was blocked. Review the review boundary section for details." |
| `runtime_status == "requires_review"` | "Execution completed but requires human review. See review boundary for details." |
| `runtime_status == "failed"` | "Execution failed. Check the errors section for details." |
| `runtime_status == "error"` | "An error occurred. Check the errors section for details." |

### Next step — derived text

| Status | Text |
|---|---|
| `ok == true` | "Inspect the structured sections below for details, or review the raw JSON output." |
| `ok == false` | "Review the errors and warnings sections below to resolve the issue." |
| `review_boundary.requires_review == true` | "Human review is required before proceeding." |

### Styling

- Card layout: light background, rounded corners, subtle border, left accent color
- Status field: color-coded (same green/orange/red as other status displays)
- Compact: single card with key-value pairs, not a full structured view

## Behavior Before/After Submit

**Before submit:** The summary card area is hidden or shows a placeholder message: "Submit a task to see the run summary."

**After submit:** The summary card populates with fields from the response.

## Preservation

- Execution trace: preserved below the summary card
- Structured result view: preserved below the trace
- Raw JSON: preserved at the bottom
- Runner selection: preserved above the submit button

Order after submit: summary card → execution trace → structured result → raw JSON.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_run_summary_card.py`

| Test | Expectation |
|---|---|
| `test_page_contains_summary_card_section` | HTML includes "Ariadne Local Run Summary" or "summary" |
| `test_summary_shows_selected_runner` | Card includes runner field |
| `test_summary_shows_what_happened` | Card includes what happened text |
| `test_summary_shows_runtime_status` | Card includes runtime_status |
| `test_summary_shows_execution_result_status` | Card includes execution_result status |
| `test_summary_shows_review_decision` | Card includes review boundary decision |
| `test_summary_shows_evidence_count` | Card includes evidence count |
| `test_summary_shows_next_step` | Card includes next step text |
| `test_summary_hidden_before_submit` | Card shows placeholder or is hidden before submit |
| `test_trace_preserved` | Trace section remains in page |
| `test_structured_view_preserved` | Structured view section remains |
| `test_raw_json_preserved` | Raw JSON `<pre>` remains |
| `test_runner_selection_preserved` | Radio buttons remain |
| `test_runs_execute_preserved` | POST /runs/execute still works |
| `test_no_external_assets` | No CDN/framework references |
| `test_app_runtime_check_works` | build_runtime_config works |

## Validation Commands

```bash
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
- `services/task_intake/tests/test_local_run_summary_card.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0083-local-run-summary-card/reviews/precommit-review.yml`

## Future Forbidden Write Paths

Same as previous PRs: no backend/runner/schema/docs/dependency changes.

## Stop Conditions

- docs/schema/smoke-only
- no executable UI code planned
- no tests planned
- summary hides trace/structured/raw JSON
- runner selection removed
- local/noop not default
- Docker becomes default or runs
- new backend route
- `/runs/execute` behavior break
- dependency/build change

## Decisions Made

### selected_strategy

Add summary card section to `_HTML_PAGE`. Client-side rendering from existing response. No backend changes.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_local_run_summary_card.py (new)
```

### trace_preservation

Preserved below summary card.

### structured_result_preservation

Preserved below trace.

### raw_json_preservation

Preserved at bottom.

### runner_selection_preservation

Radio buttons unchanged.

### validation_strategy

16 tests + full compat + CLI checks + forbidden guards.

### next_pr_notes

After PR 0083, the local page shows a concise summary card at the top of results. The next step could add approval status selection, or a "Copy summary" button.

---

PLAN written: yes
