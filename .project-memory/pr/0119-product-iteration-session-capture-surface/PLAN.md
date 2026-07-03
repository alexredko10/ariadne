# PR 0119 — Product Iteration Session Capture Surface Plan

## Summary

Add a local Product Iteration Session Capture Surface on top of the existing PR 0117 backend contract. Wire the existing browser-side confusion signals (`__ariadne_confusion_signals[]`), feedback notes, session reports, and run history into the already-existing `POST /product/iterations` endpoint. Add minimal client-side session tracking (session start, active/idle screen-time timer) and a `"record product iteration signal"` action. Small surface module with focused tests.

## Product purpose

Ariadne now has a backend/local store contract for product iteration signals (PR 0117). The existing task-intake page already collects confusion signals, feedback notes, session reports, and run history in client-side JS arrays, but never persists them. PR 0119 wires those live browser signals into the `POST /product/iterations` endpoint so future product iterations can be grounded in observed local usage. Privacy-preserving, same-origin only, no external analytics.

## Roadmap alignment

* roadmap track: architect-approved product iteration substrate/surface
* expected PR slot: PR 0119
* why this PR is next: PR 0117 established the backend store contract (`POST /product/iterations`, `GET /product/iterations`). The existing HTML page already collects confusion signals, feedback, session reports, and run history in client-side JS. This PR wires those live signals into the backend endpoint, completing the capture surface. Minimal client-side session tracking (screen-time, idle detection) is added.
* batching policy check: surface module + server HTML/JS changes + focused tests form one coherent PR on top of unchanged PR 0117 backend. ADR 0011 allows batching the browser wiring with the surface contract.
* drift heuristic check: adds browser-to-backend wiring for existing JS arrays; no mutation of backlog/decision/trace stores; no external analytics; PR 0117 backend unchanged.
* architect sign-off required: yes
* architect sign-off reference: `экран тайм, product, итерации.`

## Why this is not reopened Local Interaction UX Track

- All backend store contract work was done in PR 0117 and is not repeated here
- This PR adds only the browser wiring (session timer, signal submission) to drive data into the already-existing endpoint
- No new frontend-only widgets, no standalone UX features
- No analytics SDK, no network calls beyond same-origin `POST /product/iterations`
- Architect explicitly approved the full "экран тайм, product, итерации" direction

## Existing PR 0117 contract inventory

| Component | Status | PR |
|-----------|--------|----|
| `product_iteration.py` — module with input/record/result/status objects | IMPLEMENTED | 0117 |
| `test_product_iteration.py` — 27 focused tests | IMPLEMENTED | 0117 |
| `POST /product/iterations` — record endpoint | IMPLEMENTED | 0117 |
| `GET /product/iterations` — list endpoint | IMPLEMENTED | 0117 |
| Route in `server.py` — request parse/create/response | IMPLEMENTED | 0117 |
| Route in `app.py` — `_ROUTES` list entry | IMPLEMENTED | 0117 |
| Precommit evidence | PASS | 0117 |

PR 0117 backend contract is unchanged by PR 0119.

## Proposed session capture surface contract

### New module

`services/task_intake/src/task_intake/product_iteration_surface.py`

Contains:
- `SessionTimer` — deterministic active/idle screen-time timer (simple counter-based, no wall-clock dependence)
- `capture_confusion_signals()` — read `__ariadne_confusion_signals[]` and map to `confusion_refs`
- `capture_feedback_notes()` — read feedback textarea value and map to `feedback_refs`
- `capture_report_refs()` — read session report output and map to `report_refs`
- `capture_run_history()` — read `__ariadne_run_history[]` and map to `run_refs`
- `capture_human_iteration_note()` — read iteration note field
- `build_product_iteration_payload()` — assemble all signals into `ProductIterationInput`
- `submit_product_iteration_signal()` — POST to `/product/iterations`
- `ProductIterationSurfaceResult` — result dataclass for surface operation
- `ProductIterationSurfaceStatus` — status enum: `recorded`, `pending`, `unavailable`

### Server HTML/JS additions (in `server.py`)

The existing HTML page at `GET /` must be extended with:

1. **Session start** — a `session_ref` generated at page load (deterministic SHA256[:16] of page load timestamp + random seed, or simple deterministic UUID-like value)
2. **Screen-time timer** — `setInterval` counter for `screen_time_seconds`, `active_time_seconds`, `idle_time_seconds`
3. **Idle detection** — `mousemove`/`keydown` reset idle timer; after X seconds of no activity, increment idle counter
4. **Human iteration note field** — a textarea or reuse existing feedback notes field
5. **"Record product iteration signal" button** or automatic best-effort submission on unload/session end (if safe and deterministic)
6. **Record status indicator** — shows "recorded", "rejected", or "not recorded" after submission

Minimal page addition: a panel/section about product iteration signals, or an unobtrusive status indicator.

### Surface contract details

- `session_ref` — deterministic hash of concatenated unique page session fields; regenerated on each page load
- `screen_time_seconds` — total elapsed seconds since page load
- `active_time_seconds` — seconds since page load minus idle seconds
- `idle_time_seconds` — seconds where no user interaction detected (configurable timeout)
- `run_refs` — extracted from `__ariadne_run_history[]`
- `confusion_refs` — extracted from `__ariadne_confusion_signals[]`
- `feedback_refs` — extracted from feedback textarea and radio button answers
- `report_refs` — extracted from session report output and run report output
- `human_iteration_note` — from existing feedback notes or dedicated field
- No page transcript capture — only explicit structured fields
- No hidden reasoning capture
- No external analytics

### Failure-safe behavior

If `POST /product/iterations` returns `"rejected"` or the endpoint is unavailable, the page must:
- Report the rejected status to the user
- Keep the session data in JS (do not discard)
- Allow the user to retry

## Proposed UI/page integration

A new section on the task-intake page titled "Product Iteration Signal" or "Session Evidence" containing:

- A human iteration note field (can reuse existing `feedback_notes`)
- A "Record product iteration signal" button
- A status indicator showing recorded/rejected/not recorded
- (Optional) auto-submit on page unload via `navigator.sendBeacon()` or synchronous `fetch()`

No visual redesign of the existing page. Additive only.

## Proposed files

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/product_iteration_surface.py` | NEW |
| `services/task_intake/tests/test_product_iteration_surface.py` | NEW |
| `services/task_intake/src/task_intake/server.py` | MODIFIED — add HTML/JS for session capture and record button |

PR 0117 files must remain unchanged:
- `services/task_intake/src/task_intake/product_iteration.py` — NOT modified
- `services/task_intake/tests/test_product_iteration.py` — NOT modified
- `services/task_intake/src/task_intake/app.py` — NOT modified (unless route visibility check needs updating)

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py` — must not be created
- `services/task_intake/tests/test_decision_trace.py` — must not be created
- Any file under `.project-memory/pr/0115-*/`, `.project-memory/pr/0116-*/`, `.project-memory/pr/0117-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`, `.project-memory/post-0100/`

## Privacy/local-only boundary

- No external analytics. No third-party telemetry.
- No network calls except same-origin local `POST /product/iterations`.
- No provider calls. No Docker. No shell subprocess. No git runtime behavior.
- No personal data beyond explicit `human_iteration_note`.
- No hidden reasoning capture. No raw full page transcript capture.
- No unbounded raw text capture.
- No mutation of backlog items, decision history, or trace data.
- No decision execution.

## Non-Goals

- No external analytics or telemetry
- No third-party SDK integration
- No network calls except same-origin `/product/iterations`
- No provider/LLM/Docker/shell/git runtime behavior
- No hidden reasoning or full transcript capture
- No personal data collection beyond explicit operator note
- No backlog/decision mutation
- No decision execution
- No PR 0115/0116/0117 artifact modifications
- No ROADMAP/docs/schema/agent/dependency changes
- No resurrection of `decision_trace.py` or `test_decision_trace.py`
- No standalone frontend-only widget — always paired with backend surface module
- No changes to PR 0117 backend contract

## Implementation steps

1. Create `product_iteration_surface.py` with:
   - `SessionTimer` — counter-based active/idle timer (no wall-clock dependence)
   - `ProductIterationSurfaceResult` — result dataclass
   - `ProductIterationSurfaceStatus` — status enum: `recorded`, `pending`, `unavailable`
   - Stable reason codes for surface validation
   - `build_product_iteration_payload()` — assemble signals into `ProductIterationInput`
   - Helper functions for extracting JS array data shapes

2. Create `test_product_iteration_surface.py` with focused tests.

3. Modify `server.py` HTML/JS to add:
   - JavaScript `session_ref` generation at page load
   - JavaScript `screen_time_seconds` / `active_time_seconds` / `idle_time_seconds` timers
   - JavaScript idle detection
   - JavaScript "Record product iteration signal" button handler that POSTs to `/product/iterations`
   - JavaScript status indicator display
   - (Optional) `beforeunload` handler for best-effort session-end submission

## Test plan

| Class | Focus |
|-------|-------|
| `TestBuildPayload` | Surface payload assembly includes all fields |
| `TestConfusionRefsExtraction` | Confusion signals mapped to confusion_refs |
| `TestRunRefsExtraction` | Run history mapped to run_refs |
| `TestFeedbackRefsExtraction` | Feedback notes mapped to feedback_refs |
| `TestReportRefsExtraction` | Session/report refs mapped to report_refs |
| `TestHumanIterationNote` | Human note extracted correctly |
| `TestSessionTimer` | Timer produces deterministic counters |
| `TestActiveIdleCalculation` | Active/idle counter distribution correct |
| `TestEmptySignals` | No signals → payload with empty refs |
| `TestNoHiddenReasoning` | Hidden reasoning in note → rejected at surface |
| `TestNoExternalAnalytics` | No network calls to external URLs |
| `TestNoBacklogMutation` | Backlog store not modified |
| `TestNoDecisionMutation` | Decision store not modified |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestOldNamesNotResurrected` | `decision_trace.py`, `test_decision_trace.py` do not exist |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_backlog_trace_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_product_iteration_surface.py \
  services/task_intake/tests/test_product_iteration.py \
  services/task_intake/tests/test_decision_backlog_trace_summary.py \
  services/task_intake/tests/test_decision_history.py \
  services/task_intake/tests/test_backlog_decision.py \
  services/task_intake/tests/test_backlog_review.py \
  services/runner/tests/test_backlog_surface.py \
  services/runner/tests/test_improvement_backlog.py \
  services/runner/tests/test_session_continuity.py \
  services/runner/tests/test_improvement_candidate.py \
  services/runner/tests/test_gate_evidence.py \
  services/runner/tests/test_acceptance_criteria.py \
  services/runner/tests/test_proof_capture.py \
  services/runner/tests/test_doctor_cli.py \
  services/runner/tests/test_proof_ref.py \
  services/runner/tests/test_handoff_packet.py \
  services/runner/tests/test_readiness_gate.py \
  services/runner/tests/test_execution_smoke.py \
  services/runner/tests/test_execution_substrate_audit.py \
  -q

# Route/surface evidence grep
grep -R -n "product/iterations" services/task_intake/src/task_intake/server.py | head -5
grep -R -n "ProductIteration" services/task_intake/src/task_intake/product_iteration_surface.py 2>/dev/null || true

# No-resurrection grep
test -f services/task_intake/src/task_intake/decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"
test -f services/task_intake/tests/test_decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"

# Stable .ariadne residue check
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `product_iteration_surface.py` (new), `test_product_iteration_surface.py` (new), `server.py` (modified HTML/JS)
- **behavior drift**: browser wiring for session capture + signal submission; PR 0117 backend unchanged
- **surface object-shape drift**: all surface contract fields match the PLAN.md definitions
- **PR 0117 backend drift**: `product_iteration.py`, `test_product_iteration.py`, `app.py` — NOT modified
- **backlog-mutation drift**: no backlog files written or modified
- **decision-history mutation drift**: no decision files written or modified
- **decision execution drift**: no action dispatched
- **external analytics drift**: no network calls except same-origin `/product/iterations`
- **closed-track drift**: PR framed as product iteration substrate/surface, not reopened UX track
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no autonomous behavior
- **dirty-tree residue drift**: no `.ariadne/` residue after validation
- **old-name resurrection drift**: `decision_trace.py` and `test_decision_trace.py` must NOT exist

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- product iteration session capture surface only ✓
- PR 0117 backend contract preserved unchanged ✓
- no external analytics ✓
- same-origin `/product/iterations` only ✓
- no provider/network/Docker/shell/git behavior ✓
- no backlog/decision mutation ✓
- no decision execution ✓
- no hidden reasoning/full transcript/unbounded text capture ✓
- no personal data beyond explicit operator note ✓
- no ROADMAP/schema/doc/agent/dependency changes ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of `decision_trace.py` or `test_decision_trace.py` ✓
- not standalone frontend-only — surface module + tests present ✓
- PR 0115/0116/0117 artifacts not modified ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0119-product-iteration-session-capture-surface`
- Block if roadmap alignment section is missing — PASS: included
- Block if exact architect sign-off phrase is missing — PASS: `экран тайм, product, итерации.` recorded
- Block if plan is framed as reopening Local Interaction UX Track — PASS: explicitly distinguished
- Block if plan is frontend-only with no surface contract/tests — PASS: surface module + tests planned
- Block if plan changes PR 0117 backend contract without justification — PASS: PR 0117 unchanged by default
- Block if external analytics/provider/network/Docker/shell/git runtime behavior allowed — PASS: excluded
- Block if hidden reasoning, full transcript, or unbounded raw text capture allowed — PASS: excluded
- Block if backlog/decision mutation allowed — PASS: excluded
- Block if PR 0115/0116/0117 artifacts modified — PASS: excluded
- Block if `decision_trace.py` or `test_decision_trace.py` resurrected — PASS: explicitly forbidden
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations missing — PASS: included
