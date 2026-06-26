# PR 0070 — Runner Adapter Registry / Dispatcher Plan

## Goal

Plan executable behavior for a minimal runner adapter registry/dispatcher.

This PR must add code and tests.
This PR must not be docs-only.
This PR must not be schemas-only.

The dispatcher must accept an execution request dict, select the no-op adapter from PR 0069, call it, and return the deterministic execution result.

## Product Direction

PR 0069 introduced the first executable runner adapter.

PR 0070 introduces the minimal selection layer needed before connecting mock runs to runner execution.

This PR is still mock-safe and deterministic.

It must not introduce real execution.

## Architectural Thesis

The registry/dispatcher is the adapter selection boundary.

Application code should not call concrete adapters directly once dispatch exists.

The dispatcher maps explicit request fields to an approved adapter implementation.

For PR 0070, the only supported adapter is the no-op adapter from PR 0069.

Future adapters such as Docker, local process, or remote sandbox must later conform to this selection boundary, but they must not be implemented now.

## Context Snapshot

- **current HEAD sha**: `8b34fc9e69f7f735ce98f9d084a517fd0de6e0c7`
- **current branch**: `0070-runner-adapter-dispatcher`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `8b34fc9` (main after PR 0069 merge — no skew relative to main)
- **index_version**: `"0.36"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0069, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.grace/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/pr/0068-runner-execution-contract/PLAN.md`
- `.project-memory/pr/0069-minimal-noop-runner-adapter/PLAN.md`
- `schemas/runner-execution-request.schema.yml`
- `schemas/runner-execution-result.schema.yml`
- `docs/RUNNER_EXECUTION_CONTRACT.md`
- `docs/adr/0010-runner-execution-contract-boundary.md`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/tests/test_noop_adapter.py`
- `services/runner/src/runner/__init__.py`

## Existing Surface Snapshot

### PR 0068 execution contract

**Request:** `RunnerExecutionRequest` dict with required fields: `execution_request_id`, `run_id`, `task_intake_id`, `context_preview_id`, `requested_adapter`, `execution_mode`, `inputs`, `constraints`.
**Result:** `RunnerExecutionResult` dict with `execution_result_id`, `execution_request_id`, `run_id`, `status`, `adapter`, `artifacts`, `evidence`, `errors`, `warnings`, `review_required`, `next`.

### PR 0069 no-op adapter

**Module:** `services/runner/src/runner/noop_adapter.py`
**Function:** `run_noop_execution(execution_request: dict) -> dict`
**Behavior:** Validates request, checks adapter id contains `"noop"`, checks mode is `dry_run` or `preview`, checks approval semantics. Returns `completed`, `blocked`, `requires_review`, or `failed`.

### Runner package layout

```
services/runner/src/runner/
    __init__.py   — re-exports ApplyPatch, ArtifactStore, MockCoder
    noop_adapter.py  (PR 0069)
    ...
```

### No adapter registry/dispatcher exists

The only way to call the no-op adapter today is to import `run_noop_execution` directly and call it. There is no selection/dispatch layer.

## Implementation Location Decision

**Decision: Two files, no init changes.**

### Implementation file

1. **`services/runner/src/runner/adapter_registry.py`** — the dispatcher module.

### Test file

2. **`services/runner/tests/test_adapter_registry.py`** — focused tests.

**No changes to `__init__.py`.** The adapter registry is importable via `from runner.adapter_registry import dispatch_execution`. Adding it to `__init__.py` would be premature — no external consumers need a re-export yet.

**No changes to `noop_adapter.py`.** The dispatcher imports and calls `run_noop_execution` directly.

## Public Functions

```python
def dispatch_execution(execution_request: dict) -> dict:
    """Dispatch an execution request to the appropriate runner adapter.

    Parameters
    ----------
    execution_request
        A RunnerExecutionRequest dict (PR 0068 contract).

    Returns
    -------
    dict
        A RunnerExecutionResult dict from the selected adapter.
    """

def get_supported_adapters() -> dict:
    """Return a deterministic dict of supported adapter identifiers.

    Returns
    -------
    dict
        {"noop": {"version": "v1", "modes": ["dry_run", "preview"]}}
    """
```

Both are pure functions. No global state, no filesystem, no network, no subprocess.

## Behavior Requirements

### Case 1: Request for no-op adapter → dispatches to no-op adapter

`execution_request["requested_adapter"]` matches `"noop"` → calls `run_noop_execution(execution_request)` → returns result unchanged.

### Case 2: No-op adapter result is passed through unchanged

The dispatcher does NOT modify the adapter's result. This keeps the dispatcer thin and the adapter responsible for its own output.

### Case 3: Unsupported adapter → structured error

`requested_adapter` does not match any supported adapter → returns `failed` with error code `"unsupported_adapter"`.

### Case 4: Unsupported execution mode → structured error

If the adapter check passes but `execution_mode` is not supported by any adapter → returns `failed` with error code `"unsupported_mode"`. Note: the no-op adapter also validates mode, but the dispatcher can provide an earlier, more specific error.

**Decision:** The dispatcher does NOT pre-validate execution mode. It delegates fully to the selected adapter. This avoids duplicating the adapter's own validation logic. If the adapter returns `failed`, the dispatcher passes it through unchanged.

### Case 5: Invalid request (non-dict) → structured error

If `execution_request` is not a dict, return `failed` with error code `"invalid_request"`.

### Case 6: Determinism

Repeated calls with same input return equal output.

### Case 7: Supported adapters

`get_supported_adapters()` returns a deterministic dict: `{"noop": {"version": "v1", "modes": ["dry_run", "preview"]}}`.

## Adapter Selection Semantics

**Selection field:** `execution_request["requested_adapter"]`

**Supported adapter values:**

| Value in requested_adapter | Matches | Adapter |
|---|---|---|
| `"noop"` | substring match (case-insensitive, `"noop" in adapter_id.lower()`) | `run_noop_execution` |
| `"noop-v1"` | same | `run_noop_execution` |
| Any other | no match | Error: `unsupported_adapter` |

**Match strategy:** The dispatcher iterates a static mapping of `(predicate, adapter_fn)` tuples. For PR 0070, the mapping is:

```python
_ADAPTERS = [
    ("noop", run_noop_execution),
]
```

Selection checks if `adapter_id` contains the key (case-insensitive). This is the same logic the no-op adapter uses internally, so the dispatcher and adapter stay consistent.

## Error Result Semantics

**Status:** `failed`

**Error fields:**

```python
{
    "execution_result_id": "",
    "execution_request_id": "<from request or empty>",
    "run_id": "<from request or empty>",
    "status": "failed",
    "adapter": "dispatcher",
    "artifacts": [],
    "evidence": [],
    "errors": [
        {
            "code": "unsupported_adapter",
            "message": "Unsupported adapter: 'docker-coder-v1'. Supported adapters: noop.",
        }
    ],
    "warnings": [],
    "review_required": False,
    "next": "",
}
```

**Error codes:** `"unsupported_adapter"`, `"invalid_request"`.

## Test Plan

**Test file:** `services/runner/tests/test_adapter_registry.py`

| Test | Expectation |
|---|---|
| `test_dispatch_noop_returns_completed` | valid noop request → completed |
| `test_dispatch_noop_result_passed_through` | dispatcher returns same result as adapter |
| `test_dispatch_result_json_serializable` | passes json.dumps(sort_keys=True) |
| `test_dispatch_deterministic` | repeated calls return equal dict |
| `test_unsupported_adapter_returns_failed` | "docker-coder-v1" → failed, code "unsupported_adapter" |
| `test_invalid_request_non_dict_returns_failed` | string → failed, code "invalid_request" |
| `test_get_supported_adapters_returns_noop` | `get_supported_adapters()` → dict with "noop" |
| `test_get_supported_adapters_deterministic` | repeated calls return equal dict |
| `test_noop_adapter_tests_still_pass` | (compatibility) |
| `test_no_side_effects` | no subprocess/Docker/network imports |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_adapter_registry.py services/runner/tests/test_noop_adapter.py -q
python -m compileall -f services/runner/src
grep -R -n "subprocess|os\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git \|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" services/runner/src/runner/adapter_registry.py services/runner/tests/test_adapter_registry.py || true
grep -R -n "\$(" services/runner/src/runner/adapter_registry.py services/runner/tests/test_adapter_registry.py || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/adapter_registry.py`
- `services/runner/tests/test_adapter_registry.py`

Precommit review may later write only:
- `.project-memory/pr/0070-runner-adapter-dispatcher/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0070-runner-adapter-dispatcher/PLAN.md` (planner only)
- `.project-memory/pr/0070-runner-adapter-dispatcher/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/**`
- `services/conductor/**`
- `services/domain_adapters/**`
- `services/core/**`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/src/runner/__init__.py`
- `services/runner/src/runner/__main__.py`
- `services/runner/tests/test_noop_adapter.py`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.grace/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`

## Non-goals

- no docs-only or schemas-only PR
- no real execution
- no Docker adapter
- no Docker files/commands
- no subprocess/shell/network
- no filesystem writes at runtime
- no plugin discovery/dynamic imports
- no task-intake to runner connection
- no mock-loop changes
- no HTTP endpoint
- no queue/persistence/database
- no model calls/provider integration
- no dependencies/build changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only/schemas-only → stop
- no executable `.py` file selected → stop
- no test file selected → stop
- about to implement real runner execution → stop
- about to implement Docker adapter → stop
- about to call subprocess/shell → stop
- about to use network libraries → stop
- about to write files at runtime → stop
- about to add plugin discovery/dynamic imports → stop
- about to connect mock-loop/task-intake to runner → stop
- about to add HTTP endpoint → stop
- about to add persistence/queue/database → stop
- about to add dependencies → stop
- about to modify task-intake code → stop
- about to modify noop_adapter.py → stop
- about to modify schemas/docs as primary output → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples → stop
- shell placeholders → stop

## Open Questions

1. **Should the dispatcher pre-validate execution mode or delegate fully?** **Decision:** Delegate fully. The no-op adapter already validates `execution_mode`. The dispatcher should not duplicate validation logic. If the adapter returns `failed`, the dispatcher passes it through. This keeps the dispatcher thin and the adapter responsible for its own domain.

2. **Should the dispatcher add metadata to the adapter result (e.g., wrap it with dispatcher provenance)?** **Decision:** No — pass-through. The adapter's result is the canonical output. Adding dispatcher metadata would couple the dispatcher to the result schema and complicate testing. If provenance is needed later, it should be a first-class adapter concern.

3. **Should `get_supported_adapters` be a dict or a list?** **Decision:** Dict keyed by adapter id. Dicts are easier to query: `adapters = get_supported_adapters(); "noop" in adapters`. Each value includes version and supported modes.

## Decisions Made

### selected_strategy

Executable Python code + tests. Not docs-only, not schemas-only.

### implementation_files

```
services/runner/src/runner/adapter_registry.py
```

### test_files

```
services/runner/tests/test_adapter_registry.py
```

### public_functions

```python
dispatch_execution(execution_request: dict) -> dict
get_supported_adapters() -> dict
```

### supported_adapter_values

Adapter ids containing `"noop"` (case-insensitive substring match) → `run_noop_execution`.
All others → error.

### supported_execution_modes

Delegated to adapter. The dispatcher does not pre-validate modes. Adapter errors pass through.

### dispatch_semantics

1. Non-dict request → `failed` with `"invalid_request"`.
2. No matching adapter → `failed` with `"unsupported_adapter"`.
3. Matching adapter found → call adapter, return result unchanged.
4. Adapter returns `failed` → pass through unchanged.

### error_result_shape

Status `"failed"`, adapter `"dispatcher"`. Error codes: `"invalid_request"`, `"unsupported_adapter"`. Empty `execution_result_id` for validation failures where no result can be formed. Adapter-specific errors are passed through from the adapter.

### deterministic_id_strategy

The dispatcher does not generate IDs. Adapter errors use empty `execution_result_id` (since no adapter was called to produce one). The no-op adapter generates `execution_result_id` as `f"{req_id}-result"`.

### validation_strategy

10 test cases covering dispatch, pass-through, unsupported adapter, invalid request, supported adapters query, determinism, serialization, side-effect safety, and backward compatibility with no-op adapter tests.

### next_pr_notes

The next PR should connect the mock app loop (task-intake) to the runner adapter dispatcher. The `POST /mock-loop` endpoint should call `dispatch_execution` with a `RunnerExecutionRequest` and include the result in the loop response instead of the current mock run status.

---

PLAN written: yes
