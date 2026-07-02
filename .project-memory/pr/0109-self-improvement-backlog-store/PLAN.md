# PR 0109 — Self-Improvement Backlog Store / Local Queue

## Purpose

Add a deterministic local self-improvement backlog store / queue for Ariadne: a function and CLI command that persists evidence-backed improvement candidates (PR 0107) and session continuity follow-ups (PR 0108) as bounded, deduplicated backlog items. The backlog persists across sessions, supports lifecycle transitions (new → human_review → archived | rejected), and never autonomously edits code, commits, or calls providers.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime / Self-Improvement + Continuity Layer
* expected PR slot: 0109 — Self-Improvement Backlog Store / Local Queue
* why this PR is next: PRs 0107 and 0108 produce improvement candidates and continuity packets but have no persistence layer. PR 0109 adds the bounded local store so proposed improvements survive across sessions without relying on model memory or autonomously editing code.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0109 listed as ninth PR)
* batching policy check: backlog store runtime object + deduplication + lifecycle transitions + CLI integration + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* frontend repair note: frontend backlog display UI is deferred to a follow-up PR. This PR creates the runtime backlog store and data model that frontend can later display. The `frontend_visibility_gap` backlog category is defined so items can represent frontend gaps without modifying frontend code.
* architect sign-off required: no — ROADMAP.md and PR 0108 status are established, post-0100 strategic direction manifest explicitly lists PR 0109 as the next step after 0108.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0109 listed as ninth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime / Self-Improvement + Continuity Layer is the active track.
* PR 0108 precommit-review.yml — confirms session_continuity packet is implemented, tested, and merged (30 tests, 336 regression).

## Required reads

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
* .project-memory/pr/0101–0108 PLAN.md and precommit-review.yml files (26 artifacts read)

## Architecture context

The existing Proof-First Runtime has eight complete components (PRs 0101–0108), all passing. The CLI pattern is: `__main__.py` delegates to `doctor.main(argv)`, which defines argparse subcommand groups. Each new feature adds a `.py` module + helper in `doctor.py` + tests.

PR 0109 adds an `improvement_backlog.py` module and a `backlog` subcommand group with operations: `enqueue`, `list`, `archive`.

## Scope

### Implementation files

* `services/runner/src/runner/improvement_backlog.py` — new: `BacklogItemInput`, `BacklogItem`, `BacklogResult`, `BacklogStatus`, stable reason codes, `enqueue_backlog_item()`, `list_backlog()`, `archive_backlog_item()` functions
* `services/runner/src/runner/doctor.py` — modified: add `backlog_enqueue_file()`, `backlog_list()`, `backlog_archive_file()` helpers and wire into CLI

### Test files

* `services/runner/tests/test_improvement_backlog.py` — new: 30+ test cases covering all backlog operations
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `backlog enqueue`, `backlog list`, `backlog archive`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged
* docs/ — not modified
* pyproject.toml — not modified
* Any file outside the five target files above
* No automatic code edits, commits, PRs, or autonomous repair
* No provider/model integration, network calls, or Docker calls
* No frontend changes (frontend backlog UI deferred)

## Design

### BacklogStatus (enum)

```python
class BacklogStatus(str, enum.Enum):
    NEW = "new"
    HUMAN_REVIEW = "human_review"
    ARCHIVED = "archived"
    REJECTED = "rejected"
```

Valid transitions: `NEW → HUMAN_REVIEW → ARCHIVED | REJECTED`

### BacklogCategory (enum)

```python
class BacklogCategory(str, enum.Enum):
    SELF_IMPROVEMENT = "self_improvement"
    CONTINUITY_FOLLOWUP = "continuity_followup"
    DRIFT_RISK = "drift_risk"
    VALIDATION_GAP = "validation_gap"
    FRONTEND_VISIBILITY_GAP = "frontend_visibility_gap"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
```

### BacklogItemInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogItemInput:
    candidate_ref: str               # candidate_id from PR 0107
    continuity_ref: str              # continuity_ref from PR 0108 (optional)
    product_state_ref: str
    source_reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    improvement_category: str        # ImprovementCategory or BacklogCategory value
    next_safe_action: str
    blocked_actions: tuple[str, ...] = ()
    drift_risks: tuple[str, ...] = ()
    requires_human_review: bool = True
    phase_id: str = ""
    run_id: str = ""
    output_path: str = ""            # for artifact output
    session_label: str = ""
```

### BacklogItem (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogItem:
    backlog_item_ref: str            # first 16 hex chars of SHA256(canonical JSON)
    candidate_ref: str
    continuity_ref: str
    product_state_ref: str
    source_reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    improvement_category: str
    next_safe_action: str
    blocked_actions: tuple[str, ...]
    drift_risks: tuple[str, ...]
    requires_human_review: bool
    status: str                      # BacklogStatus value
    phase_id: str
    run_id: str
    session_label: str
    created_at: None                 # deterministic; no wall-clock time
    archived_at: None = None
```

### BacklogResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogResult:
    status: str                      # "enqueued" | "duplicate" | "archived" | "rejected"
    reason_codes: tuple[str, ...] = ()
    backlog_item: BacklogItem | None = None
    backlog_items: tuple[BacklogItem, ...] = ()  # for list operation
    artifact_path: str | None = None
    total_count: int = 0
    details: str | None = None
```

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_CANDIDATE_REF` | `"missing_candidate_ref"` |
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_EVIDENCE_REFS` | `"missing_evidence_refs"` |
| `REASON_MISSING_NEXT_SAFE_ACTION` | `"missing_next_safe_action"` |
| `REASON_MISSING_HUMAN_REVIEW_BOUNDARY` | `"missing_human_review_boundary"` |
| `REASON_DUPLICATE_CANDIDATE` | `"duplicate_candidate"` |
| `REASON_INVALID_BACKLOG_STATUS` | `"invalid_backlog_status"` |
| `REASON_INVALID_BACKLOG_ITEM` | `"invalid_backlog_item"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH` | `"unbounded_backlog_output_path"` |
| `REASON_OVERSIZED_BACKLOG_ITEM` | `"oversized_backlog_item"` |
| `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED` | `"autonomous_code_change_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |
| `REASON_COMMAND_EXECUTION_NOT_ALLOWED` | `"command_execution_not_allowed"` |

### `enqueue_backlog_item()` function

```python
def enqueue_backlog_item(
    input_data: BacklogItemInput,
    backlog_store_dir: str = ".ariadne/backlog",
    output_dir: str = ".",
) -> BacklogResult:
```

Algorithm:
1. Validate all input fields (non-empty, bounds, forbidden patterns).
2. Compute `backlog_item_ref` from SHA256 of canonical input JSON.
3. Check for duplicate: if `backlog_store_dir / {backlog_item_ref}.json` already exists, return `status="duplicate"` with `REASON_DUPLICATE_CANDIDATE`.
4. Build `BacklogItem` with `status="new"`.
5. Write item JSON to `output_dir / output_path`.
6. Symlink or copy to `backlog_store_dir / {backlog_item_ref}.json` for durable persistence.
7. Return `status="enqueued"` with item and artifact_path.

### `list_backlog()` function

```python
def list_backlog(
    backlog_store_dir: str = ".ariadne/backlog",
    status_filter: str | None = None,  # optional: "new", "human_review", "archived", "rejected"
) -> BacklogResult:
```

Algorithm:
1. List all `.json` files in `backlog_store_dir`.
2. Read each, parse as `BacklogItem`.
3. Filter by `status_filter` if provided.
4. Sort by `backlog_item_ref` (deterministic).
5. Return `status="listed"` with `backlog_items` and `total_count`.

### `archive_backlog_item()` function

```python
def archive_backlog_item(
    backlog_item_ref: str,
    target_status: str = "archived",  # "archived" or "rejected"
    backlog_store_dir: str = ".ariadne/backlog",
) -> BacklogResult:
```

Algorithm:
1. Read `backlog_store_dir / {backlog_item_ref}.json`.
2. Parse as `BacklogItem`.
3. Validate transition: `new → archived | rejected`, `human_review → archived | rejected`.
4. Update `status` and set `archived_at = None` (deterministic).
5. Write updated item back.
6. Return `status="archived"` or `status="rejected"` with item.

### Backlog store location

Default: `.ariadne/backlog/` relative to project root. Each item is a JSON file named `{backlog_item_ref}.json`.

### Deduplication

When `enqueue_backlog_item` is called with a candidate already in the store (same `backlog_item_ref`), it returns `status="duplicate"` instead of writing again. This prevents the same improvement proposal from accumulating multiple identical entries.

### Rejected operations

| Operation | Detection |
|-----------|-----------|
| No candidate ref | Empty `candidate_ref` |
| No product state | Empty `product_state_ref` |
| No evidence refs | Empty `evidence_refs` |
| No next safe action | Empty `next_safe_action` |
| No human-review boundary | `requires_human_review` not set |
| Duplicate candidate | `backlog_item_ref` already exists in store |
| Invalid status transition | Attempting archived→new, rejected→human_review, etc. |
| Invalid backlog item | Parse failure or missing fields in stored file |
| Hidden chain-of-thought | In `proposed_next_action`, `drift_risks`, or `blocked_actions` |
| External URL-only evidence | In `evidence_refs` |
| Autonomous code change/git mutation/provider call/command execution | In `next_safe_action` via forbidden pattern check |
| Unbounded output path | `..`, leading `/`, > 255 chars |
| Oversized item | Any text field exceeds its bound |

### CLI command shape

```
python -m runner backlog enqueue <path>
python -m runner backlog list [--status <filter>]
python -m runner backlog archive <backlog_item_ref> [--status archived|rejected]
```

## Required test coverage

### Unit tests (in `test_improvement_backlog.py`)

1. Enqueue valid item → `status="enqueued"`, item has `backlog_item_ref`.
2. Enqueue same input twice → `status="duplicate"`, no file overwrite.
3. Different candidate_ref produces different `backlog_item_ref`.
4. List with no items returns empty list.
5. List after enqueue returns 1 item.
6. List with status filter returns only matching items.
7. Archive changes status from `new` to `archived`.
8. Archive changes status from `human_review` to `rejected`.
9. Archive invalid transition (archived→new) → rejected.
10. Missing candidate_ref → rejected.
11. Missing product_state_ref → rejected.
12. Missing evidence_refs → rejected.
13. Missing next_safe_action → rejected.
14. Missing human_review_boundary (`requires_human_review=False`) → rejected or allowed per design.
15. Hidden reasoning → rejected.
16. URL-only evidence → rejected.
17. Autonomous code change request → rejected.
18. Git mutation request → rejected.
19. Provider call request → rejected.
20. Command execution request → rejected.
21. Unbounded output path → rejected.
22. Oversized item → rejected.
23. Created_at is None (deterministic, no wall-clock time).
24. Archived_at is None for non-archived items.
25. Deterministic JSON format with sorted keys.
26. Item includes all required output fields.
27. Product name "Ariadne".
28. No forbidden legacy names.

### CLI tests (in `test_doctor_cli.py`)

29. `backlog enqueue --help`.
30. `backlog enqueue` valid file → exit 0.
31. `backlog enqueue` invalid file → exit 1.
32. `backlog list --help`.
33. `backlog list` → exit 0, JSON output.
34. `backlog archive --help`.
35. `backlog archive <ref>` → exit 0.
36. No network/Docker/LLM imports.

## Validation strategy

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_improvement_backlog.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
```

All prerequisite test files are present.

## Plan Drift Gate requirements

The precommit-review.yml for PR 0109 must include:

```
PLAN DRIFT GATE
* verdict: pass | warning | block
* file drift:
* behavior drift:
* object-shape drift:
* CLI drift:
* frontend drift:
* backlog-lifecycle drift:
* validation drift:
* semantic drift:
* future-scope drift:
* accepted deviations:
* blockers:
```

## Stop conditions

* Block if PR/commit 0108 cannot be established — VERIFIED: session_continuity.py, tests, precommit all pass
* Block if PR 0107 improvement_candidate evidence is missing — VERIFIED
* All other stop conditions pass — no blockers

## Decisions made

* implementation files: `services/runner/src/runner/improvement_backlog.py` (new), `services/runner/src/runner/doctor.py` (modified)
* test files: `services/runner/tests/test_improvement_backlog.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* backlog object shape: `BacklogItemInput`, `BacklogItem` (frozen, includes backlog_item_ref, status, created_at/archived_at=None), `BacklogResult`
* backlog result shape: status ("enqueued"|"duplicate"|"archived"|"rejected"|"listed"), reason_codes, backlog_item, backlog_items, artifact_path, total_count
* backlog status values: NEW → HUMAN_REVIEW → ARCHIVED | REJECTED
* backlog_item_ref derivation: first 16 hex chars of SHA256(canonical input JSON)
* source evidence requirements: candidate_ref required, continuity_ref optional, evidence_refs required, product_state_ref required
* candidate integration: `candidate_ref` maps to PR 0107 improvement candidate ID
* continuity integration: `continuity_ref` maps to PR 0108 session continuity ref (optional)
* deduplication decision: Yes — enqueue of same backlog_item_ref returns `"duplicate"` instead of writing
* lifecycle/status transition decision: Yes — `new → human_review → archived | rejected`
* CLI command shape: `backlog enqueue <path>`, `backlog list [--status]`, `backlog archive <ref> [--status]`
* frontend repair decision: Deferred — backlog store data model defined for later display
* rejected operation types: missing refs, missing evidence, missing next action, missing human review, duplicate, invalid transition, hidden reasoning, URL-only, forbidden actions, unbounded path, oversized
* stable reason codes: 16 constants as defined above
* artifact format: JSON with deterministic field order, `created_at: null`, `archived_at: null`
* output path constraints: no `..`, no leading `/`, max 255 chars
* validation commands: compileall + focused pytest + regression pytest + task_intake check
* Plan Drift Gate requirements: full drift gate with backlog-lifecycle field
* blockers: none
* warnings: none
* behavior planned: 36+ test cases, enqueue/duplicate detection/list/archive lifecycle, `backlog` CLI subcommand group
* boundaries: no code edits, no commits, no PRs, no autonomous repair, no frontend

## Context snapshot

* current_head: 81539a586a6008c5a2709663a02f30f767ede969
* git_status_short: clean
* post_0100_manifest_status: agent-manifest.md exists and read
* pr_0107_status_evidence: improvement_candidate.py + tests + precommit verdict=pass (32 tests, 301 regression)
* pr_0108_status_evidence: session_continuity.py + tests + precommit verdict=pass (30 tests, 336 regression)
* stale_snapshot_policy: clean tree, HEAD verified

## Files written

* .project-memory/pr/0109-self-improvement-backlog-store/PLAN.md

## Boundary confirmations: all 50 confirmations pass
