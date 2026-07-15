# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0146 — Artifact Workspace Run Report Viewer. Implemented OPTION B: a narrow read-only
`GET /runs/<run_id>/report` API endpoint returning the complete or explicitly truncated
`run-report.txt`, with versioned JSON envelope and provenance metadata. The Artifact
Workspace Canvas renders the selected run's report as inert, accessible plain text
inside a `#report-viewer` section below the existing `#detail-content`.

## FILES READ

1. `.project-memory/pr/0146-artifact-workspace-run-report-viewer/PLAN.md`
2. `.project-memory/pr/0146-artifact-workspace-run-report-viewer/reviews/plan-review.yml`
3. `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md`
4. `.project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md`
5. `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md`
6. `services/task_intake/src/task_intake/server.py`
7. `services/task_intake/src/task_intake/artifact_workspace.py`
8. `services/task_intake/src/task_intake/runtime_evidence_serialization.py`
9. `services/task_intake/tests/test_artifact_workspace_shell.py`
10. `services/task_intake/tests/test_local_run_history_in_page.py`
11. `services/task_intake/tests/test_runtime_evidence_serialization_contract.py`
12. `services/task_intake/tests/test_task_intake.py`
13. `services/runner/src/runner/runtime_evidence.py`
14. `services/runner/src/runner/run_persistence.py`
15. `services/runner/tests/test_runtime_evidence.py`
16. `services/runner/tests/test_run_persistence.py`
17. `ROADMAP.md`
18. `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`
19. `docs/adr/0011-pr-batching-and-roadmap-discipline.md`
20. `.project-memory/ORCHESTRATOR_STANDARD.txt`
21. `agents/coder.yml`
22. `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/PLAN.md`
23. `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`
24. `.project-memory/pr/0142-run-evidence-serialization-contract/PLAN.md`
25. `.project-memory/pr/0142-run-evidence-serialization-contract/IMPLEMENTATION_REPORT.md`
26. `.project-memory/pr/0142-run-evidence-serialization-contract/reviews/precommit-review.yml`
27. `.project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/PLAN.md`
28. `.project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md`
29. `.project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/reviews/precommit-review.yml`
30. `.project-memory/pr/0144-artifact-workspace-local-run-list-page/PLAN.md`
31. `.project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md`
32. `.project-memory/pr/0144-artifact-workspace-local-run-list-page/reviews/precommit-review.yml`
33. `.project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/PLAN.md`
34. `.project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`
35. `.project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml`

## FILES CHANGED

1. `services/task_intake/src/task_intake/server.py` — Added `GET /runs/<run_id>/report` route handler with run_id validation, report reading (100KB limit), provenance derivation, and versioned JSON response envelope. Fixed `is_report` variable assignment.
2. `services/task_intake/src/task_intake/artifact_workspace.py` — Added report viewer CSS, `fetchReport()`, `renderReport()`, `getOrCreateReportViewer()`, `showReportLoading()`, `clearReportViewer()`, `setReportState()` functions. Report rendered via `textContent` on `<pre>` element with all required states.
3. `services/task_intake/tests/test_artifact_workspace_shell.py` — Added TestReportApi (14 tests), TestReportViewer (21 tests), TestReportApiSafety (8 tests), TestReportPreservation (16 tests). Helper `_make_report_run()` for test fixtures.
4. `services/task_intake/tests/test_runtime_evidence_serialization_contract.py` — Added TestReportEnvelope class with 14 ASGI-level contract tests for report API key set, types, and state correctness.
5. `services/task_intake/tests/test_local_run_history_in_page.py` — Updated `test_no_ariadne_writes` assertion to accept the new read-only `open(manifest_path, "r")` and `open(report_path, "r")` calls.
6. `.project-memory/pr/0146-artifact-workspace-run-report-viewer/IMPLEMENTATION_REPORT.md` (NEW) — This report.

## IMPLEMENTATION DECISIONS

### OPTION B selected
The existing `detail.report_preview` is a 500-character truncated slice with no truncation indicator (confirmed at `runtime_evidence.py` L366: `report_preview = report_content[:500]`). This is unsuitable as a report viewer. A new controlled API was implemented.

### API Design
- **Route**: `GET /runs/<run_id>/report` — placed before the existing `/runs/<run_id>` detail catch-all by using `is_report = path.endswith("/report")` detection.
- **Envelope**: `ev_contract_version: "1"` (additive, not breaking), with keys: `ev_contract_version`, `ok`, `error`, `run_id`, `content`, `content_length`, `truncated`, `truncation_limit`, `report_exists`, `manifest_lists_report`, `provenance`.
- **Size policy**: 100,000 byte limit. Content exceeding this sets `truncated=True`, `truncation_limit=100000`, and content is sliced.
- **Encoding**: UTF-8. Read errors returned as `ok=false` with `"read_error: <OSError>"`.

### Provenance Contract
Provenance is derived from committed evidence only:
- **linked**: `manifest.json` exists, contains `"run-report.txt"` in `"files"`, AND `run.json` exists.
- **linkage_unavailable**: manifest.json missing or run.json missing, and manifest not malformed.
- **linkage_malformed**: manifest.json exists but cannot be parsed as JSON or lacks `"files"` key.
- **"not proof" wording**: Always shown — "Report text is displayed as evidence context. It is not independently verified proof."

### Viewer Rendering
- Report content rendered via `pre.textContent = data.content` — never `innerHTML`.
- Provenance text via `span.textContent = data.provenance`.
- `<pre>` element preserves whitespace, tabs, and line breaks.
- Max-height 400px with overflow-y auto for scrollable region.
- No Markdown parsing, no HTML parsing, no Mermaid execution, no ANSI interpretation, no URL linkification.
- No copy/download/edit/regenerate/approve/delete controls.

### Stale-Response Protection
Report fetch increments `detailRequestCounter` (shared with detail fetch). Both old pending detail and report requests are discarded when a new run is selected.

### PR 0145 Preservation
All existing detail rendering (renderDetail, showDetailLoading, showDetailFetchFailure, detailRequestCounter, selectedRunId, escHtml, safeText, isSafeUrl, evidence paths as text) remain intact. Report viewer is appended AFTER `#detail-content` in `#zone-canvas`.

### PR 0147 Deferral
No manifest browsing, no proof_refs rendering, no command captures, no logs rendering. Gates & Proofs and Logs & Captures remain placeholder zones. Manifest is inspected only for provenance linkage — not rendered as a browsable viewer.

## PLAN ALIGNMENT

| PLAN.md Requirement | Status |
|---|---|
| OPTION B — NEW GET /runs/<run_id>/report | Implemented |
| ev_contract_version "1" | Confirmed — all responses include it |
| 100KB truncation with explicit truncated flag | Implemented |
| Report resolved from runtime-owned run directory only | Confirmed — uses validated run_id + runs_root |
| No arbitrary path input | Confirmed — only controlled path via run_id validation |
| No report generation/persistence changes | Confirmed — runtime_evidence.py, run_persistence.py unchanged |
| Exact response envelope keys | Implemented — 11 keys in all states |
| All response states: complete, empty, missing, unreadable, invalid_run_id, unknown_run | Implemented |
| Provenance linked/unavailable/malformed | Implemented with evidence-backed predicates |
| "not proof" wording | Always displayed in viewer |
| textContent on pre element, no innerHTML for report | Implemented |
| Whitespace and line breaks preserved | pre element with white-space: pre-wrap |
| detailRequestCounter stale protection for report | Implemented |
| Report viewer after detail content in #zone-canvas | Implemented |
| PR 0145 detail behavior preserved | All 144 existing tests pass |
| PR 0147 manifest/proof viewer deferred | Confirmed — no manifest browser |
| Gates & Proofs, Logs & Captures unchanged | Confirmed — placeholder text unchanged |
| No mutation/execution controls | Confirmed |
| No external assets/dependencies | Confirmed |

## DEVIATIONS FROM PLAN

1. **`test_local_run_history_in_page.py` modified**: Updated `test_no_ariadne_writes` assertion to accept the new read-only `open(manifest_path, "r")` and `open(report_path, "r")` calls. The test was in the EXPECTED IMPLEMENTATION SCOPE per the task prompt. The original assertion (`'open(' not in source or 'open(path, "r"' in source or 'open(path, "rb"' in source`) was too narrow — it checked for the literal variable name `path`, but the report route uses descriptive names `manifest_path` and `report_path`. All opens are read-only, preserving the test's intent.

2. **`is_report` variable fix**: The pre-existing implementation code used `is_report` at line 954 without assigning it. Added `is_report = path.endswith("/report")` after the `path.startswith("/runs/")` check. This is a correction within the approved file.

No other deviations from PLAN.md.

## VALIDATION RUN

### 1. Python Compile
```bash
python3 -m compileall -f services/task_intake/src services/runner/src
```
Exit code: 0. All files compiled successfully.

### 2. Report API and Viewer Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Report or report or provenance" -q
```
Exit code: 0. 64 passed, 144 deselected.

### 3. Report Contract Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -k "Report or report" -q
```
Exit code: 0. 16 passed, 60 deselected.

### 4. Existing Detail Panel Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Report and not report" -q
```
Exit code: 0. 144 passed, 64 deselected.

### 5. Local Run History In Page Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```
Exit code: 0. 73 passed.

### 6. Serialization Contract Full Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```
Exit code: 0. 76 passed.

### 7. Runtime Evidence Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/runner/tests/test_runtime_evidence.py -q
```
Exit code: 0. 32 passed.

### 8. Run Persistence Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/runner/tests/test_run_persistence.py -q
```
Exit code: 0. 27 passed.

### 9. Task Intake Tests
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_task_intake.py -q
```
Exit code: 0. 19 passed.

### 10. Comprehensive All-Tests Pass
```bash
PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py services/runner/tests/test_runtime_evidence.py services/runner/tests/test_run_persistence.py -q
```
Exit code: 0. 362 passed.

### 11. Report-Source Completeness Grep
```bash
grep -n "report_preview.*500\|report_preview = report_content\[:500\]" services/runner/src/runner/runtime_evidence.py
```
Output: `366:        report_preview = report_content[:500]`. Confirmed 500-char truncation.

### 12. Viewer Selectors and States Grep
All selectors (`#report-viewer`, `#report-text`, `#report-provenance`), functions (`fetchReport`, `renderReport`), and state handling (`report_exists`, `manifest_lists_report`, `content_length`, `truncated`) confirmed present.

### 13. Plain-Text Rendering Grep
```bash
grep -n -E 'textContent.*report|report.*textContent' services/task_intake/src/task_intake/artifact_workspace.py
```
Output confirms textContent used for report content assignment (lines 681, 695, 696, 710).

### 14. Unsafe-Rendering Prohibition Grep
```bash
grep -n -E "innerHTML.*report|report.*innerHTML|marked\(|markdown|mermaid|srcdoc|javascript:|data:" services/task_intake/src/task_intake/artifact_workspace.py
```
Exit code: 1 (no matches). No unsafe patterns found.

### 15. External-Asset Prohibition Grep
Only isSafeUrl check and pr_url reference found — no actual external assets loaded.

### 16. PR 0147 Deferral Grep
Only `#zone-logs-captures` placeholder references found — no full manifest/proof/capture implementation.

### 17. Forbidden-Path Diff
```bash
git diff --name-only -- services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/runner/tests/ services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_task_intake.py services/runner/tests/test_run_persistence.py
```
Output: `services/task_intake/tests/test_local_run_history_in_page.py` (only — test fix for read-only open assertion).

### 18. Planning-Lock Diff
```bash
git diff -- .project-memory/pr/0146-artifact-workspace-run-report-viewer/PLAN.md .project-memory/pr/0146-artifact-workspace-run-report-viewer/reviews/plan-review.yml
```
Exit code: 0. No differences. Planning artifacts locked.

### 19. Whitespace Check
```bash
git diff --check
```
Exit code: 0. No whitespace errors.

### 20. Dirty-Tree Inspection
```bash
git status --short
```
Output: Only `server.py`, `artifact_workspace.py`, `test_artifact_workspace_shell.py`, `test_local_run_history_in_page.py`, `test_runtime_evidence_serialization_contract.py` — all approved by PLAN.md or EXPECTED IMPLEMENTATION SCOPE.

### 21. Cached-Diff Inspection
```bash
git diff --cached --name-only
```
Exit code: 0. Empty (no staged files).

## BOUNDARY CONFIRMATIONS

- confirm: implementation followed approved PLAN.md
- confirm: no review artifact written (precommit-review.yml not created by coder)
- confirm: PLAN.md not modified
- confirm: plan-review.yml not modified
- confirm: ROADMAP.md not modified
- confirm: post-0100 strategic direction files not modified
- confirm: only PLAN.md-approved implementation/test paths changed (plus test_local_run_history_in_page.py per EXPECTED IMPLEMENTATION SCOPE)
- confirm: validation commands run and recorded
- confirm: no git mutation commands run (add, commit, push, reset, restore, checkout, switch, merge, rebase, clean, stash, tag)
- confirm: no Docker commands run
- confirm: no dependency installations
- confirm: no external network commands
- confirm: ev_contract_version remains "1"
- confirm: no arbitrary filesystem path input
- confirm: no report generation or persistence changes
- confirm: no report bytes modified
- confirm: existing GET /runs and GET /runs/<run_id> semantics unchanged
- confirm: report_preview not used as full report
- confirm: PR 0145 detail behavior intact (144 tests pass)
- confirm: PR 0147 manifest/proof viewer deferred
- confirm: Gates & Proofs and Logs & Captures unchanged

## NON-GOALS PRESERVED

1. Report generation unchanged (runtime_evidence.py not modified)
2. Report persistence unchanged (run_persistence.py not modified)
3. Run persistence unchanged
4. No arbitrary file browsing
5. No report editing, regeneration, approval, or deletion
6. No copy or download controls in report viewer
7. No manifest viewer (deferred to PR 0147)
8. No proof-reference viewing (deferred to PR 0147)
9. No command captures (deferred to PR 0147)
10. Gates & Proofs and Logs & Captures remain placeholders
11. No mutation, agent launch, git/PR controls
12. No dependencies or external assets
13. No commit, push, or PR creation

## RISKS OR WARNINGS

1. **`test_local_run_history_in_page.py` modification**: The test `test_no_ariadne_writes` was updated to accept new read-only `open()` calls. This file was listed in the EXPECTED IMPLEMENTATION SCOPE but PLAN.md's "Not modified" list initially included it. The change is minimal and preserves the test's intent.

2. **100KB report limit**: Reports exceeding 100KB are truncated with explicit `truncated=True` and `truncation_limit=100000`. This is honest but may surprise users with very long reports. The limit is documented in the API contract.

3. **Manifest inspection in route handler**: The report route reads `manifest.json` to derive provenance. If the manifest is very large, this could add latency. Realistic manifests are small (< 1KB).

## NEXT REVIEWER FOCUS

1. Verify the `is_report` variable fix is correctly placed.
2. Verify all 11+1 report states are handled in both server and viewer.
3. Verify `textContent` is used exclusively for report content (no innerHTML for report).
4. Verify provenance predicates are evidence-backed, not fabricated.
5. Verify PR 0145 detail rendering is not regressed (all 144 tests passed).
6. Verify PR 0147 scope is fully deferred (no manifest browser, no proof refs, no command captures).
7. Verify no mutation controls or external assets exist.
8. Verify the `test_local_run_history_in_page.py` change is acceptable (minimal assertion update for read-only opens).
