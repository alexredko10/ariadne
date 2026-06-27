# PR 0074 — Human Review Boundary in Runtime Result Plan

## Goal

Plan executable behavior for a deterministic human-review runtime boundary.

The boundary must interpret execution request/result data and return a plain JSON-serializable dict describing whether the runtime result is:

- completed
- requires_review
- blocked
- failed

This PR must add code and tests.
This PR must not be docs-only or schemas-only.

## Product Direction

PR 0073 created deterministic artifact/evidence envelope.
PR 0074 adds the human-review decision boundary that future runtime/harness flows can use before executing or after receiving runner results.

This PR does not add UI.
This PR does not add notifications.
This PR does not add HTTP behavior.
This PR does not execute anything.

## Implementation Decision

**Decision: New module in the runner package.**

### Implementation file

1. **`services/runner/src/runner/review_boundary.py`** — review boundary module.

### Test file

2. **`services/runner/tests/test_review_boundary.py`** — focused tests.

**No changes to `__init__.py`.** The module is importable via `from runner.review_boundary import derive_review_boundary`.

**No changes to other runner modules** — noop_adapter, adapter_registry, execution_envelope, artifacts all untouched.

### Public API

```python
def derive_review_boundary(
    execution_request: dict,
    execution_result: dict,
) -> dict:
    """Interpret execution request/result and produce a deterministic review-boundary decision.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    execution_result
        The RunnerExecutionResult dict.

    Returns
    -------
    dict
        A review-boundary decision dict.
    """
```

## Decision Object Shape

```python
{
    "schema_version": "0.1",
    "decision": "<completed|requires_review|blocked|failed|error>",
    "requires_review": False,
    "blocked": False,
    "completed": True,
    "failed": False,
    "reason_code": "",
    "reasons": [],
    "execution_request_id": "<from request>",
    "execution_result_id": "<from result>",
    "run_id": "<from request>",
    "approval": {},  # from request, normalized
    "metadata": {
        "execution_adapter": "<from result>",
        "execution_mode": "<from request>",
    },
    "errors": [],
    "warnings": [],
}
```

**Decision values:** `"completed"`, `"requires_review"`, `"blocked"`, `"failed"`, `"error"` (for invalid input).

## Review/Approval Semantics

The boundary interprets two sources of information:
1. `execution_request["approval"]` — the caller's approval expectations
2. `execution_result["status"]` — the adapter's result status

### Approval input shape (from request)

```python
execution_request["approval"]  # may be:
None                              # no approval information
{"required": False}               # approval not required
{"required": True, "status": "pending"}    # approval required, not yet given
{"required": True, "status": "approved"}   # approval granted
{"required": True, "status": "denied"}     # approval denied
{"required": True, "after_execution": True} # review required after execution
```

### Decision rules

| Request approval | Result status | Decision |
|---|---|---|
| None or not required | `completed` | `completed` |
| None or not required | `requires_review` | `requires_review` |
| None or not required | `blocked` | `blocked` |
| None or not required | `failed` or `error` | `failed` |
| Required + pending | any | `requires_review` |
| Required + denied | any | `blocked` |
| Required + approved | `completed` | `completed` |
| Required + approved | `requires_review` | `requires_review` |
| Required + approved | `blocked` | `blocked` |
| Required + approved | `failed` or `error` | `failed` |
| Required + after_execution | any completed result | `requires_review` |

### Boolean flags

The output includes boolean flags for convenience:
- `completed`: True when decision is `"completed"`.
- `requires_review`: True when decision is `"requires_review"`.
- `blocked`: True when decision is `"blocked"`.
- `failed`: True when decision is `"failed"` or `"error"`.

### Reasons

When the decision is not `completed`, the `reasons` list explains why:

```python
reasons = [
    "Human approval is required and not yet granted.",
    "Human approval was denied.",
    "Execution result requires human review.",
    "Execution is blocked pending external input.",
    "Execution failed.",
]
```

The `reason_code` is a machine-readable short code:
- `"completed"` — no review needed.
- `"approval_pending"` — approval required but not yet given.
- `"approval_denied"` — approval was denied.
- `"requires_review"` — adapter returned requires_review.
- `"blocked"` — adapter returned blocked.
- `"execution_failed"` — adapter returned failed/error.
- `"invalid_input"` — boundary input validation failed.

## Error Semantics

| Condition | Decision |
|---|---|
| `execution_request` not a dict | `"error"` with error list |
| `execution_result` not a dict | `"error"` with error list |
| Missing `execution_request_id` | `"error"` with error list |
| Missing `execution_result_id` | `"error"` with error list |
| Missing `execution_result["status"]` | `"failed"` with warning about missing status |

Errors are a list of `{"code": str, "message": str, "field": str}`.

## Test Plan

**Test file:** `services/runner/tests/test_review_boundary.py`

| Test | Expectation |
|---|---|
| `test_completed_no_approval` | No approval, completed result → decision completed |
| `test_approval_required_pending` | Required + pending → requires_review |
| `test_approval_required_denied` | Required + denied → blocked |
| `test_approval_required_approved` | Required + approved + completed result → completed |
| `test_approval_after_execution` | Required + after_execution + completed → requires_review |
| `test_result_requires_review` | Result status requires_review → decision requires_review |
| `test_result_blocked` | Result status blocked → decision blocked |
| `test_result_failed` | Result status failed → decision failed |
| `test_error_result` | Result status error → decision failed |
| `test_invalid_request_not_dict` | Non-dict request → error decision |
| `test_invalid_result_not_dict` | Non-dict result → error decision |
| `test_missing_request_id` | Missing execution_request_id → error |
| `test_missing_result_id` | Missing execution_result_id → error |
| `test_missing_result_status` | Missing status in result → failed with warning |
| `test_deterministic` | Repeated calls return equal output |
| `test_json_serializable` | Passes json.dumps(sort_keys=True) |
| `test_no_side_effects` | No filesystem/Docker/subprocess/network/uuid/datetime imports |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_review_boundary.py services/runner/tests/test_execution_envelope.py services/runner/tests/test_adapter_registry.py services/runner/tests/test_noop_adapter.py -q
python -m compileall -f services/runner/src
grep -R -n "open(\\|write(\\|Path(\\|read_text(\\|write_text(\\|subprocess|os\\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |uuid|datetime\\.now|time\\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\\.grace|@grace-\|old Flask" services/runner/src/runner/review_boundary.py services/runner/tests/test_review_boundary.py || true
grep -R -n "\\$(" services/runner/src/runner/review_boundary.py services/runner/tests/test_review_boundary.py || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/review_boundary.py`
- `services/runner/tests/test_review_boundary.py`

Precommit review may later write only:
- `.project-memory/pr/0074-human-review-runtime-boundary/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0074-human-review-runtime-boundary/PLAN.md` (planner only)
- `.project-memory/pr/0074-human-review-runtime-boundary/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/**`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/execution_envelope.py`
- `services/runner/src/runner/artifacts.py`
- `services/conductor/**`
- `services/domain_adapters/**`
- `services/core/**`
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
- no schema changes
- no HTTP changes
- no task-intake changes
- no handoff changes
- no runner dispatcher changes
- no no-op adapter changes
- no execution envelope changes
- no UI
- no notifications
- no approval storage/persistence
- no database
- no queue
- no real execution
- no Docker/subprocess/shell/network
- no filesystem reads/writes
- no model/provider calls
- no GitHub automation
- no dependency/build changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only/schemas-only → stop
- no executable `.py` file → stop
- no test file → stop
- about to modify HTTP/task-intake → stop
- about to modify dispatcher/no-op adapter → stop
- about to add UI/notifications/persistence → stop
- about to execute anything → stop
- about to use Docker/subprocess/network/filesystem IO → stop
- about to add dependencies → stop
- about to write `.ariadne/**` or `.grace/**` → stop

## Decisions Made

### selected_strategy

Executable Python code + tests in the runner package.

### implementation_files

```
services/runner/src/runner/review_boundary.py
```

### test_files

```
services/runner/tests/test_review_boundary.py
```

### public_api

```python
derive_review_boundary(execution_request: dict, execution_result: dict) -> dict
```

### decision_shape

`schema_version`, `decision` (string enum), `requires_review`, `blocked`, `completed`, `failed` (booleans), `reason_code` (string), `reasons` (list), `execution_request_id`, `execution_result_id`, `run_id`, `approval` (normalized from request), `metadata`, `errors`, `warnings`.

### approval_input_shape

`execution_request["approval"]` can be None, a dict with `required`, `status` (`"pending"`, `"approved"`, `"denied"`), `after_execution`, `reviewer`, `reason`.

### status_semantics

10 decision rules mapping request approval + result status to final decision. Boolean convenience flags provided. Machine-readable `reason_code` included.

### error_semantics

Non-dict inputs → error decision. Missing request/result IDs → error. Missing result status → failed with warning.

### deterministic_strategy

All decisions from input fields only. No wall-clock time, no random, no UUID, no external state. Repeated calls with same input produce equal output.

### validation_strategy

17 tests covering all decision paths plus determinism, serialization, and side-effect safety.

### next_pr_notes

The next PR should integrate the review boundary into the handoff flow. After building the execution envelope, the handoff should call `derive_review_boundary(request, result)` and include the decision in the response. This makes the human-review state visible to callers of `POST /runs/execute`.

---

PLAN written: yes
