# PR 0120 — Product Iteration Evidence Summary Plan

## Summary

Add a deterministic local Product Iteration Evidence Summary layer on top of PR 0117 (product iteration signal contract) and PR 0119 (session capture surface). Read existing `.ariadne/product-iterations/` records and derive deterministic read-only aggregates: total screen-time, active/idle ratios, session counts, refs histogram, and rejection/empty handling. No mutation of product iteration records, no backlog/decision mutation, no external analytics, no AI/provider summarization.

## PR 0119 merge verification

| Check | Result |
|-------|--------|
| `services/task_intake/src/task_intake/product_iteration_surface.py` exists | PRESENT ✓ |
| `services/task_intake/tests/test_product_iteration_surface.py` exists | PRESENT ✓ |
| `server.py` contains surface wiring (`recordSessionSignal`, `/product/iterations`) | CONFIRMED ✓ |
| PR 0119 project-memory directory exists | PRESENT ✓ |
| PR 0119 precommit-review.yml exists, verdict pass | CONFIRMED ✓ |

PR 0119 is fully present on current branch. PR 0120 proceeds.

## Product purpose

Ariadne now has a complete product iteration signal pipeline: backend store contract (PR 0117) and browser session capture surface (PR 0119). The next step is to derive deterministic evidence summaries from the captured records so that operators and future product decisions can quickly understand usage patterns without reading individual records. The summary is: total captured records, aggregate screen/active/idle time, session distribution, and refs histogram. Read-only, deterministic, local-only.

## Roadmap alignment

* roadmap track: architect-approved product iteration substrate/surface
* expected PR slot: PR 0120
* why this PR is next: PR 0117 created the backend store contract; PR 0119 created the browser capture surface. PR 0120 adds the read-only deterministic evidence summary layer that reads existing records and produces aggregates — completing the product iteration evidence pipeline from capture to digest.
* batching policy check: summary module + focused tests + optional read-only route form one coherent backend-only PR. ADR 0011 allows batching related read-only aggregation with its test suite.
* drift heuristic check: adds a read-only summary module; no mutation of existing records; no external analytics; no frontend-only changes; PR 0117 and PR 0119 contracts preserved.
* architect sign-off required: inherited from PR 0119 direction
* architect sign-off reference: `экран тайм, product, итерации.`

## Why this is not reopened Local Interaction UX Track

- Pure read-only aggregation — no new UI panels, no new buttons, no new forms
- No analytics SDK, no network calls, no external data export
- No mutation of any existing store or record
- PR 0117 and PR 0119 unchanged
- Architect direction (`экран тайм, product, итерации.`) covers the full evidence pipeline from capture through summary

## Existing contract inventory from PR 0117 and PR 0119

| Component | PR | Role for summary |
|-----------|----|------------------|
| `ProductIterationInput` | 0117 | Record input shape |
| `ProductIterationRecord` | 0117 | Persisted record shape (read by summary) |
| `ProductIterationResult` | 0117 | Result shape |
| `ProductIterationStatus` | 0117 | Status enum |
| `record_product_iteration_signal()` | 0117 | Write (not called by summary) |
| `list_product_iteration_signals()` | 0117 | Read (reused for record access) |
| `.ariadne/product-iterations/` | 0117 | Store (read by summary) |
| `POST /product/iterations` | 0117 | Write endpoint (not modified) |
| `GET /product/iterations` | 0117 | Read endpoint (not modified) |
| `product_iteration_surface.py` | 0119 | Browser capture (not touched) |
| `record_session_signal()` | 0119 | Browser capture helper (not touched) |
| PR 0119 precommit evidence | 0119 | PASS — verified |

## Proposed evidence summary contract

### New module

`services/task_intake/src/task_intake/product_iteration_summary.py`

Contains:
- `ProductIterationSummaryInput` — input dataclass (store dir, optional session_ref filter, max_records)
- `ProductIterationSummaryResult` — result dataclass
- `ProductIterationSummaryStatus` — status enum: `ready`, `empty`, `rejected`
- `ProductIterationSummaryData` — the aggregate data dataclass
- `build_product_iteration_summary()` — main function
- Stable reason codes for path validation, empty store, etc.

### Evidence summary shape

```python
@dataclasses.dataclass(frozen=True)
class ProductIterationSummaryData:
    total_records: int
    total_screen_time_seconds: int
    total_active_time_seconds: int
    total_idle_time_seconds: int
    active_ratio: float
    idle_ratio: float
    sessions_count: int
    latest_session_ref: str | None
    run_refs_count: int
    feedback_refs_count: int
    confusion_refs_count: int
    report_refs_count: int
    decision_trace_refs_count: int
    records_with_human_note_count: int
```

Derivation rules:
- `total_*_time_seconds` — sum across all records
- `active_ratio` — `total_active_time_seconds / total_screen_time_seconds` (0 if screen time is 0)
- `idle_ratio` — `total_idle_time_seconds / total_screen_time_seconds` (0 if screen time is 0)
- `sessions_count` — count of distinct `session_ref` values
- `latest_session_ref` — `session_ref` from the most recent record (by `created_at`)
- `*_refs_count` — total count across all `*_refs` tuples (not distinct)
- `records_with_human_note_count` — count of records where `human_iteration_note` is non-empty

### `build_product_iteration_summary()` function

```python
def build_product_iteration_summary(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: str | None = None,
    max_records: int = 1000,
) -> ProductIterationSummaryResult:
```

Algorithm:
1. Validate store path (bounded, exists, is directory)
2. List JSON files in `.ariadne/product-iterations/`
3. If no files, return `"empty"` status with zeroed summary
4. Load records up to `max_records`
5. Filter by optional `session_ref`
6. Compute aggregate sums and counts
7. Return `ProductIterationSummaryResult` with `status: "ready"`

### Optional route

`GET /product/iterations/summary` — returns JSON summary.

Route is optional and only added if the product direction justifies it. Default: keep as Python callable only; defer route to future PR unless explicitly needed.

## Proposed files

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/product_iteration_summary.py` | NEW |
| `services/task_intake/tests/test_product_iteration_summary.py` | NEW |

PR 0117 and PR 0119 files must remain unchanged:
- `services/task_intake/src/task_intake/product_iteration.py` — NOT modified
- `services/task_intake/tests/test_product_iteration.py` — NOT modified
- `services/task_intake/src/task_intake/product_iteration_surface.py` — NOT modified
- `services/task_intake/tests/test_product_iteration_surface.py` — NOT modified
- `services/task_intake/src/task_intake/server.py` — NOT modified (unless route is justified)
- `services/task_intake/src/task_intake/app.py` — NOT modified (unless route is added)

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py` — must not be created
- `services/task_intake/tests/test_decision_trace.py` — must not be created
- Any file under `.project-memory/pr/0115-*/`, `.project-memory/pr/0116-*/`, `.project-memory/pr/0117-*/`, `.project-memory/pr/0119-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`, `.project-memory/post-0100/`

## Privacy/local-only boundary

- No external analytics. No third-party telemetry.
- No network calls. No provider calls. No Docker. No shell subprocess. No git runtime behavior.
- No personal data in summary. No hidden reasoning capture. No full transcript capture.
- No mutation of product iteration records, backlog items, decision history, or trace data.
- No decision execution.

## Non-Goals

- No external analytics or telemetry
- No AI/provider summarization — deterministic aggregation only
- No network/provider/Docker/shell/git runtime behavior
- No hidden reasoning or full transcript capture
- No personal data collection beyond existing records
- No mutation of product iteration, backlog, decision, or trace data
- No decision execution
- No PR 0115/0116/0117/0119 artifact modifications
- No ROADMAP/docs/schema/agent/dependency changes
- No resurrection of `decision_trace.py` or `test_decision_trace.py`
- No standalone frontend-only widget
- No changes to PR 0117 or PR 0119 contracts

## Implementation steps

1. Create `product_iteration_summary.py` with:
   - `ProductIterationSummaryInput`, `ProductIterationSummaryResult`, `ProductIterationSummaryStatus`, `ProductIterationSummaryData`
   - Stable reason codes for path validation errors
   - `build_product_iteration_summary()` — reads records via `list_product_iteration_signals()` or direct store traversal, computes aggregates
   - Deterministic: no wall-clock time, no random values

2. Create `test_product_iteration_summary.py` with focused tests.

3. (Optional, if route justified) Add `GET /product/iterations/summary` in `server.py` and register in `app.py`.

## Test plan

| Class | Focus |
|-------|-------|
| `TestEmptyStore` | No records → `"empty"` with zeroed summary |
| `TestMissingStore` | Missing store → `"rejected"` |
| `TestUnboundedPath` | Path with `..` → `"rejected"` |
| `TestSingleRecord` | One record → correct aggregate values |
| `TestMultipleRecords` | Multiple records → summed aggregates |
| `TestActiveIdleRatios` | Active/idle ratios computed correctly |
| `TestSessionsCount` | Distinct session_ref count |
| `TestLatestSessionRef` | Most recent session_ref by created_at |
| `TestRefsCounts` | All refs histograms correct |
| `TestRecordsWithHumanNote` | Count of records with non-empty human note |
| `TestFilterBySessionRef` | Optional session_ref filter works |
| `TestDeterministicRepeats` | Same input → same output (no randomness) |
| `TestNoWrites` | Summary does not write any files |
| `TestNoMutation` | Product iteration records not modified |
| `TestNoBacklogMutation` | Backlog store not modified |
| `TestNoDecisionMutation` | Decision store not modified |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |
| `TestOldNamesNotResurrected` | `decision_trace.py`, `test_decision_trace.py` do not exist |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_backlog_trace_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_product_iteration_summary.py \
  services/task_intake/tests/test_product_iteration.py \
  services/task_intake/tests/test_product_iteration_surface.py \
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

# No-resurrection grep
test -f services/task_intake/src/task_intake/decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"
test -f services/task_intake/tests/test_decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"

# Stable .ariadne residue check
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `product_iteration_summary.py` (new), `test_product_iteration_summary.py` (new)
- **behavior drift**: `build_product_iteration_summary()` is read-only; no mutation of records
- **summary object-shape drift**: all summary fields match the PLAN.md definitions
- **PR 0117/0119 backend drift**: `product_iteration.py`, `product_iteration_surface.py`, `server.py`, `app.py` — NOT modified
- **backlog-mutation drift**: no backlog files written or modified
- **decision-history mutation drift**: no decision files written or modified
- **decision execution drift**: no action dispatched
- **external analytics drift**: no network calls, no provider calls
- **AI/provider summarization drift**: summary is deterministic aggregation only
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no autonomous behavior
- **dirty-tree residue drift**: no `.ariadne/` residue after validation
- **old-name resurrection drift**: `decision_trace.py` and `test_decision_trace.py` must NOT exist

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- product iteration evidence summary only ✓
- read-only, no mutation ✓
- deterministic aggregation, no AI/provider ✓
- no external analytics ✓
- no provider/network/Docker/shell/git behavior ✓
- no backlog/decision mutation ✓
- no decision execution ✓
- no hidden reasoning/full transcript/unbounded text capture ✓
- no ROADMAP/schema/doc/agent/dependency changes ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of `decision_trace.py` or `test_decision_trace.py` ✓
- PR 0117 and PR 0119 contracts preserved unchanged ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0120-product-iteration-evidence-summary`
- Block if PR 0119 evidence is missing on current branch — PASS: all checks passed
- Block if roadmap alignment section is missing — PASS: included
- Block if exact architect sign-off phrase is missing — PASS: recorded
- Block if plan is framed as reopening Local Interaction UX Track — PASS: explicitly distinguished
- Block if plan is frontend-only — PASS: backend-only summary module
- Block if plan mutates backlog, decisions, or source product iteration records — PASS: read-only
- Block if plan introduces external analytics, providers, network, Docker, shell, git — PASS: excluded
- Block if plan captures hidden reasoning, full transcripts, or unbounded raw text — PASS: excluded
- Block if plan modifies PR 0117/0119 artifacts — PASS: excluded
- Block if plan resurrects `decision_trace.py` or `test_decision_trace.py` — PASS: explicitly forbidden
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations missing — PASS: included
