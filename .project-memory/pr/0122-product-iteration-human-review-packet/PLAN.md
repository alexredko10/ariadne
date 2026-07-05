# PR 0122 — Product Iteration Human Review Packet Plan

## Summary

Add a deterministic local Product Iteration Human Review Packet layer that composes PR 0117 (product iteration signal store), PR 0120 (evidence summary), and PR 0121 (recommendation candidate) into one coherent human-readable review packet. The packet is read-only advisory: it assembles recorded signals, derived summary, and candidate recommendation into a deterministic markdown and JSON packet for human review. No mutation, no backlog creation, no decision execution, no AI/provider summarization. Optional read-only route `GET /product/iterations/review-packet`.

## Drift assessment against ROADMAP

- PR 0120 and PR 0121 were intentionally small substrate steps (summary + candidate).
- PR 0122 must be larger: it composes store + summary + candidate into one human review packet.
- PR 0122 must not create another isolated helper-only module. This must be a complete, coherent surface.
- PR 0122 must not mutate backlog or decisions.
- PR 0122 is still inside the product iteration substrate/surface because it prepares human review from captured local evidence without executing decisions.

**Slowdown assessment**: PR 0122 is a natural composition/consolidation step after three small substrate PRs (0120, 0121, and earlier 0119/0117). It does not slow the sequence — it is the expected synthesis step.

## PR 0121 merge verification

| Check | Result |
|-------|--------|
| `services/task_intake/src/task_intake/product_iteration_candidate.py` exists | PRESENT ✓ |
| `services/task_intake/tests/test_product_iteration_candidate.py` exists | PRESENT ✓ |
| `.project-memory/pr/0121-product-iteration-recommendation-candidate/reviews/precommit-review.yml` exists, verdict pass | PRESENT ✓ |
| `ProductIterationCandidate` in runtime | CONFIRMED ✓ |
| `build_product_iteration_candidate` in runtime | CONFIRMED ✓ |
| Reason codes `high_idle_ratio`, `low_active_ratio`, `insufficient_evidence` | CONFIRMED ✓ |
| PR 0121 preserved PR 0117/0119/0120 contracts | CONFIRMED ✓ (server.py, app.py, product_iteration.py etc. unchanged) |

PR 0121 is fully present on current branch. PR 0122 proceeds.

## Product purpose

Ariadne now has a complete product iteration pipeline: capture → store (PR 0117) → session surface (PR 0119) → evidence summary (PR 0120) → recommendation candidate (PR 0121). The next step is to compose all four into a single human review packet that a product operator can read, evaluate, and use to make an informed iteration decision. The packet combines raw signals, aggregate summary, advisory candidate, and deterministic serialized output. No execution, no mutation, no AI — pure read-only evidence compilation.

## Roadmap alignment

* roadmap track: architect-approved product iteration substrate/surface
* expected PR slot: PR 0122
* why this PR is next: PR 0120 and PR 0121 were intentionally small substrate steps (summary + candidate). PR 0122 composes store + summary + candidate into one coherent human review packet. This is the synthesis step that makes the captured evidence visible and actionable for human product decisions.
* batching policy check: review packet module + focused tests + optional read-only route form one coherent composition PR. ADR 0011 allows batching related read-only composition with its test suite.
* drift heuristic check: adds a read-only composition module that reuses four existing contracts; no mutation; no AI/provider; optional read-only route only.
* architect sign-off required: inherited from PR 0119 direction
* architect sign-off reference: `экран тайм, product, итерации.`

## Why this is not reopened Local Interaction UX Track

- Pure backend composition of existing contracts — no new UI panels, no new forms, no browser widgets
- Optional route is read-only API, not a frontend feature
- No analytics SDK, no network calls, no external data export
- No mutation of any existing store or record
- PR 0117, PR 0119, PR 0120, PR 0121 all preserved unchanged

## Existing contract inventory from PR 0117, PR 0119, PR 0120, and PR 0121

| Component | PR | Role for review packet |
|-----------|----|------------------------|
| `record_product_iteration_signal()` | 0117 | Store write (not called) |
| `list_product_iteration_signals()` | 0117 | Read records for the packet |
| `ProductIterationRecord` | 0117 | Record shape (included in packet highlights) |
| `build_product_iteration_summary_from_store()` | 0120 | Produce summary for the packet |
| `ProductIterationSummaryData` | 0120 | Summary data (included in packet) |
| `build_product_iteration_candidate_from_store()` | 0121 | Produce candidate for the packet |
| `ProductIterationCandidate` | 0121 | Candidate shape (included in packet) |
| `record_session_signal()` | 0119 | Surface capture (not called) |
| `POST /product/iterations` | 0117 | Write endpoint (not modified) |
| `GET /product/iterations` | 0117 | Read endpoint (not modified) |

PR 0117, PR 0119, PR 0120, and PR 0121 contracts are preserved unchanged.

## Proposed human review packet contract

### New module

`services/task_intake/src/task_intake/product_iteration_review_packet.py`

Contains:
- `ProductIterationReviewPacketInput` — input dataclass
- `ProductIterationReviewPacket` — the review packet dataclass
- `ProductIterationReviewPacketResult` — operation result
- `ProductIterationReviewPacketStatus` — status enum: `ready`, `empty`, `rejected`
- `build_product_iteration_review_packet()` — main composition function
- `render_product_iteration_review_packet_text()` — deterministic plain-text serialization
- `render_product_iteration_review_packet_markdown()` — deterministic markdown serialization
- Stable reason codes for path validation, empty store, etc.

### Review packet shape

```python
@dataclasses.dataclass(frozen=True)
class ProductIterationReviewPacket:
    packet_ref: str                        # deterministic SHA256[:16] of all composed data
    packet_status: str                     # "ready" | "empty" | "rejected"
    generated_from: str                    # store path
    summary: ProductIterationSummaryData | None
    candidate_ref: str | None
    candidate_status: str | None
    priority: str | None
    confidence: str | None
    reason_codes: tuple[str, ...]
    recommended_focus: str | None
    human_review_required: bool
    evidence_counts: dict[str, int]
    evidence_highlights: dict[str, int]    # same as evidence_counts (subset)
    recommended_human_questions: tuple[str, ...]
    decision_options: tuple[str, ...]
    safety_boundaries: tuple[str, ...]
    validation_notes: tuple[str, ...]
    record_count: int
    session_count: int
    markdown_text: str                     # deterministic markdown serialization
    plain_text: str                        # deterministic plain-text serialization
```

### Decision options (advisory labels only)

```python
_DECISION_OPTIONS: tuple[str, ...] = (
    "accept_for_manual_planning",
    "reject_candidate",
    "defer_until_more_evidence",
    "request_more_local_testing",
)
```

The packet must not execute these options. They are advisory labels for human consideration only.

### Recommended human questions (derived from reason codes)

```python
_RECOMMENDED_QUESTIONS: dict[str, str] = {
    "high_idle_ratio": "What caused the high idle time? Are there UI friction points or workflow pauses?",
    "low_active_ratio": "Why is active usage low? Does the task need better guidance?",
    "high_confusion_signal_count": "What specific interactions triggered confusion signals? Can we review them with the operator?",
    "feedback_present": "Has the feedback been reviewed? Are there actionable insights?",
    "human_notes_present": "Have the human iteration notes been reviewed for product ideas?",
    "long_screen_time_without_refs": "Why did the operator spend a long time without running tasks?",
    "healthy_usage_signal": "The current approach appears healthy. Is there anything to improve?",
    "insufficient_evidence": "Is there enough evidence to make a product decision, or should more data be collected?",
    "no_records_yet": "No product iteration records exist. Should session capture be started?",
}
```

### Safety boundaries

```python
_SAFETY_BOUNDARIES: tuple[str, ...] = (
    "This packet is read-only advisory. It does not modify any Ariadne state.",
    "Decision options in this packet are advisory labels only. They are not executed.",
    "No AI or LLM was used to generate this packet. All content is deterministic.",
    "No external analytics or telemetry are included.",
    "All data is local to this Ariadne instance.",
    "No personal data is included beyond explicit operator notes.",
    "No hidden reasoning or full transcripts are captured.",
    "This packet is not a replacement for human product judgment.",
)
```

### `build_product_iteration_review_packet()` function

```python
def build_product_iteration_review_packet(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: str | None = None,
    max_results: int = 1000,
) -> ProductIterationReviewPacketResult:
```

Algorithm:
1. Build summary via `build_product_iteration_summary_from_store(store_dir, session_ref, max_results)`
2. Build candidate via `build_product_iteration_candidate_from_store(store_dir, session_ref, max_results)`
3. If both empty → `"empty"` status with empty packet
4. If either rejected → `"rejected"` with combined reason codes
5. Compose packet data from summary and candidate
6. Derive `recommended_human_questions` from triggered reason codes
7. Generate `markdown_text` and `plain_text` via renderers
8. Generate deterministic `packet_ref` from SHA256 of all composed fields
9. Return `ProductIterationReviewPacketResult`

### Optional read-only route

`GET /product/iterations/review-packet` — returns JSON review packet.

Route behavior: read-only, same-origin, local-only. If added, the route is registered in `app.py` `_ROUTES` for `--check --json` visibility.

## Packet rendering / serialization contract

### Markdown serialization

Deterministic markdown with sections:
- `# Product Iteration Review Packet`
- `## Summary` — total records, session count, screen-time aggregates
- `## Recommendation` — priority, confidence, reason codes, focus
- `## Evidence Details` — evidence_counts, evidence_highlights
- `## Recommended Human Questions`
- `## Decision Options` (advisory)
- `## Safety Boundaries`
- `## Validation Notes`
- Generated at bottom with timestamp and version

### Plain-text serialization

Same content as markdown but without markdown formatting. Simple line-based format.

### Serialization rules

- No raw full transcript
- No hidden reasoning
- No unbounded raw text
- All fields bounded and deterministic
- `sort_keys=True` for JSON in snapshots
- `ensure_ascii=False` for Unicode

## Human decision boundary

The packet is advisory only. It must not:
- Create backlog items
- Mutate decisions
- Mutate product iteration records
- Mutate `.ariadne`
- Execute decision options
- Call providers or network
- Use AI/LLM summarization

## Proposed files

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/product_iteration_review_packet.py` | NEW |
| `services/task_intake/tests/test_product_iteration_review_packet.py` | NEW |
| `services/task_intake/src/task_intake/server.py` | Modified ONLY if route is added (default: optional) |
| `services/task_intake/src/task_intake/app.py` | Modified ONLY if route is added and `_ROUTES` must be updated |

PR 0117, PR 0119, PR 0120, and PR 0121 files must remain unchanged:
- `product_iteration.py`, `product_iteration_surface.py`, `product_iteration_summary.py`, `product_iteration_candidate.py` — NOT modified
- `test_product_iteration.py`, `test_product_iteration_surface.py`, `test_product_iteration_summary.py`, `test_product_iteration_candidate.py` — NOT modified

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py` — must not be created
- `services/task_intake/tests/test_decision_trace.py` — must not be created
- Any file under `.project-memory/pr/0115-*/`, `.project-memory/pr/0116-*/`, `.project-memory/pr/0117-*/`, `.project-memory/pr/0119-*/`, `.project-memory/pr/0120-*/`, `.project-memory/pr/0121-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`, `.project-memory/post-0100/`

## Privacy/local-only boundary

- No external analytics. No third-party telemetry.
- No network calls. No provider calls. No AI/LLM.
- No Docker. No shell subprocess. No git runtime behavior.
- No personal data beyond existing explicit operator notes.
- No hidden reasoning capture. No full transcript capture.
- No mutation of product iteration records, backlog items, decision history, or trace data.
- No decision execution.

## Non-Goals

- No external analytics/telemetry
- No AI/provider/LLM summarization — deterministic composition only
- No network/provider/Docker/shell/git runtime behavior
- No hidden reasoning or full transcript capture
- No personal data collection beyond existing explicit notes
- No mutation of product iteration, backlog, decision, or trace data
- No decision execution
- No backlog item creation
- No PR 0117/0119/0120/0121 artifact modifications
- No ROADMAP/docs/schema/agent/dependency changes
- No resurrection of `decision_trace.py` or `test_decision_trace.py`
- No standalone frontend-only widget
- No isolated helper-only — this PR composes four existing contracts into one coherent surface

## Implementation steps

1. Create `product_iteration_review_packet.py` with:
   - All object shapes (input, packet, result, status)
   - `build_product_iteration_review_packet()` — composes summary + candidate
   - `render_product_iteration_review_packet_text()` — plain-text serialization
   - `render_product_iteration_review_packet_markdown()` — markdown serialization
   - Deterministic `packet_ref` generation
   - Advisory decision options, recommended questions, safety boundaries
   - All stable reason codes

2. Create `test_product_iteration_review_packet.py` with focused tests.

3. (Optional, if route justified) Add `GET /product/iterations/review-packet` in `server.py` and register in `app.py` `_ROUTES`.

## Test plan

| Class | Focus |
|-------|-------|
| `TestEmptyStore` | No records → `"empty"` status |
| `TestMissingStore` | Missing store → `"rejected"` |
| `TestFullPacket` | Complete store → `"ready"` with all fields present |
| `TestPacketRefDeterministic` | Same store → same packet_ref |
| `TestPacketComposition` | Summary + candidate fields correctly composed |
| `TestReasonCodesInPacket` | Reason codes propagated from candidate |
| `TestDecisionOptions` | Advisory decision options present |
| `TestRecommendedQuestions` | Questions derived from reason codes |
| `TestSafetyBoundaries` | Safety boundaries present in packet |
| `TestMarkdownRendering` | Markdown serialization produces valid output |
| `TestPlainTextRendering` | Plain-text serialization produces valid output |
| `TestMarkdownDeterministic` | Same input → same markdown |
| `TestPlainTextDeterministic` | Same input → same plain text |
| `TestNoHiddenReasoning` | No hidden reasoning in rendered output |
| `TestNoFullTranscript` | No full transcript in rendered output |
| `TestNoUnboundedText` | All text fields bounded |
| `TestNoWrites` | Packet does not write any files |
| `TestNoMutation` | Product iteration records not modified |
| `TestNoBacklogMutation` | Backlog store not modified |
| `TestNoDecisionMutation` | Decision store not modified |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |
| `TestOldNamesNotResurrected` | Old file names do not exist |
| `TestRouteWorks` | (If route added) GET route returns valid response |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_review_packet.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_product_iteration_candidate.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_backlog_trace_summary.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_product_iteration_review_packet.py \
  services/task_intake/tests/test_product_iteration.py \
  services/task_intake/tests/test_product_iteration_surface.py \
  services/task_intake/tests/test_product_iteration_summary.py \
  services/task_intake/tests/test_product_iteration_candidate.py \
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

# Packet grep evidence
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "ProductIterationReviewPacket|build_product_iteration_review_packet|render_product_iteration_review_packet|accept_for_manual_planning|defer_until_more_evidence" services/task_intake/src/task_intake/product_iteration_review_packet.py services/task_intake/tests/test_product_iteration_review_packet.py 2>/dev/null || true

# Route check (if route added)
grep -R -n "product/iterations/review-packet" services/task_intake/src/task_intake/server.py 2>/dev/null

# No-resurrection grep
test -f services/task_intake/src/task_intake/decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"
test -f services/task_intake/tests/test_decision_trace.py && echo "RESURRECTED" || echo "NOT RESURRECTED"

# Stable .ariadne residue check
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `product_iteration_review_packet.py` (new), `test_product_iteration_review_packet.py` (new); `server.py` and `app.py` ONLY if route added
- **behavior drift**: `build_product_iteration_review_packet()` composes existing contracts read-only; no mutation
- **packet object-shape drift**: all packet fields match the PLAN.md definitions
- **PR 0117/0119/0120/0121 backend drift**: all four existing contracts preserved unchanged
- **backlog-mutation drift**: no backlog files written or modified
- **decision-history mutation drift**: no decision files written or modified
- **decision execution drift**: no action dispatched
- **AI/provider summarization drift**: deterministic composition only
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no autonomous behavior, no backlog creation, no scoring authority
- **dirty-tree residue drift**: no `.ariadne/` residue after validation
- **old-name resurrection drift**: `decision_trace.py` and `test_decision_trace.py` must NOT exist
- **slowdown/isolated-helper drift**: PR is a coherent composition of 4 contracts, not an isolated helper

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- product iteration human review packet only ✓
- composes PR 0117 + PR 0120 + PR 0121, not an isolated helper ✓
- read-only advisory; no mutation ✓
- no backlog item creation ✓
- decision options are advisory labels only ✓
- no decision execution ✓
- no AI/provider/LLM summarization ✓
- no external analytics/network/Docker/shell/git ✓
- no hidden reasoning/full transcript/unbounded text ✓
- no ROADMAP/schema/doc/agent/dependency changes ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of `decision_trace.py` or `test_decision_trace.py` ✓
- PR 0117, PR 0119, PR 0120, PR 0121 contracts preserved unchanged ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0122-product-iteration-human-review-packet`
- Block if PR 0121 evidence is missing on current branch — PASS: all checks passed
- Block if roadmap alignment section is missing — PASS: included
- Block if exact architect sign-off phrase is missing — PASS: recorded
- Block if plan is framed as reopening Local Interaction UX Track — PASS: explicitly distinguished
- Block if plan is frontend-only — PASS: backend-only composition module
- Block if plan creates another isolated helper-only PR — PASS: composes 4 existing contracts
- Block if plan creates backlog items or mutates backlog — PASS: advisory only
- Block if plan mutates decisions or executes decision options — PASS: advisory labels only
- Block if plan mutates product iteration source records — PASS: read-only
- Block if plan introduces provider/AI summarization — PASS: deterministic composition
- Block if plan introduces external analytics/network/Docker/shell/git — PASS: excluded
- Block if plan captures hidden reasoning, full transcripts, or unbounded raw text — PASS: excluded
- Block if plan modifies PR 0117/0119/0120/0121 artifacts — PASS: excluded
- Block if plan modifies PR 0117/0119/0120/0121 contracts without justification — PASS: preserved
- Block if plan resurrects `decision_trace.py` or `test_decision_trace.py` — PASS: explicitly forbidden
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations missing — PASS: included
