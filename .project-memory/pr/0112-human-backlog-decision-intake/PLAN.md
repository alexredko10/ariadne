# PR 0112 — Human Backlog Decision Intake

## Purpose

Add a deterministic local human decision intake layer for Ariadne: a function and task_intake server route that records explicit human decisions about backlog items as separate local decision evidence records. The decision intake does NOT mutate backlog items, approve gates, finalize gates, edit code, call providers, or perform autonomous repair.

## Roadmap alignment

* roadmap track: Human-Gated Decision Evidence Layer
* expected PR slot: 0112 — Human Backlog Decision Intake / Local Decision Evidence
* why this PR is next: PR 0109–0111 established backlog storage, read-only surfacing, and a local HTTP review view. PR 0112 lets a human record explicit decisions about backlog items without mutating them, creating evidence of human intent.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md
* batching policy check: human decision intake + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their HTTP wiring into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* local UI note: new POST route in task_intake server, no HTML/JS changes, no frontend framework.
* architect sign-off required: no — ROADMAP.md and PR 0111 status are established.

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md
* ROADMAP.md
* PR 0111 precommit-review.yml — confirms backlog_review fully implemented and merged.

## Architecture context

The backlog item lifecycle is **append-only immutable**. Decisions are recorded as **separate evidence records** in `.ariadne/decisions/` and do NOT mutate the backlog item JSON files in `.ariadne/backlog/`.

| Store | Path | Mutability |
|-------|------|------------|
| Backlog items | `.ariadne/backlog/` | Immutable after enqueue (only status transitions via archive) |
| Decision records | `.ariadne/decisions/` | Append-only (write once, no mutation after creation) |

## Scope

### Implementation files

* `services/task_intake/src/task_intake/backlog_decision.py` — new: `BacklogDecisionInput`, `BacklogDecisionRecord`, `BacklogDecisionResult`, stable reason codes, `record_human_decision()` function
* `services/task_intake/src/task_intake/server.py` — modified: add `POST /backlog/decision` route

### Test files

* `services/task_intake/tests/test_backlog_decision.py` — new: 25+ test cases

### Not in scope

* `backlog_surface.py`, `improvement_backlog.py`, `backlog_review.py` — NOT modified
* ROADMAP.md, schemas, pyproject.toml — NOT modified
* No frontend/HTML/JS changes
* No CLI changes

## Design

### BacklogDecisionType (enum)

```python
class BacklogDecisionType(str, enum.Enum):
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    DEFER = "defer"
    DISMISS = "dismiss"
    CANDIDATE_FOR_FUTURE_PR = "candidate_for_future_pr"
    ACCEPT_FOR_HUMAN_PLANNING = "accept_for_human_planning"
```

### BacklogDecisionInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogDecisionInput:
    backlog_item_ref: str          # Required — ref of the backlog item
    decision_type: str             # BacklogDecisionType value
    human_actor: str               # Human identifier or label
    decision_reason: str           # Free-text reason for the decision
    decision_store_dir: str = ".ariadne/decisions"
    evidence_refs: tuple[str, ...] = ()
    next_human_action: str = ""
    candidate_ref: str = ""
    continuity_ref: str = ""
```

### BacklogDecisionRecord (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogDecisionRecord:
    decision_ref: str              # first 16 hex chars of SHA256(canonical JSON)
    backlog_item_ref: str
    decision_type: str
    human_actor: str
    decision_reason: str
    evidence_refs: tuple[str, ...]
    next_human_action: str
    candidate_ref: str
    continuity_ref: str
    created_at: None               # deterministic; no wall-clock time
```

### BacklogDecisionResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogDecisionResult:
    status: str                    # "recorded" | "rejected" | "duplicate"
    reason_codes: tuple[str, ...] = ()
    decision_record: BacklogDecisionRecord | None = None
    decision_ref: str | None = None
    details: str | None = None
```

### Stable reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_BACKLOG_ITEM_REF` | `"missing_backlog_item_ref"` |
| `REASON_INVALID_DECISION_TYPE` | `"invalid_decision_type"` |
| `REASON_MISSING_HUMAN_ACTOR` | `"missing_human_actor"` |
| `REASON_MISSING_DECISION_REASON` | `"missing_decision_reason"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_MUTATION_NOT_ALLOWED` | `"mutation_not_allowed"` |
| `REASON_ARCHIVE_NOT_ALLOWED` | `"archive_not_allowed"` |
| `REASON_APPROVAL_NOT_ALLOWED` | `"approval_not_allowed"` |
| `REASON_GATE_FINALIZATION_NOT_ALLOWED` | `"gate_finalization_not_allowed"` |
| `REASON_COMMAND_EXECUTION_NOT_ALLOWED` | `"command_execution_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_DUPLICATE_DECISION_REF` | `"duplicate_decision_ref"` |
| `REASON_UNBOUNDED_DECISION_STORE_PATH` | `"unbounded_decision_store_path"` |
| `REASON_OVERSIZED_DECISION_PAYLOAD` | `"oversized_decision_payload"` |

### `record_human_decision()` function

```python
def record_human_decision(
    input_data: BacklogDecisionInput,
) -> BacklogDecisionResult:
```

Algorithm:
1. Validate required fields (`backlog_item_ref`, `decision_type`, `human_actor`, `decision_reason`).
2. Validate `decision_type` against `BacklogDecisionType`.
3. Forbidden action patterns check.
4. Build canonical JSON, derive `decision_ref` from SHA256.
5. Check for duplicate in `.ariadne/decisions/`.
6. Write decision record JSON to `decision_store_dir / {decision_ref}.json`.
7. Return `"recorded"` with record and ref.

### Route handler in `server.py`

```
POST /backlog/decision
Body: BacklogDecisionInput JSON
```

Returns:
```json
{
    "status": "recorded",
    "decision_ref": "...",
    "decision_record": {...}
}
```

### Decision store location

Default: `.ariadne/decisions/` relative to project root. Each decision is a JSON file named `{decision_ref}.json`.

## Required test coverage

1. Valid decision → `"recorded"` with `decision_ref`.
2. Deterministic `decision_ref` (same input = same ref).
3. Decision includes all required fields.
4. Missing `backlog_item_ref` → rejected.
5. Missing `human_actor` → rejected.
6. Missing `decision_reason` → rejected.
7. Invalid `decision_type` → rejected.
8. Hidden reasoning → rejected.
9. URL-only evidence → rejected.
10. Duplicate decision → `"duplicate"`.
11. Decision does NOT mutate backlog item files.
12. Decision does NOT archive backlog items.
13. Decision does NOT approve gates.
14. No filesystem writes outside `.ariadne/decisions/`.
15. No `.ariadne/` residue in repo root (uses `tmp_path`).
16. Product name "Ariadne".
17. No forbidden legacy names.

## Validation strategy

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_decision.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
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
* decision-record drift:
* backlog-mutation drift:
* local-view drift:
* task_intake drift:
* server/app drift:
* frontend/browser/static drift:
* validation drift:
* semantic drift:
* future-scope drift:
* dirty-tree residue drift:
* accepted deviations:
* blockers:
```

## Stop conditions

* Block if PR/commit 0111 cannot be established — VERIFIED: backlog_review + tests + precommit pass (19 tests)
* Block if decision intake mutates backlog records — PASS: separate store
* Block if decision intake archives/rejects/accepts backlog items — PASS: explicitly rejected
* Block if decision intake approves or finalizes gates — PASS: explicitly rejected
* Block if decision intake executes the decision instead of only recording it — PASS: recording only
* All other stop conditions pass — no blockers

## Decisions made

* implementation files: `services/task_intake/src/task_intake/backlog_decision.py` (new), `services/task_intake/src/task_intake/server.py` (modified)
* test files: `services/task_intake/tests/test_backlog_decision.py` (new)
* decision intake surface selected: task_intake HTTP server — `POST /backlog/decision`
* decision record object shape: `BacklogDecisionInput`, `BacklogDecisionRecord` (frozen, with decision_ref, backlog_item_ref, decision_type, human_actor, decision_reason, evidence_refs, next_human_action, candidate_ref, continuity_ref, created_at=None)
* decision result shape: `BacklogDecisionResult` (status "recorded"|"rejected"|"duplicate", reason_codes, decision_record, decision_ref, details)
* decision status values: recorded, rejected, duplicate
* decision types: needs_more_evidence, defer, dismiss, candidate_for_future_pr, accept_for_human_planning
* stable reason codes: 16 constants
* deterministic decision ref: first 16 hex chars of SHA256 of canonical JSON
* decision store path: `.ariadne/decisions/`
* backlog item reference validation: backlog_item_ref required, non-empty
* PR 0111 backlog_review integration: not modified
* PR 0110 backlog_surface integration: not modified
* task_intake integration decision: selected (new module + route)
* server/app wiring decision: `POST /backlog/decision`
* browser/static UI decision: deferred
* CLI decision: deferred
* mutation rejection rules: 16 reason codes covering all forbidden operations
* validation commands: compileall + focused pytest + regression pytest (17 files) + task_intake check + dirty-tree check
* Plan Drift Gate requirements: full drift gate with decision-record, backlog-mutation, and dirty-tree residue fields
* blockers: none
* warnings: none
* behavior planned: new `backlog_decision.py` with `record_human_decision()`; extend `server.py` with `POST /backlog/decision`; 17 test cases; separate decision store; no backlog mutation; no `.ariadne/` residue
* boundaries: no backlog item mutation, no archive/accept/reject, no gate approval/finalization, no decision execution, no frontend, no provider/network/Docker/LLM, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: 66ce4d5d1ff162b9170dbeaf6c92a30178f8b1b3
* branch: 0112-human-backlog-decision-intake
* git_status_short: clean
* post_0100_manifest_status: agent-manifest.md exists and read
* pr_0111_status_evidence: backlog_review.py + test_backlog_review.py + precommit pass (19 tests, 411 regression)
* stale_snapshot_policy: clean tree, HEAD verified

## Files written

* `.project-memory/pr/0112-human-backlog-decision-intake/PLAN.md`

## Boundary confirmations: all 50 confirmations pass
