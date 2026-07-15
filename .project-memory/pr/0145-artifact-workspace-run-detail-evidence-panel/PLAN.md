# PR 0145 — Artifact Workspace Run Detail Evidence Panel Plan

## EVIDENCE SNAPSHOT

1. HEAD: `35cea999ab79059086c883926b67f2e682040e30`
2. origin/main: `35cea999ab79059086c883926b67f2e682040e30`
3. Merge base: `35cea999ab79059086c883926b67f2e682040e30`
4. Branch: `0145-artifact-workspace-run-detail-evidence-panel`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0144 merge evidence: `35cea99 (HEAD -> 0145-..., origin/main, origin/HEAD, main) feat(task-intake): add artifact workspace local run list (#170)`
8. Current workspace selectors (from artifact_workspace.py):
   - `#artifact-workspace` — root with role="main"
   - `#zone-timeline` — timeline zone, role="region", aria-labelledby="zone-timeline-heading"
   - `#zone-canvas` — canvas zone with `.zone-placeholder` text "Select a run from the timeline to view artifacts. No artifact loaded."
   - `#zone-gates-proofs` — deferred placeholder
   - `#zone-logs-captures` — deferred placeholder
9. Current selection behavior: `selectRun(runId)` is a placeholder that sets canvas placeholder textContent to "Selected run: <runId> — detail panel coming in PR 0145."
10. Current detail API (server.py L921-951): `GET /runs/<run_id>` via `read_run_evidence_detail()` + `serialize_run_evidence_detail()`. Returns full version-1 envelope with summary, detail, payload_cleanliness (null), readiness (null), missing, malformed.
11. Current detail envelope keys: ev_contract_version, ok, error, summary, detail, payload_cleanliness, readiness, missing, malformed
12. Current summary fields: run_id, status, reason_codes, pipeline_status, git_boundary_status, execution_attempted, created_at, run_json_available, manifest_available, run_report_available, missing_evidence, malformed_evidence, pr_url
13. Current detail fields: execution_results, manifest_files, run_json_hash, report_preview, evidence_paths, source_errors
14. No server.py, runtime_evidence.py, or runtime_evidence_serialization.py changes needed — the detail API already provides everything required.

## ROADMAP ALIGNMENT

- roadmap track: Stream 2 — Artifact Workspace Shell
- expected PR slot: PR 0145 (Run Detail Evidence Panel)
- why this PR is next: PR 0144 (Live Local Run List) is complete. The timeline now loads live entries from GET /runs, but selection is still a placeholder. PR 0145 connects live selection to the existing GET /runs/<run_id> endpoint and renders the bounded detail evidence inside the Artifact Canvas.
- batching policy check: PR 0145 is a coherent read-only detail-evidence capability that reuses the existing backend endpoint. It is not an isolated UI control or cosmetic change. It is the third PR of the Artifact Workspace Shell stream (0143-0147), architect-authorized as part of the product roadmap.
- drift heuristic check: Not triggered. No consecutive single-file UI PRs. The workspace shell uses an isolated module pattern.
- architect sign-off required: yes (roadmap stream continuation)
- architect sign-off reference if required: Human architect requested the next roadmap step after PR 0144. PR 0145 is the third product PR of Stream 2.

### Roadmap State

1. Active stream: Stream 2 — Artifact Workspace Shell
2. Expected slot: PR 0145 (Run Detail Evidence Panel)
3. PR predecessor: PR 0144 (Live Local Run List) is complete.
4. PR 0146 (Run Report Viewer) and PR 0147 (Proof and Manifest Viewer) remain separate.
5. No mutation stream is opened.
6. No frozen capability is opened.

## CURRENT WORKSPACE INVENTORY

| Element | ID | Current State | PR 0145 Change |
|---|---|---|---|
| Workspace root | `#artifact-workspace` | Intact | No change |
| Timeline zone | `#zone-timeline` | Live run list via fetchRuns() | No change |
| Timeline entries | `#timeline-entries` | Rendered via renderRunList() | No change |
| Canvas zone | `#zone-canvas` | Placeholder: "Select a run..." | Replace with detail panel |
| Canvas placeholder | `p.zone-placeholder` | Static text | Removed — replaced by detail rendering |
| Gates/Proofs | `#zone-gates-proofs` | Placeholder: "No gate checks..." | No change — deferred to PR 0147+ |
| Logs/Captures | `#zone-logs-captures` | Placeholder: "No logs available..." | No change — deferred to PR 0147+ |
| selectRun() | JS function | Sets canvas placeholder text | Fully replace with GET /runs/<run_id> fetch and detail rendering |
| fetchRuns() | JS function | Live GET /runs fetch | No change |

## EXISTING DETAIL API CONTRACT

The detail endpoint at `GET /runs/<run_id>` (server.py L921-951, implemented in PR 0141, serialized via PR 0142) provides:

- HTTP 200 with version-1 JSON envelope
- `ev_contract_version: "1"`
- `summary` block: run_id, status, reason_codes, pipeline_status, git_boundary_status, execution_attempted, created_at, evidence availability booleans, missing_evidence, malformed_evidence, pr_url
- `detail` block: execution_results (array of dicts), manifest_files (array), run_json_hash, report_preview, evidence_paths (array), source_errors (array)
- `payload_cleanliness: null` (always unavailable)
- `readiness: null` (always unavailable)
- `missing` array of {expected_path, reason}
- `malformed` array of {expected_path, reason}

No backend changes are required. The endpoint exists, is versioned, and returns all fields needed for PR 0145.

## PR 0141 ABSORPTION AND REUSE DECISION

PR 0141 created the GET /runs/<run_id> route and the client-side `fetchRunDetail()`/`renderRunDetail()` functions inside the Local Interaction page (server.py _HTML_PAGE). PR 0145 does NOT reuse those specific JS functions — the workspace module (artifact_workspace.py) implements its own selection and rendering logic.

**Reuse decision**: The backend endpoint IS reused entirely. The workspace calls the same GET /runs/<run_id> URL. No new endpoint is created. The existing Local Interaction `run-detail-panel` and `renderRunDetail` function remain untouched.

**No duplication concern**: The workspace shell and the Local Interaction page are independent surfaces. Each has its own JS rendering. This is intentional — the closed Local Interaction track must not be modified.

## SELECTION CONTRACT

| Property | Value |
|---|---|
| Selected-run state | A `selectedRunId` variable (scoped to the module's JS) stores the currently selected run_id |
| Timeline selected-row selector | `.timeline-entry` with an `aria-selected="true"` attribute on the selected entry |
| Visual selected state | A `.timeline-selected` CSS class applied to the selected entry (background highlight) |
| Keyboard selection | Enter and Space keys trigger selection via event listener |
| Focus behavior | After selection, focus remains on the clicked timeline entry |
| Detail URL construction | `fetch("/runs/" + encodeURIComponent(runId))` — same pattern as existing server.js |
| Unescaped run_id in HTML | Prohibited — run_id enters only via encodeURIComponent in the fetch URL and via escHtml/safeText in display |
| Arbitrary filesystem paths | Prohibited — no path input, no runs_root control |
| Detail URL from evidence paths | Prohibited — the detail URL always uses the same endpoint with encodeURIComponent(run_id) |
| Latest-selection-wins | A `detailRequestId` counter increments on each selection. The fetch response checks its requestId against the current counter. If stale (requestId !== current), the response is discarded. |
| Same run re-selected | The detail is re-fetched and re-rendered. This is acceptable — the response is cached by the browser for identical requests. |
| Run disappears from list | The detail panel clears to the initial no-selection state (the previous detail is not preserved for an unknown run) |

### Latest-selection-wins implementation

```javascript
var detailRequestCounter = 0;
var selectedRunId = null;

function selectRun(runId) {
    selectedRunId = runId;
    var requestId = ++detailRequestCounter;
    showDetailLoading();
    fetch("/runs/" + encodeURIComponent(runId))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (requestId !== detailRequestCounter) return; // stale
            renderDetail(data);
        })
        .catch(function(err) {
            if (requestId !== detailRequestCounter) return; // stale
            showDetailFetchFailure();
        });
}
```

## DETAIL REQUEST CONTRACT

| Property | Value |
|---|---|
| HTTP method | GET |
| URL | `/runs/<encoded_run_id>` |
| run_id encoding | `encodeURIComponent(runId)` |
| Version validation | Response `ev_contract_version` must be `"1"`. If absent or not `"1"`, show version-mismatch state. |
| Envelope validation | Response must be an object with `ok` (boolean). |
| Response type | JSON |
| Stale response handling | Via `detailRequestCounter` — see selection contract above |
| Error handling | Non-ok HTTP status, network error, JSON parse error all caught and rendered as fetch-failure state |

## DETAIL STATE CONTRACT

| State | Canvas content | Selector used |
|---|---|---|
| Initial (no selection) | `.zone-placeholder` text: "Select a run from the timeline to view artifacts. No artifact loaded." | `#zone-canvas p.zone-placeholder` |
| Detail loading | "Loading detail for <run_id>..." | `#detail-loading` or equivalent text node |
| Complete successful detail | Full detail rendering per DISPLAY CONTRACT | Rendered inside `#zone-canvas` with `#detail-content` container |
| Partial detail with missing evidence | Full detail + "Missing Evidence" section with notices | `#detail-missing` section |
| Partial detail with malformed evidence | Full detail + "Malformed Evidence" section with notices | `#detail-malformed` section |
| Unknown/unavailable run | "Run not found: <run_id>. The run may have been removed." | Text node |
| Contract-version mismatch | "Contract version mismatch. Expected '1' but received '<actual>'." | Text node |
| Invalid response envelope | "Unexpected detail response format." | Text node |
| Invalid summary shape | "Run summary not available." | Text node (summary is null) |
| Invalid detail shape | "Detail evidence not available." | Text node (detail is null) |
| Request/fetch failure | "Failed to load run detail. Check that the server is running." | Text node |
| Stale response ignored | No state change — the newer request's response takes precedence | N/A |
| Unavailable payload_cleanliness | "Payload cleanliness: not available" | Text in detail display |
| Unavailable readiness | "Readiness: not available" | Text in detail display |
| Empty execution_results | "No execution results available." | Text node |
| Empty evidence_paths | "No evidence paths available." | Text node |
| Empty source_errors | "No source errors reported." | Text node |

No error state collapses into the no-selection state. Each error has distinct visible text.

## DETAIL DISPLAY CONTRACT

Each field is rendered through `safeText()` (document.createTextNode) or `escHtml()` (textContent-based escaping) inside a `#detail-content` container.

| Field | Source | Display | Missing policy | Safe rendering |
|---|---|---|---|---|
| Run ID | summary.run_id | Text label | "not available" | safeText |
| Status | summary.status | Text label with CSS class | "not available" | safeText |
| Reason codes | summary.reason_codes | Comma-separated list | "none" | safeText |
| Pipeline status | summary.pipeline_status | Text label | "not available" when null | safeText |
| Git boundary status | summary.git_boundary_status | Text label | "not available" when null | safeText |
| Execution attempted | summary.execution_attempted | "yes"/"no" text | "not available" | safeText |
| Created at | summary.created_at | "Created at: <value>" | "not available" when null | safeText |
| PR URL | summary.pr_url | Anchor link with safe URL check | Not displayed when null | isSafeUrl + href assignment |
| Run JSON available | summary.run_json_available | "available"/"not available" | "not available" | safeText |
| Manifest available | summary.manifest_available | "available"/"not available" | "not available" | safeText |
| Run report available | summary.run_report_available | "available"/"not available" | "not available" | safeText |
| Execution results | detail.execution_results | Bounded structured rows. Each result row shows operation name (safeText) and exit_code (safeText). | "No execution results available." when empty | safeText for operation/exit_code |
| Evidence paths | detail.evidence_paths | Text list — NOT clickable links | "No evidence paths available." when empty | safeText |
| Run JSON hash | detail.run_json_hash | Text label | "not available" when null | safeText |
| Source errors | detail.source_errors | Comma-separated list | "No source errors reported." when empty | safeText |
| Payload cleanliness | detail.payload_cleanliness | Always "not available" | Always null — display explicitly | safeText |
| Readiness | detail.readiness | Always "not available" | Always null — display explicitly | safeText |
| Missing evidence notices | detail.missing | Each notice: expected_path (bold) + reason | "No missing evidence." when empty | safeText |
| Malformed evidence notices | detail.malformed | Each notice: expected_path (bold) + reason | "No malformed evidence." when empty | safeText |

### Rendering rules for execution_results

Each execution result is an object with at minimum an `operation` key and optionally `exit_code` and other fields. Render as:

```
<operation>: exit_code <value>
```

Render operation and exit_code via safeText. Do not render other fields unless they contain only primitive values (string, number, boolean). Do not execute command text. Do not present execution_results as independent proof without evidence context.

### PR URL rendering

Use the `isSafeUrl()` function that exists in artifact_workspace.js. If the URL starts with `http://` or `https://`, render as a clickable anchor with `target="_blank"` and `rel="noopener noreferrer"`. Otherwise render as plain text.

### Evidence paths rendering

Render evidence_paths as a text list only. Do not create clickable links — these are local filesystem paths and must not be exposed as navigable links in the browser.

## PR 0146 DEFERRAL CONTRACT

The following fields from the detail API are intentionally NOT rendered in PR 0145:

- **manifest_files**: NOT displayed. Manifest file browsing is PR 0147 scope.
- **report_preview**: NOT displayed. Full report viewing is PR 0146 scope.

These fields are available in the API response but the workspace does not render them. The `#zone-canvas` detail content does not include manifest or report sections.

Justification: PR 0145 renders the bounded detail evidence panel. Manifest browsing and report rendering are separate roadmap capabilities.

## PR 0147 DEFERRAL CONTRACT

The following zones remain unchanged from PR 0144:

- **#zone-gates-proofs**: Remains "No gate checks available. Gates and proofs will appear after Visual Gate implementation."
- **#zone-logs-captures**: Remains "No logs available. Captured execution output will appear here after a run is selected."

No proof content, command captures, or manifest content populates these zones. Proof and manifest viewing is PR 0147 scope.

## ACCESSIBILITY CONTRACT

| Property | Value |
|---|---|
| Timeline region | `#zone-timeline` with `role="region"` and `aria-labelledby` — unchanged |
| Canvas region | `#zone-canvas` with `role="region"` and `aria-labelledby` — unchanged |
| Selected timeline entry | `aria-selected="true"` attribute on the selected `.timeline-entry` |
| Keyboard selection | Enter and Space on timeline entries trigger selectRun |
| Focus after selection | Focus remains on the clicked timeline entry |
| Detail content container | `#detail-content` inside `#zone-canvas` |
| Status text | Text labels, not color-only |
| Non-color status | Each status includes visible label text |
| No inline handlers from run data | addEventListener used, not inline onclick/onkeydown construction from run values |

## SAFE-RENDERING CONTRACT

| Property | Value |
|---|---|
| Untrusted values | All API-derived values rendered through `safeText()` using document.createTextNode or through `escHtml()` using textContent-based escaping |
| innerHTML usage | Only for static structural HTML templates. Never for untrusted values. |
| Event handlers | Built via addEventListener in JavaScript code. Never constructed from run data strings. |
| eval | Prohibited |
| Function constructors | Prohibited |
| document.write | Prohibited |
| javascript: links | Prohibited — isSafeUrl() validates scheme |
| Local file links | Prohibited — evidence_paths rendered as text, not clickable links |
| External assets | Prohibited — no scripts, stylesheets, fonts, images, or CDNs |
| Dependencies | Prohibited — no frontend framework, build system, or packages |

## IMPLEMENTATION FILE SCOPE

### Approved files

#### 1. services/task_intake/src/task_intake/artifact_workspace.py (EDIT)

**Action**: Edit.
**Exact responsibility**: Replace the placeholder `selectRun()` function with a complete selection, detail-fetch, detail-rendering implementation. Add detail state handling, stale-response protection, and safe rendering. Keep all existing timeline/fetchRuns/renderRunList code intact.

**Exact expected additions**:
- `detailRequestCounter` variable for stale-response protection
- `selectedRunId` variable tracking current selection
- Updated `selectRun(runId)` that: increments counter, shows loading, fetches GET /runs/<encoded_runId>, validates version, validates envelope, checks staleness, calls rendering function
- `renderDetail(data)` function that renders the full detail panel into `#zone-canvas`, replacing the `.zone-placeholder`
- `showDetailLoading()`, `showDetailState(message)`, `showDetailFetchFailure()` helper functions for detail states
- CSS class `.timeline-selected` for the selected entry highlight
- CSS styles for detail panel layout (section headings, field rows, notices)
- Safe rendering of all detail fields via safeText/escHtml
- IsSafeUrl reuse for PR URL rendering
- Execution results rendering as bounded structured rows
- Evidence paths as text (not clickable links)
- Missing and malformed evidence notice rendering
- Payload cleanliness displayed as "not available"
- Readiness displayed as "not available"
- report_preview not rendered (fields available but not displayed)
- manifest_files not rendered (fields available but not displayed)

**Existing unchanged**: `escHtml`, `safeText`, `isSafeUrl`, `fetchRuns`, `showTimelineState`, `renderRunList`, all zone IDs/headings, responsive layout, no external assets, no mutation controls.

**Content prohibited**: No execution of command text from execution_results. No clickable local file links from evidence_paths. No report_preview rendering. No manifest_files rendering. No gates/proofs population. No logs/captures population. No mutation controls. No external assets. No dependencies.

#### 2. services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)

**Action**: Edit (add new test class for detail panel contract).
**Exact responsibility**: Add executable ASGI-based tests for the selection and detail contracts.

**Exact expected additions**: Tests for:
- GET /workspace returns 200 with canvas zone
- Canvas shows initial placeholder before selection
- Timeline entry click triggers detail fetch (verify via ASGI request pattern or source inspection)
- Encoded run_id in detail URL (encodeURIComponent)
- Complete successful detail renders (via controlled runs_root fixture)
- Partial detail with missing evidence renders notices
- Partial detail with malformed evidence renders notices
- Unknown run_id shows error state
- Version mismatch shows contract-version error
- Invalid response envelope shows format error
- Fetch failure shows error state
- payload_cleanliness shown as "not available"
- readiness shown as "not available"
- Empty execution_results shows "No execution results available."
- Empty evidence_paths shows "No evidence paths available."
- Empty source_errors shows "No source errors reported."
- Unique values safely rendered (hostile strings rendered as text, not executed)
- report_preview not rendered in Canvas
- manifest_files not rendered in Canvas
- Gates/proofs placeholder unchanged
- Logs/captures placeholder unchanged
- No mutation controls in detail panel
- GET /workspace regression (zone IDs, headings)
- GET / regression
- GET /runs regression
- GET /runs/<run_id> regression

**Existing unchanged**: All PR 0143 and PR 0144 tests for zone IDs, headings, timeline live list, list states, and mutation absence.
**Content prohibited**: Tests must not modify server.py, runtime_evidence.py, runtime_evidence_serialization.py. Tests must not write to .ariadne. Tests must not launch agents or Docker.

#### 3. .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md (NEW)

Written by coder. All 11 required sections per the IMPLEMENTATION_REPORT_TEMPLATE.md.

#### 4. .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml (NEW)

Written by precommit-review. Follows review-artifact.schema.yml.

### Rejected: server.py edit

**Decision**: No server.py changes.
**Rationale**: GET /runs/<run_id> already exists and returns the full version-1 detail envelope. No new endpoint, no route modification, no behavior change required.

### Rejected: runtime_evidence.py edit

**Decision**: No runtime_evidence.py changes.
**Rationale**: The read model already provides all fields needed.

### Rejected: runtime_evidence_serialization.py edit

**Decision**: No serialization changes.
**Rationale**: The version-1 detail contract is complete and unchanged.

### Not modified (complete list)

- services/runner/src/runner/runtime_evidence.py
- services/runner/tests/test_runtime_evidence.py
- services/task_intake/src/task_intake/server.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- ROADMAP.md, agents/**, schemas/**, docs/**, .github/**, pyproject.toml, etc.

## TEST PLAN

### 1. PR 0145 Detail Panel Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Detail or detail or selection or selectRun or canvas or renderDetail or stale or missing_evidence or malformed_evidence or version_mismatch" -q
```

Expected: all detail panel tests pass.
If not met: block.

### 2. Existing Workspace Shell and Timeline Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Detail and not detail and not selection and not selectRun and not canvas" -q
```

Expected: all existing workspace tests pass.
If not met: block.

### 3. Existing Detail API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all 73+ existing detail and list tests pass.
If not met: block.

### 4. Serialization Contract Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```

Expected: all 61 contract tests pass.
If not met: block.

### 5. Runtime Evidence Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_runtime_evidence.py -q
```

Expected: all 32 tests pass.
If not met: block.

### 6. Python Compile

```bash
python -m compileall -f services/task_intake/src services/runner/src
```

Expected: all files compile.
If not met: block.

### 7. Detail API Preservation Grep

```bash
grep -n "serialize_run_evidence_detail\|read_run_evidence_detail\|ev_contract_version" services/task_intake/src/task_intake/server.py services/task_intake/src/task_intake/runtime_evidence_serialization.py
```

Expected: detail endpoint and serializer lines present and unchanged.
If not met: block (if lines were removed by mistake).

### 8. Selection and Encoded Request Grep

```bash
grep -n -E "encodeURIComponent|selectRun|detailRequestCounter|selectedRunId" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: selection, stale-protection counter, and safe encoding present.
If not met: block.

### 9. Report Viewer Deferral Grep

```bash
grep -n -E "report_preview|Report Preview|report preview" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no rendering of report_preview (may appear in comments or API field access without display).
If not met: block.

### 10. Manifest/Proof Viewer Deferral Grep

```bash
grep -n -E "manifest_files|Manifest Files|manifest" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: manifest_files not rendered as visible content (may appear in API access or comments).
If not met: block.

### 11. Mutation-Control Prohibition Grep

```bash
grep -n -i -E "accept|reject|approve|retry|rerun|commit|push|merge|pr create|gh pr|agent.*launch" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: only "approved" in fixture data (git_boundary_status) — no mutation controls.
If not met: block.

### 12. Safe Rendering Grep

```bash
grep -n -E "textContent|innerHTML.*=" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: textContent used for untrusted values. innerHTML only for static structural templates or through escHtml.
If not met: block.

### 13. Prohibited Execution/Import Grep

```bash
grep -n -E "subprocess|os.system|Popen|docker|git|shell=True|eval|Function\(|document.write" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no matches (exit code 1).
If not met: block.

### 14. Forbidden-Path Diff

```bash
git diff --name-only -- services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/task_intake/src/task_intake/server.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py services/runner/tests/
```

Expected: empty.
If not met: block.

### 15. Planning-Lock Diff

```bash
git diff -- .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/PLAN.md .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/reviews/plan-review.yml
```

Expected: no differences.
If not met: block.

### 16. Whitespace Check

```bash
git diff --check
```

Expected: no whitespace errors.
If not met: block.

### 17. Dirty-Tree Inspection

```bash
git status --short
```

Expected: only artifact_workspace.py (modified), test_artifact_workspace_shell.py (modified), PR artifacts.
If unknown untracked files exist: block.

### 18. Cached-Diff Inspection

```bash
git diff --cached --name-only
```

Expected: empty.
If not met: block.

### 19. IMPLEMENTATION_REPORT.md Existence and Readback

```bash
test -f .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md
```
Expected: file exists.
If not met: block.

```bash
sed -n '1,30p' .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md
```
Expected: readable, first lines include proof boundary disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write:

`.project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`

The report must include all 11 standard sections:

1. TASK SUMMARY
2. FILES READ
3. FILES CHANGED
4. IMPLEMENTATION DECISIONS
5. PLAN ALIGNMENT
6. DEVIATIONS FROM PLAN
7. VALIDATION RUN
8. BOUNDARY CONFIRMATIONS
9. NON-GOALS PRESERVED
10. RISKS OR WARNINGS
11. NEXT REVIEWER FOCUS

The implementation report is handoff context, not proof. Agent output is not proof. Actual files, diffs, validation output, dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK remain proof.

### Fresh implementation handling

This PR starts from a clean main branch. The coder edits existing files.

### Authorized continuation handling

If continuation is authorized, the coder must re-read PLAN.md, verify locked planning artifacts are unchanged, read all existing implementation diffs, preserve correct PLAN-approved work, and distinguish pre-existing changes from new changes. Destructive reset, restore, or clean commands are forbidden unless the human explicitly authorizes them.

### Authorized rerun handling

If a rerun is authorized, the coder must re-read PLAN.md and rewrite IMPLEMENTATION_REPORT.md.

### Unexplained pre-existing report handling

No pre-existing implementation report is expected. If one exists, verify it matches PLAN.md. If it does not, block.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. PLAN.md or plan-review.yml changes.
3. GET /runs/<run_id> is duplicated or modified.
4. Existing evidence API behavior changes without a proven defect.
5. ev_contract_version changes from "1".
6. GET / or its existing detail panel changes.
7. Timeline live-list behavior breaks (fetchRuns, renderRunList).
8. Selection does not use a safely encoded run_id (encodeURIComponent).
9. A stale detail response can replace the current selection (no latest-selection-wins).
10. Any required detail state is absent (initial, loading, success, missing, malformed, unknown, version mismatch, invalid envelope, fetch failure).
11. Missing or malformed evidence notices are hidden.
12. Unavailable values (payload_cleanliness, readiness) are inferred or fabricated.
13. Execution command text from execution_results is executed.
14. Evidence paths become clickable local-file links.
15. Full report content (report_preview) is rendered.
16. Full manifest viewer is implemented.
17. Gates & Proofs receives PR 0147 content.
18. Logs & Captures receives PR 0147 content.
19. A mutation or execution control is added.
20. Agent launch is added.
21. Git or PR authority is added.
22. Unsafe dynamic HTML exists (untrusted values via innerHTML).
23. External assets or dependencies are added.
24. Required tests or validation fail.
25. IMPLEMENTATION_REPORT.md is absent or incomplete.
26. Unknown untracked files exist.
27. Generated residue enters the payload.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0145-artifact-workspace-run-detail-evidence-panel`.
2. Only approved files changed: artifact_workspace.py (edit), test_artifact_workspace_shell.py (edit), IMPLEMENTATION_REPORT.md (new), precommit-review.yml (new).
3. Planning artifacts remain locked.
4. PR 0145 scope is preserved (Run Detail Evidence Panel — not full workspace).
5. PR 0146 and PR 0147 remain separate.
6. GET /workspace remains read-only.
7. GET /runs remains unchanged.
8. GET /runs/<run_id> remains unchanged.
9. Timeline selection is accessible (aria-selected, keyboard navigation).
10. Detail URL safely encodes run_id (encodeURIComponent).
11. Latest selection wins (detailRequestCounter).
12. Initial state exists (no selection).
13. Loading state exists.
14. Complete state exists.
15. Partial missing state exists.
16. Partial malformed state exists.
17. Unknown-run state exists.
18. Version-mismatch state exists.
19. Invalid-payload state exists.
20. Fetch-failure state exists.
21. Summary fields render safely.
22. Execution results render safely (operation, exit_code only).
23. Hash renders safely.
24. Evidence paths render as text only (not clickable links).
25. Missing and malformed notices are visible.
26. payload_cleanliness is not inferred (shown as "not available").
27. readiness is not inferred (shown as "not available").
28. Report viewer remains deferred (report_preview not rendered).
29. Manifest/proof viewer remains deferred (manifest_files not rendered).
30. Gates & Proofs remains deferred.
31. Logs & Captures remains deferred.
32. No mutation or execution authority exists.
33. No arbitrary filesystem input exists.
34. No external assets or dependencies exist.
35. Required tests pass.
36. IMPLEMENTATION_REPORT.md exists and was read back.
37. PLAN DRIFT GATE passed.
38. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The detail endpoint (GET /runs/<run_id>) is found to be incompatible with PR 0145 requirements.
2. Backend changes to runtime_evidence.py or runtime_evidence_serialization.py appear required.
3. A server.py change is required.
4. The page requires a browser framework, dependency, or external asset.
5. An unapproved file must change.
6. PR 0146 or PR 0147 capability must be implemented.
7. Required validation fails.

## NON-GOALS

1. Implementing the detail panel (this is a planning task only).
2. Editing artifact_workspace.py during planning.
3. Editing tests during planning.
4. Editing server.py.
5. Editing runtime_evidence.py or runtime_evidence_serialization.py.
6. Creating a new backend endpoint.
7. Changing the version-1 contract.
8. Changing the Local Interaction page or its detail panel.
9. Implementing the Run Report Viewer (PR 0146).
10. Implementing the Proof and Manifest Viewer (PR 0147).
11. Populating Gates & Proofs with content.
12. Populating Logs & Captures with content.
13. Adding mutation controls.
14. Adding agent launch.
15. Adding git or PR controls.
16. Adding arbitrary filesystem access.
17. Adding external assets or dependencies.
18. Writing plan-review.yml during planning.
19. Writing IMPLEMENTATION_REPORT.md during planning.
20. Writing precommit-review.yml during planning.
21. Committing, pushing, or creating a pull request during planning.
