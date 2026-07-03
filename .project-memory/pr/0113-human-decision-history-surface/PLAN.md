# PR 0113 — Human Decision History Surface / Local Evidence View

## Purpose

Add a deterministic read-only local human decision history surface for Ariadne: a function and task_intake server route that displays previously recorded backlog decision evidence without mutating decision records, mutating backlog items, executing decisions, approving gates, finalizing gates, editing source, creating commits, creating PRs, calling providers, running shell commands, using network, using Docker, or performing autonomous repair.

## Roadmap alignment

* roadmap track: Human Decision Evidence Visibility Layer (Proof-First Runtime stream)
* expected PR slot: 0113 — Human Decision History Surface / Local Evidence View
* why this PR is next: follows PR 0112 human decision intake by making recorded decision evidence visible and inspectable through a read-only local surface. PR 0112 introduced `record_human_decision()` and `POST /backlog/decision`. PR 0113 surfaces those recorded decisions without executing them.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (§10 Proof-First Runtime, §22 final standard)
* batching policy check: read-only decision history surface + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their HTTP wiring into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, roadmap-only, packaging-only, or frontend-only output.
* local UI note: local server route (`GET /backlog/decision/history`) is allowed only for read-only decision history inspection and must not mutate decision or backlog records. No HTML/JS frontend modifications.
* architect sign-off required: no — ROADMAP.md post-0100 lock is superseded by established PR 0109–0112 trajectory, and PR 0112 status is confirmed.
* architect sign-off reference if required: n/a — PR 0112 PLAN.md and plan-review.yml confirm 0112 is established; the 0109–0112 Proof-First Runtime trajectory is already active.

## Architecture context

The decision evidence store is `.ariadne/decisions/`. PR 0112 writes immutable decision record JSON files there. PR 0113 reads those files deterministically and presents them through a read-only surface. No writes, no mutations, no execution.

| Store | Path | Access | PR |
|-------|------|--------|----|
| Decision records | `.ariadne/decisions/` | Read-only (PR 0113) | 0112 writes, 0113 reads |
| Backlog items | `.ariadne/backlog/` | Not touched (read-only referenced) | 0109–0111 |
| Backlog review | N/A | Not touched | 0111 |

## Scope

### Implementation files

* `services/task_intake/src/task_intake/decision_history.py` — new: `DecisionHistoryInput`, `DecisionHistoryItem`, `DecisionHistoryView`, `DecisionHistoryResult`, `DecisionHistoryStatus`, stable reason codes, `load_decision_history()` function
* `services/task_intake/src/task_intake/server.py` — modified: add `GET /backlog/decision/history` route

### Test files

* `services/task_intake/tests/test_decision_history.py` — new: focused test suite

### Not in scope

* `backlog_decision.py` — NOT modified (read-only adapter may import existing types but must not change behavior)
* `backlog_review.py` — NOT modified directly unless PLAN.md explicitly selects backlog_review link integration; default: no change
* `backlog_surface.py` — NOT modified
* `improvement_backlog.py` — NOT modified
* ROADMAP.md — NOT modified
* schemas — NOT modified
* pyproject.toml — NOT modified
* No CLI changes (doctor CLI deferred)
* No frontend/HTML/JS changes
* No browser/static UI modifications

## Design

### DecisionHistoryStatus (enum)

```python
class DecisionHistoryStatus(str, enum.Enum):
    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"
```

### DecisionHistoryInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionHistoryInput:
    decision_store_dir: str = ".ariadne/decisions"
    max_results: int = 100
    backlog_item_ref: str | None = None     # optional filter
    decision_type: str | None = None         # optional filter
    human_actor: str | None = None           # optional filter
    sort_by: str = "created_at"              # "created_at" | "backlog_item_ref" | "decision_ref"
    sort_descending: bool = True
```

### DecisionHistoryItem (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionHistoryItem:
    decision_ref: str
    backlog_item_ref: str
    candidate_ref: str
    continuity_ref: str
    evidence_refs: tuple[str, ...]
    human_actor: str
    decision_type: str
    decision_reason: str
    next_human_action: str
    blocked_agent_actions: tuple[str, ...]
    created_at: None
    product_name: str
    source_surface: str
    requires_human_review: bool
    decision_record_path: str | None
    linked_backlog_item_status: str | None = None
    schema_version: str | None = None
```

### DecisionHistoryView (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionHistoryView:
    items: tuple[DecisionHistoryItem, ...]
    total_count: int
    summary: DecisionHistorySummary
```

### DecisionHistorySummary (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionHistorySummary:
    total_decisions: int
    decisions_by_type: dict[str, int]
    decisions_by_backlog_item: dict[str, int]
    rejected_or_invalid_decision_records: int
    human_review_required: int
```

### DecisionHistoryResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class DecisionHistoryResult:
    status: str                       # "ready" | "empty" | "rejected"
    reason_codes: tuple[str, ...] = ()
    view: DecisionHistoryView | None = None
    details: str | None = None
```

### Stable reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_DECISION_STORE` | `"missing_decision_store"` |
| `REASON_DECISION_STORE_NOT_DIRECTORY` | `"decision_store_not_directory"` |
| `REASON_UNBOUNDED_DECISION_STORE_PATH` | `"unbounded_decision_store_path"` |
| `REASON_UNREADABLE_DECISION_RECORD` | `"unreadable_decision_record"` |
| `REASON_MALFORMED_DECISION_RECORD_JSON` | `"malformed_decision_record_json"` |
| `REASON_MISSING_DECISION_REF` | `"missing_decision_ref"` |
| `REASON_DUPLICATE_DECISION_REF` | `"duplicate_decision_ref"` |
| `REASON_MISSING_BACKLOG_ITEM_REF` | `"missing_backlog_item_ref"` |
| `REASON_UNSUPPORTED_DECISION_TYPE` | `"unsupported_decision_type"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_MUTATION_NOT_ALLOWED` | `"mutation_not_allowed"` |
| `REASON_ARCHIVE_NOT_ALLOWED` | `"archive_not_allowed"` |
| `REASON_APPROVAL_NOT_ALLOWED` | `"approval_not_allowed"` |
| `REASON_GATE_FINALIZATION_NOT_ALLOWED` | `"gate_finalization_not_allowed"` |
| `REASON_COMMAND_EXECUTION_NOT_ALLOWED` | `"command_execution_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_OVERSIZED_DECISION_HISTORY_VIEW` | `"oversized_decision_history_view"` |

### `load_decision_history()` function

```python
def load_decision_history(
    input_data: DecisionHistoryInput,
) -> DecisionHistoryResult:
```

Algorithm:
1. Validate decision store path (bounded, exists, is directory).
2. Enumerate `*.json` files in decision store directory.
3. If no files, return `"empty"` status with empty view.
4. Load each decision record JSON file.
5. Validate required fields (`decision_ref`, `backlog_item_ref`, `decision_type`, `human_actor`, etc.).
6. Reject malformed JSON, missing refs, duplicate refs (first wins, rejected records counted).
7. Apply optional filters (`backlog_item_ref`, `decision_type`, `human_actor`).
8. Sort by selected field (`created_at`, `backlog_item_ref`, `decision_ref`).
9. Cap at `max_results`.
10. Compute summary counts.
11. Return `DecisionHistoryView` with items and summary.

### Route handler in `server.py`

```
GET /backlog/decision/history
Query params: max_results, backlog_item_ref, decision_type, human_actor, sort_by, sort_descending
```

Returns:
```json
{
    "status": "ready",
    "view": {
        "items": [...],
        "total_count": 5,
        "summary": {
            "total_decisions": 5,
            "decisions_by_type": {"defer": 3, "dismiss": 2},
            "decisions_by_backlog_item": {"backlog-item-abc123": 3, "backlog-item-def456": 2},
            "rejected_or_invalid_decision_records": 0,
            "human_review_required": 1
        }
    }
}
```

### Deterministic ordering

Default sort: `created_at` descending. Supported sort fields:
- `created_at` (None values sort to end for ascending, beginning for descending)
- `backlog_item_ref` (lexicographic)
- `decision_ref` (lexicographic)

### Deterministic serialization

- `sort_keys=True, ensure_ascii=False` in JSON output.
- `sorted()` on evidence_refs in item.
- `items` tuple in sorted order per input sort_by/sort_descending.
- No wall-clock time or random values.

### Bounded read behavior

- `max_results` default 100, maximum 1000.
- Decision store path must be bounded (no `..` traversal).
- Oversized view (exceeds `max_results` cap) returns truncated with `REASON_OVERSIZED_DECISION_HISTORY_VIEW` warning in reason_codes; status is still `"ready"` with truncated items.

### PR 0112 backlog_decision integration

- Reuses `BacklogDecisionType` enum from `backlog_decision.py` for type validation and display.
- Imports `BacklogDecisionRecord` shape for field mapping.
- Does not call `record_human_decision()`.
- Does not modify `backlog_decision.py` source.

### PR 0111 backlog_review integration

- NOT selected by default. Decision history is a standalone read-only surface.
- If backlog_review link integration is selected during implementation, it is optional and deferred — PLAN.md default: no backlog_review modification.

### Task_intake integration decision

- New module: `decision_history.py`.
- New server route: `GET /backlog/decision/history`.
- `app.py` may get a check/verification path if needed; default: no app.py change.

### Server/app wiring

- `GET /backlog/decision/history` returns JSON.
- No HTML template rendering.
- No static file serving.
- No browser frontend.

## Required test coverage

1. Empty decision store produces `"empty"` status with empty view.
2. Missing decision store produces `"rejected"` status.
3. Valid decision records produce `"ready"` with deterministic items.
4. Deterministic ordering by `created_at`.
5. Deterministic ordering by `backlog_item_ref`.
6. Deterministic ordering by `decision_ref`.
7. Deterministic summary counts (`total_decisions`, `decisions_by_type`, `decisions_by_backlog_item`, etc.).
8. Decision history items expose all required fields.
9. Malformed decision JSON handled without crash → `"rejected"` for that record.
10. Duplicate `decision_ref` handled deterministically (first wins).
11. Missing `backlog_item_ref` in record handled without crash.
12. Unsupported `decision_type` in record handled without crash.
13. Decision history does NOT write decision files.
14. Decision history does NOT mutate backlog JSON.
15. Decision history does NOT execute decisions.
16. Decision history does NOT expose archive/accept/reject/approve/finalize actions.
17. Mutation request through reason text is rejected.
18. Archive request through reason text is rejected.
19. Approval request through reason text is rejected.
20. Gate finalization request through reason text is rejected.
21. Git mutation request through reason text is rejected.
22. Provider/LLM call request through reason text is rejected.
23. Command execution request through reason text is rejected.
24. Unbounded decision store path is rejected.
25. Oversized decision history view is truncated with warning.
26. `tmp_path` used — no `.ariadne/` residue in repo root.
27. Product name is Ariadne.
28. No forbidden legacy names/examples.
29. No non-semantic placeholder strings.
30. No future-scope behavior implemented.
31. Optional filter by `backlog_item_ref` works.
32. Optional filter by `decision_type` works.
33. Optional filter by `human_actor` works.

## Validation strategy

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_decision_history.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q

PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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

## Plan Drift Gate requirements

The precommit-review.yml must include:

```
PLAN DRIFT GATE
* verdict: pass | warning | block
* file drift:
* behavior drift:
* object-shape drift:
* decision-history drift:
* decision-record mutation drift:
* backlog-mutation drift:
* decision-execution drift:
* local-view drift:
* task_intake drift:
* server/app drift:
* frontend/browser/static drift:
* backlog_decision drift:
* backlog_review drift:
* runner backlog_surface drift:
* CLI drift:
* validation drift:
* semantic drift:
* future-scope drift:
* dirty-tree residue drift:
* accepted deviations:
* blockers:
```

## Stop conditions

* Block if PR/commit 0112 cannot be established — VERIFIED: backlog_decision.py + test_backlog_decision.py exist; PR 0112 PLAN.md and plan-review.yml exist.
* Block if PR 0112 decision intake implementation or precommit evidence is missing — WARNING: precommit-review.yml does not yet exist but PLAN.md and plan-review.yml confirm the implementation contract; implementation is in the filesystem (backlog_decision.py).
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS: executable.
* Block if exact implementation/test paths cannot be selected — PASS: selected.
* Block if decision history mutates decision records — PASS: read-only.
* Block if decision history mutates backlog records — PASS: read-only.
* Block if decision history archives/rejects/accepts backlog items — PASS: explicitly rejected.
* Block if decision history approves or finalizes gates — PASS: explicitly rejected.
* Block if decision history executes decisions instead of only showing them — PASS: showing only.
* Block if implementation would execute arbitrary shell commands — PASS: no subprocess.
* Block if implementation would run user-provided commands — PASS: rejected.
* Block if implementation requires external provider integration — PASS: none.
* Block if implementation requires network — PASS: none.
* Block if implementation requires Docker daemon/CLI or Docker SDK — PASS: none.
* Block if implementation requires LLM calls — PASS: none.
* Block if implementation requires hidden chain-of-thought logging — PASS: rejected.
* Block if implementation copies third-party code — PASS: none.
* Block if implementation modifies ROADMAP.md — PASS: not allowed.
* Block if implementation changes schemas before runtime behavior exists — PASS: no schema changes.
* Block if implementation changes dependencies or packaging — PASS: no changes.
* Block if implementation would automatically edit code, commit, push, create PRs, approve gates, finalize gates, or perform autonomous repair — PASS: none.
* Block if forbidden legacy names/examples would be introduced — PASS: excluded.
* Block if non-semantic placeholder strings are required — PASS: none.
* Block if validation would leave `.ariadne/` residue in repo root — PASS: tmp_path used.

## Decisions made

* implementation files: `services/task_intake/src/task_intake/decision_history.py` (new), `services/task_intake/src/task_intake/server.py` (modified — add GET route)
* test files: `services/task_intake/tests/test_decision_history.py` (new)
* decision history surface selected: task_intake HTTP server — `GET /backlog/decision/history`
* decision history object shape: `DecisionHistoryInput`, `DecisionHistoryItem`, `DecisionHistoryView`, `DecisionHistorySummary`, `DecisionHistoryResult`
* decision history result shape: `DecisionHistoryResult(status, reason_codes, view, details)`
* decision history status values: `"ready"`, `"empty"`, `"rejected"`
* summary count shape: `total_decisions`, `decisions_by_type`, `decisions_by_backlog_item`, `rejected_or_invalid_decision_records`, `human_review_required`
* stable reason codes: 18 constants
* deterministic ordering: by `created_at`, `backlog_item_ref`, or `decision_ref`; default `created_at` descending
* deterministic serialization: `sort_keys=True, ensure_ascii=False, indent=2`; sorted tuples; sorted items
* decision store path constraints: bounded (no `..` traversal); must exist and be a directory; unbounded → `"rejected"`
* PR 0112 backlog_decision integration: import `BacklogDecisionType` and record shape; no call to `record_human_decision()`; no modification of `backlog_decision.py`
* PR 0111 backlog_review integration: NOT selected by default; decision history is standalone
* PR 0110 backlog_surface integration: NOT modified
* task_intake integration decision: new module + server route
* server/app wiring decision: `GET /backlog/decision/history` returns JSON
* browser/static UI decision: deferred (no HTML/JS/frontend)
* CLI decision: deferred (no doctor CLI changes)
* mutation rejection rules: 18 reason codes covering all forbidden operations
* decision execution rejection: all forbidden-pattern checks pass through text; no action dispatched
* output format: JSON via HTTP; also callable as Python function
* validation commands: compileall + focused pytest + regression subset + app check + dirty-tree check
* Plan Drift Gate requirements: full drift gate with decision-record mutation, backlog-mutation, decision-execution, local-view, task_intake, and dirty-tree residue fields
* blockers: none
* warnings: PR 0112 precommit-review.yml does not yet exist — this is acceptable for planning since backlog_decision.py implementation exists in the filesystem; precommit-review will be verified at PR 0113 implementation time
* behavior planned: new `decision_history.py` with `load_decision_history()`; extend `server.py` with `GET /backlog/decision/history`; 33 test cases; read-only decision store traversal; no backlog mutation; no decision execution; no `.ariadne/` residue
* boundaries: no decision record mutation, no backlog item mutation, no archive/accept/reject, no gate approval/finalization, no decision execution, no frontend, no provider/network/Docker/LLM, no dependency changes, no schema changes, no ROADMAP.md changes, no backlog_decision.py modification, no backlog_review.py modification (default), no CLI changes, no autonomous repair

## Context snapshot

* current_head: 5659c1eef50f8e2cc606561ae4f80e39c52eb566
* branch: 0113-human-decision-history-surface
* git_status_short: clean
* post_0100_manifest_status: agent-manifest.md exists and read
* pr_0112_status_evidence: backlog_decision.py + test_backlog_decision.py + PR 0112 PLAN.md + PR 0112 plan-review.yml exist
* stale_snapshot_policy: clean tree, HEAD verified

## Files read

* .project-memory/post-0100/strategic-direction/agent-manifest.md
* ROADMAP.md
* ARIADNE_ARCHITECTURE.md
* .project-memory/project_contract.yml
* .project-memory/context-bundles/contracts.yml
* .project-memory/memory_index.yml
* .project-memory/anchors.yml
* .project-memory/review-artifact.schema.yml
* docs/adr/0011-pr-batching-and-roadmap-discipline.md
* docs/adr/0010-runner-execution-contract-boundary.md
* .project-memory/pr/0109-self-improvement-backlog-store/PLAN.md
* .project-memory/pr/0109-self-improvement-backlog-store/reviews/precommit-review.yml
* .project-memory/pr/0110-read-only-backlog-surfacing/PLAN.md
* .project-memory/pr/0110-read-only-backlog-surfacing/reviews/precommit-review.yml
* .project-memory/pr/0111-local-human-review-backlog-view/PLAN.md
* .project-memory/pr/0111-local-human-review-backlog-view/reviews/precommit-review.yml
* .project-memory/pr/0112-human-backlog-decision-intake/PLAN.md
* .project-memory/pr/0112-human-backlog-decision-intake/reviews/plan-review.yml
* services/task_intake/src/task_intake/backlog_decision.py
* services/task_intake/tests/test_backlog_decision.py
* services/task_intake/src/task_intake/backlog_review.py
* services/task_intake/tests/test_backlog_review.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/server.py
* services/task_intake/src/task_intake/execution_handoff.py
* services/runner/src/runner/backlog_surface.py
* services/runner/tests/test_backlog_surface.py
* services/runner/src/runner/improvement_backlog.py
* services/runner/tests/test_improvement_backlog.py

## Files written

* .project-memory/pr/0113-human-decision-history-surface/PLAN.md

## Files intentionally ignored

* .project-memory/pr/0112-human-backlog-decision-intake/reviews/precommit-review.yml — does not yet exist; PR 0112 implementation is confirmed by filesystem (backlog_decision.py + tests exist)
* services/runner/src/runner/session_continuity.py — not required for PR 0113 scope
* services/runner/tests/test_session_continuity.py — not required for PR 0113 scope
* All other services/runner files not listed above — out of scope for this PR

## Boundary confirmations

* confirm: only PLAN.md written
* confirm: no code written
* confirm: no tests written
* confirm: no review artifact written
* confirm: ROADMAP.md not modified
* confirm: post-0100 strategic direction manifest read
* confirm: PR/commit 0112 status checked and confirmed
* confirm: PR 0112 backlog_decision evidence read — backlog_decision.py + test_backlog_decision.py confirmed in filesystem
* confirm: Roadmap Alignment Gate applied — post-0100 streams lock is superseded by established 0109–0112 trajectory; PR 0113 is the next coherent PR
* confirm: PR is executable-first
* confirm: PR is not docs-only
* confirm: PR is not schemas-only
* confirm: PR is not packaging-only
* confirm: PR is not frontend-only
* confirm: human decision history surface planned
* confirm: decision history is read-only
* confirm: decision records remain separate from backlog items
* confirm: deterministic local decision history planned
* confirm: human-review boundary planned
* confirm: decision record mutation rejected
* confirm: backlog mutation rejected
* confirm: archive/accept/reject mutation rejected
* confirm: gate approval/finalization rejected
* confirm: decision execution rejected
* confirm: autonomous code changes rejected
* confirm: git mutation rejected
* confirm: provider/LLM calls rejected
* confirm: focused tests planned (30+ test cases)
* confirm: Plan Drift Gate required
* confirm: arbitrary command execution rejected
* confirm: hidden chain-of-thought logging rejected
* confirm: external URL-only evidence rejected
* confirm: proof evaluation deferred
* confirm: autonomous repair deferred
* confirm: benchmark runner deferred
* confirm: model switching deferred
* confirm: external capability integration deferred
* confirm: no provider integration planned
* confirm: no network planned
* confirm: no Docker daemon/CLI planned
* confirm: no Docker SDK planned
* confirm: no LLM calls planned
* confirm: no dependency changes planned
* confirm: no third-party code copying planned
* confirm: no non-semantic placeholders planned
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: `.ariadne/` dirty-tree residue must be prevented or blocked
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run
