# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0151 — Visual Gate Readiness Checker.

Implemented OPTION A (On-Demand Computed Readiness). A new pure module
`visual_gate_readiness.py` determines whether the Visual Gate for a selected
run is technically ready for human review. Readiness is computed on demand
from the existing `VisualGateResult`, `run-profile.json`, and the PR 0150
renderer. No persistence, no caching, no mutation of `visual-gate-result.json`.

## CORRECTIVE DELTA (B001)

**Blocker B001**: The original implementation created
`test_visual_gate_readiness_display.py` as a separate file, which is outside
the locked PLAN.md implementation allowlist. The plan requires display tests
in `test_artifact_workspace_shell.py` (EDIT).

**Fix**: Moved the complete `TestVisualGateReadinessDisplay` class (21 tests)
plus required helpers (`FIXTURES_DIR`, `_load_fixture`) into the approved
file `services/task_intake/tests/test_artifact_workspace_shell.py`. The
original separate file was physically removed. No production code was changed.

## SELECTED ARCHITECTURE

OPTION A — On-Demand Computed Readiness.

## FILES CHANGED

### New files (PLAN.md allowlist):

1. **services/runner/src/runner/visual_gate_readiness.py** — Core module.
   Function `check_visual_gate_readiness(runs_root, run_id) -> dict`.
   Pure computation function using `read_visual_gate_result()`,
   `read_run_profile()`, `resolve_run_relative()`, `render_mermaid_to_svg()`,
   `sanitize_svg()`. No persistence, no caching, no HTTP. Returns exact
   result schema: `{ok, is_ready, status, reason_codes, explanation,
   diagram_results, renderer_available, staleness_guard}`.

2. **services/runner/tests/test_visual_gate_readiness.py** — 18 domain tests
   covering all decision-table scenarios.

3. **services/task_intake/tests/test_visual_gate_readiness_api.py** — 7 API
   route tests.

4. **scripts/smoke-visual-gate-readiness.py** — End-to-end deterministic smoke.

5. **tests/fixtures/empty-profile.json** — Empty profile fixture.

### Edited files (PLAN.md allowlist):

6. **services/task_intake/src/task_intake/server.py** — Added import of
   `check_visual_gate_readiness`. Added `is_readiness` route detection flag.
   Added `GET /runs/<run_id>/visual-gate-readiness` route handler with
   versioned JSON response. Added `is_readiness` to run_id extraction logic.
   No changes to existing routes.

7. **services/task_intake/src/task_intake/artifact_workspace.py** — Added
   `fetchReadiness()`, `renderReadinessResult()`, `showReadinessLoading()`,
   `showReadinessUnavailable()` functions. Added `__readinessStalenessGuard`
   variable. Wired `fetchReadiness(runId)` into `selectRun()`. Readiness
   displayed in Gates & Proofs zone. All values via textContent.
   renderGatesProofs() unchanged.

8. **services/task_intake/tests/test_artifact_workspace_shell.py** (CORRECTIVE
   EDIT) — Added `TestVisualGateReadinessDisplay` class with 21 display tests,
   added `FIXTURES_DIR` and `_load_fixture` helpers. This is the approved
   location per PLAN.md allowlist.

### File removed (B001 fix):

9. **services/task_intake/tests/test_visual_gate_readiness_display.py**
   — Physically removed from filesystem. No placeholder, inert file, or
   symlink left behind. Originally contained 21 display tests. All tests
   moved to `test_artifact_workspace_shell.py`. This path no longer exists.

### Unchanged files (read-only calls):

- `mermaid_renderer.py` — Readiness calls it but does not modify it.
- `svg_sanitizer.py` — Readiness calls it but does not modify it.

## READINESS RESULT SCHEMA

| Field | Type | Always | Description |
|---|---|---|---|
| ok | bool | yes | True if readiness could be determined. |
| is_ready | bool | yes | True if gate is technically ready. |
| status | str | yes | ready, not_ready, no_gate, unavailable. |
| reason_codes | list[str] | yes | Blocking condition identifiers. |
| explanation | str | yes | Human-readable summary. |
| diagram_results | list[dict] or null | var | Per-diagram detail when VG exists. |
| renderer_available | bool | yes | Node.js renderer availability. |
| staleness_guard | str | yes | Deterministic hash for stale detection. |

## READINESS STATUSES

| Status | is_ready | Meaning |
|---|---|---|
| ready | true | All required diagrams valid and renderable. |
| not_ready | false | At least one required diagram cannot be verified. |
| no_gate | false | No VisualGateResult exists for this run. |
| unavailable | false | System-level issue (malformed VG, malformed profile). |

## REASON CODE COVERAGE

20 reason codes implemented per decision table.

## TESTS

| Suite | Count | Status |
|---|---|---|
| test_visual_gate_readiness.py (domain) | 18 (17 pass, 1 skip) | ALL PASS |
| test_visual_gate_readiness_api.py (API) | 7 | ALL PASS |
| **test_artifact_workspace_shell.py (display)** | **21 (VisualGateReadinessDisplay)** | **ALL PASS** |
| Existing workspace (not Readiness) | 341 | ALL PASS |
| Existing VG result | 33 | ALL PASS |
| Existing profile | 50 | ALL PASS |
| Existing diagram viewer + sanitizer + VG | 73 (72 pass, 1 skip) | ALL PASS |
| unapproved display test file | N/A | deleted from filesystem |
| Full regression | 823 (822 pass, 1 skip) | ALL PASS |

## REAL RENDERER EVIDENCE

All tests use the real Node.js renderer (not a mock). The READY state
test verifies that `render_mermaid_to_svg()` produces valid SVG and
`sanitize_svg()` accepts the output.

## SMOKE

Script: `scripts/smoke-visual-gate-readiness.py`

Marker: `VISUAL GATE READINESS SMOKE PASSED` — confirmed as last stdout line.

## DEPENDENCIES

No new Python or npm dependencies.

## VALIDATION RESULTS

| # | Command | Status | Details |
|---|---------|--------|---------|
| 1 | test_visual_gate_readiness.py | PASS | 17 pass, 1 skip |
| 2 | test_visual_gate_readiness_api.py | PASS | 7 passed |
| 3 | test_artifact_workspace_shell.py -k VisualGateReadinessDisplay | PASS | **21 collected, 21 passed** |
| 4 | test_visual_gate_readiness_display.py (deleted) | PASS | **File removed, path does not exist** |
| 5 | Existing workspace (not Readiness) | PASS | 341 passed |
| 6 | test_visual_gate_result.py | PASS | 33 passed |
| 7 | test_run_profile.py | PASS | 50 passed |
| 8 | Diagram viewer + sanitizer | PASS | 72 pass, 1 skip |
| 9 | Full regression | PASS | 823 pass, 1 skip |
| 10 | Smoke | PASS | "VISUAL GATE READINESS SMOKE PASSED" |
| 11 | Forbidden file diff | PASS | empty |
| 12 | Plan lock diff | PASS | empty |
| 13 | No mutation grep | PASS | exit 1 |
| 14 | renderGatesProofs unchanged | PASS | function present |
| 15 | Physical deletion verified | PASS | test ! -e succeeds, file absent from git status |
| 16 | Whitespace check | PASS | git diff --check: exit 0 |

## PLAN DRIFT GATE

All 23 conditions PASS (B001 resolved: unapproved file physically deleted).

## NO-DRIFT CHECK

All 24 conditions PASS (condition 3 corrected: exact allowlist followed).

## CURRENT STATE

- HEAD: 8a6d1ea9acf5454f37ac2417f664129180117116
- Branch: 0151-visual-gate-readiness-checker
- Dirty tree: 3 modified + 6 untracked (all PLAN.md allowlist approved)
- Old display test file: removed
- New display tests: in test_artifact_workspace_shell.py (21 collected)
- IMPLEMENTATION COMPLETE: yes
- IMPLEMENTATION REPORT WRITTEN: yes
