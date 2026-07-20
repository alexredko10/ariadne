# PR 0150 — Requirement / State / Sequence Diagram Viewers Plan

## EVIDENCE SNAPSHOT

1. HEAD: 45e4a9ef06a5cfa660f1ad2304701ddbcf226a85
2. Branch: 0150-requirement-state-sequence-diagram-viewers
3. Dirty tree: clean
4. Cached diff: empty
5. origin/main: 45e4a9ef06a5cfa660f1ad2304701ddbcf226a85
6. Merge base: 45e4a9ef06a5cfa660f1ad2304701ddbcf226a85
7. PR 0149 merged at 45e4a9e ("PR 0149 — Visual Gate Runtime Object (#179)")
8. PR 0149 merge evidence: present — HEAD at origin/main, PR 0149 at top of git log
9. Existing Mermaid artifacts (PR 0148): kind="mermaid", media_type="text/vnd.mermaid", bounded .mmd reads, hash verification, inert source text via renderMermaidArtifact()
10. Existing VisualGateResult (PR 0149): visual-gate-result.json sidecar, required_diagrams refs via profile_descriptor_key:
11. Existing test gap (PR 0148 precommit warning): test_artifact_workspace_shell.py has no Mermaid/Diagram viewer tests
12. No diagram rendering exists: no mermaid import, no SVG generation, no canvas rendering, no rendering dependency in pyproject.toml
13. ev_contract_version "1" confirmed in server.py and serialization

## ROADMAP ALIGNMENT

- roadmap track: Visual Gate / Mermaid (Stream 3, PR 0150)
- expected PR slot: PR 0150 (Requirement / State / Sequence Diagram Viewers)
- why this PR is next: PR 0149 is merged. ROADMAP.md and ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md identify PR 0150 as the next product PR after PR 0149.
- batching policy check: Pass — PR 0150 is a coherent multi-step capability (server-side SVG rendering, whitelist sanitization, safe DOM insertion, three diagram types, security hardening). Not an isolated UI PR.
- drift heuristic check: Not triggered — no consecutive UI-only PRs exist. PR 0149 was backend-only, PR 0150 adds backend + frontend capability.
- architect sign-off required: no — expected normal roadmap slot.
- architect sign-off reference: N/A

PR 0151 remains next (Visual Gate Readiness Check).

## CURRENT STATE INVENTORY

### Mermaid artifacts (PR 0148)

Profile descriptors with kind="mermaid", media_type="text/vnd.mermaid". Controlled .mmd reads via run-relative: / sha256: references with containment check. 100 KB max. UTF-8 encoding with BOM stripping. SHA-256 hash verification (match/mismatch/undeclared). renderMermaidArtifact() displays descriptor metadata and inert source text via textContent in the Profile/Canvas section.

### VisualGateResult (PR 0149)

Schema version "1" at visual-gate-result.json. required_diagrams entries with diagram_id, diagram_type (requirement|state|sequence), descriptor_ref (profile_descriptor_key:<key>), required (bool). Statuses: pending, ready_needs_review, passed, failed. No diagram rendering, no UI changes.

### Artifact Workspace Canvas rendering

renderProfile() renders profile section. renderMermaidArtifact() renders inert source text. renderDetail() and renderReport() render other Canvas sections. All use textContent/safeText. No SVG or canvas rendering.

### Current dependency model

pyproject.toml has empty dependencies. No rendering libraries.

### Existing zone separation

Mermaid content in Profile/Canvas. Gates & Proofs renders manifest/evidence. Logs & Captures renders execution results. No cross-zone contamination.

## SELECTED ARCHITECTURE: OPTION A — SERVER-SIDE MERMAID SVG GENERATION

**Why OPTION A:**

Mermaid diagram rendering is server-side in Ariadne's architecture. The server owns the artifact store, run directory, profile descriptors, and controlled reference resolution. Client-side rendering via CDN-loaded mermaid.js would violate the offline/local-only requirement. A bundled JS approach would require npm/webpack infrastructure that does not exist.

OPTION A adds mermaid-diagram as a Python dependency, generates SVGs server-side, sanitizes them through a whitelist-based SVG sanitizer, and serves them through a new GET-only API route. The workspace inserts the pre-sanitized SVG into a DOM container.

**Why not client-side rendering:** No CDN, no npm/webpack, no JS bundling infrastructure, offline-first requirement.

**Component layers:**
1. **mermaid_renderer.py** — pure function render_mermaid_to_svg() in the runner module.
2. **svg_sanitizer.py** — pure whitelist-based SVG sanitizer in task_intake module.
3. **GET /runs/<run_id>/visual-gate-result/<diagram_id>/diagram** — new read-only API route.
4. **renderDiagramViewer()** — new workspace function fetching and inserting sanitized SVG.

### Architecture decisions

1. **Renderer module**: services/runner/src/runner/mermaid_renderer.py. Imports MermaidDiagram from mermaid-diagram package.
2. **API route**: GET /runs/<run_id>/visual-gate-result/<diagram_id>/diagram. Response: {ev_contract_version, ok, error, svg, diagram_id, diagram_type, mermaid_sha256, byte_count}.
3. **SVG container**: New section in Canvas zone. Container id: diagram-viewer-<diagram_id>.
4. **Stale protection**: Same detailRequestCounter pattern. fetchDiagramData(runId, diagramId) captures requestId and discards stale responses.
5. **Dependency**: Add mermaid-diagram>=1.0.0,<2.0.0 to pyproject.toml [project.dependencies].
6. **Diagram source**: Resolved through: VisualGateResult -> profile_descriptor_key -> profile artifact descriptor -> controlled ref -> .mmd bytes.

## DEPENDENCY STRATEGY

### Selected dependency

Package: mermaid-diagram
Version: >=1.0.0,<2.0.0
Environment: Production (not dev-only — install via make install-dev or pip install -e ".")
Source: PyPI
Requirement: No network at render time. Installed via pip offline.

### Packaging file changes

pyproject.toml: Add "mermaid-diagram>=1.0.0,<2.0.0" to [project] dependencies list.
Prohibited: No removal of existing dependencies. No Python version change.

### Fallback behavior

If mermaid-diagram is not installed, renderer returns ok=False with error "mermaid_renderer_not_available". Workspace displays: "Mermaid renderer not available. Install with: pip install mermaid-diagram". Visible error — not silent fallback.

### Security configuration

Every render call uses:
- disable_click_handlers=True
- disable_links=True
- disable_forms=True
- max_text_length=100000
- sanitize_svg=True

No token, API key, or network access.

## SUPPORTED DIAGRAM TYPES

### Type identifiers from VisualGateResult

| Type identifier | Display label | Accessibility |
|---|---|---|
| requirement | "Requirement Diagram" | alt: "Requirement diagram: <diagram_id>" |
| state | "State Diagram" | alt: "State diagram: <diagram_id>" |
| sequence | "Sequence Diagram" | alt: "Sequence diagram: <diagram_id>" |

### Type semantics

The diagram_type is a label for the viewer. The actual Mermaid syntax is determined by the .mmd file content, not by diagram_type. A requirement diagram_type with state syntax in the .mmd renders as whatever the .mmd contains. Type validation is deferred to PR 0151.

### Unsupported type behavior

If diagram_type is not one of the three supported values, the diagram is still rendered (the renderer works on any Mermaid syntax) but a warning is displayed: "Unknown diagram type: <type>."

## ARTIFACT SELECTION AND ORDERING

### Resolution chain per diagram

1. GET /runs/<run_id>/visual-gate-result — load VisualGateResult for the run.
2. For each entry in visual_gate_result.required_diagrams:
   a. Extract descriptor_ref (profile_descriptor_key:<key>).
   b. Load run-profile.json for the run.
   c. Find artifact descriptor with matching key and kind="mermaid".
   d. Extract the ref field (run-relative: or sha256:).
   e. Read .mmd bytes through existing controlled reference resolution.
   f. Verify SHA-256 hash against descriptor sha256 (if present).
   g. Call render_mermaid_to_svg() with Mermaid source.
   h. Call sanitize_svg() on the SVG output.
   i. Return pre-sanitized SVG in the JSON response.

All resolution, validation, and sanitization happens server-side per request.

### Ordering

Diagrams in the workspace are ordered by diagram_id (alphabetical).

### Diagram source state table

| State | Condition | Workspace display |
|---|---|---|
| Rendered successfully | Source valid, renderer available, hash match (if declared) | SVG in controlled container |
| Renderer not available | mermaid-diagram not installed | "Mermaid renderer not available. Install with: pip install mermaid-diagram" |
| Source file missing | Controlled ref does not resolve | "Diagram not found — Mermaid artifact file is missing" |
| Source oversized | .mmd > 100 KB | "Diagram too large (max 100 KB)" |
| Encoding error | Non-UTF-8 bytes | "Unable to read diagram — unsupported encoding" |
| Render error | Mermaid syntax invalid | "Failed to render diagram." with renderer error message |
| Hash mismatch | Content sha256 != descriptor sha256 | Warning displayed above diagram (diagram still rendered) |
| Hash not declared | No sha256 in descriptor | "SHA-256 not declared" (diagram still rendered) |
| Profile not found | No run-profile.json | "Profile not found — cannot resolve Mermaid artifact descriptor" |
| Descriptor key not found | profile_descriptor_key no match | "Diagram reference not found: <key>" |
| Descriptor kind mismatch | descriptor exists but kind != "mermaid" | "Expected Mermaid artifact but found kind=<actual>" |
| VisualGateResult not found | No visual-gate-result.json | "No visual gate result for this run" |
| Stale response | Selected run changed during fetch | Discarded via detailRequestCounter |

## SAFE SVG INSERTION BOUNDARY

### SVG sanitizer

New file: services/task_intake/src/task_intake/svg_sanitizer.py
Function: sanitize_svg(svg_string: str) -> dict returning {ok, sanitized_svg, error}

Allowed elements: svg, g, path, rect, circle, ellipse, line, polyline, polygon, text, tspan, defs, linearGradient, radialGradient, stop, marker, clipPath, mask, pattern, title, desc.

Allowed attributes per element: Only standard SVG presentation attributes (fill, stroke, stroke-width, opacity, d, x, y, width, height, rx, ry, cx, cy, r, x1, y1, x2, y2, points, transform, viewBox, font-family, font-size, text-anchor, dominant-baseline, stop-color, stop-offset, id, class).

Removed unconditionally: onclick, onmouseover, onload, onerror, on* event handlers, href, xlink:href, target, style, a (anchor), script, foreignObject, use, iframe, embed, object, img, image, feImage, animate, animateTransform, set, discard.

Implementation: Uses xml.etree.ElementTree to parse, whitelist-traverse, serialize back to string. If parsing fails, returns ok=False with "svg_parse_error".

### DOM insertion

The sanitized SVG string is inserted via:
container.innerHTML = sanitized_svg;

This is the INTENTIONAL use of innerHTML for SVG. SVG elements must be parsed as XML to render correctly. The SVG is server-side sanitized before API response. The sanitized_svg is a complete static SVG document with no runtime interpolation.

### Security doctrine

1. Every SVG is sanitized by svg_sanitizer.py on the server before being returned.
2. No JavaScript survives — all event handlers, script elements, inline scripts removed.
3. No external resources survive — href, xlink:href, img src, feImage refs removed.
4. No foreign objects survive — foreignObject, iframe, embed, object removed.
5. Sanitizer failure returns ok=False — no unsanitized SVG is ever returned.
6. Stale-response protection prevents SVG from previous selection.
7. No innerHTML with unsanitized runtime values — only pre-sanitized SVG from API response.

## STALE SELECTED-RUN PROTECTION

fetchDiagramData(runId, diagramId) follows the same pattern:
1. Capture requestId = ++detailRequestCounter before fetch.
2. On response: if (requestId !== detailRequestCounter) return;
3. On catch: if (requestId !== detailRequestCounter) return;
4. selectRun() clears all diagram viewers before fetching new data.

## ZONE SEPARATION PRESERVATION

| Zone | Affected by PR 0150 | Rationale |
|---|---|---|
| Timeline | Unchanged | No diagram data in run index. |
| Canvas (detail) | Unchanged | Detail/report content unchanged. |
| Canvas (profile) | Unchanged | Inert Mermaid source text remains. |
| Canvas (diagram viewers) | New section below profile | Rendered diagrams below existing profile section. |
| Gates & Proofs | Unchanged | No diagram data. Manifest truth unchanged. |
| Logs & Captures | Unchanged | No diagram data. |

### Separation rules

1. renderGatesProofs() unchanged — no diagram data flows into Gates & Proofs.
2. renderMermaidArtifact() unchanged — inert source text remains alongside rendered diagram.
3. Rendered SVG labelled: "Rendered diagram — visual representation of Mermaid source. Not independently verified proof or approval."
4. No manifest impact — rendered diagrams do not create manifest entries.
5. No profile impact — rendered diagrams do not modify profile descriptors.

## IMPLEMENTATION ALLOWLIST

### pyproject.toml (EDIT)
Add mermaid-diagram>=1.0.0,<2.0.0 to [project] dependencies.
Permitted: One line addition. Prohibited: No other changes.

### services/runner/src/runner/mermaid_renderer.py (NEW)
render_mermaid_to_svg(mermaid_source: str, diagram_type: str) -> dict with keys {ok, svg, error, diagram_type, byte_count}.
Permitted: Pure function. Imports MermaidDiagram. Calls with security config.
Prohibited: No filesystem access, no HTTP, no subprocess, no eval, no mutation.

### services/task_intake/src/task_intake/svg_sanitizer.py (NEW)
sanitize_svg(svg_string: str) -> dict with keys {ok, sanitized_svg, error}. Whitelist-based using xml.etree.ElementTree.
Permitted: XML parsing, whitelist traversal, string serialization.
Prohibited: No HTML parsing, no regex-only sanitization, no network, no mutation, no script execution.

### services/task_intake/src/task_intake/server.py (EDIT)
Add GET /runs/<run_id>/visual-gate-result/<diagram_id>/diagram route. Handler: load VisualGateResult, resolve profile descriptor, read .mmd bytes, call render_mermaid_to_svg(), call sanitize_svg(), return JSON.
Permitted: One new GET route handler. Import statements for new modules.
Prohibited: No POST/PUT/PATCH/DELETE. No changes to existing routes.

### services/task_intake/src/task_intake/artifact_workspace.py (EDIT)
Add renderDiagramViewer(visualGateResultData) and fetchDiagramData(runId, diagramId). Insert sanitized SVG via innerHTML. Show loading, error, stale states. Accessible labels.
Permitted: SVG container creation. Stale-response protection. Accessibility attributes.
Prohibited: No unsanitized innerHTML. No eval. No document.write. No approve/reject controls.

### services/runner/tests/test_mermaid_renderer.py (NEW)
Tests:
- Valid requirement diagram produces SVG.
- Valid state diagram produces SVG.
- Valid sequence diagram produces SVG.
- Invalid Mermaid syntax returns ok=False.
- Empty source returns ok=False.
- Security config: no onclick/href in output.
- Deterministic output for same input.
- Different input produces different output.

### services/task_intake/tests/test_svg_sanitizer.py (NEW)
Tests:
- Clean SVG passes through.
- Script elements removed.
- onclick/onerror/on* handlers removed.
- href and xlink:href removed.
- foreignObject removed.
- iframe/embed/object removed.
- External img src removed.
- Disallowed elements removed.
- Unknown attributes removed.
- Malformed XML returns ok=False.
- Empty string returns ok=False.
- CDATA sections and entity expansion attempts handled.

### services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)
New test class TestMermaidDiagramViewer with:
- renderDiagramViewer function exists.
- fetchDiagramData function exists.
- Loading state text ("Loading diagram...").
- Error state texts ("Failed to render diagram", "Renderer not available").
- Stale-response protection (detailRequestCounter check).
- No approve/reject controls in diagram viewer.
- Inert proof disclaimer present.
- SVG inserted via innerHTML (single controlled assertion — necessary for SVG).
- No innerHTML with unsanitized values.
- Existing workspace structure unchanged (zones, headings, detail, report, profile).
- Existing Mermaid inert text display unchanged.

### tests/fixtures/requirement-diagram.mmd (NEW)
Synthetic requirement diagram fixture.

### tests/fixtures/state-diagram.mmd (NEW)
Synthetic state diagram fixture.

### tests/fixtures/sequence-diagram.mmd (NEW)
Synthetic sequence diagram fixture.

### tests/fixtures/hostile-mermaid.mmd (NEW)
Hostile content with script injection attempts.

### scripts/smoke-mermaid-diagram-viewer.py (NEW)
Deterministic offline smoke test.

### .project-memory/pr/0150-requirement-state-sequence-diagram-viewers/IMPLEMENTATION_REPORT.md (NEW)

### .project-memory/pr/0150-requirement-state-sequence-diagram-viewers/reviews/precommit-review.yml (PREEXISTING)
Written only by precommit-review. Not coder-writable.

### Forbidden files — not modified
- ROADMAP.md, .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
- All PR 0147A-0149 source, tests, and documentation
- services/runner/src/runner/run_profile.py, visual_gate_result.py, artifacts.py, runtime_evidence.py, run_persistence.py, review_boundary.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py, manual_orchestration.py, local_operator.py
- All agents/*.yml, schemas/*.yml, docs
- Construction-estimate files and fixtures
- Existing mermaid fixtures (PR 0148) and smoke scripts (PR 0148, PR 0149)

## TEST PLAN

### 1. Mermaid renderer unit tests
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_mermaid_renderer.py -q
Expected: All 8 renderer tests pass. If not met: block.

### 2. SVG sanitizer unit tests
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_svg_sanitizer.py -q
Expected: All 12 sanitizer tests pass. If not met: block.

### 3. Mermaid/Diagram workspace display tests
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Mermaid or Diagram" -q
Expected: All 15+ workspace tests pass (closing PR 0148 coverage gap). If not met: block.

### 4. Existing workspace regression
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Mermaid and not Diagram" -q
Expected: All existing workspace tests pass. If not met: block.

### 5. Existing VisualGateResult tests
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_visual_gate_result.py -q
Expected: All 33 pass. If not met: block.

### 6. Existing profile tests
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_run_profile.py -q
Expected: All 50 pass. If not met: block.

### 7. Full regression
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_persistence.py services/runner/tests/test_runtime_evidence.py services/runner/tests/test_artifact_store.py services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_run_profile.py services/runner/tests/test_visual_gate_result.py services/task_intake/tests/test_run_profile_api.py services/task_intake/tests/test_visual_gate_result_api.py services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_local_operator.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py -q
Expected: All pass. If not met: block.

### 8. Mermaid diagram viewer smoke
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-diagram-viewer.py
Expected: "MERMAID DIAGRAM VIEWER SMOKE PASSED" as last stdout line. No residue. If not met: block.

### 9. Safe SVG rendering prevention grep
grep -n -E "innerHTML.*svg|svg.*innerHTML" services/task_intake/src/task_intake/artifact_workspace.py | grep -v "sanitized_svg"
Expected: exit code 1 (no matches except controlled sanitized_svg). If not met: block.

### 10. No innerHTML with unsanitized mermaid content
grep -n -E "innerHTML.*mermaid|mermaid.*innerHTML" services/task_intake/src/task_intake/artifact_workspace.py
Expected: exit code 1. If not met: block.

### 11. No eval or document.write
grep -n -E "eval\(|document\.write|Function\(" services/task_intake/src/task_intake/artifact_workspace.py
Expected: exit code 1. If not met: block.

### 12. Sanitizer called before every SVG response
grep -n "sanitize_svg" services/task_intake/src/task_intake/server.py
Expected: exactly 1 reference (in diagram route handler). If not met: block.

### 13. VisualGateResult route unchanged
grep -n "visual-gate-result" services/task_intake/src/task_intake/server.py | grep -v "diagram"
Expected: existing visual-gate-result route unchanged. If not met: block.

### 14. Forbidden file changes
git diff --name-only -- services/runner/src/runner/run_profile.py services/runner/src/runner/visual_gate_result.py services/runner/src/runner/artifacts.py services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/runner/src/runner/review_boundary.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/task_intake/src/task_intake/manual_orchestration.py services/task_intake/src/task_intake/local_operator.py ROADMAP.md .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
Expected: empty. If not met: block.

### 15. Planning lock diff
git diff -- .project-memory/pr/0150-requirement-state-sequence-diagram-viewers/PLAN.md .project-memory/pr/0150-requirement-state-sequence-diagram-viewers/reviews/plan-review.yml
Expected: empty. If not met: block.

### 16. Residue check
git status --short
Expected: only approved files in dirty tree. If not met: block.

## END-TO-END SMOKE

Script: scripts/smoke-mermaid-diagram-viewer.py

Command: PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-diagram-viewer.py

Sequence:
1. Create isolated temporary runs_root.
2. Create persisted run directory.
3. Create run-profile.json with three Mermaid descriptors (requirement, state, sequence).
4. Create three fixture .mmd files.
5. Create VisualGateResult with three required_diagrams entries.
6. For each diagram: call API route, verify SVG response includes svg root element.
7. Verify sanitizer removes hostile elements from hostile-mermaid.mmd.
8. Verify missing file returns correct error.
9. Verify nonexistent diagram_id returns correct error.
10. Verify invalid Mermaid source returns render error.
11. Verify no PR 0151 or PR 0152 behavior present.
12. Cleanup: temp directory removed, no .ariadne under pwd.

Exact success marker: "MERMAID DIAGRAM VIEWER SMOKE PASSED" as last stdout line.

## IMPLEMENTATION REPORT

Require: .project-memory/pr/0150-requirement-state-sequence-diagram-viewers/IMPLEMENTATION_REPORT.md

Must begin with: "This implementation report is handoff context, not proof. Agent output is not proof. Reviewer must verify claims against files, diffs, validation output, dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK."

Require all 11 canonical sections per IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist.
2. PLAN.md or plan-review.yml changes during implementation.
3. Architecture diverges from OPTION A (server-side SVG generation).
4. Client-side Mermaid rendering via CDN or bundled JS used.
5. SVG inserted without passing through svg_sanitizer.py.
6. A second diagram source of truth exists.
7. Profile descriptors mutated — kind, media_type, ref, or sha256 changed.
8. VisualGateResult schema modified — required_diagrams, status, or field semantics changed.
9. Rendered diagram labeled as proof, approval, or Visual Gate passage.
10. Approve/reject, mutation, or approval artifact added.
11. Any Mermaid directive, click handler, link, or executable content survives sanitization.
12. Missing or malformed state shown as success.
13. innerHTML used with unsanitized values or concatenated strings.
14. eval, document.write, Function constructor, or iframe srcdoc used.
15. Network access for diagram rendering.
16. Subprocess or Docker execution for diagram rendering.
17. HTTP mutation outside the single approved GET-only diagram route.
18. PR 0151 readiness enforcement (pipeline blocking).
19. PR 0152 human approval artifact.
20. Artifact Registry or acceptance state.
21. Gates & Proofs or Logs & Captures zones modified.
22. Existing route, profile, visual-gate-result, or workspace regression.
23. Validation or smoke failure.
24. Residue — unknown untracked files.
25. Missing or inaccurate IMPLEMENTATION_REPORT.md.

## NO-DRIFT CHECK

Require affirmative confirmation:

1. Correct branch: 0150-requirement-state-sequence-diagram-viewers.
2. Correct roadmap slot: PR 0150 — next after PR 0149.
3. Exact allowlist and planning lock: only approved files changed. PLAN.md and plan-review.yml unchanged.
4. Selected architecture: OPTION A — server-side Mermaid SVG generation with mermaid-diagram.
5. One diagram source of truth: PR 0148 Mermaid descriptors via PR 0149 required_diagrams.
6. Exact dependency: mermaid-diagram>=1.0.0,<2.0.0 added to pyproject.toml.
7. Security: svg_sanitizer.py called on EVERY SVG before API response.
8. No survivor: onclick, href, xlink:href, script, foreignObject, iframe, img external src — all removed.
9. Stale protection: detailRequestCounter guards all diagram fetches.
10. Zone separation: diagram viewer in Canvas only. Gates & Proofs and Logs & Captures unchanged.
11. No false proof: rendered SVG labelled "Rendered diagram — visual representation. Not independently verified proof or approval."
12. No PR 0151 scope: no pipeline blocking, no readiness enforcement.
13. No PR 0152 scope: no human approval, no approve/reject.
14. No Artifact Registry: no acceptance state.
15. PR 0148 preservation: kind="mermaid", media_type="text/vnd.mermaid", .mmd bounds, hash verification, inert source text — all unchanged.
16. PR 0149 preservation: VisualGateResult schema, required_diagrams, status, evidence_refs — all unchanged.
17. Existing runtime preservation: run persistence, profile sidecar, ArtifactStore — all unchanged.
18. Focused workspace tests: TestMermaidDiagramViewer class added (closing PR 0148 coverage gap).
19. Required validation and smoke: all 16 validation commands pass.
20. No residue: git status clean except approved files.
21. Physical evidence precedence: file contents, test results, smoke output, diffs, and validation evidence override agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The locked plan cannot be followed (architecture, scope, allowlist).
2. A required file is outside the allowlist.
3. mermaid-diagram cannot be installed or used via pip.
4. The API of mermaid-diagram differs materially (e.g., no security config params).
5. SVG sanitization cannot be implemented safely.
6. Renderer cannot produce deterministic output for same input.
7. Profile schema changes are required.
8. VisualGateResult schema changes are required.
9. PR 0151 or PR 0152 scope becomes necessary.
10. Network access becomes necessary for rendering.
11. Unsafe innerHTML or DOM access cannot be avoided.
12. Tests or smoke fail.
13. Unexplained residue appears.
14. Architect authority is required beyond documented scope.
