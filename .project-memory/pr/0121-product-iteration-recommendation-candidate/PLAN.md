# PR 0121 — Product Iteration Recommendation Candidate Plan

## Summary

Add a deterministic local Product Iteration Recommendation Candidate layer on top of PR 0120 evidence summary. Derive advisory recommendation candidates from `ProductIterationSummaryData` using deterministic thresholds and reason-code rules. The candidate is read-only advisory — it does not create backlog items, mutate decisions, mutate product iteration records, call providers, use AI, or introduce analytics. No UI, no route (default). Small module with focused tests.

## PR 0120 merge verification

| Check | Result |
|-------|--------|
| `services/task_intake/src/task_intake/product_iteration_summary.py` exists | PRESENT ✓ |
| `services/task_intake/tests/test_product_iteration_summary.py` exists | PRESENT ✓ |
| `.project-memory/pr/0120-product-iteration-evidence-summary/reviews/precommit-review.yml` exists | PRESENT ✓ |
| `ProductIterationSummaryData` in runtime | CONFIRMED ✓ |
| `build_product_iteration_summary` in runtime | CONFIRMED ✓ |
| `total_screen_time_seconds` in summary data | CONFIRMED ✓ |
| `active_ratio` in summary data | CONFIRMED ✓ |
| `idle_ratio` in summary data | CONFIRMED ✓ |
| `records_with_human_note_count` in summary data | CONFIRMED ✓ |

PR 0120 is fully present on current branch. PR 0121 proceeds.

## Product purpose

Ariadne now has a complete product iteration evidence pipeline: capture (PR 0117 → PR 0119) → summary (PR 0120). The next step is to derive deterministic advisory recommendation candidates from the summary so a human can decide the next product iteration. The candidate uses hard-coded thresholds and reason codes to produce deterministic suggestions like "high idle ratio suggests UI friction" or "confusion signals detected — consider review". Pure advisory — no execution, no mutation, no AI.

## Roadmap alignment

* roadmap track: architect-approved product iteration substrate/surface
* expected PR slot: PR 0121
* why this PR is next: PR 0120 produces deterministic summaries. PR 0121 derives advisory candidates from those summaries using threshold-based rules. This completes the evidence pipeline from capture → summary → recommendation candidate.
* batching policy check: candidate module + focused tests form one coherent backend-only PR. ADR 0011 allows batching related read-only derivation with its test suite.
* drift heuristic check: adds a read-only advisory candidate module; no mutation of any record; no provider/AI; no frontend; no route.
* architect sign-off required: inherited from PR 0119 direction
* architect sign-off reference: `экран тайм, product, итерации.`

## Why this is not reopened Local Interaction UX Track

- Pure backend deterministic rule application — no UI, no route, no analytics
- No mutation of any existing store or record
- No provider/AI summarization — strictly deterministic threshold rules
- No external network, no analytics
- PR 0117, PR 0119, PR 0120 contracts unchanged

## Existing contract inventory from PR 0117, PR 0119, and PR 0120

| Component | PR | Role for candidate |
|-----------|----|-------------------|
| `ProductIterationInput` | 0117 | — (not used) |
| `ProductIterationRecord` | 0117 | — (not used) |
| `ProductIterationResult` | 0117 | — (not used) |
| `record_product_iteration_signal()` | 0117 | — (not called) |
| `list_product_iteration_signals()` | 0117 | — (not called) |
| `.ariadne/product-iterations/` | 0117 | — (not read directly) |
| `ProductIterationSummaryData` | 0120 | Input to candidate derivation |
| `ProductIterationSummaryResult` | 0120 | — (not directly used) |
| `build_product_iteration_summary()` | 0120 | — (candidate reads summary data directly) |
| `build_product_iteration_summary_from_store()` | 0120 | Convenience — may be reused to produce summary for candidate |
| `record_session_signal()` | 0119 | — (not used) |
| `POST /product/iterations` | 0117 | — (not modified) |
| `GET /product/iterations` | 0117 | — (not modified) |

PR 0117, PR 0119, and PR 0120 contracts are preserved unchanged.

## Proposed recommendation candidate contract

### New module

`services/task_intake/src/task_intake/product_iteration_candidate.py`

Contains:
- `ProductIterationCandidate` — the recommendation candidate dataclass
- `ProductIterationCandidateResult` — operation result
- `ProductIterationCandidateStatus` — status enum: `ready`, `empty`, `rejected`
- `build_product_iteration_candidate()` — main function that takes a `ProductIterationSummaryData` and returns candidate(s)
- `build_product_iteration_candidate_from_store()` — convenience that calls `build_product_iteration_summary_from_store()` then `build_product_iteration_candidate()`
- Deterministic reason-code constants
- Threshold constants (all hard-coded, test-covered)

### Recommendation candidate shape

```python
@dataclasses.dataclass(frozen=True)
class ProductIterationCandidate:
    candidate_ref: str                        # deterministic SHA256[:16] of summary hash + rules version
    candidate_status: str                     # "recommended" | "no_recommendation" | "insufficient_evidence"
    priority: str                             # "high" | "medium" | "low" | "none"
    confidence: str                           # "high" | "medium" | "low"
    reason_codes: tuple[str, ...]
    summary_snapshot: str                     # JSON snapshot of the summary data that produced this candidate
    recommended_focus: str                    # human-readable focus area
    human_review_required: bool
    evidence_counts: dict[str, int]           # key summary metrics
    explanation_lines: tuple[str, ...]        # human-readable explanation
```

### Stable reason codes

| Constant | Value | Trigger |
|----------|-------|---------|
| `RC_NO_RECORDS_YET` | `"no_records_yet"` | `total_records == 0` |
| `RC_HIGH_IDLE_RATIO` | `"high_idle_ratio"` | `idle_ratio > 0.5` |
| `RC_LOW_ACTIVE_RATIO` | `"low_active_ratio"` | `active_ratio < 0.2` |
| `RC_HIGH_CONFUSION_SIGNAL_COUNT` | `"high_confusion_signal_count"` | `confusion_refs_count >= 3` |
| `RC_FEEDBACK_PRESENT` | `"feedback_present"` | `feedback_refs_count > 0` |
| `RC_HUMAN_NOTES_PRESENT` | `"human_notes_present"` | `records_with_human_note_count > 0` |
| `RC_LONG_SCREEN_TIME_WITHOUT_REFS` | `"long_screen_time_without_refs"` | `total_screen_time_seconds > 3600` and `run_refs_count == 0` |
| `RC_HEALTHY_USAGE_SIGNAL` | `"healthy_usage_signal"` | `active_ratio >= 0.5` and `idle_ratio <= 0.3` and `confusion_refs_count == 0` |
| `RC_INSUFFICIENT_EVIDENCE` | `"insufficient_evidence"` | `total_records < 3` and no other strong signals |

### Threshold constants

```python
HIGH_IDLE_RATIO_THRESHOLD = 0.5
LOW_ACTIVE_RATIO_THRESHOLD = 0.2
HIGH_CONFUSION_SIGNAL_THRESHOLD = 3
LONG_SCREEN_TIME_THRESHOLD_SECONDS = 3600
HEALTHY_ACTIVE_RATIO_THRESHOLD = 0.5
HEALTHY_IDLE_RATIO_MAX = 0.3
INSUFFICIENT_EVIDENCE_RECORDS = 3
RULES_VERSION = "1"
```

### `build_product_iteration_candidate()` function

```python
def build_product_iteration_candidate(
    summary: ProductIterationSummaryData,
) -> ProductIterationCandidateResult:
```

Algorithm:
1. Check `summary.total_records`
2. Apply each reason-code rule against summary fields
3. If `no_records_yet`: return `"insufficient_evidence"` with `priority="none"`
4. If `insufficient_evidence` and no strong signals: return `"insufficient_evidence"` with `priority="low"`
5. Otherwise derive `priority`, `confidence`, `recommended_focus` from the most significant reason code
6. Build `explanation_lines` — one line per triggered reason code
7. Generate deterministic `candidate_ref` from SHA256 of summary+reason_codes+rules_version
8. Return `ProductIterationCandidateResult`

### `build_product_iteration_candidate_from_store()` convenience

```python
def build_product_iteration_candidate_from_store(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: str | None = None,
    max_results: int = 1000,
) -> ProductIterationCandidateResult:
```

## Proposed files

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/product_iteration_candidate.py` | NEW |
| `services/task_intake/tests/test_product_iteration_candidate.py` | NEW |

PR 0117, PR 0119, and PR 0120 files must remain unchanged:
- `product_iteration.py`, `test_product_iteration.py` — NOT modified
- `product_iteration_surface.py`, `test_product_iteration_surface.py` — NOT modified
- `product_iteration_summary.py`, `test_product_iteration_summary.py` — NOT modified
- `server.py`, `app.py` — NOT modified (no route unless explicitly justified)

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py` — must not be created
- `services/task_intake/tests/test_decision_trace.py` — must not be created
- Any file under `.project-memory/pr/0115-*/`, `.project-memory/pr/0116-*/`, `.project-memory/pr/0117-*/`, `.project-memory/pr/0119-*/`, `.project-memory/pr/0120-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`, `.project-memory/post-0100/`

## Privacy/local-only boundary

- No external analytics. No third-party telemetry.
- No network calls. No provider calls. No AI/LLM.
- No Docker. No shell subprocess. No git runtime behavior.
- No personal data in candidate output — only aggregate summary metrics.
- No hidden reasoning capture. No full transcript capture.
- No mutation of product iteration records, backlog items, decision history, or trace data.
- No decision execution.

## Non-Goals

- No external analytics/telemetry
- No AI/provider summarization — deterministic rules only
- No network/provider/Docker/shell/git runtime behavior
- No hidden reasoning or full transcript capture
- No personal data collection beyond existing summary aggregates
- No mutation of product iteration, backlog, decision, or trace data
- No decision execution
- No backlog item creation
- No PR 0117/0119/0120 artifact modifications
- No ROADMAP/docs/schema/agent/dependency changes
- No resurrection of `decision_trace.py` or `test_decision_trace.py`
- No standalone frontend-only widget
- No UI, no route (default)

## Implementation steps

1. Create `product_iteration_candidate.py` with:
   - `ProductIterationCandidate`, `ProductIterationCandidateResult`, `ProductIterationCandidateStatus`
   - All stable reason-code constants and threshold constants
   - `build_product_iteration_candidate()` — deterministic rule engine
   - `build_product_iteration_candidate_from_store()` — convenience
   - Deterministic `candidate_ref` generation
   - All thresholds covered by tests

2. Create `test_product_iteration_candidate.py` with focused tests.

## Test plan

| Class | Focus |
|-------|-------|
| `TestNoRecords` | Empty summary → `"insufficient_evidence"` with `rc=no_records_yet` |
| `TestHighIdleRatio` | High idle ratio → `"recommended"` with `rc=high_idle_ratio` |
| `TestLowActiveRatio` | Low active ratio → `"recommended"` with `rc=low_active_ratio` |
| `TestHighConfusionSignals` | Many confusion refs → `"recommended"` with `rc=high_confusion_signal_count` |
| `TestFeedbackPresent` | Feedback refs present → `"recommended"` with `rc=feedback_present` |
| `TestHumanNotesPresent` | Human notes present → `"recommended"` with `rc=human_notes_present` |
| `TestLongScreenTimeWithoutRefs` | Long screen time + no run refs → `rc=long_screen_time_without_refs` |
| `TestHealthyUsage` | Good ratios + no confusion → `"recommended"` with `rc=healthy_usage_signal` |
| `TestInsufficientEvidence` | Few records + no strong signals → `rc=insufficient_evidence` |
| `TestMultipleReasonCodes` | Multiple triggers → multiple reason codes |
| `TestPriorityDerivation` | Priority matches the most significant reason code |
| `TestConfidenceDerivation` | Confidence matches rule strictness |
| `TestDeterministicRef` | Same summary → same candidate_ref |
| `TestDeterministicRepeats` | Same summary → same output (no randomness) |
| `TestNoWrites` | Candidate does not write any files |
| `TestNoMutation` | Product iteration records not modified |
| `TestNoBacklogMutation` | Backlog store not modified |
| `TestNoDecisionMutation` | Decision store not modified |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |
| `TestOldNamesNotResurrected` | Old file names do not exist |
| `TestFromStoreConvenience` | `build_product_iteration_candidate_from_store()` works with real store |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_candidate.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_backlog_trace_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_product_iteration_candidate.py \
  services/task_intake/tests/test_product_iteration.py \
  services/task_intake/tests/test_product_iteration_surface.py \
  services/task_intake/tests/test_product_iteration_summary.py \
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

# Candidate grep evidence
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "ProductIterationCandidate|build_product_iteration_candidate|HIGH_IDLE_RATIO_THRESHOLD|LOW_ACTIVE_RATIO_THRESHOLD" services/task_intake/src/task_intake/product_iteration_candidate.py services/task_intake/tests/test_product_iteration_candidate.py 2>/dev/null || true

# No-resurrection grep
test -f services/task_intake/src/task_intake/decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"
test -f services/task_intake/tests/test_decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"

# Stable .ariadne residue check
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `product_iteration_candidate.py` (new), `test_product_iteration_candidate.py` (new)
- **behavior drift**: `build_product_iteration_candidate()` is read-only advisory; no mutation
- **candidate object-shape drift**: all candidate fields match the PLAN.md definitions
- **PR 0117/0119/0120 backend drift**: `product_iteration.py`, `product_iteration_surface.py`, `product_iteration_summary.py`, `server.py`, `app.py` — NOT modified
- **backlog-mutation drift**: no backlog files written or modified
- **decision-history mutation drift**: no decision files written or modified
- **decision execution drift**: no action dispatched
- **AI/provider summarization drift**: deterministic threshold rules only
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no autonomous behavior, no backlog creation, no scoring authority
- **dirty-tree residue drift**: no `.ariadne/` residue after validation
- **old-name resurrection drift**: `decision_trace.py` and `test_decision_trace.py` must NOT exist

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- product iteration recommendation candidate only ✓
- read-only advisory; no mutation ✓
- deterministic rules; no AI/provider ✓
- no external analytics ✓
- no provider/network/Docker/shell/git behavior ✓
- no backlog/decision mutation ✓
- no decision execution ✓
- no backlog item creation ✓
- no hidden reasoning/full transcript/unbounded text capture ✓
- no ROADMAP/schema/doc/agent/dependency changes ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of `decision_trace.py` or `test_decision_trace.py` ✓
- PR 0117, PR 0119, PR 0120 contracts preserved unchanged ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0121-product-iteration-recommendation-candidate`
- Block if PR 0120 evidence is missing on current branch — PASS: all checks passed
- Block if roadmap alignment section is missing — PASS: included
- Block if exact architect sign-off phrase is missing — PASS: recorded
- Block if plan is framed as reopening Local Interaction UX Track — PASS: explicitly distinguished
- Block if plan is frontend-only — PASS: backend-only candidate module
- Block if plan creates backlog items or mutates decisions/source records — PASS: read-only advisory
- Block if plan introduces provider/AI summarization — PASS: deterministic rules only
- Block if plan introduces external analytics/network/Docker/shell/git — PASS: excluded
- Block if plan captures hidden reasoning, full transcripts, or unbounded raw text — PASS: excluded
- Block if plan modifies PR 0117/0119/0120 artifacts — PASS: excluded
- Block if plan modifies PR 0117/0119/0120 contracts without explicit justification — PASS: preserved
- Block if plan resurrects `decision_trace.py` or `test_decision_trace.py` — PASS: explicitly forbidden
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations missing — PASS: included
