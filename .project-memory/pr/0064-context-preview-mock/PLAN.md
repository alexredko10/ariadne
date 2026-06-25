# PR 0064 — Context Preview Mock Plan

## Goal

Plan the second visible application-loop endpoint:

```
POST /context/preview
```

The endpoint should accept normalized task intake data and return a deterministic preview of the context that Ariadne would use for a future run.

This is a mock preview, not run execution.

## Architectural Thesis

0063 introduced task intake normalization.

0064 should let a caller see what context would be used next, before creating a run.

Application loop:

```
raw task request
→ normalized task intake
→ context preview
→ future run creation
```

This PR should not execute runs, call models, scan the repository, or create persistent state.

## Context Snapshot

- **current HEAD sha**: `d576b4b3f298d5d2d14e343ea6dffc71025a410a`
- **current branch**: `0064-context-preview-mock`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `d576b4b` (main after PR 0062 merge — PR 0063 is planned but not merged)
- **index_version**: `"0.29"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0062. PR 0063 is planned but not yet merged; this is expected since PR 0063 and 0064 can be developed in parallel or sequentially. No blocking delta.
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/pr/0063-task-intake-normalize-mock/PLAN.md`
- `docs/DEVELOPMENT_ORDER.md` — not present
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/src/task_intake/app.py`
- `services/task_intake/src/task_intake/models.py`
- `services/task_intake/tests/test_task_intake_http.py`
- `services/conductor/src/conductor/context_pack_inputs.py`
- `services/conductor/src/conductor/context_compiler.py`
- `services/conductor/src/conductor/dry_run.py`

## Existing Application Surface Snapshot

### Current Product Loop

1. **Task Intake Normalize** (PR 0063, planned) — `POST /task-intake/normalize` accepts raw task text and returns a normalized task intake structure with `raw_task`, `task_goal`, `source`, `metadata`, `constraints`, `inferred_mode`, `inferred_domains`, `warnings`.

2. **Context Preview** (this PR) — `POST /context/preview` accepts normalized task intake data and returns a context preview.

### Available Substrate

- **`services/conductor/src/conductor/context_pack_inputs.py`** — `build_context_pack_inputs(...)` builds a validated context-pack-inputs dict from explicit params. Pure function, stdlib-only, no I/O.
- **`services/conductor/src/conductor/context_compiler.py`** — `compile_context_pack(...)` compiles inputs into a context pack. Pure function, stdlib-only, no I/O.

### Existing Server Infra

- **`services/task_intake/src/task_intake/server.py`** — stdlib ASGI application with routes for `/health`, `/submit`, `/task-intake/submit`. Following PR 0063, will also have `/task-intake/normalize`.
- **`services/task_intake/tests/test_task_intake_http.py`** — synchronous ASGI test harness via `asyncio.run()`.

### Route for context preview

The context preview belongs on the same server as task intake, since it's part of the product loop. The route `POST /context/preview` should be added to `server.py`.

## Implementation Location Decision

**Decision: Place context preview logic in a new module under `services/task_intake/`, route in `server.py`.**

### New module

1. **`services/task_intake/src/task_intake/context_preview.py`** — pure deterministic context preview function.

### Modified file

2. **`services/task_intake/src/task_intake/server.py`** — add route for `POST /context/preview`.

### New test file

3. **`services/task_intake/tests/test_context_preview.py`** — focused tests.

**Rationale for task_intake location:** The product loop (normalize → preview → run) is the task intake service's domain. Placing the preview alongside the normalize endpoint keeps the product flow coherent and prevents coupling from task_intake to conductor. The preview is a mock — it doesn't need the full context compiler.

**Rationale for not importing from conductor:** `context_pack_inputs.py` and `context_compiler.py` live under `services/conductor/`, which has no existing import relationship with `services/task_intake/`. Importing from conductor would create a coupling that should be deliberate (with a shared package or explicit dependency), not incidental. The preview mock is self-contained with its own deterministic logic.

### Not modified

- `services/task_intake/pyproject.toml` — no dependency changes.
- `services/task_intake/src/task_intake/app.py` — `/submit` flow untouched.
- `services/task_intake/src/task_intake/models.py` — no new models needed.
- `services/task_intake/src/task_intake/normalizer.py` — Sprint 0 legacy, untouched.
- `services/task_intake/src/task_intake/normalize.py` — PR 0063 module, untouched.
- `services/task_intake/tests/test_task_intake_http.py` — existing tests untouched.
- `services/task_intake/tests/test_normalize.py` — PR 0063 tests, untouched.
- `services/conductor/**` — no changes.
- `services/core/**`, `services/runner/**`, `services/domain_adapters/**` — no changes.
- `schemas/`, `.project-memory/`, `pyproject.toml` — no changes.

## Context Preview Request Contract

```json
{
  "task_intake": {
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
  "include_sections": ["task", "scope", "risks", "anchors"],
  "preview_options": {
    "format": "compact",
    "include_summary": true
  },
  "metadata": {
    "preview_requested_by": "demo"
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `task_intake` | dict | Yes | Normalized task intake structure (from `/task-intake/normalize` output) |
| `include_sections` | list[string] | No | Context sections to include (default: `["task", "scope", "risks"]`) |
| `preview_options` | dict | No | Preview options (format, summary preference) |
| `metadata` | dict | No | Preview request metadata |

## Context Preview Response Contract

```json
{
  "ok": true,
  "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
  "task_intake_id": "task_e5b71a2f3c4d",
  "preview": {
    "task_summary": "Implement JWT authentication middleware",
    "inferred_mode": "feature",
    "inferred_domains": ["auth"],
    "context_sections": {
      "task": {
        "goal": "Implement JWT authentication middleware",
        "constraints": ["no_git_mutation", "no_network"],
        "requested_output": "plan"
      },
      "scope": {
        "allowed_paths": ["services/**"],
        "forbidden_paths": [".git/**", ".env", "secrets/**"],
        "inferred_domain": "auth"
      },
      "risks": {
        "warnings": []
      },
      "anchors": {
        "relevant": ["@ariadne-domain auth"]
      }
    },
    "context_pack_preview_summary": {
      "schema_version": "0.1",
      "sections_included": ["task", "scope", "risks", "anchors"],
      "field_count": 4
    },
    "missing_inputs": []
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "next": "/runs"
}
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `ok` | bool | Whether preview generation succeeded |
| `context_preview_id` | string | Deterministic preview ID |
| `task_intake_id` | string | Task intake ID from the request |
| `preview` | dict | Deterministic context preview |
| `validation` | dict | Validation results |
| `next` | string | Suggested next step (`"/runs"`) |

**ID strategy:** `ctxpreview_<first 12 hex chars of sha256(task_goal + source)>` — deterministic, stdlib-only.

## Preview Logic

The `generate_context_preview(task_intake: dict, options: dict) -> dict` function:

1. **Validates input** — returns structured errors for invalid input.
2. **Extracts task summary** — from `task_intake.task_goal`.
3. **Builds context sections** — based on `include_sections`:
   - `task` — goal, constraints, requested_output.
   - `scope` — allowed/forbidden paths (from defaults: `services/**` / `.git/**`, `.env`, `secrets/**`), inferred domain.
   - `risks` — warnings from task intake.
   - `anchors` — generates `@ariadne-domain <domain>` from inferred domains.
   - `contracts` — lists relevant contracts (from defaults: context-pack schema references).
   - `cache` — generates a mock cache key ref.
4. **Builds context pack preview summary** — lists included sections and field count.
5. **Identifies missing inputs** — e.g., if no constraints are provided, adds a warning.
6. **Returns** the preview structure.

This is a mock. It does not call the real context compiler, load external documents, scan the repository, or call models.

## Validation Behavior

| Input condition | Response |
|---|---|
| Missing `task_intake` | `ok: false`, 400 status |
| `task_intake` not a dict | `ok: false`, 400 status |
| Missing `task_goal` in `task_intake` | `ok: false`, 400 status |
| `include_sections` not a list | `ok: false`, 400 status |
| `preview_options` not a dict | `ok: false`, 400 status |
| Valid input | `ok: true`, 200 status |

## Endpoint Strategy

**Route:** `POST /context/preview` in `server.py`.

**Pattern:** Same as existing routes — `if method == "POST" and path == "/context/preview"`.

**Behavior:**
1. Read body via ASGI `receive()` events.
2. Parse JSON.
3. Call `generate_context_preview(data)` from the new `context_preview.py`.
4. If `ok: false`, return 400 with error details.
5. If `ok: true`, return 200 with preview structure.

**Error strategy:** 400 for invalid input (same pattern as PR 0063 `/normalize`).

## Tests

### Test module: `services/task_intake/tests/test_context_preview.py`

Use the same synchronous ASGI test harness pattern.

```python
class TestContextPreviewEndpoint:
    # Endpoint behavior
    def test_valid_request_returns_200(self): ...
    def test_valid_request_has_ok_true(self): ...
    def test_valid_request_has_preview_id(self): ...
    def test_valid_request_has_preview(self): ...
    def test_valid_request_has_next_runs(self): ...

    # Request fields
    def test_task_intake_goal_preserved(self): ...
    def test_include_sections_controls_output(self): ...
    def test_preview_options_preserved(self): ...

    # Validation
    def test_missing_task_intake_returns_400(self): ...
    def test_missing_task_goal_returns_400(self): ...
    def test_non_dict_task_intake_returns_400(self): ...
    def test_non_list_include_sections_returns_400(self): ...

    # Preview content
    def test_preview_has_task_summary(self): ...
    def test_preview_has_context_sections(self): ...
    def test_preview_has_context_pack_summary(self): ...
    def test_preview_identifies_missing_inputs(self): ...

    # Determinism
    def test_deterministic(self): ...
    def test_json_serializable(self): ...

    # Side effect safety
    def test_no_forbidden_source_strings(self): ...
    def test_no_old_names(self): ...
```

### Compatibility

- Existing `test_task_intake_http.py` tests pass.
- Existing `test_normalize.py` tests pass (PR 0063).
- Existing `test_task_intake.py` tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/task_intake/src/task_intake/context_preview.py services/task_intake/tests/test_context_preview.py services/task_intake/src/task_intake/server.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/task_intake/src/task_intake/context_preview.py services/task_intake/tests/test_context_preview.py services/task_intake/src/task_intake/server.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/context_preview.py` (new)
- `services/task_intake/tests/test_context_preview.py` (new)
- `services/task_intake/src/task_intake/server.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0064-context-preview-mock/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0064-context-preview-mock/PLAN.md` (planner only)
- `.project-memory/pr/0064-context-preview-mock/reviews/plan-review.yml` (plan-review only)
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
- `services/task_intake/src/task_intake/normalize.py` (PR 0063)
- `services/task_intake/tests/test_normalize.py` (PR 0063)
- `services/task_intake/tests/test_task_intake_http.py`
- `services/task_intake/tests/test_task_intake.py`
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
- no run status object
- no authentication
- no UI
- no full API surface
- no GitHub integration
- no Docker
- no dependency changes
- no schema changes
- no project-memory runtime writes
- no imports from conductor (self-contained mock)
- no reads of filesystem or Git state
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to add dependency/build config → stop
- about to add new web framework → stop
- about to add database/persistence → stop
- about to add model/provider behavior → stop
- about to import from `services/conductor/` → stop (mock is self-contained)
- about to inspect Git/repository state → stop
- about to scan repository files → stop
- about to implement runs/status → stop
- about to execute runs → stop
- about to modify runtime/core/runner/domain adapters → stop
- about to modify schemas → stop
- about to modify project-memory registry/templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should context preview import from `conductor.context_pack_inputs`?** **Decision:** No. The preview is a self-contained mock. Importing from conductor would create a coupling path from task_intake to conductor that should be deliberate (via a shared package or explicit dependency in pyproject.toml), not incidental. The mock generates deterministic preview content using its own logic.

2. **Should the preview generate deterministic mock cache key refs?** **Decision:** Yes — as a preview section. The `cache` section includes a mock cache key ref `{"namespace": "context", "artifact_kind": "context_pack", "input_digest": "<deterministic>"}`. This shows what the real integration would look like without actually calling any cache backend.

3. **Should `next` point to `/runs` or a full URL?** **Decision:** Just `"/runs"` — a relative path. The server doesn't know its own base URL. The client resolves relative paths.

## Decisions Made

### implementation_files

```
services/task_intake/src/task_intake/context_preview.py (new)
services/task_intake/src/task_intake/server.py (modify)
```

### test_files

```
services/task_intake/tests/test_context_preview.py (new)
```

### optional_route_files

None — the route is added directly to the existing `server.py`.

### request_shape

```
{
    "task_intake": dict,              # required, normalized task intake structure
    "include_sections": list[str],    # optional, default ["task", "scope", "risks"]
    "preview_options": dict,           # optional
    "metadata": dict,                  # optional
}
```

### response_shape

```
{
    "ok": bool,
    "context_preview_id": str,
    "task_intake_id": str,
    "preview": {
        "task_summary": str,
        "inferred_mode": str,
        "inferred_domains": list[str],
        "context_sections": dict,        # keys: task, scope, risks, anchors, etc.
        "context_pack_preview_summary": dict,
        "missing_inputs": list[str],
    },
    "validation": {"valid": bool, "errors": list[str], "warnings": list[str]},
    "next": str,
}
```

### id_strategy

`ctxpreview_<first 12 hex chars of sha256(task_goal + source)>` — deterministic, stdlib-only SHA-256.

### validation_rules

- Missing/non-dict `task_intake` → 400.
- Missing `task_goal` in `task_intake` → 400.
- Non-list `include_sections` → 400.
- Repeated calls → identical output.
- No old names/examples, no shell placeholders.

### endpoint_strategy

Route `POST /context/preview` in `server.py`. Same ASGI pattern as existing routes. 400 for invalid input, 200 for valid.

### context_substrate_reuse

None. Self-contained mock. No imports from `services/conductor/`.

### deterministic_policy

- Preview ID from SHA-256 (deterministic).
- All preview content from explicit request fields (no inference from repository or environment).
- No random ids, no timestamps, no current time.
- No absolute paths, no machine-specific values.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused endpoint tests via ASGI test harness.
Compatibility tests for existing task_intake tests.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes
