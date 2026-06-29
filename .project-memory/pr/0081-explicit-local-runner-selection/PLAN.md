# PR 0081 — Explicit Local Runner Selection Plan

## Goal

Plan a minimal UI and request-path improvement that makes Ariadne understandable to a local user.

The local page must clearly explain what Ariadne currently does and must expose explicit runner selection:

- local / noop deterministic mode as the default
- docker-agent as explicit opt-in boundary only

## Implementation Decision

**Decision: Update `_HTML_PAGE` in `server.py` to add explanation panel and runner selection radio buttons. The page sends `requested_adapter` in the request payload based on selection.**

### Modified file

1. **`services/task_intake/src/task_intake/server.py`** — update `_HTML_PAGE` with explanation panel, runner selection UI, and updated JS to send `requested_adapter`.

### New test file

2. **`services/task_intake/tests/test_local_runner_selection.py`** — tests for runner selection UI behavior.

**No changes to backend logic.** The `execution_handoff.py` already reads `raw.get("requested_adapter", "noop")`. No modification needed.

**Not modified:**
- `execution_handoff.py` — no changes needed.
- `adapter_registry.py`, `docker_agent_adapter.py`, `local_harness.py` — no changes.
- `app.py` — no changes.
- `test_mode.py` — no changes.
- `services/runner/**` — no changes.

## Explanation Panel

Added at the top of the page, before the task input:

```html
<div id="explanation">
  <p>Ariadne turns your task into an execution request.</p>
  <p>The local harness dispatches the request to a selected runner adapter.</p>
  <p><strong>Default mode is deterministic local/no-op.</strong></p>
  <p>No real agent execution happens by default.</p>
  <p>Docker agent is an explicit opt-in boundary. Selecting it returns a structured result without running Docker.</p>
  <p>The response includes execution result, execution envelope, and review boundary.</p>
</div>
```

Styled with a light background panel to distinguish it from interactive controls.

## Runner Selection UI

Radio buttons placed between the explanation panel and the task input:

```html
<fieldset id="runner-selection">
  <legend>Runner adapter</legend>
  <label>
    <input type="radio" name="runner" value="noop" checked>
    Local deterministic / no-op (default)
  </label>
  <br>
  <label>
    <input type="radio" name="runner" value="docker-agent">
    Docker agent (opt-in — does not run Docker)
  </label>
</fieldset>
```

Default: `noop` (checked). Docker agent is visible but not selected by default. Labels clearly indicate what each option does.

## Request Payload Shape

The JavaScript reads the selected runner and includes it in the request:

```javascript
var runner = document.querySelector('input[name="runner"]:checked').value;
var body = {task: task, requested_adapter: runner};
```

This maps directly to the existing `execution_handoff.py` which reads `raw.get("requested_adapter", "noop")`. No backend changes needed.

### Request shapes

**Local/no-op (default):**
```json
{"task": "Implement JWT auth", "requested_adapter": "noop"}
```

**Docker agent (opt-in):**
```json
{"task": "Implement JWT auth", "requested_adapter": "docker-agent"}
```

## Default Runner Rule

- Radio button `checked` attribute on the noop option ensures the user must explicitly switch to Docker agent.
- No change to the default value in `execution_handoff.py` (`"noop"`).
- If JavaScript fails to read the runner value (edge case), the handoff still defaults to `"noop"`.

## Docker Opt-In Boundary

- Docker agent is visible as a radio option but not selected by default.
- The label explicitly states: "Docker agent (opt-in — does not run Docker)".
- The existing `docker_agent_adapter.py` returns a `blocked` result when `allow_docker=False` (the default), so selecting Docker agent returns a safe structured result without running Docker.
- No Docker daemon is required.

## Execute API Reuse

Same as PR 0079 and 0080: `POST /runs/execute` with `{"task": taskText, "requested_adapter": runnerType}`.

## Handoff Propagation

No changes to `execution_handoff.py`. It already handles `requested_adapter`. The value flows through:
1. Page JS → `requested_adapter` in POST body
2. Server route → `data` dict
3. `run_mock_execution_handoff(data)` → `_build_execution_request` → `raw.get("requested_adapter", "noop")`
4. `run_local_execution_harness(execution_request)` → `dispatch_execution(execution_request)`
5. Dispatcher selects adapter based on substring match

## Result View Updates

The existing structured result view already displays the requested adapter and used adapter. No changes needed to the rendering. The `Requested adapter` field in the execution request section and the `Adapter` field in the execution result section will reflect the selected runner.

## Test Plan

**Test file:** `services/task_intake/tests/test_local_runner_selection.py`

| Test | Expectation |
|---|---|
| `test_page_contains_explanation_panel` | HTML includes "Ariadne turns your task" |
| `test_page_explains_default_mode` | HTML includes "default" or "deterministic local/no-op" |
| `test_page_explains_docker_opt_in` | HTML includes "opt-in" and "Docker" |
| `test_page_has_noop_runner_option` | HTML includes `value="noop"` on a radio/option |
| `test_page_has_docker_agent_option` | HTML includes `value="docker-agent"` on a radio/option |
| `test_noop_is_default` | HTML includes `checked` on the noop option |
| `test_page_submits_requested_adapter` | HTML includes `requested_adapter` in the JS fetch body |
| `test_runs_execute_with_noop_returns_completed` | POST with noop → completed |
| `test_runs_execute_with_docker_returns_blocked` | POST with docker-agent → blocked (no allow_docker) |
| `test_runs_execute_preserves_structured_view` | Response includes execution_envelope |
| `test_runs_execute_preserves_raw_json` | Full JSON still returned |
| `test_app_runtime_check_works` | `build_runtime_config(["--check"])` works |
| `test_test_mode_cli_works` | `test_mode.main(["--task", "test"])` returns 0 |
| `test_no_new_execution_route` | No new backend route introduced |
| `test_no_external_assets` | No CDN/framework references |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_local_runner_selection.py \
  services/task_intake/tests/test_local_result_structured_view.py \
  services/task_intake/tests/test_local_interaction_page.py \
  services/task_intake/tests/test_execution_handoff_http.py \
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
  services/task_intake/tests/test_local_runner_selection.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_runner_selection.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/server.py` (modify)
- `services/task_intake/tests/test_local_runner_selection.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0081-explicit-local-runner-selection/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0081-explicit-local-runner-selection/PLAN.md` (planner only)
- `.project-memory/pr/0081-explicit-local-runner-selection/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/task_intake/src/task_intake/test_mode.py`
- `services/task_intake/tests/test_local_interaction_page.py`
- `services/task_intake/tests/test_local_result_structured_view.py`
- `services/task_intake/tests/test_execution_handoff_http.py`
- `services/runner/**`
- `services/conductor/**`
- `services/domain_adapters/**`
- `services/core/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.grace/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`

## Stop Conditions

- docs-only/schemas-only/smoke-test-only/backend-only outcome
- no explanation panel planned
- no explicit runner selection planned
- local/noop is not default
- Docker adapter becomes default
- Docker daemon required
- real agent execution required
- model/provider call required
- new execution backend route required
- `/runs/execute` behavior broken
- execution_handoff/local_harness bypass required
- frontend framework/build system required
- external assets/CDN required
- dependency/build change required
- persistence/auth/users required
- broad write paths
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Update `_HTML_PAGE` in `server.py`. Explanation panel + radio buttons. No backend changes.

### implementation_files

```
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_local_runner_selection.py (new)
```

### explanation_panel

6-line description panel at top of page explaining what Ariadne does, what the default mode is, what Docker agent means, and what the response contains.

### runner_selection_ui

Radio buttons in a `<fieldset>`: noop (checked by default) and docker-agent (opt-in, clearly labeled).

### request_payload_shape

```json
{"task": "...", "requested_adapter": "noop|docker-agent"}
```

### default_runner_rule

Local/no-op is default. Handoff defaults to `"noop"` if not provided.

### docker_opt_in_boundary

Visible but not selected by default. Label states "opt-in — does not run Docker". Existing adapter returns blocked result without `allow_docker=True`.

### execute_api_usage

Same `POST /runs/execute` with added `requested_adapter` field.

### handoff_propagation

No changes. `execution_handoff.py` already reads `raw.get("requested_adapter", "noop")`.

### result_view_updates

No changes needed. Existing structured view already shows requested adapter and used adapter.

### api_preservation

`/runs/execute` unchanged. Handoff defaults work without `requested_adapter`.

### runtime_preservation

App runtime unchanged. `_ROUTES` unchanged.

### validation_strategy

14 tests + full compat + check command + test-mode CLI + forbidden guards.

### next_pr_notes

After PR 0081, the local page explains what it does and lets users choose runner mode. The next PR could add a `--adapter` flag to the app runtime `--check --json` output to show which adapters are available.

---

PLAN written: yes
