# PR 0110 — Read-Only Self-Improvement Backlog Surfacing

## Purpose

Add a read-only self-improvement backlog surfacing layer for Ariadne: a runtime view model and CLI command that presents PR 0109 backlog items in a human-inspectable, deterministic, read-only format. The surface does not mutate backlog items, archive/reject/accept them, approve gates, edit code, or call providers.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime / Human Review Visibility Layer
* expected PR slot: 0110 — Read-Only Self-Improvement Backlog Surfacing
* why this PR is next: PR 0109 added the backlog store (enqueue/list/archive). PR 0110 adds the dedicated human-review surface that renders backlog items with full detail, summary counts, category groupings, and drift risk analysis — all without mutation.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0110 listed as tenth PR)
* batching policy check: read-only backlog surfacing view model + CLI subcommand + focused tests form one coherent executable-first PR. ADR 0011 allows batching related view models and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* frontend repair note: frontend (browser) backlog display UI is deferred. The correct executable-first prerequisite is a runtime JSON view model + CLI, which this PR delivers. A browser-based UI should follow in a later PR (0111 or later).
* architect sign-off required: no — ROADMAP.md and PR 0109 status are established, post-0100 strategic direction manifest lists PR 0110 next after 0109.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0110 listed as tenth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime / Human Review Visibility Layer is the active track.
* PR 0109 precommit-review.yml — confirms improvement_backlog store is implemented, tested, and merged (29 tests, 374 regression).

## Architecture context

The existing backlog store (PR 0109) provides:
- `BacklogItem`, `BacklogItemInput`, `BacklogResult`, `BacklogStatus`, `BacklogCategory`
- `enqueue_backlog_item()`, `list_backlog()`, `archive_backlog_item()`
- CLI: `backlog enqueue <path>`, `backlog list [--status]`, `backlog archive <ref>`

The existing `backlog list` returns a minimal item subset (backlog_item_ref, candidate_ref, status, category, next_safe_action, requires_human_review). PR 0110 adds a richer read-only view with:
- Full item details (all fields)
- Summary counts by status and category
- Drift risk breakdown
- Human-review readiness assessment
- Deterministic sort and grouping

No browser/frontend app exists at `apps/web/` (only README.md). The surfacing layer is correctly placed in the runner as a runtime view model + CLI.

## Scope

### Implementation files

* `services/runner/src/runner/backlog_surface.py` — new: `BacklogSurfaceInput`, `BacklogSurfaceView`, `BacklogSurfaceResult`, `BacklogSurfaceStatus`, stable reason codes, `build_backlog_surface()` function
* `services/runner/src/runner/doctor.py` — modified: add `backlog_surface()` helper and `backlog surface` CLI subcommand

### Test files

* `services/runner/tests/test_backlog_surface.py` — new: 25+ test cases covering `build_backlog_surface()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `backlog surface` subcommand

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged
* docs/ — not modified
* pyproject.toml — not modified
* apps/web/ — frontend deferred
* Any file outside the four target files above
* No backlog mutation of any kind
* No archive/reject/accept operations
* No gate approval or finalization
* No autonomous repair
* No provider/network/Docker/LLM calls

## Design

### BacklogSurfaceInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogSurfaceInput:
    backlog_store_dir: str = ".ariadne/backlog"
    status_filter: str | None = None  # optional: new, human_review, archived, rejected
    category_filter: str | None = None  # optional: self_improvement, continuity_followup, etc.
    max_items: int = 0  # 0 = unlimited
```

### BacklogSurfaceView (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogSurfaceView:
    items: tuple[dict, ...]       # Full detail dicts for each item
    summary: dict                  # Counts by status and category
    total_count: int
    human_review_required_count: int
    drift_risk_items: tuple[dict, ...]  # Items with drift risks
    ready_for_review_items: tuple[str, ...]  # backlog_item_refs of items needing human review
```

The item dicts contain all `BacklogItem` fields serialized as JSON-safe types.

### BacklogSurfaceStatus (enum)

```python
class BacklogSurfaceStatus(str, enum.Enum):
    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"
```

### BacklogSurfaceResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogSurfaceResult:
    status: BacklogSurfaceStatus
    reason_codes: tuple[str, ...] = ()
    surface_view: BacklogSurfaceView | None = None
    details: str | None = None
```

### Stable reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_BACKLOG_STORE` | `"missing_backlog_store"` |
| `REASON_BACKLOG_STORE_NOT_DIRECTORY` | `"backlog_store_not_directory"` |
| `REASON_UNBOUNDED_BACKLOG_STORE_PATH` | `"unbounded_backlog_store_path"` |
| `REASON_UNREADABLE_BACKLOG_ITEM` | `"unreadable_backlog_item"` |
| `REASON_MALFORMED_BACKLOG_ITEM_JSON` | `"malformed_backlog_item_json"` |
| `REASON_DUPLICATE_BACKLOG_ITEM_REF` | `"duplicate_backlog_item_ref"` |
| `REASON_UNSUPPORTED_BACKLOG_STATUS` | `"unsupported_backlog_status"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_MUTATION_NOT_ALLOWED` | `"mutation_not_allowed"` |
| `REASON_ARCHIVE_NOT_ALLOWED` | `"archive_not_allowed"` |
| `REASON_APPROVAL_NOT_ALLOWED` | `"approval_not_allowed"` |
| `REASON_GATE_FINALIZATION_NOT_ALLOWED` | `"gate_finalization_not_allowed"` |
| `REASON_COMMAND_EXECUTION_NOT_ALLOWED` | `"command_execution_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_OVERSIZED_BACKLOG_VIEW` | `"oversized_backlog_view"` |

### `build_backlog_surface()` function

```python
def build_backlog_surface(
    input_data: BacklogSurfaceInput,
) -> BacklogSurfaceResult:
```

Algorithm:
1. Validate `backlog_store_dir` path (exists, is directory, bounded).
2. Use `list_backlog()` to load items from store.
3. Apply optional `status_filter` and `category_filter`.
4. Enforce `max_items` limit if set.
5. For each item, build a full detail dict with all `BacklogItem` fields.
6. Check for duplicate `backlog_item_ref` values.
7. Check for malformed items (missing required fields).
8. Build summary counts:
   ```json
   {
     "total": 5,
     "by_status": {"new": 3, "human_review": 1, "archived": 1, "rejected": 0},
     "by_category": {"self_improvement": 2, "continuity_followup": 1, "drift_risk": 1, "validation_gap": 0, "frontend_visibility_gap": 1, "human_review_required": 0}
   }
   ```
9. Build `drift_risk_items` list: items where `drift_risks` is non-empty.
10. Build `ready_for_review_items` list: `backlog_item_ref` values where `status == "new"` and `requires_human_review is True`.
11. Return `READY` with `BacklogSurfaceView`.

### CLI command shape

```
python -m runner backlog surface [--status <filter>] [--category <filter>] [--max-items <N>]
```

Read-only. Returns JSON with `status`, `command`, `result` containing `view`, `summary`, `human_review_required_count`, `drift_risk_items`, `ready_for_review_items`.

Exit code: 0 if `READY` or `EMPTY`, 1 if `REJECTED` (e.g., missing store, malformed items).

### Read-only guarantees

The `backlog surface` CLI:
- Does NOT write any files
- Does NOT modify any backlog JSON files
- Does NOT modify source code
- Does NOT mutate git state
- Does NOT leave `.ariadne/` residue (reads from existing store only)
- Does NOT call archive/accept/reject operations
- Does NOT approve gates or finalize work
- Does NOT call providers, network, Docker, or LLMs

### Rejected conditions

| Condition | Detection |
|-----------|-----------|
| Missing backlog store | Path does not exist → `REASON_MISSING_BACKLOG_STORE` |
| Backlog store is a file | Path is not a directory → `REASON_BACKLOG_STORE_NOT_DIRECTORY` |
| Unbounded path | Path contains `..` or leading `/` → `REASON_UNBOUNDED_BACKLOG_STORE_PATH` |
| Malformed item JSON | JSON parse failure → `REASON_MALFORMED_BACKLOG_ITEM_JSON` |
| Duplicate ref | Same `backlog_item_ref` in multiple files → `REASON_DUPLICATE_BACKLOG_ITEM_REF` |
| Unsupported status | Invalid status string → `REASON_UNSUPPORTED_BACKLOG_STATUS` |
| Hidden reasoning | In any text field → `REASON_HIDDEN_REASONING_NOT_ALLOWED` |
| URL-only evidence | In `evidence_refs` or `source_reason_codes` → `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` |
| Mutation/archive/approval/finalization/git/provider/command requests | Any attempt to pass mutating input → rejected with appropriate reason code |

## Required test coverage

### Unit tests for `build_backlog_surface()` (in `test_backlog_surface.py`)

1. Empty backlog store → `EMPTY`, zero totals.
2. Missing backlog store → `REJECTED` with `REASON_MISSING_BACKLOG_STORE`.
3. Valid backlog items → `READY`, items included in view.
4. Items sorted deterministically by `backlog_item_ref`.
5. Summary counts correct (by status and category).
6. `human_review_required_count` correct.
7. `drift_risk_items` contains items with non-empty drift_risks.
8. `ready_for_review_items` contains items where status=="new" and requires_human_review==True.
9. Status filter works (only items with matching status).
10. Category filter works (only items with matching category).
11. Max_items limit enforced.
12. Malformed item JSON handled deterministically.
13. Duplicate `backlog_item_ref` handled deterministically.
14. Unsupported status handled deterministically.
15. Hidden reasoning → rejected.
16. URL-only evidence → rejected.
17. Mutation request → rejected (read-only enforcement).
18. Archive request → rejected.
19. Approval request → rejected.
20. Gate finalization request → rejected.
21. Command execution request → rejected.
22. Provider call request → rejected.
23. Git mutation request → rejected.
24. No filesystem writes after surface build.
25. Product name "Ariadne".
26. No forbidden legacy names.

### CLI tests (in `test_doctor_cli.py`)

27. `backlog surface --help`.
28. `backlog surface` with valid store → exit 0, JSON output with view/summary/drift_risk_items/ready_for_review_items.
29. `backlog surface --status new` → filtered.
30. `backlog surface --status nonexistent` → handled (rejected or empty).
31. `backlog surface` with nonexistent store → exit 1, rejected.
32. No network/Docker/LLM imports.

## Validation strategy

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_backlog_surface.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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

All prerequisite test files are present.

## Plan Drift Gate requirements

The precommit-review.yml for PR 0110 must include:

```
PLAN DRIFT GATE
* verdict: pass | warning | block
* file drift:
* behavior drift:
* object-shape drift:
* read-only drift:
* UI/surface drift:
* CLI drift:
* frontend drift:
* validation drift:
* semantic drift:
* future-scope drift:
* dirty-tree residue drift:
* accepted deviations:
* blockers:
```

## Stop conditions

* Block if PR/commit 0109 cannot be established — VERIFIED: improvement_backlog.py, tests, precommit all pass (29 tests, 374 regression)
* Block if implementation would mutate backlog records — PASS: read-only by design
* Block if implementation would archive/reject/accept backlog items — PASS: explicitly rejected
* Block if implementation would approve or finalize gates — PASS: explicitly rejected
* All other stop conditions pass — no blockers

## Decisions made

* implementation files: `services/runner/src/runner/backlog_surface.py` (new), `services/runner/src/runner/doctor.py` (modified)
* test files: `services/runner/tests/test_backlog_surface.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* surfacing layer selected: runtime view model (`backlog_surface.py`) + CLI (`backlog surface`)
* read-only view object shape: `BacklogSurfaceInput` (frozen, with store_dir, status_filter, category_filter, max_items), `BacklogSurfaceView` (items, summary dict, total_count, human_review_required_count, drift_risk_items, ready_for_review_items)
* read-only result shape: `BacklogSurfaceResult` (status enum READY/EMPTY/REJECTED, reason_codes, surface_view, details)
* read-only status values: READY, EMPTY, REJECTED
* summary count shape: dict with total, by_status (4 statuses), by_category (6 categories)
* deterministic ordering: by `backlog_item_ref` (string sort)
* source backlog requirements: reads from PR 0109 backlog store via `list_backlog()`
* local UI/browser decision: deferred — no browser app exists; runner CLI is the correct first surface
* task_intake integration decision: not selected — runner module is the correct layer
* CLI surfacing decision: selected — `backlog surface [--status] [--category] [--max-items]`
* mutation rejection rules: 18 stable reason codes covering all forbidden mutation operations
* stable reason codes: 17 constants as defined above
* output format: JSON with `status`, `command`, `result`, `error`; view contains items, summary, counts, drift items, ready-for-review refs
* backlog store path constraints: path must exist, be a directory, no `..`, no leading `/`
* validation commands: compileall + focused pytest (backlog_surface) + focused pytest (test_doctor_cli) + full regression (13 files) + task_intake check + dirty-tree residue check
* Plan Drift Gate requirements: full drift gate with read-only, UI/surface, frontend, and dirty-tree-residue fields
* blockers: none
* warnings: none
* behavior planned: new `backlog_surface.py` with `build_backlog_surface()`; extend `doctor.py` with `backlog_surface()` helper and `backlog surface` CLI; 32 test cases; read-only guarantees enforced by reason codes; dirty-tree check in validation
* boundaries: no mutation, no archive/accept/reject, no approval/finalization, no frontend, no provider/network/Docker/LLM, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: 8f6d80c11c00d6649c8f36842b0634503af8b2ef
* git_status_short: clean
* post_0100_manifest_status: agent-manifest.md exists and read
* pr_0109_status_evidence: improvement_backlog.py + tests + precommit verdict=pass (29 tests, 374 regression)
* stale_snapshot_policy: clean tree, HEAD verified

## Files written

* .project-memory/pr/0110-read-only-backlog-surfacing/PLAN.md

## Boundary confirmations: all 50+ confirmations pass
