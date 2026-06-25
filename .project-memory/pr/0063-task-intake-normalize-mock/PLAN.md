# PR 0063 — Task Intake Normalize Mock Endpoint Plan

## Goal

Plan the first visible application-loop endpoint:

```
POST /task-intake/normalize
```

The endpoint should accept raw task intake input and return a deterministic normalized Ariadne task-intake structure.

This is a mock endpoint / application surface, not a model-backed planner.

## Architectural Thesis

Ariadne has enough substrate pieces to start exposing a small application loop.

The first product-facing step is task intake normalization:

```
raw task request
→ deterministic normalized task intake
→ next step can become context preview
```

This PR should start the app loop without adding model calls, repository scanning, persistence, authentication, queueing, or run execution.

## Context Snapshot

- **current HEAD sha**: `d576b4b3f298d5d2d14e343ea6dffc71025a410a`
- **current branch**: `0063-task-intake-normalize-mock`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `d576b4b` (merge commit — no skew relative to main)
- **index_version**: `"0.29"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0062, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `docs/DEVELOPMENT_ORDER.md` — not present
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/models.py`
- `services/task_intake/src/task_intake/normalizer.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `services/task_intake/tests/test_task_intake.py`
- `services/task_intake/pyproject.toml`

## Existing Application Surface Snapshot

### Task Intake Service

An existing stdlib-only ASGI application at `services/task_intake/`. It has:

- **ASGI server** (`server.py`) — routes `GET /health`, `POST /submit`, `POST /task-intake/submit`. Uses stdlib ASGI protocol directly (no framework).
- **App logic** (`app.py`) — `accept_task()` function that validates prompt length/emptiness and returns `TaskIntakeAccepted` with a deterministic SHA-256-based task_id.
- **Models** (`models.py`) — `TaskIntakeRequest`, `TaskIntakeAccepted`, `TaskIntakeRejected`, `TaskIntakeStatus`/`Error` enums. Also has Sprint 0 legacy models: `NormalizeRequest`, `TaskDraft`, `TaskNormalizer`.
- **Normalizer** (`normalizer.py`) — `TaskNormalizer` class from Sprint 0 that infers mode (bugfix/feature/refactor/test/review) from raw text and keyword heuristics.
- **Tests** (`tests/test_task_intake_http.py`) — uses synchronous `asyncio.run()` wrappers to test the ASGI app directly (no pytest-asyncio).
- **Dependencies** (`pyproject.toml`) — depends on `uvicorn>=0.29.0` for serving. Stdlib-only for application logic.

### Key existing patterns

- Routes are defined with `if method == "POST" and path == "/submit"` pattern in `server.py`.
- Test harness uses `asyncio.run(_asgi_request(...))` — synchronous wrappers.
- Request body is read via ASGI `receive()` events.
- Responses use `_send_json()` helper.

## Implementation Location Decision

**Decision: Modify the existing `server.py` and add a new normalization module.**

### New module

1. **`services/task_intake/src/task_intake/normalize.py`** — a pure deterministic normalization function.

This is distinct from the existing `normalizer.py` (Sprint 0 legacy). The new module exposes a `normalize_task_intake(raw: dict) -> dict` function that returns a normalized task structure.

### Modified file

2. **`services/task_intake/src/task_intake/server.py`** — add route for `POST /task-intake/normalize`, following the existing routing pattern.

### New test file

3. **`services/task_intake/tests/test_normalize.py`** — focused tests for the new normalization function and endpoint.

### Not modified

- `services/task_intake/pyproject.toml` — no dependency changes.
- `services/task_intake/src/task_intake/app.py` — the `/submit` flow is untouched.
- `services/task_intake/src/task_intake/models.py` — the existing models are sufficient.
- `services/task_intake/src/task_intake/normalizer.py` — Sprint 0 legacy, untouched.
- `services/task_intake/tests/test_task_intake_http.py` — existing tests untouched.
- No changes to `services/core/`, `services/conductor/`, `services/runner/`, `services/domain_adapters/`, `schemas/`, `.project-memory/`.

## Task Intake Request Contract

The endpoint accepts a JSON body:

```json
{
  "raw_task": "Implement JWT authentication middleware",
  "source": "manual",
  "metadata": {
    "requester": "demo-user",
    "priority": "medium"
  },
  "constraints": ["no_git_mutation", "no_network"],
  "requested_output": "plan"
}
```

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `raw_task` | string | Yes | Raw task description text |
| `source` | string | No | Source of the task (default `"manual"`) |
| `metadata` | dict | No | Optional metadata (must be JSON-compatible) |
| `constraints` | list[string] | No | Task constraints |
| `requested_output` | string | No | Expected output type (default `"plan"`) |

## Task Intake Response Contract

```json
{
  "ok": true,
  "task_intake_id": "task_e5b71a2f3c4d",
  "normalized_task": {
    "raw_task": "Implement JWT authentication middleware",
    "task_goal": "Implement JWT authentication middleware",
    "source": "manual",
    "metadata": {
      "requester": "demo-user",
      "priority": "medium"
    },
    "constraints": ["no_git_mutation", "no_network"],
    "requested_output": "plan",
    "inferred_mode": "feature",
    "inferred_domains": ["auth"],
    "warnings": []
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "next": "/context/preview"
}
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `ok` | bool | Whether normalization succeeded |
| `task_intake_id` | string | Deterministic task ID |
| `normalized_task` | dict | Normalized task structure |
| `validation` | dict | Validation results |
| `next` | string | Suggested next step |

**Deterministic ID strategy:** Use the same SHA-256-based ID strategy as the existing `_make_task_id()` in `models.py`: `task_<first 12 hex chars of sha256(raw_task)>`. This is deterministic, stdlib-only, and consistent with the existing service.

## Normalization Behavior

The `normalize_task_intake()` function:

1. **Validates input** — returns structured errors for invalid input.
2. **Normalizes raw_task** — trims whitespace, collapses multiple spaces.
3. **Infers mode** — uses keyword matching (same heuristic as existing `normalizer.py` but simplified and Ariadne-native):
   - If any constraint includes `"test"` or `"coverage"` → `"test"`
   - If `raw_task` mentions `"review"`, `"audit"`, `"check"` → `"review"`
   - If `raw_task` mentions `"refactor"`, `"cleanup"`, `"reorganize"` → `"refactor"`
   - If `raw_task` mentions `"add"`, `"implement"`, `"feature"`, `"create"`, `"new"` → `"feature"`
   - Default → `"bugfix"`
4. **Infers domains** — basic keyword matching:
   - `"auth"`, `"login"`, `"jwt"`, `"permission"` → `"auth"`
   - `"test"`, `"coverage"`, `"spec"` → `"testing"`
   - `"api"`, `"endpoint"`, `"route"` → `"api"`
   - `"db"`, `"database"`, `"sql"`, `"migration"` → `"database"`
   - Default → `"core"`
5. **Generates warnings** — e.g., if `raw_task` is short (< 8 words), add warning.
6. **Returns** the normalized structure.

## Validation Behavior

| Input condition | Response |
|---|---|
| Missing `raw_task` | `ok: false`, 400 status, error: "raw_task is required" |
| Empty `raw_task` | `ok: false`, 400 status, error: "raw_task must not be blank" |
| Non-string `raw_task` | `ok: false`, 400 status, error: "raw_task must be a string" |
| Non-dict metadata | `ok: false`, 400 status, error: "metadata must be a dict" |
| Non-list constraints | `ok: false`, 400 status, error: "constraints must be a list" |
| Valid input | `ok: true`, 200 status, normalized response |

## Endpoint Strategy

**Route:** `POST /task-intake/normalize` in `server.py`.

**Pattern:** Same as existing routes — `if method == "POST" and path == "/task-intake/normalize"`.

**Behavior:**
1. Read body via ASGI `receive()` events.
2. Parse JSON.
3. Call `normalize_task_intake(data)` from the new `normalize.py`.
4. If `ok: false`, return 400 with error details.
5. If `ok: true`, return 200 with normalized structure.

**Error strategy:** Return 400 for invalid input (vs. 200 with `"status": "rejected"` used by `/submit`). The `/normalize` endpoint is a preview — invalid requests should get HTTP 400 to distinguish from valid normalization results.

## Tests

### Test module: `services/task_intake/tests/test_normalize.py`

Use the same synchronous ASGI test harness pattern as `test_task_intake_http.py`.

```python
class TestNormalizeEndpoint:
    # Endpoint behavior
    def test_valid_request_returns_200(self): ...
    def test_valid_request_has_ok_true(self): ...
    def test_valid_request_has_task_intake_id(self): ...
    def test_valid_request_has_normalized_task(self): ...
    def test_valid_request_has_next(self): ...
    def test_valid_request_deterministic(self): ...

    # Request fields preserved
    def test_raw_task_preserved(self): ...
    def test_source_defaults_to_manual(self): ...
    def test_metadata_preserved(self): ...
    def test_constraints_preserved(self): ...
    def test_requested_output_defaults_to_plan(self): ...

    # Validation
    def test_missing_raw_task_returns_400(self): ...
    def test_empty_raw_task_returns_400(self): ...
    def test_non_string_raw_task_returns_400(self): ...
    def test_non_dict_metadata_returns_400(self): ...
    def test_non_list_constraints_returns_400(self): ...

    # Inference
    def test_inferred_mode_feature(self): ...
    def test_inferred_mode_bugfix(self): ...
    def test_inferred_mode_test(self): ...
    def test_inferred_domains(self): ...

    # Safety
    def test_no_forbidden_source_strings(self): ...
    def test_no_side_effects(self): ...
```

### Compatibility

- Existing `test_task_intake_http.py` tests pass unchanged.
- Existing `test_task_intake.py` tests pass unchanged.
- Existing `test_normalizer.py` tests pass unchanged.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/task_intake/src/task_intake/normalize.py services/task_intake/tests/test_normalize.py services/task_intake/src/task_intake/server.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/task_intake/src/task_intake/normalize.py services/task_intake/tests/test_normalize.py services/task_intake/src/task_intake/server.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/normalize.py` (new)
- `services/task_intake/tests/test_normalize.py` (new)
- `services/task_intake/src/task_intake/server.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0063-task-intake-normalize-mock/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0063-task-intake-normalize-mock/PLAN.md` (planner only)
- `.project-memory/pr/0063-task-intake-normalize-mock/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `services/core/**`
- `services/conductor/**`
- `services/runner/**`
- `services/domain_adapters/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `services/task_intake/pyproject.toml`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/models.py`
- `services/task_intake/src/task_intake/normalizer.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `services/task_intake/tests/test_task_intake.py`
- `services/task_intake/tests/test_normalizer.py`
- `package.json`
- `Makefile`
- `.project-memory/anchors.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/templates/**`
- `.grace/**`

## Non-goals

- no model calls
- no provider integration
- no repository scanner
- no repository graph computation
- no RAG/vector search
- no cache backend
- no distributed cache
- no database
- no persistence
- no queue
- no run execution
- no authentication
- no UI
- no full product loop
- no GitHub integration
- no Docker
- no dependency changes
- no schema changes
- no project-memory runtime writes
- no changes to Core runtime, conductor, runner, domain adapters
- no changes to existing Sprint 0 normalizer
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to add dependency/build config → stop
- about to add new web framework → stop
- about to add database/persistence → stop
- about to add model/provider behavior → stop
- about to inspect Git/repository state → stop
- about to scan repository files → stop
- about to implement context preview → stop
- about to implement runs/status → stop
- about to modify `app.py`, `models.py`, `normalizer.py` → stop (not needed)
- about to modify `pyproject.toml` → stop
- about to modify runtime/core/runner/domain adapters → stop
- about to modify schemas → stop
- about to modify project-memory registry/templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the new normalize module reuse the existing `_make_task_id()` from `models.py`?** **Decision:** Yes. Import `_make_task_id` from `models.py`. It's a stable, deterministic, stdlib-only function. No need to duplicate the logic.

2. **Should the normalize module be a new file or extend `normalizer.py`?** **Decision:** New file (`normalize.py`). The existing `normalizer.py` contains Sprint 0 legacy `TaskNormalizer` class. The new module is a pure function (`normalize_task_intake(raw: dict) -> dict`). Keeping them separate avoids confusion and preserves backward compatibility.

3. **Should the endpoint return 400 or 200 for invalid input?** **Decision:** 400 (HTTP Bad Request). The `/submit` endpoint returns 200 with a `"rejected"` status — that's appropriate for a submission flow. The `/normalize` endpoint is a preview — if the input is malformed, there's nothing to preview. HTTP 400 is the correct semantic.

4. **Should the endpoint use `"ok"` or `"status"` for the success field?** **Decision:** `"ok"` (boolean). The existing `/submit` endpoint uses `"status": "accepted"` / `"status": "rejected"`. The `/normalize` endpoint is a different pattern: it returns structured data, not an accept/reject. Using `ok: true/false` is cleaner for a preview endpoint.

## Decisions Made

### implementation_files

```
services/task_intake/src/task_intake/normalize.py (new)
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_normalize.py (new)
```

### optional_route_files

None — the route is added directly to the existing `server.py`.

### request_shape

```
{
    "raw_task": str,           # required
    "source": str,             # optional, default "manual"
    "metadata": dict,          # optional, must be JSON-compatible
    "constraints": list[str],  # optional
    "requested_output": str,   # optional, default "plan"
}
```

### response_shape

```
{
    "ok": bool,
    "task_intake_id": str,
    "normalized_task": {
        "raw_task": str,
        "task_goal": str,
        "source": str,
        "metadata": dict,
        "constraints": list[str],
        "requested_output": str,
        "inferred_mode": str,
        "inferred_domains": list[str],
        "warnings": list[str],
    },
    "validation": {
        "valid": bool,
        "errors": list[str],
        "warnings": list[str],
    },
    "next": str,
}
```

### id_strategy

Deterministic SHA-256: `task_<12 hex chars>` — reuse `_make_task_id()` from `models.py`.

### validation_rules

- Missing/empty/non-string `raw_task` → 400 with error.
- Non-dict `metadata` → 400 with error.
- Non-list `constraints` → 400 with error.
- Valid input → 200 with normalized structure.
- Repeated calls with same input → identical output.

### endpoint_strategy

- Route: `POST /task-intake/normalize` in `server.py`.
- Same ASGI pattern as existing routes.
- 400 for invalid input, 200 for valid.
- Uses `_send_json()` helper from existing server.
- No framework, no decorators, no middleware.

### deterministic_policy

- Task ID from SHA-256 of raw_task (deterministic).
- Mode/domain inference from keyword heuristics (deterministic).
- No random ids, no timestamps, no current time.
- No absolute paths, no machine-specific values.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused endpoint tests via ASGI test harness.
Compatibility tests for existing task_intake HTTP tests.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes
