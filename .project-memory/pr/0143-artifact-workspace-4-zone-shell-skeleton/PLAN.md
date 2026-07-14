# PR 0143 — Artifact Workspace 4-Zone Shell Skeleton Plan

## EVIDENCE SNAPSHOT

1. HEAD: `01856eba8ee4083f4d24df6b3bfa3d2d7c8e4366`
2. origin/main: `01856eba8ee4083f4d24df6b3bfa3d2d7c8e4366`
3. Merge base: `01856eba8ee4083f4d24df6b3bfa3d2d7c8e4366` (HEAD equals origin/main and merge base)
4. Branch: `0143-artifact-workspace-4-zone-shell-skeleton`
5. Dirty tree: clean (no modified tracked files)
6. Cached diff: empty
7. Current ORCHESTRATOR_STANDARD version: 1.2
8. Workflow companion version: 1.0.0 (ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md)
9. PR 0142A merge evidence: `01856eb (HEAD -> 0143-..., origin/main, origin/HEAD, main) docs(project-memory): codify three-response orchestrator workflow (#168)` — confirmed in git log.
10. Current route inventory (from server.py):
    - `GET /health` — health check
    - `GET /backlog` — backlog decision route
    - `GET /backlog/decision/history` — decision history
    - `GET /backlog/decision/trace` — decision trace
    - `GET /product/iterations` — product iteration list
    - `GET /product/iterations/review-packet` — review packet
    - `GET /runs/<run_id>` — run detail evidence (PR 0141, L920)
    - `GET /runs` — run index evidence (PR 0139, L955)
    - `GET /` — Local Interaction page with inline _HTML_PAGE (L981-982)
11. Existing page ownership: The `GET /` route sends `_HTML_PAGE` — a single ~1000-line inline HTML/CSS/JS string embedded directly in server.py (L1024+). This is the entire closed Local Interaction UX track.
12. Existing runtime evidence API contract: `runtime_evidence_serialization.py` provides `EVIDENCE_CONTRACT_VERSION = "1"`, `serialize_run_index()`, `serialize_run_evidence_detail()`, `serialize_run_evidence_summary()`. Both GET /runs and GET /runs/<run_id> use these serializers.
13. Existing tests:
    - `test_local_run_history_in_page.py`: Tests GET /, GET /runs, GET /runs/<run_id>. Uses `_request("GET", "/")` helper. 73+ tests. Assertions for `run-history-section`, `run-detail-panel`, `ev_contract_version == "1"`.
    - `test_runtime_evidence_serialization_contract.py`: 61 versioned contract tests.
    - `test_task_intake.py`: regression tests.
14. All 29 required files read successfully.

## CURRENT-SURFACE INVENTORY

### GET / — Local Interaction Page

| Property | Value |
|---|---|
| File owner | server.py (L981-1022 route handler + L1024+ _HTML_PAGE constant) |
| Route owner | ASGI `app` function in server.py |
| Current responsibility | Full local interaction UI: task submission form, runner selection, summary card, execution trace, structured view, raw JSON, feedback panel, confusion signals, session report, run report, run history list, run detail panel |
| Behavior unchanged | Must remain accessible at GET /. Must continue to serve the full _HTML_PAGE. No content removed or renamed. |
| Relationship to PR 0143 | Not modified. Not reused. The workspace shell is a separate surface. |

### GET /runs — Run Index

| Property | Value |
|---|---|
| File owner | server.py (L955-978 route handler) |
| Route owner | ASGI `app` function in server.py |
| Current responsibility | Returns versioned run index JSON via `serialize_run_index()` |
| Behavior unchanged | Must continue to return versioned JSON with ev_contract_version "1". No contract changes. |
| Relationship to PR 0143 | The workspace shell may consume this API for timeline population. Not modified. |

### GET /runs/<run_id> — Run Detail

| Property | Value |
|---|---|
| File owner | server.py (L920-953 route handler) |
| Route owner | ASGI `app` function in server.py |
| Current responsibility | Returns versioned run detail JSON via `serialize_run_evidence_detail()` |
| Behavior unchanged | Must continue to return versioned JSON with ev_contract_version "1". No contract changes. |
| Relationship to PR 0143 | The workspace shell may consume this API. Not modified. |

### runtime_evidence_serialization.py

| Property | Value |
|---|---|
| File owner | task_intake/src |
| Current responsibility | Pure serialization helpers for versioned evidence JSON |
| Behavior unchanged | Not modified. No serialization contract changes. |
| Relationship to PR 0143 | Referenced but not modified. |

### runtime_evidence.py (runner)

| Property | Value |
|---|---|
| File owner | runner |
| Current responsibility | Read model for run evidence |
| Behavior unchanged | Not modified. |
| Relationship to PR 0143 | Not modified. |

## ROADMAP ALIGNMENT

- roadmap track: Stream 2 — Artifact Workspace Shell
- expected PR slot: PR 0143
- why this PR is next: PR 0142 completed the Run Evidence Serialization Contract. PR 0142A completed the governance insertion without consuming a product slot. PR 0143 is the next product roadmap PR — the first Artifact Workspace Shell PR that establishes a separate four-zone workspace surface.
- batching policy check: PR 0143 is an architect-approved coherent multi-zone frontend shell PR, not an isolated UI control, button, toggle, copy change, or cosmetic edit. The batching exception from ADR 0011 (architect sign-off required for frontend-only PRs) is satisfied by the human architect's explicit instruction to proceed with the next roadmap step after PR 0142A.
- drift heuristic check: Not triggered. No consecutive single-file UI PRs exist in recent history. The Artifact Workspace Shell touches a new route and a new module, not exclusively server.py.
- architect sign-off required: yes
- architect sign-off reference if required: Human architect explicitly requested the next roadmap step after PR 0142A. This is the first product PR of Stream 2 (Artifact Workspace Shell, PR 0143).

### Roadmap State

1. Active stream: Stream 2 — Artifact Workspace Shell
2. Expected slot: PR 0143 (Artifact Workspace 4-Zone Shell Skeleton)
3. PR purpose: Establish a separately identifiable read-only Artifact Workspace surface with four semantic zones.
4. PR 0142A consumed no product slot — product PR 0143 is unchanged.
5. PR 0144 through PR 0147 remain separate product capabilities.
6. No frozen stream is opened.

## ROUTE DECISION

The Artifact Workspace Shell will use a **new dedicated GET-only route**: `GET /workspace`.

### Rationale

1. **Prevents destabilizing the closed Local Interaction track.** The existing `GET /` inline _HTML_PAGE (~1000 lines) is the entire closed track. Adding the workspace shell inline would couple two independent surfaces into one massive string and violate the closed-track boundary.

2. **Follows repository convention.** The repository already uses dedicated route paths for distinct surfaces (GET /runs, GET /runs/<run_id>, GET /product/iterations, GET /backlog). A `GET /workspace` route follows this existing pattern.

3. **Enables future evolution.** PR 0144, PR 0145, PR 0146, and PR 0147 can extend the workspace surface independently without touching the Local Interaction page.

4. **Preserves GET / behavior.** The Local Interaction page at `GET /` is completely untouched — no content removed, no IDs renamed, no HTML/CSS/JS modified.

5. **Allows an isolated renderer module.** The workspace shell HTML/CSS/JS can live in a dedicated `artifact_workspace.py` module, avoiding further bloat of server.py.

### Route Specification

| Property | Value |
|---|---|
| Exact workspace route | `GET /workspace` |
| Exact HTTP method | GET only |
| Exact content type | `text/html` (UTF-8) |
| Exact status behavior | 200 on success. Unsupported methods (POST, PUT, PATCH, DELETE) return 404 via catch-all. |
| Relationship to GET / | Independent. GET / remains the Local Interaction page. GET /workspace is the new Artifact Workspace shell. No cross-referencing between the two. |
| Relationship to GET /runs | GET /workspace may call GET /runs via client-side fetch to populate the timeline zone. GET /runs unchanged. |
| Relationship to GET /runs/<run_id> | GET /workspace may call GET /runs/<run_id> via client-side fetch to show selected run evidence. GET /runs/<run_id> unchanged. |
| Behavior for unsupported methods | Catch-all at the end of the ASGI `app` function returns 404. |

## FOUR-ZONE CONTRACT

### Stable semantic selectors

| Zone | ID | Heading / Label | Semantic Purpose |
|---|---|---|---|
| Workspace root | `artifact-workspace` | "Artifact Workspace" (h1) | Root container for the entire 4-zone shell |
| Left timeline | `zone-timeline` | "Timeline" (h2) | Run history navigation or timeline placeholder |
| Center artifact canvas | `zone-canvas` | "Artifact Canvas" (h2) | Selected artifact display or canvas placeholder |
| Right gates and proofs | `zone-gates-proofs` | "Gates & Proofs" (h2) | Visual gates and proof status placeholders |
| Bottom logs and captures | `zone-logs-captures` | "Logs & Captures" (h2) | Execution logs and diagnostic capture placeholders |

### Zone contracts

#### Left timeline zone (`#zone-timeline`)

| Property | Value |
|---|---|
| Semantic purpose | Run history navigation — the user selects a run to inspect |
| Heading / accessible label | h2 with text "Timeline" |
| Initial empty/placeholder state | "No runs available. Submit a task to see timeline entries." |
| Data source allowed in PR 0143 | Contract-faithful deterministic fixture (JSON matching GET /runs response shape with ev_contract_version "1"). Inline mock data array that matches the serialization contract shape. |
| Data explicitly deferred | Full live GET /runs fetch with loading/error states (PR 0144). |
| Controls allowed | A clickable list of mock run entries for demonstrating zone semantics |
| Controls prohibited | No mutation controls. No accept/reject/approve. No agent launch. No git/gh operations. |
| Expected responsive behavior | On narrow viewports (<768px), zones stack vertically: timeline at top, canvas below, gates/logs below. |
| Test assertions | Zone exists. Zone has h2 heading with "Timeline". Zone body is non-empty with placeholder text. No mutation buttons present. |

#### Center artifact canvas zone (`#zone-canvas`)

| Property | Value |
|---|---|
| Semantic purpose | Display of the selected artifact content |
| Heading / accessible label | h2 with text "Artifact Canvas" |
| Initial empty/placeholder state | "Select a run from the timeline to view artifacts. No artifact loaded." |
| Data source allowed in PR 0143 | None in PR 0143 — fully placeholder. |
| Data explicitly deferred | Full run detail evidence panel (PR 0145), run report viewer (PR 0146), proof and manifest viewer (PR 0147). |
| Controls allowed | None. |
| Controls prohibited | No artifact upload. No accept/reject. No edit. No mutation. |
| Expected responsive behavior | On narrow viewports, appears second in vertical stack. |
| Test assertions | Zone exists. Zone has h2 heading with "Artifact Canvas". Zone body shows placeholder text that does not fabricate evidence. |

#### Right gates and proofs zone (`#zone-gates-proofs`)

| Property | Value |
|---|---|
| Semantic purpose | Gate status indicators and proof acceptance state |
| Heading / accessible label | h2 with text "Gates & Proofs" |
| Initial empty/placeholder state | "No gate checks available. Gates and proofs will appear after Visual Gate implementation." |
| Data source allowed in PR 0143 | None in PR 0143 — fully placeholder. |
| Data explicitly deferred | Visual Gate readiness and approval UI (PR 0148-0152). |
| Controls allowed | None. |
| Controls prohibited | No gate mutation. No accept/reject. No proof submission. |
| Expected responsive behavior | On narrow viewports, appears third in vertical stack (below canvas). |
| Test assertions | Zone exists. Zone has h2 heading with "Gates & Proofs". Placeholder text does not claim evidence is present. |

#### Bottom logs and captures zone (`#zone-logs-captures`)

| Property | Value |
|---|---|
| Semantic purpose | Execution logs, diagnostic captures, and command outputs |
| Heading / accessible label | h2 with text "Logs & Captures" |
| Initial empty/placeholder state | "No logs available. Captured execution output will appear here after a run is selected." |
| Data source allowed in PR 0143 | None in PR 0143 — fully placeholder. |
| Data explicitly deferred | Execution log viewer, capture display (future PRs). |
| Controls allowed | None. |
| Controls prohibited | No arbitrary file path input. No file upload. No log submission. |
| Expected responsive behavior | On narrow viewports, appears at bottom of vertical stack. |
| Test assertions | Zone exists. Zone has h2 heading with "Logs & Captures". Placeholder text does not claim evidence is present. |

### Fabrication prohibition

No zone may claim runtime evidence that is unavailable. Placeholder text must be explicit about the absence of data. No zone may include mock status indicators that appear to be real gate results, proof acceptance, or run evidence unless they are clearly labeled as mock/placeholder data.

## DATA CONNECTION CONTRACT

### Decision: Contract-faithful deterministic fixture

PR 0143 uses an **inline deterministic fixture** (a Python list of dicts matching the GET /runs response envelope shape with ev_contract_version "1") for the timeline zone. The center, gates, and logs zones are fully placeholder.

**Rationale**: The full GET /runs fetch with loading states, error handling, and empty-root detection is the scope of PR 0144 (Local Run List Page). PR 0143 establishes the shell structure only. Using a deterministic fixture avoids duplicating PR 0144 scope while still demonstrating a connected-looking timeline zone.

| Property | Value |
|---|---|
| Trigger for loading | On page load — the fixture data is rendered immediately without fetch. |
| Loading state | Not applicable (inline fixture has no loading delay). |
| Empty state | "No runs available. Submit a task to see timeline entries." (same as full placeholder). |
| Error state | Not applicable (fixture data always succeeds). |
| Version check | The fixture data includes `ev_contract_version: "1"` to confirm contract awareness. |
| Safe rendering method | DOM textContent via escHtml (same pattern as existing fetchRunsDetail in server.js). |
| No-fabrication rule | Fixture data is explicitly mock data. Placeholder zones do not claim evidence. |
| No-mutation rule | No POST, PUT, PATCH, DELETE controls. |
| Fields allowed in skeleton | `run_id`, `status`, `created_at` — sufficient to populate timeline entries. |
| Fields deferred to PR 0144-0147 | Full run list pagination, evidence indicators, PR URLs, missing/malformed notices, detail panel, report viewer, proof/manifest viewer. |

## IMPLEMENTATION FILE SCOPE

### Approved files

#### 1. services/task_intake/src/task_intake/artifact_workspace.py (NEW)

**Action**: New file.
**Exact responsibility**: Pure HTML/CSS/JS string constant and a single render function that returns the workspace shell HTML page. This module isolates the entire Artifact Workspace shell from the rest of server.py.
**Exact expected additions**: A single function `render_artifact_workspace() -> str` that returns the complete HTML page for the 4-zone shell, including:
- Inline CSS for layout (flexbox/grid 4-zone layout, responsive fallback)
- Inline JavaScript for timeline fixture data (matching GET /runs response shape)
- All four zone containers with stable IDs
- Accessible headings for each zone
- Placeholder text for empty zones
- escHtml safe-rendering function for any fixture data text
- No external dependencies, no framework, no CDN references
**Existing behavior unchanged**: None — this is a new file.
**Content prohibited**: No mutation controls. No agent launch. No git/gh references. No accept/reject/approve buttons. No arbitrary file path handling. No POST/PUT/PATCH/DELETE behavior. No external scripts, stylesheets, fonts, images, or CDNs. No localStorage or sessionStorage. No subprocess/os.system/Docker/git/gh calls. No runtime evidence model imports. No filesystem access.
**Tests proving boundary**: New test file tests that the workspace page renders all four zones with correct headings. Tests confirm no mutation controls exist.

#### 2. services/task_intake/src/task_intake/server.py (EDIT)

**Action**: Narrow edit.
**Exact responsibility**: Add one new route handler for `GET /workspace` that calls `render_artifact_workspace()` from the new module.
**Exact expected additions**: 
- One import: `from .artifact_workspace import render_artifact_workspace`
- One route block (before the GET / catch-all, after the GET / page route):
  ```
  if method == "GET" and path == "/workspace":
      html = render_artifact_workspace().encode("utf-8")
      return 200, [(b"content-type", b"text/html; charset=utf-8")], html
  ```
**Existing behavior unchanged**: GET /, GET /runs, GET /runs/<run_id>, and all other existing routes remain untouched. No content from the Local Interaction _HTML_PAGE is modified, moved, or removed. No route ordering is changed except the addition.
**Content prohibited**: No modification to the _HTML_PAGE string. No removal or renaming of existing div IDs or CSS classes. No change to existing route handlers. No addition of inline HTML outside the workspace route.
**Tests proving boundary**: New test file verifies GET /workspace returns 200 with text/html. Existing test_local_run_history_in_page.py tests for GET / continue to pass. Existing GET /runs and GET /runs/<run_id> tests continue to pass.

#### 3. services/task_intake/tests/test_artifact_workspace_shell.py (NEW)

**Action**: New file.
**Exact responsibility**: Executable behavioral tests for the Artifact Workspace shell.
**Exact expected additions**: Tests verifying:
- GET /workspace returns 200 status
- GET /workspace returns text/html content type
- Response contains `#artifact-workspace` root element
- Response contains `#zone-timeline` with h2 heading "Timeline"
- Response contains `#zone-canvas` with h2 heading "Artifact Canvas"
- Response contains `#zone-gates-proofs` with h2 heading "Gates & Proofs"
- Response contains `#zone-logs-captures` with h2 heading "Logs & Captures"
- Timeline zone has non-empty content (fixture data or placeholder)
- Center zone shows placeholder text without fabricated evidence
- Gates zone shows placeholder text without fabricated evidence
- Logs zone shows placeholder text without fabricated evidence
- No POST/PUT/PATCH/DELETE workspace route exists (404 for unsupported methods on /workspace)
- No accept, reject, approve, retry, rerun, commit, push, merge, or PR controls present in HTML
- No external asset URLs (http://, https://, //) in the page
- ev_contract_version is "1" in fixture data (if fixture approach used)
- GET / still returns successfully (existing page preserved)
- Existing page identifiers (run-history-section, run-detail-panel) remain present in GET /
- GET /runs still returns versioned JSON
- GET /runs/<run_id> still returns versioned JSON
- Tests use `_request()` helper from the existing test infrastructure
- Tests use isolated temporary directories where filesystem interaction is needed
- No real git, gh, Docker, subprocess, or network calls in tests
**Existing behavior unchanged**: None — this is a new file.
**Content prohibited**: Tests must not modify server.py, runtime_evidence.py, or runtime_evidence_serialization.py. Tests must not write to .ariadne. Tests must not launch agents or Docker.

#### 4. .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md (NEW)

Written by coder. All 11 required sections per the IMPLEMENTATION_REPORT_TEMPLATE.md.

#### 5. .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/reviews/precommit-review.yml (NEW)

Written by precommit-review. Follows review-artifact.schema.yml.

### Rejected candidate: test_local_run_history_in_page.py edit

**Decision**: No edit needed.
**Rationale**: GET /, GET /runs, and GET /runs/<run_id> behavior is completely unchanged by this PR. The new workspace route is independent. Existing tests will continue to pass without modification. The new test file covers the workspace surface.

### Not modified

- services/runner/src/runner/runtime_evidence.py
- services/runner/tests/test_runtime_evidence.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- ROADMAP.md
- .project-memory/ORCHESTRATOR_STANDARD.txt
- .project-memory/workflow/**
- .project-memory/templates/**
- .project-memory/roadmaps/**
- agents/**
- schemas/**
- docs/**
- pyproject.toml, poetry.lock, requirements*.txt, package.json
- All previous PR artifacts

## UI AND ACCESSIBILITY CONTRACT

| Property | Required |
|---|---|
| Document title | "Ariadne — Artifact Workspace" |
| Page heading | h1 with text "Artifact Workspace" |
| Workspace root landmark | `<main id="artifact-workspace" role="main">` or `<div id="artifact-workspace" role="region" aria-label="Artifact Workspace">` |
| Zone landmarks | Each zone div has `role="region"` and `aria-labelledby` referencing its heading |
| Heading hierarchy | h1 (page title), h2 (zone headings), consistent across all zones |
| Keyboard navigation | Zones are focusable via tab through rendered links/buttons in timeline. No keyboard trap. |
| Focus behavior | Timeline entries are clickable elements (buttons or links). Tab through to access. |
| Text contrast | Default browser colors with light background for content areas. Standard contrast (no requiring screenshot approval). |
| Responsive fallback | CSS media query: below 768px zones stack vertically in order (timeline, canvas, gates/proofs, logs/captures). Above 768px: two-row grid (top row: timeline | canvas | gates, bottom row: logs spanning full width). |
| Explicit empty states | Each zone shows distinct placeholder text describing what will appear there. No zone is zero-height. |
| Loading/error states | Not applicable in PR 0143 — inline fixture renders synchronously without fetch. |
| No color-only status | Placeholder text uses text content, not color alone, to communicate absence of data. |
| No external assets | No external scripts, stylesheets, fonts, images, icons, or CDNs. All CSS and JS inline. |
| Safe rendering | All fixture data rendered through `escHtml()` using DOM textContent assignment (same pattern as server.js `escHtml`). |

## TEST PLAN

### 1. Workspace Route Tests (new file)

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q
```

Expected: all workspace shell tests pass.
If not met: block.

### 2. Existing GET / Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all existing page tests pass (73+ tests).
If not met: block.

### 3. Existing GET /runs and GET /runs/<run_id> Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```

Expected: all route and contract tests pass.
If not met: block.

### 4. task_intake Full Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_task_intake.py -q
```

Expected: all task intake tests pass.
If not met: block.

### 5. Python Compile

```bash
python -m compileall -f services/task_intake/src/services/runner/src
```

Expected: all files compile.
If not met: block.

### 6. Four-Zone Selector Grep

```bash
grep -n -E "artifact-workspace|zone-timeline|zone-canvas|zone-gates-proofs|zone-logs-captures" services/task_intake/src/task_intake/artifact_workspace.py services/task_intake/tests/test_artifact_workspace_shell.py
```

Expected: all five stable selectors present in both renderer and tests.
If not met: block.

### 7. Mutation-Control Prohibition Grep

```bash
grep -n -i -E "accept|reject|approve|retry|rerun|commit|push|merge|pr create|gh pr|git add|agent.*launch" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no mutation control references except in placeholder text describing what will appear later.
If not met: block.

### 8. External-Asset Prohibition Grep

```bash
grep -n -i -E "https?://|//[a-z]+\." services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no match (exit code 1) — no external URL references.
If not met: block.

### 9. Prohibited Execution Import Grep

```bash
grep -n -E "subprocess|os\.system|docker|git|Popen|shell=True" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no match (exit code 1).
If not met: block.

### 10. Existing API Route Preservation Grep

```bash
grep -n "_HTML_PAGE|run-history-section|run-detail-panel" services/task_intake/src/task_intake/server.py | head -10
```

Expected: existing page identifiers remain present.
If not met: block.

### 11. Forbidden-Path Diff

```bash
git diff --name-only -- services/runner/ docs/ agents/ schemas/ pyproject.toml poetry.lock .gitignore ROADMAP.md .project-memory/workflow/ .project-memory/templates/ .project-memory/roadmaps/ .project-memory/pr/0131* .project-memory/pr/0132* .project-memory/pr/0133* .project-memory/pr/0134* .project-memory/pr/0135* .project-memory/pr/0136* .project-memory/pr/0137* .project-memory/pr/0138* .project-memory/pr/0139* .project-memory/pr/0140* .project-memory/pr/0141* .project-memory/pr/0142* .project-memory/pr/0142a*
```

Expected: empty.
If not met: block.

### 12. Planning-Lock Diff

```bash
git diff -- .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/PLAN.md .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/reviews/plan-review.yml
```

Expected: no differences (planning artifacts remain locked).
If not met: block.

### 13. Whitespace Check

```bash
git diff --check
```

Expected: no whitespace errors.
If not met: block.

### 14. Dirty-Tree Inspection

```bash
git status --short
```

Expected: only approved implementation files (artifact_workspace.py, server.py, test_artifact_workspace_shell.py, PR artifacts).
If unknown untracked files exist: block.

### 15. Cached-Diff Inspection

```bash
git diff --cached --name-only
```

Expected: empty.
If not met: block.

### 16. IMPLEMENTATION_REPORT.md Existence

```bash
test -f .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md
```

Expected: file exists.
If not met: block.

### 17. IMPLEMENTATION_REPORT.md Physical Readback

```bash
sed -n '1,30p' .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md
```

Expected: readable, first lines include proof boundary disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write:

`.project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md`

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

This PR starts from a clean main branch with no pre-existing implementation. The coder creates all new files and edits server.py.

### Authorized continuation handling

If continuation is authorized, the coder must:
- Re-read this PLAN.md.
- Verify locked planning artifacts are unchanged.
- Read all existing diffs from the current implementation state.
- Distinguish pre-existing correct work from new changes.
- Preserve correct PLAN-approved work.
- Destructive reset, restore, or clean commands are forbidden unless the human explicitly authorizes them.

### Authorized rerun handling

If a rerun is authorized, the coder must re-read PLAN.md, verify locked planning artifacts are unchanged, and rewrite IMPLEMENTATION_REPORT.md. Existing correct work may be preserved at the coder's discretion.

### Unexplained pre-existing report handling

No pre-existing implementation report is expected. If one exists, the reviewer must verify it matches PLAN.md and flag its provenance. If it does not match PLAN.md, block.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside the approved scope changes.
2. PLAN.md or plan-review.yml changes.
3. Existing GET / behavior breaks (page fails to render, IDs renamed, content removed).
4. Existing GET /runs contract changes (response shape, field names, ev_contract_version).
5. Existing GET /runs/<run_id> contract changes.
6. ev_contract_version changes from "1".
7. Runtime evidence model (runtime_evidence.py) changes.
8. All four zones are not present in the workspace shell.
9. Any zone lacks a stable semantic selector (ID).
10. Any zone fabricates unavailable evidence (false status, fake proof, fake gate results).
11. A mutation control is added (accept, reject, approve, retry, rerun).
12. An agent-launch control is added.
13. A git, gh, commit, push, merge, or PR control is added.
14. Arbitrary filesystem access (file path input, directory traversal) is added.
15. POST, PUT, PATCH, or DELETE workspace behavior is added.
16. External scripts, styles, fonts, images, or CDNs are present.
17. Dependencies or a frontend build system are added.
18. PR 0144, PR 0145, PR 0146, or PR 0147 scope is absorbed (full run list, detail panel, report viewer, proof/manifest viewer).
19. The closed Local Interaction page (_HTML_PAGE) is broadly rewritten or its content is modified.
20. Tests are missing or weak (no zone selector tests, no placeholder tests, no mutation prohibition tests).
21. Required validation is absent or failing.
22. IMPLEMENTATION_REPORT.md is absent or incomplete.
23. Unknown untracked files exist.
24. Generated residue enters the commit payload.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0143-artifact-workspace-4-zone-shell-skeleton`.
2. Only approved files changed: artifact_workspace.py (new), server.py (narrow edit), test_artifact_workspace_shell.py (new), IMPLEMENTATION_REPORT.md (new), precommit-review.yml (new).
3. Planning artifacts (PLAN.md, plan-review.yml) remain locked — no modifications by coder or precommit-review.
4. PR 0143 roadmap scope is preserved (Artifact Workspace 4-Zone Shell Skeleton — not the full workspace).
5. Product PR 0144 through PR 0147 remain separate (run list, detail panel, report viewer, proof/manifest viewer are all deferred).
6. Workspace route is exact (`GET /workspace`) and read-only (GET only, no POST/PUT/PATCH/DELETE).
7. Workspace root element exists with ID `artifact-workspace`.
8. Left timeline zone exists with ID `zone-timeline`.
9. Center artifact canvas zone exists with ID `zone-canvas`.
10. Right gates and proofs zone exists with ID `zone-gates-proofs`.
11. Bottom logs and captures zone exists with ID `zone-logs-captures`.
12. Every zone is semantically labelled (h2 heading).
13. Placeholder states do not fabricate unavailable evidence.
14. Existing GET / behavior is preserved.
15. Existing GET /runs behavior is preserved.
16. Existing GET /runs/<run_id> behavior is preserved.
17. ev_contract_version remains "1".
18. Runtime evidence model (runtime_evidence.py) is unchanged.
19. No mutation or execution authority exists in the workspace shell.
20. No arbitrary filesystem access exists.
21. No external assets or dependencies exist.
22. Required tests pass (new workspace tests + existing regressions).
23. IMPLEMENTATION_REPORT.md exists and was read back.
24. PLAN DRIFT GATE passed.
25. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. A separately identifiable read-only shell cannot be introduced without modifying the closed Local Interaction _HTML_PAGE.
2. Exact route ownership for `GET /workspace` cannot be established in server.py without breaking existing routes.
3. Exact four-zone semantics cannot be established with stable IDs.
4. The shell requires changing the runtime evidence contract (runtime_evidence.py, runtime_evidence_serialization.py).
5. The shell requires a new mutation endpoint.
6. The shell requires arbitrary filesystem reads.
7. The shell requires a frontend framework, build system, or external dependency.
8. An unapproved file must be changed.
9. A later roadmap capability (PR 0144-0147 scope) must be implemented.
10. Required validation fails.

## NON-GOALS

1. Implementing the shell (this is a planning task only).
2. Editing server.py beyond the narrow route integration.
3. Creating artifact_workspace.py beyond the narrow shell contract.
4. Writing test_artifact_workspace_shell.py during planning.
5. Writing plan-review.yml during planning.
6. Writing IMPLEMENTATION_REPORT.md during planning.
7. Writing precommit-review.yml during planning.
8. Modifying GET /, GET /runs, or GET /runs/<run_id> behavior.
9. Modifying runtime_evidence.py.
10. Modifying runtime_evidence_serialization.py.
11. Implementing the full run list (PR 0144).
12. Implementing the full run detail evidence panel (PR 0145).
13. Implementing the run report viewer (PR 0146).
14. Implementing the proof and manifest viewer (PR 0147).
15. Adding mutation controls (accept, reject, approve, retry, rerun).
16. Adding agent launch.
17. Adding git or PR actions.
18. Adding arbitrary file access.
19. Adding external assets (CDN, fonts, images, frameworks).
20. Adding dependencies (Python, JS, or CSS packages).
21. Adding a frontend build system.
22. Opening later roadmap streams (Visual Gate, Context Core, etc.).
23. Committing, pushing, or creating a pull request during planning.
