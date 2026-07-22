# PR 0151b — Artifact Workspace UI: Two-Column Layout

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Artifact Workspace UI Redesign (Stream 1) |
| **Slot** | PR 0151b (UI redesign after PR 0139 run list view and PR 0146 run detail panel) |
| **Why this PR is next** | The current single-column debug form has accumulated features (summary card, execution trace, structured view, raw JSON, feedback panel, session report, confusion signals, onboarding) into a long vertical scroll. This PR replaces it with a clean two-column layout: left panel for task input + runner selection + run history, right panel for tabbed result views. Bulma CSS from CDN provides the grid/tab/chip components without a build step. All route handlers remain untouched. |
| **Batching policy** | Single-purpose: layout redesign only. No new backend routes, no runtime changes. |
| **Drift heuristic** | Does not add backend routes, does not change POST /runs/execute behavior, does not change GET /runs response shape, does not add authentication, does not add persistence, does not add Docker execution, does not add a frontend build step. |

## Discovery Evidence

### Existing UI Structure

The page at `GET /` in `services/task_intake/src/task_intake/server.py` is a single-column layout with:

1. **Onboarding panel** (`#onboarding-panel`) — dismissible welcome section
2. **Explanation box** (`#explanation`) — description of Ariadne
3. **Guided scenarios** (`#scenarios` fieldset) — preset task/runner buttons
4. **Runner selection** (`#runner-selection` fieldset) — radio buttons for noop/docker-agent
5. **Task textarea** (`#task`) + **Submit button** (`#submit`)
6. **Error panel** (`#error-panel`) — dismissible error display
7. **Result section** (`#result`) containing:
   - Summary card (`#summary-card`)
   - Run report section (`#run-report-section`)
   - Run history section (`#run-history-section`)
   - Run detail panel (`#run-detail-panel`)
   - Execution trace section (`#execution-trace-section`)
   - Structured view (`#structured-view`)
   - Raw JSON (`#json` pre block)
8. **Feedback panel** (`#feedback-panel`) — checklist, confusion signals, survey, session report
9. **Product iteration capture** — Record session signal

All CSS is inline `<style>`. All JS is inline `<script>`. No external dependencies.

### Existing Test Constraints

The test file `services/task_intake/tests/test_local_run_history_in_page.py` has **41 tests** across 4 classes:

- **`TestRunHistoryPanel`** (10 tests): JS function/variable names, run history container elements, `__ariadne_run_history` JS array, `pushRunHistory`, `renderRunHistory`, `clearRunHistory`, length cap check.
- **`TestExistingUIPreserved`** (10 tests): Element IDs and text content — `summary-card`, `Execution Trace`, `structured-view`, `<pre`, `name="runner"`, `Guided scenarios`, `User Test Feedback`, `Generate session report`, `run-report-section`, and critically `test_no_external_assets` which asserts `"cdn" not in html.lower()`.
- **`TestRunsExecutePreserved`** (2 tests): POST /runs/execute behavior unchanged.
- **`TestDetailPanel`** (19 tests): Detail panel HTML/JS elements, `fetchRunDetail`, `renderRunDetail`, `run-detail-panel`.

**Critical tension**: `test_no_external_assets` forbids any CDN URL in the HTML. Introducing a Bulma CDN stylesheet link (`cdnjs.cloudflare.com`) will cause this test to fail. The test must be updated to allow `cdnjs.cloudflare.com` while still blocking `unpkg` and `jsdelivr`.

### CDN Verify

Bulma 0.9.4 CSS is available at:
`https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css`

This URL is stable and does not require CSP changes (no CSP header is set by the existing server.py for the HTML page response).

## UI Slice Identity

1. PR 0151b is the **Artifact Workspace UI Two-Column Layout Redesign**.
2. This replaces the **inline CSS** with **Bulma from CDN** plus minimal custom overrides.
3. This preserves all **existing JS function signatures** (`pushRunHistory`, `renderRunHistory`, `clearRunHistory`, `fetchRunDetail`, `renderRunDetail`, `get`, `val`, `boolSpan`, `listItems`, `keyValue`, `section`, etc.).
4. This preserves all **existing JS variables** (`__ariadne_run_history`, `__ariadne_confusion_signals`, `__ariadne_session_ref`, `TRACE_STEPS`, etc.).
5. This preserves all **existing element IDs** and class names that tests assert on, except where structurally impossible.
6. This preserves all **existing route handlers** — no changes to Python logic.

## Implementation Scope

| File | Action | Justification |
|------|--------|---------------|
| `services/task_intake/src/task_intake/server.py` | Replace the entire `_HTML_PAGE` string with new two-column HTML/CSS/JS. Replace inline CSS with Bulma CDN `<link>` + minimal custom overrides. Restructure DOM into two-column layout. Keep all JS function/variable names intact. Keep all route handlers intact. | Evidence: `server.py` is the ASGI server with the inline HTML. The `_HTML_PAGE` string is the full page. Only the HTML/CSS/JS template string changes. |
| `services/task_intake/tests/test_local_run_history_in_page.py` | Update `test_no_external_assets` to allow `cdnjs.cloudflare.com`. Add/update assertions that verify two-column layout elements exist. Preserve all other tests. | Evidence: `test_no_external_assets` will fail with CDN URL. Must be relaxed. Other tests can be preserved by keeping element IDs/JS names. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/**` | No runtime changes. |
| `services/task_intake/src/task_intake/*.py` (except server.py) | No Python changes outside the HTML string. |
| `services/task_intake/tests/test_runs.py` | Not modified. Run route tests unchanged. |
| `services/task_intake/tests/test_task_intake.py` | Not modified. Task intake tests unchanged. |
| `services/task_intake/tests/test_local_interaction_page.py` | Not modified. |
| `services/task_intake/tests/test_local_run_summary_card.py` | Not modified. |
| `services/task_intake/tests/test_local_runner_selection.py` | Not modified. |
| `services/task_intake/tests/test_local_execution_trace.py` | Not modified. |
| `services/task_intake/tests/test_local_result_structured_view.py` | Not modified. |
| `services/task_intake/tests/test_local_user_test_feedback_panel.py` | Not modified. |
| `services/task_intake/tests/test_local_user_test_session_report.py` | Not modified. |
| `services/task_intake/tests/test_local_user_confusion_signals.py` | Not modified. |
| `services/task_intake/tests/test_first_time_user_onboarding_panel.py` | Not modified. |
| `services/task_intake/tests/test_guided_local_user_test_scenarios.py` | Not modified. |
| `services/task_intake/tests/test_local_empty_error_states.py` | Not modified. |

### Not Modified

- `ROADMAP.md`
- `docs/`, `agents/`, `schemas/`
- `pyproject.toml`, `poetry.lock`, `requirements*.txt`
- All previous PR artifacts
- All Python files except `server.py` (and only the HTML string)
- All test files except `test_local_run_history_in_page.py` (and only specific test updates)

## Layout Design
| **Governance insertion** | PR 0151B is authorized by the human architect between PR 0151A (CI Node Dependency Bootstrap Correction) and product PR 0152 (Human Visual Approval Artifact). It does not consume or renumber product roadmap slot PR 0152. PR 0152 remains Human Visual Approval Artifact. |
### Two-Column Layout (Bulma)

The page uses Bulma's `columns` grid:

```html
<div class="columns is-fullheight">
  <div class="column is-one-quarter" id="left-column">...</div>
  <div class="column" id="right-column">...</div>
</div>
```

- `is-one-quarter` → ~25% width (~320px minimum via `min-width: 320px` override)
- Right column gets `flex: 1` via Bulma's default column behavior

### Top Bar

```html
<nav class="navbar" role="navigation">
  <div class="navbar-brand">
    <span class="navbar-item has-text-weight-bold">Ariadne</span>
  </div>
  <div class="navbar-menu">
    <div class="navbar-start">
      <a class="navbar-item is-active">runs</a>
      <a class="navbar-item" disabled>artifacts</a>
      <a class="navbar-item" disabled>context</a>
      <a class="navbar-item" disabled>proofs</a>
    </div>
    <div class="navbar-end">
      <span class="navbar-item">
        <span class="tag" id="runner-badge">local</span>
      </span>
    </div>
  </div>
</nav>
```

### Left Column (`#left-column`)

Order from top to bottom:

1. **Guided scenarios** (`#scenarios` fieldset) — preserved from current layout to keep `test_scenarios_preserved` passing. Collapsible in Bulma `message` box.
2. **Task textarea** — `textarea#task` with `placeholder="Describe the task…"` and validation message `#task-validation`.
3. **Runner selector** — radio buttons `name="runner"` styled as Bulma `buttons has-addons` chip group. Three options: `noop` (default, selected), `local` (alias for noop), `docker-agent` (opt-in). Include `#allow-docker-checkbox` for real Docker opt-in.
4. **Submit button** — `button#submit.is-primary.is-fullwidth`.
5. **Error panel** — `#error-panel` preserved.
6. **Run history section** (`#run-history-section`) — `#run-history-placeholder`, `#clear-history-btn`, `#run-history-list` — all preserved with same JS functions.
7. **Run detail panel** (`#run-detail-panel`) — `#detail-run-id`, `#run-detail-content` — preserved with same JS functions.

### Right Column (`#right-column`)

Tab bar using Bulma `tabs`:

```html
<div class="tabs is-boxed">
  <ul>
    <li class="is-active" data-tab="summary"><a>Summary</a></li>
    <li data-tab="proof-refs"><a>Proof refs</a></li>
    <li data-tab="trace"><a>Trace</a></li>
    <li data-tab="raw-json"><a>Raw JSON</a></li>
  </ul>
</div>
```

Tab panels:
- **Summary tab** (`#tab-summary`): Contains `#summary-card` (preserved id for test), status, pipeline, git boundary, runner, PR URL, started time, proof refs list with command + exit code + timestamp.
- **Proof refs tab** (`#tab-proof-refs`): Full list of captured proof refs with evidence paths.
- **Trace tab** (`#tab-trace`): Contains `#execution-trace-section` and `#trace-steps` (preserved for test compatibility). Collapsible step list.
- **Raw JSON tab** (`#tab-raw-json`): Contains `#structured-view` (preserved for test compatibility) and `<pre id="json">`.

### Bottom Strip (`#bottom-strip`)

Below the two columns (full width):

1. **Run report section** (`#run-report-section`) — preserved id. Buttons: Generate, Copy, Download.
2. **Feedback panel** (`#feedback-panel`) — preserved structure with `User Test Feedback` heading, checklist, confusion signals, survey questions, session report.
3. **Product iteration capture** — Record session signal button.

## JS Function Preservation

The following JS functions and variables must remain available with identical names (their internal implementation may be updated):

| Name | Preserved | Notes |
|------|-----------|-------|
| `__ariadne_run_history` | Yes | JS array, still populated by `pushRunHistory` and evidence-backed `fetchRuns()` |
| `pushRunHistory(data)` | Yes | Pushes to array, calls `renderRunHistory`, checks length > 10 cap |
| `renderRunHistory()` | Yes | Renders `#run-history-list` from array |
| `clearRunHistory()` | Yes | Clears array, re-renders |
| `fetchRuns()` | Yes | Evidence-backed fetch from `GET /runs` |
| `fetchRunDetail(runId)` | Yes | Fetches `GET /runs/{id}`, calls `renderRunDetail` |
| `renderRunDetail(data)` | Yes | Renders `#run-detail-content` |
| `get(obj, path, def)` | Yes | Safe nested accessor |
| `val(v, def)` | Yes | Null-safe value display |
| `boolSpan(v)` | Yes | Green/red boolean span |
| `listItems(arr)` | Yes | Renders list as `<ul>` |
| `keyValue(key, value)` | Yes | Renders key-value pair |
| `section(title, content)` | Yes | Renders collapsible section |
| `fillScenario(runnerValue, taskText)` | Yes | Prefills task/runner from scenario buttons |
| `showError(msg)` / `dismissError()` | Yes | Error panel control |
| `validateTask()` | Yes | Empty task validation |
| `generateFeedback()` | Yes | Feedback generation |
| `generateSessionReport()` | Yes | Session report generation |
| `generateRunReport()` | Yes | Run report generation |
| `addConfusionSignal(type)` | Yes | Confusion signal recording |
| `renderConfusionSignals()` | Yes | Confusion signal list render |
| `clearConfusionSignals()` | Yes | Clear all signals |
| `updateChecklistCounter()` | Yes | Checklist counter |
| `dismissOnboarding()` | Yes | Onboarding dismiss |
| `recordSessionSignal()` | Yes | Product iteration capture |
| `getOrCreateSessionRef()` | Yes | Session ref management |
| `__ariadne_confusion_signals` | Yes | JS array |
| `__ariadne_session_ref` | Yes | Session ref variable |
| `__ariadne_session_start` | Yes | Session start timestamp |
| `TRACE_STEPS` | Yes | Trace step definitions |
| `esc(s)` / `escHtml(s)` | Yes | HTML escaping |
| `renderSummaryCard(data)` | Yes | Summary card HTML generation |
| `renderTrace(data)` | Yes | Trace step HTML generation |
| `renderStructured(data)` | Yes | Structured view HTML generation |

## Existing Test Preservation Matrix

| Test | Assertion | Preservation Strategy |
|------|-----------|----------------------|
| `test_page_contains_run_history_section` | `"run-history-section"` in html or `"Run History"` in html | Keep `id="run-history-section"` and `<h2>Run History</h2>` in left column |
| `test_history_empty_before_submit` | `"No runs yet"` in html | Keep placeholder text |
| `test_history_has_clear_button` | `"clear-history-btn"` in html | Keep `id="clear-history-btn"` |
| `test_history_has_list_container` | `"run-history-list"` in html | Keep `id="run-history-list"` |
| `test_history_no_persistence` | `"localStorage"` not in html | No localStorage usage |
| `test_history_has_js_array` | `"__ariadne_run_history"` in html | Keep variable |
| `test_history_has_push_function` | `"pushRunHistory"` in html | Keep function |
| `test_history_has_render_function` | `"renderRunHistory"` in html | Keep function |
| `test_history_has_clear_function` | `"clearRunHistory"` in html | Keep function |
| `test_history_max_entries_capped` | `"> 10"` or `"length > 10"` in html | Keep cap check in `pushRunHistory` |
| `test_summary_card_preserved` | `"summary-card"` in html | Keep `id="summary-card"` in Summary tab |
| `test_trace_preserved` | `"Execution Trace"` or `"trace"` in html | Keep `"Execution Trace"` heading in Trace tab |
| `test_structured_view_preserved` | `"structured-view"` in html | Keep `id="structured-view"` in Raw JSON tab |
| `test_raw_json_preserved` | `"<pre"` in html | Keep `<pre id="json">` in Raw JSON tab |
| `test_runner_selection_preserved` | `'name="runner"'` in html | Keep radio buttons with name="runner" |
| `test_scenarios_preserved` | `"Guided scenarios"` in html | Keep fieldset/legend in left column |
| `test_feedback_panel_preserved` | `"User Test Feedback"` in html | Keep heading in bottom strip |
| `test_session_report_preserved` | `"Generate session report"` in html | Keep button text |
| `test_run_report_section_preserved` | `"run-report-section"` in html | Keep `id="run-report-section"` in bottom strip |
| `test_no_external_assets` | `"cdn" not in html.lower()` | **UPDATE**: Allow `cdnjs.cloudflare.com` while blocking unpkg/jsdelivr |
| `test_page_contains_detail_panel` | `"run-detail-panel"` in html | Keep `id="run-detail-panel"` in left column |
| `test_page_contains_detail_js_functions` | `"fetchRunDetail"` and `"renderRunDetail"` | Keep both functions |
| `test_run_list_entries_are_clickable` | `"fetchRunDetail("` and `"View</button>"` | Keep View buttons and onclick handlers |
| `test_selection_fetches_detail_route` | `'fetch("/runs/"'` | Keep fetch URL pattern |
| `test_detail_panel_sections` | `"Execution Results"`, `"Manifest Files"`, etc. | Keep section headings in renderRunDetail |
| All other `TestDetailPanel` tests | Various | Keep JS rendering patterns |
| `test_no_localstorage_persistence` | `"localStorage"` not in html | No localStorage usage |

### Required Test Updates

**`test_no_external_assets`** — must be updated from:
```python
def test_no_external_assets(self):
    _, html = _request("GET", "/")
    assert "cdn" not in html.lower()
    assert "unpkg" not in html.lower()
    assert "jsdelivr" not in html.lower()
```
To:
```python
def test_allowed_cdn_only(self):
    _, html = _request("GET", "/")
    # Bulma CDN is allowed; unpkg, jsdelivr are not
    assert "cdnjs.cloudflare.com" in html
    assert "unpkg" not in html.lower()
    assert "jsdelivr" not in html.lower()
```

## Allowed files:
pyproject.toml — dev environment fix only: adds [tool.setuptools] packages = [] to suppress egg-info generation during local dev install
This is the only test that **must** change its assertion logic. All other tests can be preserved by keeping the existing element IDs, class names, JS function/variable names, and text content in the new layout.

## Route Preservation

### GET / (unchanged)

The route handler itself stays the same — it returns `_HTML_PAGE`. Only the content of `_HTML_PAGE` changes.

### POST /runs/execute (unchanged)

No changes. The submit button's JavaScript still calls the same endpoint. The `window._latestData` pattern, `renderSummaryCard`, `renderTrace`, `renderStructured`, `pushRunHistory`, `fetchRuns` call chain is preserved.

### GET /runs (unchanged)

No changes. `fetchRuns()` still calls `GET /runs`. Response still populates `#run-history-list` with evidence-backed data.

### GET /runs/<run_id> (unchanged)

No changes. `fetchRunDetail(runId)` still calls `GET /runs/{id}`. `renderRunDetail(data)` still renders to `#run-detail-content`.

### POST /product/iterations (unchanged)

No changes. `recordSessionSignal()` still posts to this endpoint.

## HTML Structure Compatibility

The new HTML must preserve these element IDs for test and JS compatibility:

- `#onboarding-panel`
- `#scenarios`
- `#runner-selection`
- `#task`
- `#task-validation`
- `#submit`
- `#error-panel`, `#error-message`, `#dismiss-error-btn`
- `#status-bar`
- `#result`
- `#summary-card`
- `#summary-placeholder`
- `#run-report-section`, `#run-report-placeholder`, `#generate-run-report-btn`, `#copy-run-report-btn`, `#download-run-report-btn`, `#run-report-output`
- `#run-history-section`, `#run-history-placeholder`, `#clear-history-btn`, `#run-history-list`
- `#run-detail-panel`, `#detail-run-id`, `#run-detail-content`
- `#execution-trace-section`, `#trace-steps`
- `#structured-view`
- `#json`
- `#feedback-panel`
- `#manual-checklist`, `#checklist-counter`, `#reset-checklist-btn`
- `#confusion-signals-panel`, `#confusion-note-input`, `#confusion-signal-list`, `#clear-confusion-btn`
- `#feedback-output`
- `#generate-feedback-btn`
- `#generate-session-report-btn`, `#copy-report-btn`, `#session-report-output`
- `#record-session-btn`, `#session-status`
- `#allow-docker-checkbox`
- `.confusion-btn` (class)
- `.checklist-cb` (class)

All `.confusion-btn` onclick handlers (`addConfusionSignal(...)`) preserved same as current.

## Custom CSS Overrides (beyond Bulma)

Minimal custom styles to handle:
- Left column min-width: 320px
- Run history list item styling (status dot colors, truncation)
- Tab content padding
- Bottom strip layout
- Status colors (green/red/amber) for run status dots using Bulma color classes where possible

These overrides go in a `<style>` block in the HTML `<head>`, after the Bulma CDN `<link>`.

## Validation Strategy

### 1. Compile Check

```bash
python -m compileall -f services/task_intake/src
```

Expected: all Python files compile.
If not met: block.

### 2. All Existing Tests Pass (with test update)

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all previous tests pass (with `test_no_external_assets` updated to `test_allowed_cdn_only`).
If not met: block.

### 3. Full Local UI Test Suite

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_local_interaction_page.py \
  services/task_intake/tests/test_local_run_summary_card.py \
  services/task_intake/tests/test_local_runner_selection.py \
  services/task_intake/tests/test_local_execution_trace.py \
  services/task_intake/tests/test_local_result_structured_view.py \
  services/task_intake/tests/test_local_user_test_feedback_panel.py \
  services/task_intake/tests/test_local_user_test_session_report.py \
  services/task_intake/tests/test_local_user_confusion_signals.py \
  services/task_intake/tests/test_first_time_user_onboarding_panel.py \
  services/task_intake/tests/test_guided_local_user_test_scenarios.py \
  services/task_intake/tests/test_local_empty_error_states.py \
  services/task_intake/tests/test_local_run_history_in_page.py \
  -q
```

Expected: all pass.
If not met: block.

### 4. Regression Subset

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_task_intake.py \
  services/task_intake/tests/test_app_runtime.py \
  services/task_intake/tests/test_runs.py \
  services/task_intake/tests/test_copy_export_local_run_report.py \
  -q
```

Expected: regression passes.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|shell=True|os.system" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_run_history_in_page.py \
  .project-memory/pr/0151b-artifact-workspace-ui-two-column-redesign
```

Expected: no unsafe real mutation authority added.

### 6. Bulma CDN URL Present

```bash
grep -n "cdnjs.cloudflare.com" services/task_intake/src/task_intake/server.py
```

Expected: Bulma CDN stylesheet link present.

### 7. Git Status

```bash
git status --short
git diff --name-only
```

Expected: only `server.py` and `test_local_run_history_in_page.py` modified (plus PR directory).

### 8. PLAN DRIFT GATE

Verify that only the planned files are changed:
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_local_run_history_in_page.py`
- `.project-memory/pr/0151b-artifact-workspace-ui-two-column-redesign/PLAN.md`
- `.project-memory/pr/0151b-artifact-workspace-ui-two-column-redesign/reviews/plan-review.yml`
- `.project-memory/pr/0151b-artifact-workspace-ui-two-column-redesign/reviews/precommit-review.yml`

If any other file is modified: block.

### 9. NO-DRIFT CHECK

- No changes to runtime behavior
- No new backend routes
- No changes to Python logic outside the HTML string
- No changes to `services/runner/`
- No changes to `agents/`, `schemas/`, `docs/`, `ROADMAP.md`, dependencies
- No frontend build step
- No authentication
- No persistent storage
- No React/Vue/Svelte

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131–0136 Production Line | All existing code unchanged. |
| PR 0137 Roadmap Unlock | Not modified. |
| PR 0138 Read Model | Not modified. |
| PR 0139 Run List View | `GET /runs`, `fetchRuns()`, evidence-backed list — all preserved. |
| PR 0146 Run Detail Panel | `GET /runs/<run_id>`, `fetchRunDetail()`, `renderRunDetail()` — all preserved. |
| All JS functions/variables | Function signatures preserved. Internal implementation may be updated for new layout. |
| All route handlers | No Python handler changes. |
| Feedback/session/report features | All preserved in bottom strip. |
| Confusion signals | All preserved. |
| Onboarding panel | Preserved in left column. |
| Guided scenarios | Preserved in left column. |

## Non-Goals

- No new backend routes
- No real Docker execution
- No authentication
- No persistent storage beyond existing `.ariadne/runs/`
- No React/Vue/Svelte
- No frontend build step
- No dark mode (Bulma handles light mode; dark mode is post-MVP)
- No mobile layout (desktop-first)
- No changes to `GET /runs` response shape
- No changes to `POST /runs/execute` behavior
- No changes to Python route handlers
- No changes to `services/runner/`
- No new test files
- No CSS framework other than Bulma from CDN

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0151b-artifact-workspace-ui-two-column-redesign`
- `server.py` `GET /` route cannot be found
- `test_local_run_history_in_page.py` has assertions that cannot be preserved without backend changes
- Bulma CDN URL is unreachable at task time
- The required `test_no_external_assets` update is rejected
- PLAN modifies Python route handlers
- PLAN adds a new frontend stack or build step
- PLAN modifies `services/runner/`, `agents/`, `schemas/`, dependencies, `.gitignore`, `ROADMAP.md`
- PLAN implements any capability from frozen streams
