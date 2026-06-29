# PR 0082 — Visible Local Execution Trace Plan

## Goal

Plan a minimal visible local execution trace for Ariadne's local browser page.

The app already runs locally and explains runner selection. PR 0082 must make the user see the execution path clearly:

```
task → execution request → handoff → harness → runner → result → envelope → review boundary
```

## Implementation Decision

**Decision: Add an execution trace section to `_HTML_PAGE` in `server.py`. Trace is rendered client-side from the existing `/runs/execute` response.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update `_HTML_PAGE` to add execution trace section.

### New test file

2. **`services/task_intake/tests/test_local_execution_trace.py`** — tests for trace content.

**No backend changes.** The trace is derived entirely from the existing `/runs/execute` JSON response.

## Trace Steps

The trace shows 8 steps, each with a status indicator (completed, active, pending):

| # | Step | Status when complete | Rendered from |
|---|---|---|---|
| 1 | Task received | Completed | Response received |
| 2 | Execution request built | Completed | `execution_request` present |
| 3 | Handoff prepared | Completed | `handoff` path used (implied by response) |
| 4 | Local harness invoked | Completed | `execution_envelope` present |
| 5 | Runner selected | Completed | `execution_result.adapter` |
| 6 | Execution result returned | Completed | `execution_result.status` |
| 7 | Execution envelope created | Completed | `execution_envelope.envelope_id` |
| 8 | Review boundary derived | Completed | `review_boundary.decision` |

The trace shows which runner was selected (step 5 displays the adapter name: "noop-v1" or "docker-agent-v1").

The trace shows the final runtime status (step 8 shows the review boundary decision).

## Trace Rendering

The trace is rendered as a vertical step list with:

- Step number (1–8)
- Step label (e.g., "Task received")
- Status indicator: ✅ completed, ⏳ active, ⬜ pending
- For step 5, the adapter name is shown inline
- For step 8, the review boundary decision is shown inline

The trace replaces placeholders with data from the JSON response after submission.

**Before submission:** The trace shows all 8 steps with ⬜ pending indicators and a message like "Submit a task to see the execution trace."

**After submission:** Steps 1–8 show ✅ completed indicators with inline data from the response.

## Response Source

The trace is rendered from the existing `/runs/execute` response. No backend modification needed. The JavaScript reads:

- `data.execution_request.requested_adapter` for step 5 adapter name
- `data.execution_result.status` for step 6 status
- `data.execution_envelope.envelope_id` for step 7 envelope presence
- `data.review_boundary.decision` for step 8 decision

## Execute API Reuse

Same `POST /runs/execute` flow. No change. The trace is rendered client-side in the existing JavaScript click handler.

## Structured Result Preservation

The existing structured result view (status summary, execution request, execution result, envelope, review boundary, warnings/errors) remains visible below the trace. The trace is the first output section, followed by the structured view, followed by raw JSON.

## Raw JSON Preservation

The `<pre id="json">` remains at the bottom. No change.

## Runner Selection Preservation

Radio buttons (`noop` default, `docker-agent` opt-in) remain unchanged.

## Docker Opt-In Preservation

Docker agent remains opt-in. The trace displays "docker-agent-v1" when selected, and `blocked` status because Docker doesn't run.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_execution_trace.py`

| Test | Expectation |
|---|---|
| `test_page_contains_execution_trace_section` | HTML includes "Execution Trace" or "trace" |
| `test_trace_contains_task_received_step` | HTML includes "Task received" |
| `test_trace_contains_execution_request_step` | HTML includes "Execution request built" |
| `test_trace_contains_handoff_step` | HTML includes "Handoff prepared" |
| `test_trace_contains_harness_step` | HTML includes "Local harness invoked" |
| `test_trace_contains_runner_step` | HTML includes "Runner selected" |
| `test_trace_contains_result_step` | HTML includes "Execution result returned" |
| `test_trace_contains_envelope_step` | HTML includes "Execution envelope created" |
| `test_trace_contains_review_step` | HTML includes "Review boundary derived" |
| `test_trace_has_placeholder_state_before_submit` | Trace shows pending indicators |
| `test_page_still_has_structured_view` | Structured view section remains |
| `test_page_still_has_raw_json` | Raw JSON `<pre>` remains |
| `test_runner_selection_preserved` | Radio buttons remain |
| `test_runs_execute_preserved` | POST /runs/execute still returns runtime_status |
| `test_no_external_assets` | No CDN/framework references |
| `test_app_runtime_check_works` | build_runtime_config works |
| `test_test_mode_cli_works` | test_mode CLI works |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json
grep -R -n "subprocess|os\.system|popen|docker compose|Dockerfile|requests|httpx|urllib|redis|sqlite|import docker|from docker|docker\.from_env|uuid|datetime\.now|time\.time|random|cdn|unpkg|jsdelivr|react|vue|svelte|vite|webpack|npm|yarn|pnpm|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_execution_trace.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_execution_trace.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_execution_trace.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0082-visible-local-execution-trace/reviews/precommit-review.yml`

## Future Forbidden Write Paths

Same pattern as previous PRs: no backend changes, no runner changes, no assets, no dependencies.

## Stop Conditions

- docs-only/schemas-only/smoke-test-only/backend-only outcome
- no visible execution trace planned
- trace requires new backend route or `/runs/execute` changes
- trace hides structured result view, raw JSON, or runner selection
- runner selection removed
- local/noop not default
- Docker adapter becomes default
- Docker daemon required
- real agent execution required
- model/provider calls required
- execution_handoff/local_harness bypass required
- frontend framework/build system/external assets/CDN required
- dependency/build changes required
- persistence/auth/users required
- broad write paths
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Add execution trace section to `_HTML_PAGE`. Client-side rendering from existing response. No backend changes.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_local_execution_trace.py (new)
```

### trace_steps

8 steps: Task received → Execution request built → Handoff prepared → Local harness invoked → Runner selected → Execution result returned → Execution envelope created → Review boundary derived.

### trace_rendering

Vertical step list with ✅/⏳/⬜ indicators. Before submission: all pending with message. After submission: all completed with inline data (adapter name for step 5, decision for step 8).

### response_source

Existing `/runs/execute` response. Fields: `execution_request.requested_adapter`, `execution_result.status`, `execution_envelope.envelope_id`, `review_boundary.decision`.

### execute_api_usage

Unchanged. Same `POST /runs/execute` with `{"task": "...", "requested_adapter": "..."}`.

### structured_result_preservation

Preserved below the trace. Order: trace → structured view → raw JSON.

### raw_json_preservation

Preserved at bottom.

### runner_selection_preservation

Radio buttons unchanged.

### docker_opt_in_preservation

Unchanged. Adapter name shown in trace when Docker selected.

### validation_strategy

17 tests + full compat + CLI checks + forbidden guards.

### next_pr_notes

After PR 0082, the local page shows a clear execution trace. The next PR could add configurable parameters (e.g., approval status) to the runner selection UI, or add a button to copy the trace output.

---

PLAN written: yes
