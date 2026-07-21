# PR 0151 — Visual Gate Readiness Checker Plan

## EVIDENCE SNAPSHOT

1. HEAD: eb93d4e5458a2fce05c1e8780b01a149d28e2941
2. Branch: 0151-visual-gate-readiness-checker
3. Dirty tree: clean
4. Cached diff: empty
5. origin/main: eb93d4e5458a2fce05c1e8780b01a149d28e2941
6. PR 0150 merge evidence: present — "PR 0150 — Requirement / State / Sequence Diagram Viewers (#180)" at HEAD
7. No PR 0151 implementation exists.

## ROADMAP ALIGNMENT

- roadmap track: Visual Gate / Mermaid (Stream 3, PR 0151)
- expected PR slot: PR 0151 (Visual Gate Readiness Checker)
- why this PR is next: PR 0150 is merged. ROADMAP.md and ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md identify PR 0151 as the next product PR after PR 0150.
- batching policy check: Pass — PR 0151 is a coherent single-capability PR (deterministic readiness assessment). Not isolated UI work.
- drift heuristic check: Not triggered — no consecutive UI-only PRs.
- architect sign-off required: no — expected normal roadmap slot.
- architect sign-off reference: N/A

PR 0152 remains next (Human Visual Approval Artifact).

## CAPABILITY BOUNDARY

PR 0151 determines whether the Visual Gate for a selected run is *technically ready* for human review. Readiness is a deterministic, read-only, fail-closed assessment. It is:

- **Not** human approval (PR 0152).
- **Not** artifact acceptance (Stream 4).
- **Not** pipeline enforcement (no execution blocking).
- **Not** a general file browser or upload surface.
- **Not** a second registry or schema.

The readiness assessment evaluates the following chain against the selected run:

1. A `VisualGateResult` exists and is valid for the run.
2. The VisualGateResult has at least one `required_diagrams` entry.
3. For each required diagram entry, the referenced Mermaid artifact exists in the run profile.
4. For each referenced artifact, the .mmd source file exists and is readable.
5. For each .mmd source, the PR 0150 renderer can produce SVG (renderer available + parseable syntax).
6. For each rendered SVG, the sanitizer accepts the output.
7. No required diagram is missing, malformed, oversized, encoding-broken, hash-mismatched, or render-failed.
8. No stale-run or stale-profile race condition discarded the results.

The readiness result is computed **on demand** for the currently selected run. It is **not persisted** — it is a transient, per-selection assessment that reflects the current state of the run's artifacts. This avoids creating a second source of truth alongside `visual-gate-result.json`.

## SELECTED ARCHITECTURE: ON-DEMAND COMPUTED READINESS

**Why on demand (OPTION A):**

Readiness is a function of the current run's artifacts plus the current availability of the renderer. Neither the artifacts nor the renderer availability change between evaluations unless the underlying files or installed tools change. Storing a cached readiness result would create a second source of truth that could contradict the live `VisualGateResult` status after an artifact update. On-demand computation is simpler, avoids stale-cache problems, and has no persistence cost.

**Canonical input:** `VisualGateResult` (from `visual-gate-result.json`), run profile (from `run-profile.json`), and the renderer availability (from `_check_renderer_available()`).

**Ownership layer:** `services/runner/src/runner/visual_gate_readiness.py` — new pure module. No server.py, No workspace.py.

**API surface:** `check_visual_gate_readiness(runs_root, run_id) -> dict`. This is an internal function. The workspace fetches readiness via an HTTP route or internal call.

**Readiness result type:** A dict with fields: `{ok, is_ready, status, reason_codes, explanation, diagram_results, renderer_available, staleness_guard}`.

**Readiness statuses:** `ready`, `not_ready`, `no_gate`, `unavailable`.

**Persistence strategy:** None. Readiness is computed on each request. No file is written. No cache is stored. No `visual-gate-result.json` field is modified.

**Stale-response protection:** Same `detailRequestCounter` pattern as all other selection-based fetches. The function itself does not add a second stale-protection layer.

## READINESS RESULT SCHEMA

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| ok | bool | yes | Whether readiness could be determined at all. False if run/profile/VG result are unreadable. |
| is_ready | bool | yes | Whether the Visual Gate is technically ready for human review. |
| status | str | yes | One of: ready, not_ready, no_gate, unavailable. |
| reason_codes | list of str | no | Stable identifiers for each blocking condition. Empty when ready. |
| explanation | str | no | Human-readable summary of what is blocking readiness. Empty when ready. |
| diagram_results | list of DiagramReadinessResult | no | Per-diagram readiness results. Present when VG result exists and has required_diagrams. |
| renderer_available | bool | yes | Whether the Node.js Mermaid renderer is available. |
| staleness_guard | str | yes | A deterministic hash of (run_id, profile_sha256, visual_gate_sha256). The caller uses this to detect stale responses. |

### DiagramReadinessResult fields

| Field | Type | Required | Description |
|---|---|---|---|
| diagram_id | str | yes | From VisualGateResult required_diagrams entry. |
| diagram_type | str | yes | From VisualGateResult required_diagrams entry. |
| required | bool | yes | Whether this diagram is required. |
| descriptor_found | bool | yes | Whether profile_descriptor_key resolves to an existing descriptor with kind="mermaid". |
| source_found | bool | yes | Whether the controlled reference resolves to an existing .mmd file. |
| hash_match | bool or None | yes | Whether the source sha256 matches the descriptor sha256. None if no sha256 declared. |
| render_ok | bool or None | yes | Whether PR 0150 renderer produced SVG. None if source not found or hash mismatch. |
| sanitize_ok | bool or None | yes | Whether SVG passed sanitizer. None if render failed. |
| error | str or None | no | Error identifier for this diagram if any. |
| source_size_bytes | int or None | no | File size in bytes. |

### Status values

| Status | is_ready | Meaning |
|---|---|---|
| ready | true | All required diagrams exist, are valid, and render successfully. Gate is technically ready for human review. |
| not_ready | false | At least one required diagram cannot be verified or rendered. See reason_codes for details. |
| no_gate | false | No VisualGateResult exists for this run. Gate has not been configured. |
| unavailable | false | Run, profile, or VisualGateResult could not be read. System-level issue. |

## REASON CODES

| Reason code | Status | Explanation text |
|---|---|---|
| run_not_found | unavailable | "Run not found at specified path." |
| visual_gate_result_not_found | no_gate | "No VisualGateResult exists for this run." |
| visual_gate_result_malformed | unavailable | "VisualGateResult is malformed or unreadable." |
| visual_gate_result_unsupported_version | unavailable | "VisualGateResult has an unsupported schema version." |
| visual_gate_result_hash_mismatch | unavailable | "VisualGateResult stored hash does not match computed hash. Data may be inconsistent." |
| profile_not_found | no_gate | "Run profile not found — cannot resolve Mermaid artifact descriptors." |
| profile_malformed | unavailable | "Run profile is malformed or unreadable." |
| no_required_diagrams | not_ready | "VisualGateResult has no required_diagrams." |
| descriptor_not_found:<key> | not_ready | "Required diagram references descriptor key '{key}' which does not exist in run profile." |
| descriptor_kind_mismatch:<key> | not_ready | "Descriptor '{key}' exists but its kind is '{actual}', expected 'mermaid'." |
| source_not_found:<id> | not_ready | "Mermaid source file for diagram '{id}' was not found at the controlled reference path." |
| source_too_large:<id> | not_ready | "Mermaid source file for diagram '{id}' exceeds 100 KB maximum." |
| source_encoding_error:<id> | not_ready | "Mermaid source file for diagram '{id}' is not valid UTF-8." |
| hash_mismatch:<id> | not_ready | "Mermaid source for diagram '{id}' has a content hash that does not match the declared hash." |
| renderer_unavailable | not_ready | "Mermaid renderer (Node.js + mermaid npm package) is not available." |
| render_error:<id> | not_ready | "Failed to render diagram '{id}' — Mermaid syntax error or renderer failure." |
| sanitize_error:<id> | not_ready | "SVG output for diagram '{id}' failed sanitization. Possible security issue." |
| internal_error | unavailable | "Internal error while checking readiness." |
| stale_response | not_ready | "Readiness check completed for a stale selection. Reload to confirm." |

## DETERMINISTIC DECISION TABLE

| # | Scenario | Status | Reason codes | Evaluation continues? | User-visible result | PR 0152 eligible? |
|---|---|---|---|---|---|---|
| 1 | All required diagrams: descriptor found, source found, hash matches, render OK, sanitize OK | ready | [] | Yes | "Gate is ready for human review." | Yes (if accepted) |
| 2 | Missing required descriptor (profile_descriptor_key not in profile) | not_ready | descriptor_not_found:<key> | Stops for this diagram | "Required diagram references descriptor key '<key>' which does not exist." | Yes (upon readiness) |
| 3 | Descriptor exists but kind != "mermaid" | not_ready | descriptor_kind_mismatch:<key> | Stops for this diagram | "Descriptor '<key>' exists but its kind is '<actual>', expected 'mermaid'." | Yes (upon readiness) |
| 4 | Descriptor exists, ref resolves, source file missing | not_ready | source_not_found:<id> | Stops for this diagram | "Source file for diagram '<id>' not found." | Yes (upon readiness) |
| 5 | Source found but sha256 mismatch | not_ready | hash_mismatch:<id> | Stops for this diagram | "Content hash for diagram '<id>' does not match declared hash." | Yes (upon readiness) |
| 6 | Source found but > 100KB | not_ready | source_too_large:<id> | Stops for this diagram | "Source file for diagram '<id>' exceeds 100 KB." | Yes (upon readiness) |
| 7 | Source found but encoding error | not_ready | source_encoding_error:<id> | Stops for this diagram | "Source file for diagram '<id>' is not valid UTF-8." | Yes (upon readiness) |
| 8 | Source valid but renderer unavailable | not_ready | renderer_unavailable | Continues (all diagrams evaluated) | "Mermaid renderer is not available. Run 'npm install'." | No (renderer required) |
| 9 | Renderer available but syntax/invalid Mermaid | not_ready | render_error:<id> | Stops for this diagram | "Failed to render diagram '<id>'." | Yes (upon readiness) |
| 10 | Render succeeded but sanitizer rejects SVG | not_ready | sanitize_error:<id> | Stops for this diagram | "SVG output for diagram '<id>' failed security sanitization." | Yes (upon readiness) |
| 11 | Unsupported diagram type (not requirement/state/sequence) | not_ready | unsupported_diagram_type | Continues (other diagrams evaluated) | "Diagram '<id>' has unsupported type '<type>'. Supported types: requirement, state, sequence." | Yes (upon readiness) |
| 12 | Duplicate required diagram_id | not_ready | duplicate_diagram_id:<id> | Stops for this diagram | "Duplicate diagram_id '<id>' in required_diagrams." | Yes (upon readiness) |
| 13 | All source/descriptor checks pass but render times out | not_ready | render_error:<id> (timeout) | Stops for this diagram | "Rendering diagram '<id>' timed out." | Yes (upon readiness) |
| 14 | Empty required_diagrams list | not_ready | no_required_diagrams | Stops | "VisualGateResult has no required_diagrams." | No (nothing to review) |
| 15 | VisualGateResult file malformed/unreadable | unavailable | visual_gate_result_malformed | Stops | "VisualGateResult is unreadable." | No (system issue) |
| 16 | VisualGateResult missing (file not found) | no_gate | visual_gate_result_not_found | Stops | "No VisualGateResult exists for this run." | Yes (needs gate) |
| 17 | VisualGateResult unsupported schema version | unavailable | visual_gate_result_unsupported_version | Stops | "VisualGateResult has unsupported schema version '<v>'." | No (system issue) |
| 18 | Profile missing (no run-profile.json) | no_gate | profile_not_found | Stops | "Run profile not found." | No (needs profile) |
| 19 | All descriptors valid, source found, render OK, sanitize OK — plus extra non-required diagram | ready | [] (extra diagram ignored if optional) | Yes | "Gate is ready for human review." | Yes (if accepted) |
| 20 | Stale response detected (detailRequestCounter mismatch) | not_ready | stale_response | Stops | "Readiness check completed for a stale selection." | No (re-run needed) |
| 21 | VG status=passed — all diagrams valid and render OK | ready | [] | Yes | "Gate is ready for human review." | Yes (human may still accept) |
| 22 | VG status=ready_needs_review — all diagrams valid and render OK | ready | [] | Yes | "Gate is ready for human review." | Yes (this is the expected flow) |

## SEPARATION OF RESPONSIBILITY

| Layer | PR | Responsibility | Created by |
|---|---|---|---|
| Artifact description | 0148 | Controlled Mermaid descriptors in profile | run_profile.py |
| Gate declaration | 0149 | required_diagrams in VisualGateResult | visual_gate_result.py |
| Safe rendering | 0150 | Render .mmd to SVG, sanitize, display | mermaid_renderer.py + svg_sanitizer.py |
| **Readiness check** | **0151** | **Determine whether gate is technically ready** | **visual_gate_readiness.py (new)** |
| Human decision | 0152 | Record human approve/reject | deferred |

A **technically ready** result means:
- All required diagrams exist, are valid Mermaid, and render safely.
- The renderer is available and produces SVGs.
- No hash, encoding, size, or syntax issue blocks any required diagram.

A **technically ready** result does **not** mean:
- approved, accepted, executable, mergeable, or authorized.
- The renderer output is correct or factually accurate.
- Any human has reviewed or accepted the diagrams.

## READINESS FUNCTION CONTRACT

```python
def check_visual_gate_readiness(
    runs_root: str,
    run_id: str,
    node_render_script: str | None = None,   # Path to scripts/mermaid-render.cjs
) -> dict:
    """Determine whether the Visual Gate is technically ready for human review.

    Returns dict with fields:
      - ok: bool
      - is_ready: bool
      - status: str (ready, not_ready, no_gate, unavailable)
      - reason_codes: list[str]
      - explanation: str
      - diagram_results: list[dict] or None
      - renderer_available: bool
      - staleness_guard: str
    """
```

The function follows this order:

1. **Check renderer availability** — call `_check_renderer_available()` which checks `node --version` + script existence.
2. **Load VisualGateResult** via `read_visual_gate_result(runs_root, run_id)`. If not ok: return unavailable/no_gate.
3. **Extract VG status**. If VG status itself is `failed`, record as a note but evaluate anyway (readiness != gate passage).
4. **Check required_diagrams not empty**. If empty: `not_ready` with `no_required_diagrams`.
5. **Load run profile** via `read_run_profile(runs_root, run_id)`. If not ok or no `artifact_descriptors`: return no_gate/unavailable.
6. **For each required_diagram entry** (in diagram_id order):
   a. Resolve `descriptor_ref` (profile_descriptor_key:<key>) against profile descriptors.
   b. If not found: `descriptor_not_found`, stop for this diagram.
   c. If found but kind != "mermaid": `descriptor_kind_mismatch`, stop.
   d. Extract ref and sha256 from descriptor.
   e. Resolve controlled ref via `resolve_run_relative()` or ArtifactStore.
   f. Check file exists, size <= 100KB, read as UTF-8. If any fail: stop for this diagram.
   g. If sha256 declared: verify hash against content. Mismatch: `hash_mismatch`, stop.
   h. Check diagram_type is in allowed set (requirement, state, sequence). Unknown: warning but continue.
   i. Call `render_mermaid_to_svg()` with the source text.
   j. If render fails: `render_error` or `renderer_unavailable`, stop.
   k. Call `sanitize_svg()` on the SVG output.
   l. If sanitize fails: `sanitize_error`, stop.
   m. Record DiagramReadinessResult for this diagram.
7. **Aggregate**: If all required diagrams pass, `is_ready=True`, status=`ready`, reason_codes empty.
8. **Compute staleness_guard**: `sha256(f"{run_id}:{profile_sha256}:{vg_sha256}")[:16]`.

## API ROUTE

### GET /runs/<run_id>/visual-gate-readiness

New read-only route added to `server.py`. Returns JSON with the readiness result schema.

**Response contract:**

| Field | Type | Always present | Description |
|---|---|---|---|
| ev_contract_version | str | yes | "1" |
| ok | bool | yes | Readiness check completed. |
| run_id | str | yes | Run identifier. |
| is_ready | bool | yes | Whether gate is technically ready. |
| status | str | yes | One of: ready, not_ready, no_gate, unavailable. |
| reason_codes | list of str | yes | Empty list when ready. |
| explanation | str | yes | Human-readable summary. |
| diagram_results | list of dict or None | no | Per-diagram detail. Present when VG result exists. |
| renderer_available | bool | yes | Whether Node.js renderer is installed. |
| staleness_guard | str | yes | Deterministic hash for stale-response detection. |

**HTTP status:** Always 200. Errors conveyed in JSON body (same pattern as all Ariadne read routes).

**States:**
- Ready: ok=True, is_ready=True, status="ready", reason_codes=[].
- Not ready: ok=True, is_ready=False, status="not_ready", reason_codes lists blockers.
- No gate: ok=True, is_ready=False, status="no_gate", reason_codes=["visual_gate_result_not_found"].
- Unavailable: ok=False, is_ready=False, status="unavailable", reason_codes describes system issue.

**No browser-controlled roots** — runs_root is server-configured.

**No mutation** — GET only.

## UI PLACEMENT

### Readiness belongs in Gates & Proofs

The readiness status and reason codes are displayed in the **Gates & Proofs zone** (`#zone-gates-proofs`), rendered by a new function `renderReadinessResult()` called from the existing detail fetch or from a separate readiness fetch. The existing `renderGatesProofs()` is **not modified** — readiness is displayed as a new section within the same zone.

### Why Gates & Proofs, not Canvas/Profile

Readiness is a gate assessment (technical gate readiness), not a diagram artifact. It belongs with the manifest, evidence, and proof-refs already displayed in Gates & Proofs. The rendered diagram SVGs remain in Canvas (PR 0150). The separation:

- **Canvas zone**: profile metadata, inert Mermaid source text (PR 0148), rendered diagram viewers (PR 0150).
- **Gates & Proofs zone**: manifest files, evidence paths, source errors, agent claims, report provenance, proof refs (PR 0147), **and now** Visual Gate readiness status/reasons (PR 0151).

### Display behavior

| Readiness state | Gates & Proofs display |
|---|---|
| ready | "Visual Gate: Ready. All required diagrams are valid and renderable." |
| not_ready | "Visual Gate: Not ready. Reason: <explanation>. Reason codes: <codes>" with list of blocking per-diagram issues |
| no_gate | "Visual Gate: Not configured. No VisualGateResult exists for this run." |
| unavailable | "Visual Gate: Unavailable. Error: <error>" |
| loading | "Checking Visual Gate readiness..." |
| stale (guard mismatch) | "Readiness check is stale. Refreshing..." (automatically cleared) |

### Stale-response and race protection

`fetchReadiness(runId)` follows the same `detailRequestCounter` pattern:
1. Captures `requestId = ++detailRequestCounter` before fetch.
2. On response: `if (requestId !== detailRequestCounter) return;`.
3. On catch: `if (requestId !== detailRequestCounter) return;`.
4. In addition, the response includes `staleness_guard`. The caller compares it against a stored value. If it differs from what was expected (e.g., profile or VG result changed between fetch and render), the result is discarded and re-fetched.

`selectRun()` clears the readiness section before fetching new data.

### No approve/reject controls

The Gates & Proofs zone remains read-only. No accept/reject buttons, approval dropdowns, or mutation controls are added. PR 0152 remains responsible for the human decision interface.

## IMPLEMENTATION ALLOWLIST

### services/runner/src/runner/visual_gate_readiness.py (NEW)

Core module. Function `check_visual_gate_readiness(runs_root, run_id, node_render_script=None) -> dict`. Pure computation function. Calls `read_visual_gate_result()`, `read_run_profile()`, `resolve_run_relative()`, `render_mermaid_to_svg()`, `sanitize_svg()`. No persistence, no caching, no HTTP.

Permitted: Pure Python function. Standard library only (hashlib, os, json). Calls existing runner and task_intake functions via import.

Prohibited: No file writes. No caching. No HTTP. No mutation of `visual-gate-result.json` or `run-profile.json`. No agent, subprocess (beyond calling the existing renderer), shell, git, gh, or Docker.

### services/task_intake/src/task_intake/server.py (EDIT)

Add import of `check_visual_gate_readiness`. Add `GET /runs/<run_id>/visual-gate-readiness` route handler. Route handler: validate run_id, call check function, build versioned JSON response.

Permitted: One additive GET route handler. Import statement.

Prohibited: No POST/PUT/PATCH/DELETE. No changes to existing routes (profile, VG result, diagram, report, detail, health, root, workspace, orchestration, product iteration).

### services/task_intake/src/task_intake/artifact_workspace.py (EDIT)

Add function `renderReadinessResult(data)` that renders the readiness status and reason_codes into the Gates & Proofs zone (`#gates-content`). Add function `showReadinessLoading()` and `showReadinessUnavailable()`. Add function `fetchReadiness(runId)` that calls `GET /runs/<run_id>/visual-gate-readiness` with stale-response protection (detailRequestCounter + staleness_guard comparison). Wire into `selectRun()` so readiness is fetched alongside detail, profile, report, and profile.

Permitted: Additive functions in the Gates & Proofs section. CSS for readiness display elements.

Prohibited: No changes to existing renderGatesProofs function. No changes to Canvas, Timeline, or Logs & Captures zones. No approve/reject controls. No mutation controls. No diagram viewer changes. No innerHTML with unsanitized values. All runtime values via textContent/safeText.

### services/runner/tests/test_visual_gate_readiness.py (NEW)

Focused domain tests for every readiness branch and reason code in the decision table.

Tests:
- All required diagrams valid → ready.
- Missing required descriptor → not_ready, descriptor_not_found.
- Descriptor kind mismatch → not_ready, descriptor_kind_mismatch.
- Missing source file → not_ready, source_not_found.
- Hash mismatch → not_ready, hash_mismatch.
- Source too large → not_ready, source_too_large.
- Encoding error → not_ready, source_encoding_error.
- Renderer unavailable → not_ready, renderer_unavailable.
- Render failure → not_ready, render_error.
- Sanitize failure → not_ready, sanitize_error.
- Unsupported diagram type → not_ready, unsupported_diagram_type.
- Duplicate diagram_id → not_ready, duplicate_diagram_id.
- Empty required_diagrams → not_ready, no_required_diagrams.
- VisualGateResult missing → no_gate, visual_gate_result_not_found.
- VisualGateResult malformed → unavailable, visual_gate_result_malformed.
- VisualGateResult unsupported version → unavailable, visual_gate_result_unsupported_version.
- VisualGateResult hash mismatch → unavailable, visual_gate_result_hash_mismatch.
- Profile missing → no_gate, profile_not_found.
- Profile malformed → unavailable, profile_malformed.
- Extra non-required diagram + all valid → ready.
- Valid optional diagram missing → ready (optional).
- VG status=passed with all valid → ready.
- VG status=ready_needs_review with all valid → ready.
- Staleness_guard mismatch detected.
- Renderer available/not available detection.
- No filesystem mutation after check.

### services/task_intake/tests/test_visual_gate_readiness_api.py (NEW)

API route tests for GET /runs/<run_id>/visual-gate-readiness.

Tests:
- Ready state returns 200 with is_ready=True.
- Not ready state returns 200 with is_ready=False and reason_codes.
- No gate state returns 200 with status="no_gate".
- Unavailable state returns 200 with status="unavailable".
- Invalid run_id returns ok=False.
- Missing runs_root handled gracefully.
- GET-only: POST/PUT/PATCH/DELETE return 404.

### services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)

New test class `TestVisualGateReadinessDisplay` in the existing workspace test file.

Tests:
- renderReadinessResult function exists.
- showReadinessLoading function exists.
- showReadinessUnavailable function exists.
- fetchReadiness function exists.
- Ready state text: "Visual Gate: Ready."
- Not ready state text: "Visual Gate: Not ready."
- No gate state text: "Visual Gate: Not configured."
- Unavailable state text: "Visual Gate: Unavailable."
- Loading state text: "Checking Visual Gate readiness..."
- Stale-response protection: staleness_guard comparison.
- detailRequestCounter integration.
- selectRun calls fetchReadiness.
- No approve/reject controls.
- No mutation controls.
- All runtime values via textContent (no innerHTML with values).
- Existing zones unaffected.
- Existing PR 0147 renderGatesProofs functions unchanged.
- Existing PR 0150 renderDiagramViewer functions unchanged.

### tests/fixtures/empty-profile.json (NEW)

Empty profile for malformed-profile test cases.

### scripts/smoke-visual-gate-readiness.py (NEW)

End-to-end deterministic local smoke test.

Target marker: `VISUAL GATE READINESS SMOKE PASSED`.

### .project-memory/pr/0151-visual-gate-readiness-checker/IMPLEMENTATION_REPORT.md (NEW)

Written by coder per Implementation Handoff Artifact Contract.

### .project-memory/pr/0151-visual-gate-readiness-checker/reviews/precommit-review.yml (PREEXISTING)

Written only by precommit-review. Not coder-writable.

### Forbidden files — not modified

- ROADMAP.md, .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
- All PR 0147A-0150 source, tests, and documentation
- services/runner/src/runner/run_profile.py, visual_gate_result.py, artifacts.py, runtime_evidence.py, run_persistence.py, review_boundary.py
- services/runner/src/runner/mermaid_renderer.py (readiness calls it but does not modify it)
- services/task_intake/src/task_intake/svg_sanitizer.py (readiness calls it but does not modify it)
- services/task_intake/src/task_intake/runtime_evidence_serialization.py, manual_orchestration.py, local_operator.py
- All agents/*.yml, schemas/*.yml, docs
- Construction-estimate files and fixtures
- PR 0148 Mermaid fixtures, scripts
- PR 0150 diagram viewer scripts, render script, fixtures

## TEST PLAN

All test commands use existing physical test files or future PLAN-approved files.

### 1. Visual Gate Readiness unit tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_visual_gate_readiness.py -q
```

Expected: All 22+ readiness domain tests pass. If not met: block.

### 2. Visual Gate Readiness API tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_visual_gate_readiness_api.py -q
```

Expected: All 7+ API tests pass. If not met: block.

### 3. Workspace readiness display tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Readiness or Gate" -q
```

Expected: All 15+ readiness display tests pass. If not met: block.

### 4. Existing workspace tests (excluding new tests)

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Readiness and not Gate" -q
```

Expected: All existing workspace tests pass. If not met: block.

### 5. Existing VG result tests

```bash
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_visual_gate_result.py -q
```

Expected: All 33 pass. If not met: block.

### 6. Existing profile tests

```bash
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_run_profile.py -q
```

Expected: All 50 pass. If not met: block.

### 7. Existing diagram viewer tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_mermaid_renderer.py services/task_intake/tests/test_svg_sanitizer.py services/runner/tests/test_visual_gate_result.py -q
```

Expected: All pass. If not met: block.

### 8. Full regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_persistence.py services/runner/tests/test_runtime_evidence.py services/runner/tests/test_artifact_store.py services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_run_profile.py services/runner/tests/test_visual_gate_result.py services/runner/tests/test_mermaid_renderer.py services/task_intake/tests/test_run_profile_api.py services/task_intake/tests/test_visual_gate_result_api.py services/task_intake/tests/test_svg_sanitizer.py services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_local_operator.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py -q
```

Expected: All pass. If not met: block.

### 9. Readiness smoke

```bash
npm install 2>/dev/null; PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-readiness.py
```

Expected: "VISUAL GATE READINESS SMOKE PASSED" as last stdout line. No residue. If not met: block.

### 10. Forbidden file changes

```bash
git diff --name-only -- services/runner/src/runner/run_profile.py services/runner/src/runner/visual_gate_result.py services/runner/src/runner/artifacts.py services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/runner/src/runner/review_boundary.py services/runner/src/runner/mermaid_renderer.py services/task_intake/src/task_intake/svg_sanitizer.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/task_intake/src/task_intake/manual_orchestration.py services/task_intake/src/task_intake/local_operator.py ROADMAP.md .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
```

Expected: empty. If not met: block.

### 11. Planning lock diff

```bash
git diff -- .project-memory/pr/0151-visual-gate-readiness-checker/PLAN.md .project-memory/pr/0151-visual-gate-readiness-checker/reviews/plan-review.yml
```

Expected: empty. If not met: block.

### 12. Residue check

```bash
git status --short
```

Expected: only approved files in dirty tree. If not met: block.

### 13. No mutation grep

```bash
grep -n -E "approve|reject|accept" services/task_intake/src/task_intake/artifact_workspace.py | grep -i "button\|click\|function\|onclick\|control\|dropdown"
```

Expected: exit code 1 (no approve/reject controls). If not met: block.

### 14. Gates & Proofs not overwritten

```bash
grep -n "renderGatesProofs" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: existing renderGatesProofs function unchanged. If not met: block.

## END-TO-END SMOKE

Script: `scripts/smoke-visual-gate-readiness.py`

Command: `npm install 2>/dev/null; PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-readiness.py`

Sequence:
1. Create isolated temporary runs_root.
2. Create persisted run directory with run.json.
3. Create run-profile.json with one valid Mermaid descriptor (kind="mermaid", media_type="text/vnd.mermaid", ref pointing to a synthetic .mmd file).
4. Create the synthetic .mmd file.
5. Create a VisualGateResult with one required_diagram entry referencing the descriptor.
6. Call `check_visual_gate_readiness()`. Assert is_ready=True, status="ready".
7. Delete the .mmd source file. Call again. Assert is_ready=False, status="not_ready", source_not_found.
8. Re-create the .mmd file with invalid Mermaid syntax. Assert is_ready=False, render_error.
9. Delete the VisualGateResult file. Call again. Assert is_ready=False, status="no_gate".
10. Verify GET /runs/<run_id>/visual-gate-readiness returns correct JSON for ready state.
11. Verify GET route returns 200 with ok=False for missing run_id.
12. Verify no repository residue: temporary directory cleaned up, no .ariadne under pwd.
13. Verify no approve/reject controls in workspace output.
14. Verify no filesystem mutation by readiness check (file hashes unchanged before/after).

Exact success marker: `VISUAL GATE READINESS SMOKE PASSED` as last stdout line.

## DEPENDENCY STRATEGY

No new Python dependencies or npm packages. The readiness checker reuses:
- `read_visual_gate_result()` from existing `visual_gate_result.py`.
- `read_run_profile()` from existing `run_profile.py`.
- `resolve_run_relative()` from existing `run_profile.py`.
- `render_mermaid_to_svg()` from existing `mermaid_renderer.py` (requires `npm install` already done by PR 0150).
- `sanitize_svg()` from existing `svg_sanitizer.py`.
- `hashlib`, `os`, `json` from Python standard library.

The Node.js renderer dependency (mermaid npm package) was introduced by PR 0150. PR 0151 does not add to it or require a different install target. If the renderer is not available, the readiness check reports `renderer_unavailable` and `is_ready=False`.

## IMPLEMENTATION REPORT

Require: `.project-memory/pr/0151-visual-gate-readiness-checker/IMPLEMENTATION_REPORT.md`

Must begin with: "This implementation report is handoff context, not proof. Agent output is not proof. Reviewer must verify claims against files, diffs, validation output, dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK."

Require all 11 canonical sections per IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist.
2. PLAN.md or plan-review.yml changes during implementation.
3. Architecture diverges from OPTION A (on-demand computed readiness).
4. Readiness state persisted to `visual-gate-result.json` (creating second truth).
5. Readiness state persisted to any file.
6. Renderer checks skipped or weakened.
7. Sanitizer checks skipped or weakened.
8. Missing/malformed/hash-mismatched source shown as ready.
9. Descriptor presence alone establishes readiness (must verify source + render + sanitize).
10. any `is_ready=True` when `renderer_available=False`.
11. Approve/reject, acceptance, or mutation controls added.
12. Pipeline enforcement or execution blocking added.
13. Diagram viewer or Canvas zone modified.
14. renderGatesProofs function modified (readiness displayed separately).
15. Existing PR 0147 manifest/evidence display broken.
16. Gateway response without `ev_contract_version`.
17. Non-deterministic response for same immutable inputs.
18. Network access for readiness check.
19. Subprocess executed beyond the existing PR 0150 renderer call.
20. Existing route regression.
21. Validation or smoke failure.
22. Residue — unknown untracked files.
23. Missing or inaccurate IMPLEMENTATION_REPORT.md.

## NO-DRIFT CHECK

Require affirmative confirmation:

1. Correct branch: `0151-visual-gate-readiness-checker`.
2. Correct roadmap slot: PR 0151 — next after PR 0150.
3. Exact allowlist and planning lock: only approved files changed. PLAN.md and plan-review.yml unchanged.
4. Selected architecture: OPTION A — on-demand computed readiness. No persistence. No cache.
5. One readiness source of truth: `check_visual_gate_readiness()` evaluates PR 0149 VG result + PR 0148 profile + PR 0150 renderer.
6. Every reason code has a deterministic trigger (see decision table).
7. All 22 decision-table scenarios covered by tests.
8. Renderer unavailability causes `is_ready=False` (fail-closed).
9. Malformed/absent VG result causes `is_ready=False` (fail-closed).
10. Missing/malformed/hash-mismatched source causes `is_ready=False` (fail-closed).
11. sanitizer rejection causes `is_ready=False` (fail-closed).
12. `ok=False` means readiness could not be determined at all.
13. `is_ready=True` means technical readiness only, not approval.
14. No approve/reject controls exist.
15. No `visual-gate-result.json` field modified.
16. No `visual-gate-result.json` field read incorrectly.
17. PR 0148 preservation: kind="mermaid", media_type="text/vnd.mermaid", .mmd bounds, hash verification, inert source text — all unchanged.
18. PR 0149 preservation: VisualGateResult schema, required_diagrams, status, evidence_refs, hash — all unchanged.
19. PR 0150 preservation: renderer, sanitizer, diagram route, diagram viewer, tests, fixtures, smoke — all unchanged.
20. Existing runtime preservation: run persistence, profile sidecar, ArtifactStore — all unchanged.
21. Focused tests: 22+ domain tests + 7+ API tests + 15+ workspace tests.
22. Required validation: all 14 validation commands pass.
23. No residue: git status clean except approved files.
24. Physical evidence precedence: file contents, test results, smoke output, diffs, and validation evidence override agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The locked plan cannot be followed (architecture, scope, allowlist).
2. A required file is outside the allowlist.
3. Readiness cannot be computed without modifying `visual-gate-result.json`.
4. Readiness cannot be computed without adding a new rendering capability.
5. Renderer unavailability cannot be detected without modifying the renderer.
6. Approve/reject or mutation controls become necessary.
7. Pipeline enforcement becomes necessary.
8. Network access becomes necessary for readiness.
9. Tests or smoke fail.
10. Unexplained residue appears.
11. Architect authority is required beyond documented scope.
