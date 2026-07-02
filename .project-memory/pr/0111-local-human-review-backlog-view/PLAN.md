# PR 0111 — Local Human Review Backlog View

## Purpose

Add a read-only local human review backlog view to Ariadne's task_intake server: a new ASGI route (`GET /backlog`) that renders the PR 0110 `backlog_surface` view, and focused tests verifying the route is read-only, deterministic, and does not mutate, approve, archive, or finalize anything.

## Roadmap alignment

* roadmap track: Human Review Visibility Layer
* expected PR slot: 0111 — Local Human Review Backlog View
* why this PR is next: PR 0110 added the runtime `backlog_surface` view model and CLI. PR 0111 exposes the same read-only surface through the local task_intake HTTP server, making backlog items inspectable from a browser — the last remaining gap before humans can routinely review improvement candidates.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md
* batching policy check: local read-only route + focused tests form one coherent executable-first PR. ADR 0011 allows batching a single read-only route and its tests into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* frontend/local UI note: the task_intake `server.py` already exposes an HTML page at `GET /`. PR 0111 adds `GET /backlog` returning JSON (consumable by a future browser panel). The existing HTML page is NOT modified (no `frontend-only` risk). No new browser framework, static files, or UI dependencies are introduced.
* architect sign-off required: no — ROADMAP.md and PR 0110 status are established.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md
* ROADMAP.md
* PR 0110 precommit-review.yml — confirms backlog_surface implemented, tested, merged (32 tests, 379 regression, no `.ariadne/` residue).

## Architecture context

The existing task_intake server (`server.py`) is a minimal stdlib ASGI application with these routes:

| Route | Method | Handler | Notes |
|-------|--------|---------|-------|
| `/` | GET | Serves `_HTML_PAGE` (static HTML) | Existing browser interaction page |
| `/health` | GET | Returns `doctor()` JSON | Service health |
| `/submit` | POST | `accept_task()` | Task submission |
| `/task-intake/submit` | POST | `accept_task()` | Task submission (alt path) |
| `/task-intake/normalize` | POST | `normalize_task_intake()` | Input normalization |
| `/context/preview` | POST | `generate_context_preview()` | Context preview |
| `/runs` | POST | `create_mock_run()` | Mock run creation |
| `/runs/execute` | POST | `run_mock_execution_handoff()` | Execute task |
| `/mock-loop` | POST | `run_mock_loop()` | Mock loop |
| Everything else | — | Returns 404 | |

No existing route exposes the backlog surface. The PR 0110 CLI (`python -m runner backlog surface`) calls `build_backlog_surface()` from the runner. PR 0111 adds a `GET /backlog` route that does the same — but through the HTTP server so a browser can consume it.

## Scope

### Implementation files

* `services/task_intake/src/task_intake/backlog_review.py` — new: `BacklogReviewInput`, `build_backlog_review_json()` function that calls `build_backlog_surface()` from the runner, verifies no mutation, and returns a deterministic JSON dict
* `services/task_intake/src/task_intake/server.py` — modified: add route handler for `GET /backlog` and `POST /backlog` (POST returns same data — purely a convenience, still read-only)

### Test files

* `services/task_intake/tests/test_backlog_review.py` — new: 20+ test cases covering the backlog review route via the ASGI app directly

### Not in scope

* `services/runner/src/runner/backlog_surface.py` — NOT modified. PR 0111 consumes it, does not change it.
* `services/runner/src/runner/doctor.py` — NOT modified. CLI already works.
* ROADMAP.md — not modified.
* Schema files — unchanged.
* pyproject.toml — not modified.
* `apps/web/` — frontend deferred.
* No mutation, archive, accept, reject, approve, finalize, gate operations.
* No HTML/JS modifications to the existing `_HTML_PAGE`.

## Design

### BacklogReviewInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class BacklogReviewInput:
    backlog_store_dir: str = ".ariadne/backlog"
    status_filter: str | None = None
    category_filter: str | None = None
    max_items: int = 0  # 0 = unlimited
```

### `build_backlog_review_json()` function

```python
def build_backlog_review_json(
    input_data: BacklogReviewInput,
) -> dict:
```

Algorithm:
1. Calls `build_backlog_surface()` from `runner.backlog_surface`.
2. Converts the result into a JSON-safe dict.
3. Adds a `read_only: true` flag to every response.
4. Adds `_warnings` array for any issue detected during transit.
5. Returns the dict ready for JSON serialization.

This is a thin adapter — no business logic duplication.

### Route handler in `server.py`

```
GET /backlog?status=new&category=self_improvement&max_items=50
POST /backlog  (body: BacklogReviewInput JSON)
```

Both return JSON:

```json
{
    "status": "ready",
    "read_only": true,
    "surface": {
        "items": [...],
        "summary": {...},
        "total_count": 5,
        "human_review_required_count": 3,
        "drift_risk_items": [...],
        "ready_for_review_items": ["ref1", "ref2"]
    }
}
```

Error/empty responses:

```json
{"status": "empty", "read_only": true, "surface": {"items": [], ...}}
{"status": "rejected", "read_only": true, "reason_codes": ["missing_backlog_store"], "details": "..."}
```

### Mutation rejection rules (in `build_backlog_review_json`)

The adapter function checks:
- If the `BacklogSurfaceResult` has any reason code matching a mutation pattern, the response is rejected immediately.
- If the result is `READY`, the response includes `read_only: true` and no actions/buttons.
- No POST body field is treated as a mutation command — all fields act as filters only.

### Stable reason codes (same as PR 0110 surface, re-exported from `runner.backlog_surface`)

`REASON_MISSING_BACKLOG_STORE`, `REASON_MALFORMED_BACKLOG_ITEM_JSON`, `REASON_DUPLICATE_BACKLOG_ITEM_REF`, `REASON_MUTATION_NOT_ALLOWED`, etc.

## Required test coverage

### Unit tests (in `test_backlog_review.py`)

1. `GET /backlog` with no backlog store → JSON with `status: "rejected"` and `missing_backlog_store`.
2. `GET /backlog` with empty store dir → JSON with `status: "empty"`, zero counts.
3. `GET /backlog` with valid store → JSON with `status: "ready"`, `read_only: true`, items.
4. `GET /backlog?status=new` → filtered results.
5. `GET /backlog?category=self_improvement` → filtered results.
6. `GET /backlog?max_items=1` → limited results.
7. `POST /backlog` with body → same as GET, returns data.
8. `POST /backlog` with invalid JSON body → 400.
9. Response always includes `read_only: true`.
10. Response does NOT include `archive`, `accept`, `reject`, `approve`, `finalize` action fields.
11. Malformed item in store → rejection with `malformed_backlog_item_json`.
12. Duplicate ref in store → rejection with `duplicate_backlog_item_ref`.
13. No filesystem writes after route call.
14. No `.ariadne/` residue left in repo root.
15. Product name "Ariadne" in docstrings.
16. No forbidden legacy names.

## Validation strategy

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest services/task_intake/tests/test_backlog_review.py -q
# Full regression:
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

## Plan Drift Gate requirements

The precommit-review.yml must include:

```
PLAN DRIFT GATE
* verdict: pass | warning | block
* file drift:
* behavior drift:
* object-shape drift:
* read-only drift:
* local-view drift:
* UI/surface drift:
* task_intake drift:
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

* Block if PR/commit 0110 cannot be established — VERIFIED: backlog_surface.py + tests + precommit pass (32 tests, 379 regression)
* Block if PR 0110 backlog_surface evidence is missing — VERIFIED
* Block if implementation would be frontend-only — PASS: only Python route, no HTML/JS changes
* Block if implementation bypasses PR 0110 backlog_surface — PASS: calls `build_backlog_surface()` directly
* Block if implementation mutates backlog records — PASS: read-only by design
* All other stop conditions pass — no blockers

## Decisions made

* implementation files: `services/task_intake/src/task_intake/backlog_review.py` (new), `services/task_intake/src/task_intake/server.py` (modified)
* test files: `services/task_intake/tests/test_backlog_review.py` (new)
* human-facing surface selected: task_intake HTTP server — `GET /backlog` and `POST /backlog`
* local view object shape: JSON response with `status`, `read_only: true`, `surface` (containing items, summary, counts, drift_risk_items, ready_for_review_items), or `reason_codes` + `details` on rejection
* PR 0110 backlog_surface integration: calls `build_backlog_surface()` directly — no duplicate logic
* task_intake integration decision: selected — new route in existing server
* CLI decision: not selected — PR 0110 already has `backlog surface` CLI
* browser/static UI decision: deferred — route returns JSON; browser panel left for PR 0112+
* mutation rejection rules: `read_only: true` in every response; no mutation fields exposed
* stable reason codes: re-exported from `runner.backlog_surface`
* validation commands: compileall + focused pytest + full regression (13 runner files) + task_intake check + dirty-tree check
* Plan Drift Gate requirements: full drift gate included
* blockers: none
* warnings: none
* behavior planned: 16 test cases, read-only JSON route, no mutation, no `.ariadne/` residue
* boundaries: no mutation, no archive/accept/reject/approve/finalize, no HTML/JS changes, no frontend, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: cdd376b6a06fe346bebe79a9f4eb0f4627052d54
* git_status_short: clean
* post_0100_manifest_status: agent-manifest.md exists and read
* pr_0110_status_evidence: backlog_surface.py + test_backlog_surface.py + precommit pass (32 tests, 379 regression, no `.ariadne/` residue)
* stale_snapshot_policy: clean tree, HEAD verified

## Files written

* .project-memory/pr/0111-local-human-review-backlog-view/PLAN.md

## Boundary confirmations: all 50 confirmations pass
