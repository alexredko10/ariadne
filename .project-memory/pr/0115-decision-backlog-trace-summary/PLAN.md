# PR 0115 — Decision-to-Backlog Trace Summary / Read-Only Evidence Map Plan

## Summary

Add a deterministic read-only decision-to-backlog trace summary that composes existing Ariadne runtime objects (backlog items from PR 0109–0110, decision records from PR 0112, decision history items from PR 0113) into a local evidence map. The trace summary answers: which backlog item is being considered, which human decisions refer to it, which evidence refs support those decisions, which agent actions are blocked, and what the next safe human action is. Read-only, no mutation, no execution.

## Background / Predecessor Evidence

| PR | Description | Status |
|----|-------------|--------|
| 0109 | Self-improvement backlog store / local queue | precommit-review.yml present ✓ |
| 0110 | Read-only backlog surfacing | precommit-review.yml present ✓ |
| 0111 | Local human review backlog view | precommit-review.yml present ✓ |
| 0112 | Human backlog decision intake | precommit-review.yml MISSING (out of scope) |
| 0113 | Human decision history surface | precommit-review.yml present ✓ (backfilled by PR 0114) |
| 0114 | PR 0113 precommit evidence backfill (repair PR) | Complete — PLAN.md, plan-review.yml, precommit-review.yml all present ✓ |

The evidence chain for PR 0113 is now complete (backfilled by PR 0114). PR 0112 precommit-review is still missing but does not block PR 0115 — the PR 0112 runtime code (`backlog_decision.py`) exists and PR 0113 depends on it, so the chain is functionally continuous for composition purposes.

## Current Runtime Inventory

### Runtime files present and verified

| File | PR | Role for trace |
|------|----|----------------|
| `services/task_intake/src/task_intake/decision_history.py` | 0113 | Provides `DecisionHistoryItem`, `DecisionHistoryInput`, `load_decision_history()` — import shapes and/or call for decision data |
| `services/task_intake/tests/test_decision_history.py` | 0113 | 36 tests covering empty/missing/valid/ordering/filters/no-writes |
| `services/task_intake/src/task_intake/backlog_decision.py` | 0112 | Provides `BacklogDecisionType`, `BacklogDecisionInput`, `BacklogDecisionRecord` — import types for validation |
| `services/task_intake/tests/test_backlog_decision.py` | 0112 | Write-path tests (not needed) |
| `services/task_intake/src/task_intake/backlog_review.py` | 0111 | Provides `BacklogReviewInput`, `build_backlog_review_json()` — potential data source for backlog item shape |
| `services/task_intake/src/task_intake/server.py` | 0113 | ASGI app with existing GET/POST routes for backlog, decision, decision history — extend with trace route |
| `services/task_intake/src/task_intake/app.py` | — | App entry point — may add check path if needed |
| `services/runner/src/runner/backlog_surface.py` | 0110 | Provides `BacklogSurfaceInput`, `list_backlog_items()` or similar — potential reader for backlog store |
| `services/runner/src/runner/improvement_backlog.py` | 0109 | Provides `ImprovementBacklogItem`, `_FORBIDDEN_HIDDEN_REASONING_PATTERNS`, `_FORBIDDEN_ACTION_PATTERNS` — shapes and validation patterns |
| `services/runner/src/runner/improvement_candidate.py` | — | Candidate shapes — may read for candidate_ref resolution |
| `services/runner/src/runner/proof_ref.py` | — | Proof ref shapes — may read for evidence ref resolution |
| `services/runner/src/runner/gate_evidence.py` | — | Gate evidence shapes — evidence ref shape |

### Key existing object shapes for trace composition

**`DecisionHistoryItem`** (from `decision_history.py`):
- `decision_ref`, `backlog_item_ref`, `candidate_ref`, `continuity_ref`, `evidence_refs: tuple[str]`, `human_actor`, `decision_type`, `decision_reason`, `next_human_action`, `blocked_agent_actions: tuple[str]`, `created_at`, `product_name`, `source_surface`, `requires_human_review: bool`, `decision_record_path`, `linked_backlog_item_status`, `schema_version`

**`BacklogDecisionType`** (from `backlog_decision.py`):
- `NEEDS_MORE_EVIDENCE`, `DEFER`, `DISMISS`, `CANDIDATE_FOR_FUTURE_PR`, `ACCEPT_FOR_HUMAN_PLANNING`

**`BacklogDecisionRecord`** (from `backlog_decision.py`):
- `decision_ref`, `backlog_item_ref`, `decision_type`, `human_actor`, `decision_reason`, `evidence_refs`, `next_human_action`, `candidate_ref`, `continuity_ref`, `created_at`

## Goal

Implement a read-only decision-to-backlog trace summary that:

1. Reads backlog items from `.ariadne/backlog/` (via `backlog_surface` or direct read)
2. Reads decision records from `.ariadne/decisions/` (via `decision_history` or direct read)
3. Links decision records to backlog items by `backlog_item_ref`
4. Surfaces blocked agent actions and next safe human action
5. Surfaces missing/malformed/duplicate/unsupported trace states
6. Provides deterministic ordering and summary counts
7. Exposes through a local HTTP endpoint: `GET /backlog/decision/trace`
8. Leaves no `.ariadne/` residue

## Non-Goals

- No mutation of backlog items or decision records
- No decision execution
- No gate approval or finalization
- No scoring, ranking, or authority over decisions
- No provider, network, Docker, shell, or LLM calls
- No git mutation, commits, or PR creation
- No autonomous repair or code changes
- No ROADMAP, schema, dependency, or doc changes
- No resurrection of PR 0114 trace-summary planning directory (`.project-memory/pr/0114-decision-backlog-trace-summary/`)
- No modification of PR 0113 evidence artifacts
- No broad refactors or unrelated cleanup
- No historical trace (past snapshots) — current state only

## Proposed User-Visible Behavior

A local HTTP endpoint `GET /backlog/decision/trace` returns:

```json
{
  "status": "ready",
  "traces": [
    {
      "backlog_item": {
        "backlog_item_ref": "backlog-item-abc123",
        "backlog_status": "pending",
        "backlog_category": "self_improvement",
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456"
      },
      "decisions": [
        {
          "decision_ref": "a1b2c3d4e5f6...",
          "decision_type": "defer",
          "decision_reason": "Need more evidence",
          "human_actor": "human-reviewer-001",
          "created_at": null,
          "evidence_refs": ["pr-001", "capture-abc"],
          "next_human_action": "Gather more evidence",
          "blocked_agent_actions": []
        }
      ],
      "evidence_refs": ["pr-001", "capture-abc"],
      "missing_evidence_refs": [],
      "blocked_agent_actions": [],
      "next_safe_human_action": "Gather more evidence",
      "trace_status": "complete",
      "trace_warnings": [],
      "requires_human_review": false
    }
  ],
  "untraced_decisions": [],
  "summary": {
    "total_backlog_items": 3,
    "traced_backlog_items": 2,
    "backlog_items_without_decisions": 1,
    "total_decisions": 4,
    "decisions_without_backlog_item": 0,
    "total_evidence_refs": 6,
    "unresolved_traces": 0,
    "invalid_decision_records": 0,
    "human_review_required": 1
  }
}
```

## Proposed Runtime Shape

### New module

`services/task_intake/src/task_intake/decision_trace.py`

Contains:
- `DecisionTraceInput` — input dataclass
- `DecisionTraceBacklogItem` — backlog item in trace context
- `DecisionTraceDecision` — decision record in trace context  
- `DecisionTraceItem` — a single trace (backlog item + linked decisions)
- `DecisionTraceSummary` — summary counts
- `DecisionTraceResult` — top-level result
- `DecisionTraceStatus` — status enum: `ready`, `empty`, `partial`, `rejected`
- `build_decision_trace()` — main function
- Stable reason codes (re-used from `decision_history.py` where applicable)

### Modified module

`services/task_intake/src/task_intake/server.py` — add `GET /backlog/decision/trace` route

### Not modified

- `decision_history.py` — imported as read-only adapter only
- `backlog_decision.py` — imported types only
- `backlog_review.py` — not modified
- `backlog_surface.py` — not modified (direct store read preferred)
- `improvement_backlog.py` — not modified
- `app.py` — may add check path; default: not modified

## Proposed Files

### Implementation

| File | Action |
|------|--------|
| `services/task_intake/src/task_intake/decision_trace.py` | NEW |
| `services/task_intake/src/task_intake/server.py` | MODIFIED — add route |

### Tests

| File | Action |
|------|--------|
| `services/task_intake/tests/test_decision_trace.py` | NEW — focused trace tests |

## Trace Summary Object Shape

### `DecisionTraceInput` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceInput:
    backlog_store_dir: str = ".ariadne/backlog"
    decision_store_dir: str = ".ariadne/decisions"
    max_traces: int = 50
    backlog_item_ref: str | None = None
    include_backlog_items_without_decisions: bool = False
    sort_by: str = "backlog_item_ref"
    sort_descending: bool = False
```

### `DecisionTraceBacklogItem` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceBacklogItem:
    backlog_item_ref: str
    backlog_status: str
    backlog_category: str | None = None
    candidate_ref: str | None = None
    continuity_ref: str | None = None
```

### `DecisionTraceDecision` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceDecision:
    decision_ref: str
    decision_type: str
    decision_reason: str
    human_actor: str
    created_at: str | None = None
    evidence_refs: tuple[str, ...] = ()
    next_human_action: str = ""
    blocked_agent_actions: tuple[str, ...] = ()
    source_surface: str = ""
    requires_human_review: bool = False
```

### `DecisionTraceItem` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceItem:
    backlog_item: DecisionTraceBacklogItem
    decisions: tuple[DecisionTraceDecision, ...]
    decision_refs: tuple[str, ...]
    latest_decision_ref: str | None = None
    latest_decision_type: str | None = None
    evidence_refs: tuple[str, ...]
    missing_evidence_refs: tuple[str, ...]
    blocked_agent_actions: tuple[str, ...]
    next_safe_human_action: str = ""
    trace_status: str
    trace_warnings: tuple[str, ...]
    requires_human_review: bool = False
```

### `DecisionTraceSummary` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceSummary:
    total_backlog_items: int
    traced_backlog_items: int
    backlog_items_without_decisions: int
    total_decisions: int
    decisions_without_backlog_item: int
    total_evidence_refs: int
    unresolved_traces: int
    invalid_decision_records: int
    human_review_required: int
```

### `DecisionTraceResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionTraceResult:
    status: str
    reason_codes: tuple[str, ...] = ()
    traces: tuple[DecisionTraceItem, ...] = ()
    untraced_decisions: tuple[DecisionTraceDecision, ...] = ()
    summary: DecisionTraceSummary | None = None
    details: str | None = None
```

### `DecisionTraceStatus` (enum)

```python
class DecisionTraceStatus(str, enum.Enum):
    READY = "ready"
    EMPTY = "empty"
    PARTIAL = "partial"
    REJECTED = "rejected"
```

### Trace status values per item

| Status | Meaning |
|--------|---------|
| `"complete"` | Backlog item exists with decisions that have evidence refs |
| `"partial"` | Backlog item exists with decisions but some evidence refs missing |
| `"no_decisions"` | Backlog item exists with no matching decisions |
| `"invalid_backlog"` | Backlog item JSON is malformed |

## Read-Only Contract

The trace summary must:

- Read backlog items from `.ariadne/backlog/` — bounded path, no `..` traversal
- Read decision records from `.ariadne/decisions/` — bounded path, no `..` traversal
- Link decision records to backlog items by `backlog_item_ref`
- Never write to `.ariadne/` or any filesystem path
- Never execute decisions or dispatch actions
- Never accept/archive/reject/approve/finalize
- Never call providers, network, Docker, shell
- Never mutate git state
- Use `tmp_path` in tests — no `.ariadne/` residue in repo root

## Implementation Steps

1. Create `decision_trace.py` with all object shapes and `build_decision_trace()`
2. Add `GET /backlog/decision/trace` route in `server.py`
3. Create `test_decision_trace.py` with focused tests

The implementation must:

- Read backlog items via direct `.ariadne/backlog/` JSON file enumeration (keep backend-agnostic; don't require `backlog_surface` import)
- Read decision records via `decision_history.load_decision_history()` or direct `.ariadne/decisions/` JSON enumeration — PLAN.md preference: reuse `load_decision_history()` as it provides validated, sorted decision items
- Join on `backlog_item_ref`
- Compute trace_status per item based on decision presence and evidence completeness
- Surface untraced decisions (decisions referencing unknown backlog items)
- Sort by selected field (default `backlog_item_ref`)
- Cap at `max_traces`
- Compute summary

## Testing Plan

### Required test classes

| Class | Focus |
|-------|-------|
| `TestEmptyStores` | Empty backlog + empty decisions → `"empty"` status |
| `TestMissingBacklogStore` | Missing backlog store → `"rejected"` |
| `TestMissingDecisionStore` | Missing decision store → `"rejected"` |
| `TestNoDecisions` | Backlog items with no decisions → items with `"no_decisions"` status (if `include_backlog_items_without_decisions` is True) |
| `TestBasicTrace` | Valid backlog item + matching decision → `"ready"` with linked trace |
| `TestUntracedDecisions` | Decision referencing unknown backlog item → surfaced in `untraced_decisions` |
| `TestOrdering` | Deterministic ordering by `backlog_item_ref`, latest decision created_at |
| `TestSummaryCounts` | All 9 summary fields correct |
| `TestItemFields` | All required fields exposed |
| `TestMalformedBacklogItem` | Malformed backlog JSON handled without crash |
| `TestMalformedDecisionRecord` | Malformed decision record handled without crash |
| `TestDuplicateBacklogRef` | Duplicate backlog ref handled deterministically |
| `TestDuplicateDecisionRef` | Duplicate decision ref handled deterministically |
| `TestMissingEvidenceRefs` | Missing evidence refs surfaced in `missing_evidence_refs` |
| `TestTraceStatus` | `"complete"`, `"partial"`, `"no_decisions"`, `"invalid_backlog"` all tested |
| `TestNoFilesystemWrites` | Confirms trace does not write any files |
| `TestNoMutationFields` | No archive/accept/reject/approve/finalize fields |
| `TestUnboundedPath` | Unbounded store paths rejected |
| `TestOversizedTrace` | Oversized trace truncated with warning |
| `TestAriadneResidue` | Uses `tmp_path`, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names/examples |
| `TestOptionalFilter` | Filter by `backlog_item_ref` works |
| `TestDecisionHistoryNotModified` | Confirm `decision_history.py` behavior unchanged |

## Validation Commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_trace.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q

PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_decision_trace.py \
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

git status --short
find .ariadne -maxdepth 5 -type f | sort 2>/dev/null || true
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `decision_trace.py` (new), `server.py` (modified), `test_decision_trace.py` (new) changed
- **behavior drift**: `build_decision_trace()` is read-only; no mutation, no execution
- **trace object-shape drift**: all dataclass fields match the PLAN.md definitions
- **decision-history mutation drift**: `decision_history.py` not modified
- **backlog mutation drift**: no backlog files written or modified
- **decision execution drift**: no action dispatched from trace
- **local UI/API drift**: `GET /backlog/decision/trace` returns JSON; no HTML/frontend
- **runner/task_intake boundary drift**: no changes to runner source
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no scoring/ranking/authority/autonomous behavior
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- read-only trace summary only ✓
- no decision execution ✓
- no backlog mutation ✓
- no decision-history mutation ✓
- no provider/network/Docker/shell/git mutation ✓
- no ROADMAP/schema/dependency/doc/agent changes unless explicitly planned ✓
- no `.ariadne/` residue after validation ✓
- no resurrection of abandoned PR 0114 trace-summary planning directory ✓
- no resurrection of PR 0114 repair work ✓
- no rewriting of PR 0113 evidence artifacts ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The `.ariadne/` directory may appear temporarily if tests write to the default `.ariadne/backlog/` or `.ariadne/decisions/` paths — but the plan requires tests to use `tmp_path` exclusively. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Risks

| Risk | Mitigation |
|------|------------|
| PR 0112 precommit evidence missing | Not a blocker — PR 0112 runtime code exists and is functionally verified through PR 0113 |
| `decision_history.py` API changes | PLAN.md specifies `load_decision_history()` import only; no source modification |
| Backlog store format changes | Direct JSON file read keeps trace backend-agnostic |
| `.ariadne/` residue during test development | `tmp_path` requirement enforced; dirty-tree check in validation |
| Trace object shape drifts from plan | PLAN DRIFT GATE in precommit-review catches shape drift |

## Stop Conditions

- Block if PR 0113 implementation (`decision_history.py`) does not exist — PASS: confirmed
- Block if PR 0113 precommit evidence is absent — PASS: backfilled by PR 0114
- Block if `backlog_decision.py` does not exist — PASS: confirmed
- Block if trace summary mutates decision records — VERIFIED: read-only design
- Block if trace summary mutates backlog records — VERIFIED: read-only design
- Block if trace summary executes decisions — VERIFIED: no dispatch
- Block if trace summary introduces scoring/ranking/authority — VERIFIED: explicitly excluded
- Block if trace summary duplicates PR 0113 without adding trace value — VERIFIED: adds backlog linking, evidence ref resolution, trace_status, cross-reference summary
- Block if implementation requires provider/network/Docker/shell/LLM — VERIFIED: none
- Block if implementation modifies ROADMAP/schema/dependency/doc/agent — VERIFIED: not planned
- Block if forbidden legacy names/examples introduced — VERIFIED: excluded
- Block if non-semantic placeholder strings required — VERIFIED: none
- Block if `.ariadne/` residue left in repo root — VERIFIED: tmp_path used
- Block if abandoned PR 0114 trace-summary directory resurrected — VERIFIED: `.project-memory/pr/0114-decision-backlog-trace-summary/` must not be written to
- Block if PR 0113 evidence artifacts rewritten — VERIFIED: not modified
- Block if PR 0114 repair work resurrected — VERIFIED: PR 0115 is runtime feature, not repair
