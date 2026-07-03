# PR 0117 — Product Iteration Signal Contract / Local Screen-Time Record Plan

## Summary

Add a local product iteration signal contract for Ariadne: a deterministic, bounded, privacy-preserving local store at `.ariadne/product-iterations/` for operator screen-time and session evidence. Backend-first: new module (`product_iteration.py`), two REST endpoints (`POST /product/iterations`, `GET /product/iterations`), and focused tests. No external analytics, no network, no mutation of existing backlog/decision/trace data.

## Product purpose

Ariadne now has backlog, human decisions, decision history, decision-to-backlog trace summary, and the task_intake HTML page already collects confusion signals, feedback notes, and session reports in client-side JS. The next product step is to persist these signals as local evidence for product iteration decisions. Screen-time, session refs, confusion signals, feedback, and run refs must become local iteration evidence — not external analytics.

## Roadmap alignment

* roadmap track: architect-approved product iteration substrate
* expected PR slot: PR 0117
* why this PR is next: The task_intake HTML page already collects confusion signals, feedback, session reports, and run history in client-side JS arrays with no backend persistence. PR 0117 adds the local store/API contract to persist these as bounded deterministic evidence, connecting operator usage to future product iteration decisions. This follows the decision-to-backlog trace summary (PR 0115–0116) which completed the decision/backlog evidence chain.
* batching policy check: backend store/write + read-back endpoint + focused tests + minimal UI/wire if batched — one coherent backend-first PR. ADR 0011 allows batching related store+read operations.
* drift heuristic check: adds a new dedicated local store and two endpoints; no mutation of existing stores; no frontend-only work; no external analytics.
* architect sign-off required: yes
* architect sign-off reference: `экран тайм, product, итерации.`

## Why this is not closed-track UX work

- No frontend-only widget or screen-time popup
- No browser analytics SDK integration
- No external telemetry
- Backend store contract (`product_iteration.py` module, bounded local path, deterministic JSON records, no network)
- REST API endpoints (`POST /product/iterations`, `GET /product/iterations`) — backend-first
- Any HTML/JS changes are strictly limited to driving data into the backend contract, not UI feature work
- This is a product iteration substrate PR, explicitly approved by the architect despite the closed Local Interaction UX Track

## Existing evidence inventory

| Feature | PR | Persistence | Client-side |
|---------|----|-------------|-------------|
| Confusion signals | 0115+ | None (JS array only) | `__ariadne_confusion_signals[]` with type/note/timestamp |
| Feedback notes | 0115+ | None (textarea value) | `feedback_notes` textarea |
| Session report | 0115+ | None (JS generated, copied) | `generateSessionReport()` → markdown |
| Run history | 0111+ | In-memory visible | Displayed via `/runs` HTML |
| Screen time | None | None | Not tracked |
| Decision trace | 0115 | `.ariadne/backlog/` + `.ariadne/decisions/` | Trace endpoint |
| Decision history | 0113 | `.ariadne/decisions/` | History endpoint |

## Backend/store/API contract

### New module

`services/task_intake/src/task_intake/product_iteration.py`

Contains:
- `ProductIterationInput` — input dataclass
- `ProductIterationRecord` — record dataclass (persisted shape)
- `ProductIterationResult` — result dataclass
- `ProductIterationStatus` — status enum: `recorded`, `empty`, `rejected`
- `record_product_iteration_signal()` — validates input, generates deterministic `iteration_ref`, writes JSON to `.ariadne/product-iterations/{ref}.json`
- `list_product_iteration_signals()` — reads from `.ariadne/product-iterations/`, returns sorted list with optional `session_ref` filter
- Stable reason codes for bounded path rejection, missing fields, hidden reasoning rejection, etc.

### Endpoints

| Method | Path | Input | Output |
|--------|------|-------|--------|
| `POST /product/iterations` | Create signal | JSON `ProductIterationInput` body | JSON `ProductIterationResult` |
| `GET /product/iterations` | List signals | Optional `session_ref` query param | JSON list |

### Server module

`services/task_intake/src/task_intake/server.py` — modified to add the two routes.

### App module

`services/task_intake/src/task_intake/app.py` — only if `--check --json` needs to verify the new routes are registered. Default: no change.

## Product signal record shape

```python
@dataclasses.dataclass(frozen=True)
class ProductIterationInput:
    session_ref: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    screen_time_seconds: int = 0
    active_time_seconds: int = 0
    idle_time_seconds: int = 0
    run_refs: tuple[str, ...] = ()
    feedback_refs: tuple[str, ...] = ()
    confusion_refs: tuple[str, ...] = ()
    report_refs: tuple[str, ...] = ()
    decision_trace_refs: tuple[str, ...] = ()
    human_iteration_note: str = ""
    source_surface: str = "task_intake"

@dataclasses.dataclass(frozen=True)
class ProductIterationRecord:
    iteration_ref: str                   # deterministic SHA256[:16] of canonical JSON
    session_ref: str
    started_at: str | None
    ended_at: str | None
    screen_time_seconds: int
    active_time_seconds: int
    idle_time_seconds: int
    run_refs: tuple[str, ...]
    feedback_refs: tuple[str, ...]
    confusion_refs: tuple[str, ...]
    report_refs: tuple[str, ...]
    decision_trace_refs: tuple[str, ...]
    human_iteration_note: str
    product_signal_status: str           # "recorded" | "draft" | "rejected"
    created_at: None                     # deterministic; no wall-clock time
    source_surface: str
    schema_version: str = "1"
```

## Local store path

`.ariadne/product-iterations/` — each record written as `{iteration_ref}.json`.

## Privacy/local-only boundary

- No external analytics. All data stays in `.ariadne/product-iterations/`.
- No network calls. No provider calls. No Docker. No shell subprocess.
- No personal data beyond explicit `human_iteration_note` field.
- No hidden reasoning capture. No raw full page transcript capture.
- No mutation of backlog items, decision history, or trace data.
- No decision execution.

## Non-Goals

- No external analytics or telemetry
- No network/provider/LLM/Docker/shell/git behavior
- No hidden reasoning capture
- No raw full page transcript capture
- No personal data collection beyond explicit operator note
- No mutation of backlog items, decision records, or trace data
- No decision execution
- No PR 0115/0116 artifact changes
- No ROADMAP/docs/schema/agent/dependency changes
- No resurrection of `decision_trace.py` or `test_decision_trace.py`
- No frontend-only changes without backend store contract
- No closed Local Interaction UX Track reopening

## Allowed files

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/product_iteration.py` | NEW |
| `services/task_intake/tests/test_product_iteration.py` | NEW |
| `services/task_intake/src/task_intake/server.py` | MODIFIED — add `POST /product/iterations`, `GET /product/iterations` |
| `services/task_intake/src/task_intake/app.py` | MODIFIED only if needed for `--check --json` route visibility |

Optional (batched with backend contract): minimal HTML/JS in `server.py` to wire confusion signals/submit button to `POST /product/iterations`.

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py`
- `services/task_intake/tests/test_decision_trace.py`
- Any file under `.project-memory/pr/0115-*/` or `.project-memory/pr/0116-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`, `.project-memory/post-0100/`

## Implementation steps

1. Create `product_iteration.py` with all object shapes, stable reason codes, `record_product_iteration_signal()`, and `list_product_iteration_signals()`
2. Add `POST /product/iterations` and `GET /product/iterations` routes in `server.py`
3. Create `test_product_iteration.py` with focused tests
4. (Optional) Add minimal JS in `server.py` to submit confusion signals and session data to `POST /product/iterations` on session end

## Test plan

| Class | Focus |
|-------|-------|
| `TestValidSignal` | Valid input → `"recorded"` status |
| `TestMissingFields` | Missing required fields → `"rejected"` |
| `TestDeterministicRef` | Same input → same `iteration_ref` |
| `TestEmptyStore` | No signals → `"empty"` |
| `TestMissingStore` | Missing `.ariadne/` → `"rejected"` |
| `TestUnboundedPath` | Path with `..` → `"rejected"` |
| `TestRecordFields` | Record includes all required fields |
| `TestReadBack` | Read after write matches |
| `TestNoWritesOutside` | Only product-iterations files written |
| `TestRunRefs` | Run refs stored and returned |
| `TestConfusionRefs` | Confusion refs stored and returned |
| `TestFeedbackRefs` | Feedback refs stored and returned |
| `TestReportRefs` | Report refs stored and returned |
| `TestDecisionTraceRefs` | Decision trace refs stored and returned |
| `TestHumanIterationNote` | Human note stored and returned |
| `TestSourceSurface` | Source surface stored |
| `TestFilterBySessionRef` | GET with `session_ref` filter works |
| `TestOrdering` | Items sorted deterministically |
| `TestNoHiddenReasoning` | Hidden reasoning in note → rejected |
| `TestNoBacklogMutation` | Backlog store not modified |
| `TestNoDecisionMutation` | Decision store not modified |
| `TestNoAriadneResidue` | Uses `tmp_path`, no `.ariadne/` residue |
| `TestProductName` | Docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names/examples |
| `TestServerPostRoute` | POST route returns valid JSON |
| `TestServerGetRoute` | GET route returns valid JSON |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_backlog_trace_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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

# Check no resurrection of obsolete PR 0115 file names
test -f services/task_intake/src/task_intake/decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"
test -f services/task_intake/tests/test_decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"

git status --short
find .ariadne -maxdepth 5 -type f | sort 2>/dev/null || true
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `product_iteration.py` (new), `test_product_iteration.py` (new), `server.py` (modified for routes)
- **behavior drift**: `record_product_iteration_signal()` and `list_product_iteration_signals()` only; no mutation of backlog/decision/trace stores
- **signal object-shape drift**: all fields match the PLAN.md definitions
- **backlog-mutation drift**: no backlog files written or modified
- **decision-history mutation drift**: no decision files written or modified
- **decision execution drift**: no action dispatched
- **external analytics drift**: no network calls, no provider calls, no analytics SDKs
- **local API drift**: POST/GET return JSON; no frontend-only changes
- **runner/task_intake boundary drift**: no changes to runner source
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no autonomous behavior, no scoring/ranking/authority
- **dirty-tree residue drift**: no `.ariadne/` residue after validation
- **PR 0115/0116 drift**: no changes to PR 0115 or PR 0116 artifacts
- **old-name resurrection drift**: `decision_trace.py` and `test_decision_trace.py` must NOT exist
- **closed-track drift**: PR framed as product iteration substrate, not reopened UX track

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- product iteration substrate only ✓
- not reopened Local Interaction UX Track ✓
- no external analytics ✓
- no network/provider/Docker/shell/git behavior ✓
- no backlog mutation ✓
- no decision mutation ✓
- no decision execution ✓
- no hidden reasoning capture ✓
- no raw full page transcript capture ✓
- no personal data beyond explicit operator note ✓
- no ROADMAP/schema/doc/agent/dependency changes ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of `decision_trace.py` or `test_decision_trace.py` ✓
- no frontend-only changes without backend store contract ✓
- PR 0115/0116 artifacts not modified ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0117-local-product-iteration-signal-contract`
- Block if ROADMAP alignment section is missing — PASS: included
- Block if exact architect sign-off phrase is missing — PASS: `экран тайм, product, итерации.` recorded
- Block if plan is framed as reopened Local Interaction UX Track — PASS: explicitly distinguished
- Block if backend/store/API/test contract is not explicit — PASS: explicit
- Block if plan is frontend-only — PASS: backend-first
- Block if external analytics/network/provider/Docker/shell/git runtime behavior allowed — PASS: excluded
- Block if backlog/decision mutation allowed — PASS: read/write only to own store
- Block if PR 0115/0116 artifacts modified — PASS: excluded
- Block if `decision_trace.py` or `test_decision_trace.py` resurrected — PASS: explicitly forbidden
- Block if hidden reasoning capture or raw page transcript capture — PASS: excluded
- Block if `.ariadne/` residue left in repo root — PASS: tmp_path
- Block if non-semantic placeholder strings required — PASS: none
