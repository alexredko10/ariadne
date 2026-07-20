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

## CORRECTIVE AMENDMENT: ARCHITECTURE REVISION — NODE.JS SUBPROCESS MERMAID SVG RENDERING

**Effective immediately.** This amendment replaces the SELECTED ARCHITECTURE, DEPENDENCY STRATEGY, and affected allowlist sections of the locked PLAN.md. All other sections remain in effect.

**Evidence for revision (physically verified):**

1. `mermaid-diagram>=1.0.0,<2.0.0` (locked PLAN.md dependency) does not exist on PyPI. The only available version — `mermaid_diagram` 0.1.2 — provides a `Packet` class that generates Mermaid *source text* only. It has no `MermaidDiagram` class and cannot produce SVG.
2. `python-mermaid` 0.1.6 provides a `MermaidDiagram` class alias for `Diagram` — also generates Mermaid source text only. No SVG rendering.
3. `pymermaid` 1.7.1 renders by launching a real browser via Selenium — violates offline determinism, adds heavyweight dependencies (Firefox/Chrome, geckodriver).
4. **No pure-Python package on PyPI can render Mermaid to SVG.** This is a known limitation: Mermaid SVG rendering is a JavaScript/Node.js capability.

**Selected fallback architecture: OPTION B — Node.js Subprocess Mermaid Renderer**

The renderer invokes `node` as a subprocess with a committed rendering script (`scripts/mermaid-render.cjs`). The script uses the `mermaid` npm package (v11.x) with `JSDOM` to render Mermaid source to SVG deterministically without a real browser.

**Why OPTION B over alternatives:**
- The `mermaid` npm package (v11.16.0, 83.5MB unpacked, 1171 files) is the *official* Mermaid rendering engine. Every other approach generates source text or requires a real browser.
- Node.js v25 is available in the environment (`node` on PATH).
- JSDOM provides a virtual DOM without a real browser, network, or GPU.
- The render script is a committed file — no dynamic code execution.
- Subprocess receives only .mmd text via stdin, never shell commands.
- Strict timeout (30s) and size limits (100 KB source) prevent resource exhaustion.
- Deterministic: same .mmd source → same SVG output (with fixed mermaid config).

### Dependency changes

**Removed from pyproject.toml**:
- `mermaid-diagram>=1.0.0,<2.0.0` — this package does not exist as described and cannot render SVG.

**Added to package.json**:
- `"mermaid": "^11.0.0"` — the official Mermaid rendering engine.
- `"jsdom": "^29.0.0"` — virtual DOM for server-side rendering without a browser.

**Added make install target**:
- `npm install` added to the `install-dev` make target (or a separate `make install-mermaid-renderer`).

**Fallback behavior unchanged**: If Node.js or the npm packages are not available, the renderer returns `ok=False` with error `mermaid_renderer_not_available`.

### Security boundary

The render script (`scripts/mermaid-render.cjs`):
- Reads Mermaid source from stdin only.
- Renders with `mermaid.render()` inside JSDOM.
- All click handlers disabled via mermaid config (`securityLevel: 'strict'`).
- Outputs SVG to stdout only.
- No filesystem access, no network, no shell commands from the .mmd content.
- Stderr for errors only.

### Existing renderer and sanitizer changes

**services/runner/src/runner/mermaid_renderer.py** — REWRITE:
- Replace `from mermaid_diagram import MermaidDiagram` with subprocess-based invocation.
- `_MERMAID_AVAILABLE` detection: checks for `node` on PATH + `scripts/mermaid-render.cjs` exist.
- `render_mermaid_to_svg()` writes source to stdin of `node scripts/mermaid-render.cjs`, captures stdout (SVG), stderr (errors), with 30-second timeout.
- Returns same dict shape: `{ok, svg, error, diagram_type, byte_count, mermaid_sha256}`.
- All existing return values unchanged.

**services/runner/tests/test_mermaid_renderer.py** — UPDATE:
- Remove `_MERMAID_AVAILABLE` import-check of `mermaid_diagram`.
- `_MERMAID_AVAILABLE` detection checks for `node` on PATH + render script.
- Test methods unchanged — same assertions, same fixtures.
- Three SVG-producing tests (`test_valid_requirement/state/sequence_diagram_produces_svg`) now **pass** instead of skip/fail when node+mermaid are installed.

**services/task_intake/src/task_intake/svg_sanitizer.py** — UNCHANGED.
The sanitizer is not affected by the rendering backend change.

**scripts/mermaid-render.cjs** — NEW:
Committed Node.js script for server-side Mermaid SVG rendering.

**scripts/smoke-mermaid-diagram-viewer.py** — UNCHANGED.
The smoke script exercises the API route and sanitizer, not the renderer directly.

### Implementation allowlist changes

| File | Change from locked plan |
|---|---|
| pyproject.toml | Remove `mermaid-diagram>=1.0.0,<2.0.0`. No Python dependency added. |
| package.json | Add `"mermaid": "^11.0.0"` and `"jsdom": "^29.0.0"` to devDependencies. |
| Makefile (EDIT) | Add `install-mermaid-renderer` target: `cd frontend && npm install` (or similar). |
| scripts/mermaid-render.cjs (NEW) | Committed Node.js render script. Read from stdin, render via mermaid+jsdom, output SVG to stdout. |
| mermaid_renderer.py (REWRITE) | Replace import-based rendering with subprocess-based rendering. |
| test_mermaid_renderer.py (UPDATE) | Replace availability detection. All test methods unchanged. |
| svg_sanitizer.py | Unchanged. |
| test_svg_sanitizer.py | Unchanged. |
| All other files from locked allowlist | Unchanged. |

### Test plan runner changes

Validation command #1 changes from:
```
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_mermaid_renderer.py -q
```
To:
```
cd frontend && npm install && cd .. && PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_mermaid_renderer.py -q
```
(Or equivalent `make install-mermaid-renderer && pytest ...`)

Expected result updated: All 13 tests pass (including the 3 SVG-producing tests).

### PLAN DRIFT GATE additions

In addition to the existing 25 drift gate conditions:

26. Subprocess execution not sanitized (stdin contains only .mmd text, not shell commands).
27. Committed render script modified to execute arbitrary shell commands from .mmd content.
28. Node.js renderer invoked with untrusted arguments (only `scripts/mermaid-render.cjs` script path).
29. Subprocess timeout not enforced (must be ≤ 30 seconds).
30. npm packages replaced with network-dependent alternatives.
31. Pure-Python Mermaid package claimed to exist without physical evidence.

### NO-DRIFT CHECK additions

In addition to the existing 21 conditions:

22. Node.js subprocess uses committed render script (no dynamic code generation).
23. npm packages `mermaid` and `jsdom` installed locally (not global, not network-at-runtime).
24. Render script has no filesystem, network, or shell execution beyond reading stdin.
25. Corrected dependency: no `mermaid-diagram>=1.0.0,<2.0.0` in pyproject.toml.
26. Three SVG-producing renderer tests pass with Node.js backend.

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
| Renderer not available | Node.js or npm packages not installed | "Mermaid renderer not available. Install dependencies with: npm install" |
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
Remove `mermaid-diagram>=1.0.0,<2.0.0` from [project] dependencies (this package does not exist as described and cannot render SVG). No Python dependency is added for Mermaid rendering.
Permitted: Removal of the phantom dependency line. Prohibited: No other changes to pyproject.toml.

### package.json (EDIT)
Add `"mermaid": "^11.0.0"` and `"jsdom": "^29.0.0"` to `devDependencies` (or similar dependencies field). These are the official Mermaid rendering engine and a virtual DOM for server-side SVG generation without a real browser.
Permitted: Two dependency additions. Prohibited: No changes to scripts, version, name, or other fields.

### Makefile (EDIT)
Add `install-mermaid-renderer` target that runs `npm install` (or equivalent). This target must be run before the 3 SVG-producing renderer tests pass. The target is NOT part of the default `make install-dev` — it is a separate opt-in step for the mermaid rendering capability.
Permitted: One additive target. Prohibited: No changes to existing targets (install-dev, test, lint, smoke, local-operator).

### scripts/mermaid-render.cjs (NEW)
Committed Node.js rendering script. Reads Mermaid source from stdin. Uses JSDOM + mermaid to render to SVG. Outputs SVG to stdout. Uses `mermaid.initialize({securityLevel: 'strict'})` to disable all click handlers, links, and forms.
Permitted: Deterministic Node.js script. No network, no filesystem writes, no dynamic code.

### services/runner/src/runner/mermaid_renderer.py (REWRITE)
Replace `from mermaid_diagram import MermaidDiagram` with subprocess invocation of `node scripts/mermaid-render.cjs`. Availability detection checks for `node` on PATH + render script existence. Returns same dict shape: {ok, svg, error, diagram_type, byte_count, mermaid_sha256}. 30-second subprocess timeout. Stdin = .mmd source. Stdout = SVG. Stderr = error message.
Permitted: subprocess with strict timeout, committed script path, stdin/stdout/stderr only. Prohibited: No dynamic script paths, no shell=True, no eval, no network, no filesystem writes outside the render call.

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

### services/runner/tests/test_mermaid_renderer.py (UPDATE)
Replace import-check availability detection with node+script availability detection. All 13 test methods unchanged — same assertions, same fixtures. Three SVG-producing tests now pass when node+mermaid are installed.

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
# Install npm packages first (if not yet done), then run renderer tests.
# The make target install-mermaid-renderer installs npm packages. Run once per environment.
```
npm install 2>/dev/null; PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_mermaid_renderer.py -q
```
Expected: All 13 tests pass (including 3 SVG-producing tests). If not met: block.

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
```
npm install 2>/dev/null; PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-diagram-viewer.py
```
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

Command: npm install 2>/dev/null; PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-diagram-viewer.py

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
3. Architecture diverges from OPTION B (Node.js subprocess Mermaid rendering). No pure-Python package is claimed to render SVG without physical evidence.
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
16. Unsafe subprocess execution: dynamic script paths, shell=True, arbitrary arguments, or missing timeout. The committed render script `scripts/mermaid-render.cjs` is the only permitted subprocess target.
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
4. Selected architecture: OPTION B — Node.js subprocess Mermaid rendering via committed `scripts/mermaid-render.cjs` + npm `mermaid` package.
5. One diagram source of truth: PR 0148 Mermaid descriptors via PR 0149 required_diagrams.
6. Corrected dependency: npm packages `mermaid` and `jsdom` added to package.json devDependencies. `pyproject.toml` no longer contains `mermaid-diagram>=1.0.0,<2.0.0` (phantom package does not exist).
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
3. The Node.js + npm rendering pipeline cannot be installed (node not on PATH, npm install fails, package resolution fails).
4. The render script cannot produce deterministic SVG for valid Mermaid source.
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
