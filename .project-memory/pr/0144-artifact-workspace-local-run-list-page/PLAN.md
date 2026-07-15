# PR 0144 — Artifact Workspace Local Run List Page Plan

## EVIDENCE SNAPSHOT

1. HEAD: `af3a53b0d543dc741643ec626bafdf3796518aa1`
2. origin/main: `af3a53b0d543dc741643ec626bafdf3796518aa1`
3. Merge base: `af3a53b0d543dc741643ec626bafdf3796518aa1`
4. Branch: `0144-artifact-workspace-local-run-list-page`
5. Dirty tree: clean (no modified tracked files)
6. Cached diff: empty
7. PR 0143 merge evidence: `af3a53b (HEAD -> 0144-..., origin/main, origin/HEAD, main) feat(task-intake): add artifact workspace four-zone shell (#169)`
8. Current workspace selectors (from artifact_workspace.py):
   - `#artifact-workspace` — root
   - `#zone-timeline` — timeline zone with h2 "Timeline"
   - `#zone-canvas` — canvas zone with h2 "Artifact Canvas"
   - `#zone-gates-proofs` — gates & proofs zone with h2 "Gates & Proofs"
   - `#zone-logs-captures` — logs & captures zone with h2 "Logs & Captures"
9. Current fixture behavior: `_WORKSPACE_FIXTURE` with 2 mock entries. `#fixture-notice` div says "Fixture data — not runtime evidence. Live timeline coming in PR 0144." `selectRun()` sets canvas placeholder text but fetches no detail.
10. Current GET /runs v1 contract (from serialize_run_evidence_summary):
    - Index envelope: ev_contract_version, ok, count, runs, runs_root
    - Entry keys: run_id, status, reason_codes, pipeline_status, git_boundary_status, execution_attempted, created_at, run_json_available, manifest_available, run_report_available, missing_evidence, malformed_evidence, pr_url, payload_cleanliness_available, readiness_available
    - Does NOT include: branch, generated_at, readiness value
    - created_at is Optional[str] derived from finished_at or started_at in run.json
    - readiness_available is hardcoded False in the serializer
11. Persisted run.json fields (from run_persistence.py): schema_version, run_id, branch, base_branch, status, reason_codes, pipeline_status, pipeline_final_action, pipeline_has_blockers, pipeline_step_summary, pipeline_gate_summary, git_boundary_status, command_plan_summary, execution_attempted, execution_results_summary, approval_summary, artifact_hashes, warnings, next_action, started_at, finished_at
12. Current runtime evidence summary fields (RunEvidenceSummary dataclass): run_id, status, reason_codes, pipeline_status, git_boundary_status, execution_attempted, created_at, run_json_path, manifest_path, run_report_path, pr_url, missing_evidence, malformed_evidence. Does NOT include branch.
13. Readiness behavior: readiness is always None in RunEvidenceDetail.payload_cleanliness and readiness. readiness_available is hardcoded False in the serializer.
14. Existing tests: test_artifact_workspace_shell.py (61 tests), test_local_run_history_in_page.py (73 tests), test_runtime_evidence_serialization_contract.py (61 tests), test_runtime_evidence.py (32 tests), test_task_intake.py (19 tests).

## ROADMAP ALIGNMENT

- roadmap track: Stream 2 — Artifact Workspace Shell
- expected PR slot: PR 0144 (Local Run List Page)
- why this PR is next: PR 0143 (4-Zone Shell Skeleton) is complete. The timeline fixture must be replaced with a live read-only GET /runs connection. This PR delivers the first live evidence-backed capability in the workspace.
- batching policy check: PR 0144 is a coherent live read-only run list capability backed by the existing versioned evidence API. It is not an isolated UI control or cosmetic change. This is the second PR of the Artifact Workspace Shell stream (0143-0147), architect-authorized as part of the product roadmap.
- drift heuristic check: Not triggered. No consecutive single-file UI PRs. The workspace shell already uses an isolated module pattern.
- architect sign-off required: yes (roadmap stream continuation)
- architect sign-off reference if required: Human architect requested the next roadmap step after PR 0143. PR 0144 is the second product PR of Stream 2.

### Roadmap State

1. Active stream: Stream 2 — Artifact Workspace Shell
2. Expected slot: PR 0144 (Local Run List Page)
3. PR predecessor: PR 0143 four-zone shell is complete.
4. PR 0145 through PR 0147 remain separate (detail panel, report viewer, proof/manifest viewer).
5. No mutation stream is opened.
6. No frozen capability is opened.

## CONTRACT GAP DECISION

### Gap table

| Roadmap field | Current API field | Persisted source | Availability | UI behavior | Contract change | Fabrication risk |
|---|---|---|---|---|---|---|
| run_id | run_id | run.json run_id | Always available | Display as text | No | None |
| status | status | run.json status | Always available | Display as text | No | None |
| branch | Not available | run.json branch, base_branch | Not in v1 API response | Display "not available" | None in this PR | Cannot fabricate from API |
| generated_at | Not available | run.json started_at, finished_at | Not an exact field in v1 | Display created_at labeled "Created at" with semantic note | None in this PR | Cannot fabricate; created_at is derived from finished_at/started_at |
| created_at | created_at | run.json finished_at or started_at | Always available (null possible) | Display as "Created at" label | No | Must not relabel as "generated_at" |
| readiness | Not available | None (readiness is always None in RunEvidenceDetail) | Not in v1 API | Display "not available" | None in this PR | Cannot fabricate; readiness_available is hardcoded False |
| readiness_available | readiness_available (hardcoded False) | Not persisted | Always False | Use as "readiness: not available" signal | No | Must not present as readiness value |

### Decision: OPTION A — CURRENT CONTRACT ONLY

PR 0144 uses GET /runs version 1 unchanged.

**Rationale:**
1. **Evidence-based**: The v1 contract has no `branch` field, no `generated_at` field, and `readiness` is not exposed as a meaningful value. These are facts confirmed by reading `runtime_evidence.py`, `runtime_evidence_serialization.py`, and `run_persistence.py`.
2. **Backward compatible**: No changes to runtime_evidence.py, runtime_evidence_serialization.py, or the GET /runs response.
3. **Minimal**: Only artifact_workspace.py changes are needed (HTML/JS). No server.py, no serializer, no evidence model changes.
4. **Honest**: The UI explicitly displays "not available" for branch, reports `readiness_available: False` as "not available", and labels the timestamp as "Created at" (matching the actual field name `created_at`).
5. **Sufficient for PR 0144**: The roadmap fields `branch`, `generated_at`, and `readiness` are intentionally deferred to a future additive contract extension (Option B) that must be separately planned.

**Deferred roadmap fields statement**: The roadmap acceptance for PR 0144 states `run_id, status, branch, generated_at, readiness`. Fields `branch`, `generated_at`, and `readiness` are NOT available in the current v1 API response. The implementation explicitly displays them as unavailable. Satisfying these roadmap fields requires a future Option B contract extension (adding `branch` to `RunEvidenceSummary` and `serialize_run_evidence_summary`, and defining `generated_at` semantics). This extension is out of scope for PR 0144 and must be planned separately.

## LIVE LIST DATA FLOW

| Property | Value |
|---|---|
| Exact page route | GET /workspace |
| Exact API route | GET /runs (existing versioned endpoint, unmodified) |
| Exact load trigger | On page load (immediately after the DOM is ready) |
| Exact request method | GET |
| Exact request URL | `/runs` (relative, same origin) |
| Query parameters | None propagated in PR 0144. The default runs_root from the server is used. |
| Contract-version validation | Response must have `ev_contract_version === "1"`. If absent or not "1", reject visibly. |
| Envelope validation | Response must be a JSON object with `ok` (boolean), `runs` (array), `ev_contract_version` (string). |
| Entry validation | Each entry in `runs` must be an object with at minimum `run_id` (string) and `status` (string). Entries missing both are skipped with a warning indicator. |
| Sorting behavior | Entries are displayed in the order returned by the server (newest-first per list_run_evidence_summaries). No client-side reordering. |
| Rendering boundary | HTML structure is built in JavaScript via `document.createElement` and `textContent` assignment, then inserted into `#timeline-entries`. No `innerHTML` concatenation of untrusted values. |
| Refresh behavior | The page fetches GET /runs once on load. No periodic polling. |
| Failure behavior | On any fetch failure, the timeline zone shows a specific error state. Existing content is cleared. |
| Production fixture removal | The `_WORKSPACE_FIXTURE` array is replaced with an empty fallback array. The `#fixture-notice` div is removed. |
| Test fixture boundary | Test fixtures remain in `test_artifact_workspace_shell.py` only, using the ASGI server with controlled runs_root. |

## LIST ITEM CONTRACT

Each run is rendered as one `.timeline-entry` div inside `#timeline-entries`.

| Field | Source key | Visible label | Missing policy | Escaping method | Required/Optional |
|---|---|---|---|---|---|
| run_id | `run_id` | Displayed as bold text | Entry skipped if absent (no minimum identifier) | escHtml via textContent | Required |
| status | `status` | Colored status text | "unknown" shown if absent | escHtml via textContent | Required |
| branch | Not available | "branch: not available" (shown below run_id) | Always "not available" — no field in v1 response | Static text via textContent | N/A — always unavailable |
| timestamp | `created_at` | Labeled "Created at" | "not available" text if null | escHtml via textContent | Optional (displays "not available") |
| readiness | Not available | "readiness: not available" | Always "not available" — readiness_available is False | Static text via textContent | N/A — always unavailable |
| reason_codes | `reason_codes` | Shown as comma-separated text below status | None shown if empty array | escHtml via textContent | Optional |
| evidence status | `missing_evidence`, `malformed_evidence` | Count indicators with condition | Empty counts omitted | textContent | Optional |
| PR URL | `pr_url` | Safe link when present | Not shown if null | anchor element with href verified as safe | Optional |
| run_json_available | `run_json_available` | Diagnostic signal | "not available" if False | textContent | Optional |

### PR URL safety

If `pr_url` is present and non-null, render it as an HTML anchor `<a>` element with `href` set to the URL value and `target="_blank"`. The anchor text is the display value. No JavaScript URL (`javascript:`) or data URL scheme may be rendered as a link. If the URL does not start with `http://` or `https://`, render it as plain text instead of a link.

## STATE CONTRACT

| State | Selector/Content | Text | Transition |
|---|---|---|---|
| Loading | `#timeline-entries` | "Loading runs..." | Set on page load before fetch begins |
| Non-empty success | `#timeline-entries` with `.timeline-entry` children | One div per run with identifier, status, timestamp | After successful parse of version-1 response with count>0 |
| Empty success | `#timeline-entries` | "No runs available. Submit a task to see timeline entries." | After successful parse of version-1 response with count===0 |
| Missing/unreadable root | `#timeline-entries` | "Runs directory not available. Run a task to create run evidence." | Response ok===false with error message. Error message rendered safely as text. |
| Malformed run entry | Entry displays run_id if available with "(incomplete)" status text | Shows run_id and "(incomplete)" for entries without minimum fields | During entry validation — non-fatal for other entries |
| Missing evidence | Entry shows warning indicator | "Missing: [file list]" | If entry.missing_evidence.length > 0 |
| Version mismatch | `#timeline-entries` | "Contract version mismatch. Expected '1' but received '<actual>'." | After successful fetch but ev_contract_version is not "1" |
| Invalid payload | `#timeline-entries` | "Unexpected response format. Could not parse run list." | Response is valid JSON but lacks required envelope fields (ok, runs) |
| Fetch failure | `#timeline-entries` | "Failed to load run data. Check that the server is running." | Network error, HTTP error status, or JSON parse failure |
| Unavailable branch | Each entry shows static text | "branch: not available" | Always shown after run_id |
| Unavailable timestamp | Each entry shows "not available" for created_at | "created_at: not available" | If entry.created_at is null |
| Unavailable readiness | Each entry shows static text | "readiness: not available" | Always shown on each entry (readiness_available is always False) |

### Failure during refresh

On any fetch failure after a successful previous load, the timeline content is cleared and the relevant error state shown. Previously fetched entries are not preserved across refresh failures.

## IMPLEMENTATION FILE SCOPE

### Approved files

#### 1. services/task_intake/src/task_intake/artifact_workspace.py (EDIT)

**Action**: Edit.
**Exact responsibility**: Replace the `_WORKSPACE_FIXTURE` mechanism with a live GET /runs fetch. Remove production fixture data, the `#fixture-notice` div, and the `selectRun` placeholder from the HTML template. Update JavaScript to:
- Fetch GET /runs on page load
- Validate ev_contract_version is "1"
- Validate envelope (ok, runs)
- Validate each entry (run_id, status)
- Render each entry with exact fields per the LIST ITEM CONTRACT
- Handle all states per the STATE CONTRACT
- Use escHtml via textContent for all untrusted values
- Keep the canvas, gates, and logs zones as placeholders
- Remove the `_WORKSPACE_FIXTURE` constant (or replace with empty fallback array)
- Remove the `#fixture-notice` element from HTML
- Update `selectRun` to update canvas placeholder with selected run_id

**Exact expected additions**:
- `fetchRuns()` function that calls `GET /runs` and handles all states
- Version validation (ev_contract_version)
- Entry rendering with all required fields
- Safe URL rendering for pr_url

**Existing unchanged**: Workspace root ID, all four zone IDs and headings, responsive layout, escHtml function structure, CSS classes for status coloring, zone placeholder patterns.

**Content prohibited**: No mutation controls (accept, reject, approve, retry, rerun). No agent launch. No git/gh/PR controls. No fetch to arbitrary URLs. No arbitrary file path input. No POST/PUT/PATCH/DELETE behavior. No external scripts, stylesheets, fonts, images, or CDNs. No localStorage or sessionStorage. No subprocess/os.system/Docker/git/gh calls. No runtime evidence model imports. No filesystem access.

**Tests proving boundary**: Existing workspace shell tests amended. New tests validate live list, empty state, missing root, malformed evidence, version mismatch, invalid payload, fetch failure, safe rendering, branch/readiness unavailability, no mock production entries, semantic list structure, and accessibility.

#### 2. services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)

**Action**: Edit (add new test class).
**Exact responsibility**: Add executable ASGI-based tests for the live GET /runs connection and all state contracts.
**Exact expected additions**: Tests for:
- GET /workspace returns 200 with timeline zone
- Production fixture notice (fixture-notice div) is absent
- Non-empty run list renders (via controlled runs_root)
- Empty run list renders (empty runs_root)
- Missing/unreadable root state renders (nonexistent runs_root)
- Version mismatch state renders (mock API with wrong version)
- Invalid payload state renders (malformed JSON response)
- All entries have run_id visible
- All entries have status visible
- Each entry shows "branch: not available" text
- Each entry shows "readiness: not available" text
- Each entry shows "Created at" for the timestamp field
- Malformed evidence indicator visible
- Missing evidence indicator visible
- Safe rendering of hostile strings (XSS attempt rendered as text)
- Semantic list structure (ul/li or equivalent accessible container)
- Status communicated with text (not color-only)
- No mutation/agent/git/PR controls present
- Canvas remains a PR 0145 placeholder
- Gates/proofs remain deferred
- Logs/captures remain deferred
- GET /runs contract remains compatible
- GET /runs/<run_id> remains compatible
- GET / remains unchanged

**Existing unchanged**: All PR 0143 zone, heading, fixture, and mutation tests remain.
**Content prohibited**: Tests must not modify server.py, runtime_evidence.py, or runtime_evidence_serialization.py. Tests must not write to .ariadne. Tests must not launch agents or Docker.

#### 3. .project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md (NEW)

Written by coder. All 11 required sections per the IMPLEMENTATION_REPORT_TEMPLATE.md.

#### 4. .project-memory/pr/0144-artifact-workspace-local-run-list-page/reviews/precommit-review.yml (NEW)

Written by precommit-review. Follows review-artifact.schema.yml.

### Rejected candidate: server.py edit

**Decision**: No server.py changes needed.
**Rationale**: GET /workspace already exists and calls `render_artifact_workspace()`. GET /runs already returns versioned run list JSON. No new route, no route modification, no server behavior change is required.

### Rejected candidate: runtime_evidence.py edit

**Decision**: No runtime_evidence.py changes.
**Rationale**: Option A uses the current contract without extension. Adding `branch` to `RunEvidenceSummary` would be an Option B extension. This is intentionally deferred.

### Rejected candidate: runtime_evidence_serialization.py edit

**Decision**: No changes to the serialization contract.
**Rationale**: Option A uses version 1 unchanged. No fields added, removed, or renamed.

### Not modified

- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/task_intake/src/task_intake/server.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- ROADMAP.md, agents/**, schemas/**, docs/**, .github/**, pyproject.toml, etc.

## ACCESSIBILITY AND SAFETY CONTRACT

| Property | Value |
|---|---|
| Timeline region preservation | `#zone-timeline` with `role="region"` and `aria-labelledby="zone-timeline-heading"` unchanged |
| List landmark | `#timeline-entries` is container for timeline entries. Each entry has `role="button"` if interactive. |
| Accessible list label | h2 heading "Timeline" referenced via aria-labelledby |
| Run-item semantics | Each entry is a `.timeline-entry` div with `role="button"`, `tabindex="0"` |
| Status text | status value displayed as text (e.g., "completed", "blocked") — not color-only |
| Non-color status communication | Each status value has a text prefix or label ("Status: completed") — color is supplemental |
| Keyboard behavior | Each entry supports Enter and Space keys for selection |
| Focus behavior | After page load, focus remains on the page body or h1. After entry click, focus stays on the clicked entry. |
| Loading announcement | "Loading runs..." is visible text content (not hidden) |
| Error announcement | Error text is visible in the timeline zone (not hidden) |
| Safe text insertion | All field values rendered via escHtml using document.createElement + textContent |
| Safe optional-link behavior | pr_url rendered as anchor if http/https, plain text otherwise. Verified by URL scheme check. |
| No inline handlers from run values | No `onclick` or inline event handlers built from run data values. Event delegation or addEventListener on entry container. |
| No external assets | Zero external scripts, stylesheets, fonts, images, icons, or CDNs. |
| No mutation controls | Zero accept, reject, approve, retry, rerun, commit, push, merge, or PR controls. |

## TEST PLAN

### 1. PR 0144 Focused Tests (new test class in existing test file)

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Live or live or state or state or list or List or timeline or Timeline or version or version or branch or readiness or render or Render or safe" -q
```

Expected: all live list state contract tests pass.
If not met: block.

### 2. Existing Workspace Shell Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Live and not live and not state and not State" -q
```

Expected: all PR 0143 regression tests pass (zone IDs, headings, placeholders, mutation absence, etc.).
If not met: block.

### 3. Existing Local Interaction and Route Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all 73+ existing route tests pass.
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

### 7. Forbidden-Path Diff

```bash
git diff --name-only -- services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/task_intake/src/task_intake/server.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/runner/tests/ services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py
```

Expected: empty (no changes to these files).
If not met: block.

### 8. Planning-Lock Diff

```bash
git diff -- .project-memory/pr/0144-artifact-workspace-local-run-list-page/PLAN.md .project-memory/pr/0144-artifact-workspace-local-run-list-page/reviews/plan-review.yml
```

Expected: no differences.
If not met: block.

### 9. Whitespace Check

```bash
git diff --check
```

Expected: no whitespace errors.
If not met: block.

### 10. Live GET /runs Connection Grep

```bash
grep -n -E "fetch\(|fetchRuns|/runs|ev_contract_version|version.*mismatch|version.*check" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: fetch call to /runs and version validation present.
If not met: block.

### 11. Production Mock-Entry Absence Grep

```bash
grep -n "fixture-notice\|_WORKSPACE_FIXTURE\|mock-run\|Fixture data" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: No production fixture notice or mock entry references (or only in fallback/empty-array pattern).
If not met: block.

### 12. Mutation-Control Prohibition Grep

```bash
grep -n -i -E "accept|reject|approve|retry|rerun|commit|push|merge|pr create|gh pr|agent.*launch" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no mutation control references.
If not met: block.

### 13. Safe Rendering Grep

```bash
grep -n -E "textContent|innerHTML.*=" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: textContent used for untrusted values. innerHTML only for static structural HTML or through escHtml.
If not met: block.

### 14. External-Asset Prohibition Grep

```bash
grep -n -i -E "https?://|//[a-z]+\." services/task_intake/src/task_intake/artifact_workspace.py; echo "EXIT:$?"
```

Expected: no match (exit code 1).
If not met: block.

### 15. Branch and Readiness Unavailability Grep

```bash
grep -n -i -E "branch.*not available|readiness.*not available|created_at|Created at" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: branch and readiness shown as unavailable; created_at labeled as "Created at".
If not met: block.

### 16. Dirty-Tree Inspection

```bash
git status --short
```

Expected: only artifact_workspace.py (modified), test_artifact_workspace_shell.py (modified), PR artifact files.
If unknown untracked files exist: block.

### 17. Cached-Diff Inspection

```bash
git diff --cached --name-only
```

Expected: empty.
If not met: block.

### 18. IMPLEMENTATION_REPORT.md Existence and Readback

```bash
test -f .project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md
```
Expected: file exists.
If not met: block.

```bash
sed -n '1,30p' .project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md
```
Expected: readable, first lines include proof boundary disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write:

`.project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md`

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

This PR starts from a clean main branch. The coder edits existing files that already exist in the working tree.

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
3. PR 0144 is not the only product capability implemented.
4. The production timeline still uses mock entries as its data source (fixture-notice div present).
5. GET /runs is not the live data source for the timeline.
6. Branch, timestamp, or readiness values are fabricated.
7. created_at is silently relabelled as generated_at without an approved semantic rule.
8. readiness_available is presented as a readiness value.
9. Contract gap decision (Option A) is not explicit in the implementation.
10. ev_contract_version validation is absent.
11. Existing API response fields are assumed to exist when they do not (branch, generated_at, readiness).
12. Loading, empty, root-error, malformed, version-error, invalid-payload, or fetch-error states are missing.
13. Unsafe HTML rendering exists (untrusted values via innerHTML).
14. Untrusted values enter inline executable event handlers.
15. An arbitrary path control or filesystem input is added.
16. A mutation or execution control is added.
17. An agent-launch control is added.
18. A git or PR control is added.
19. External assets or dependencies are added.
20. GET / or closed Local Interaction behavior changes.
21. PR 0145 through PR 0147 scope is absorbed (detail panel, report viewer, proof/manifest viewer).
22. Required tests are missing or weak.
23. Required validation is missing or failing.
24. IMPLEMENTATION_REPORT.md is absent or incomplete.
25. Unknown untracked files exist.
26. Generated residue enters the payload.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0144-artifact-workspace-local-run-list-page`.
2. Only approved files changed: artifact_workspace.py (edit), test_artifact_workspace_shell.py (edit), IMPLEMENTATION_REPORT.md (new), precommit-review.yml (new).
3. Planning artifacts remain locked.
4. PR 0144 roadmap scope is preserved (Local Run List Page — not full workspace).
5. PR 0145 through PR 0147 remain separate.
6. GET /workspace remains read-only.
7. Timeline uses GET /runs as its data source.
8. Production mock entries (fixture-notice) are removed as active data.
9. Contract gap decision is explicit Option A.
10. No field value is fabricated (branch, readiness, generated_at all shown as "not available").
11. run_id is rendered.
12. status is rendered.
13. branch policy is rendered as "not available".
14. timestamp policy uses "Created at" label (not "generated_at").
15. readiness policy is rendered as "not available".
16. Loading state exists.
17. Empty state exists.
18. Root-error/missing-root state exists.
19. Malformed-evidence indicator exists.
20. Version-mismatch state exists.
21. Invalid-payload state exists.
22. Fetch-failure state exists.
23. Safe rendering is enforced (escHtml, textContent).
24. Semantic accessible list exists (accessible role, keyboard navigation, text status).
25. GET / remains unchanged.
26. Existing evidence routes (GET /runs, GET /runs/<run_id>) remain compatible.
27. No mutation or execution authority exists.
28. No arbitrary filesystem input exists.
29. No external assets or dependencies exist.
30. Required tests pass (new + all existing regressions).
31. IMPLEMENTATION_REPORT.md exists and was read back.
32. PLAN DRIFT GATE passed.
33. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The roadmap field gap cannot be resolved without fabricated values (branch, readiness, generated_at).
2. Exact GET /runs compatibility cannot be preserved.
3. A breaking contract change is required.
4. Readiness must be inferred rather than read from persisted evidence.
5. The page requires arbitrary filesystem input.
6. A browser framework, dependency, or external asset is required.
7. An unapproved file must change.
8. PR 0145 through PR 0147 capability must be implemented.
9. Required validation fails.

## NON-GOALS

1. Implementing the run list (this is a planning task only).
2. Editing artifact_workspace.py during planning.
3. Editing tests during planning.
4. Editing server.py.
5. Editing runtime_evidence.py.
6. Editing runtime_evidence_serialization.py.
7. Editing run_persistence.py.
8. Editing test_local_run_history_in_page.py.
9. Editing test_runtime_evidence_serialization_contract.py.
10. Extending the version-1 serialization contract.
11. Writing plan-review.yml during planning.
12. Writing IMPLEMENTATION_REPORT.md during planning.
13. Writing precommit-review.yml during planning.
14. Implementing run detail evidence panel (PR 0145).
15. Implementing report rendering (PR 0146).
16. Implementing proof or manifest rendering (PR 0147).
17. Adding mutation controls.
18. Adding agent launch.
19. Adding git or PR controls.
20. Adding arbitrary filesystem access.
21. Adding external assets.
22. Adding dependencies.
23. Creating a second run-list endpoint.
24. Committing, pushing, or creating a pull request during planning.
