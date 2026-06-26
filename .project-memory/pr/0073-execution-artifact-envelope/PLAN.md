# PR 0073 — Execution Artifact Envelope Plan

## Goal

Plan executable behavior for a deterministic execution artifact/evidence envelope runtime object.

This PR must add code and tests.
This PR must not be docs-only.
This PR must not be schemas-only.

The envelope must normalize artifact and evidence metadata from execution request/result data into a JSON-serializable runtime object.

## Product Direction

PR 0069 proved deterministic runner adapter output.
PR 0070 proved deterministic adapter dispatch.
PR 0071 connected mock run to runner dispatcher.
PR 0072 exposed that path over HTTP.
PR 0073 adds the runtime envelope layer that future execution flows can use to represent artifacts and evidence consistently.

This PR does not collect files yet.
This PR does not write artifact manifests yet.
This PR does not connect the envelope to HTTP yet.

## Implementation Location Decision

**Decision: New module in the runner package.**

### Implementation file

1. **`services/runner/src/runner/execution_envelope.py`** — envelope module.

### Test file

2. **`services/runner/tests/test_execution_envelope.py`** — focused tests.

**Rationale:** The envelope normalizes execution request/result data that lives in the runner layer (contract schemas, adapter output). It does not depend on task_intake.

**Not modified:**
- `noop_adapter.py`, `adapter_registry.py`, `artifacts.py`, `models.py` — no changes.
- `services/task_intake/**` — no changes.
- `schemas/`, `docs/` — no changes.

## Public Functions

```python
def build_execution_envelope(
    execution_request: dict,
    execution_result: dict,
) -> dict:
    """Build a deterministic execution envelope from request and result.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    execution_result
        The RunnerExecutionResult dict.

    Returns
    -------
    dict
        A normalized envelope dict.
    """
```

## Envelope Shape

```python
{
    "schema_version": "0.1",
    "envelope_id": "env_<sha256[:12]>",
    "execution_request_id": "<from request>",
    "execution_result_id": "<from result>",
    "run_id": "<from request>",
    "status": "<from result>",
    "artifacts": [...],
    "evidence": [...],
    "errors": [...],
    "warnings": [...],
    "metadata": {
        "adapter": "<from result>",
        "execution_mode": "<from request>",
    },
}
```

**Envelope ID:** `env_<first 12 hex chars of sha256(execution_request_id + execution_result_id)>` — deterministic, stdlib-only.

## Artifact Normalization

**Input:** `execution_result["artifacts"]` — list of dicts from the runner execution result.

**Normalization rules:**
- `artifact_id` — if present in source, preserve. If missing, fill with `"artifact-{execution_result_id}-{index}"`.
- `kind` — preserve as-is.
- `reference` — preserve as-is.
- `relative_path` — preserve as-is. If the raw data uses `"path"` instead of `"relative_path"`, alias to `relative_path`.
- `digest` — preserve only if non-empty. Do not compute from filesystem.
- `producer` — preserve as-is. If missing, set to `"execution_adapter"`.
- Warning if `relative_path` is an absolute path (starts with `/`). Do not reject — envelope is metadata-only.

**Output:** Normalized list of artifact dicts.

## Evidence Normalization

**Input:** `execution_result["evidence"]` — list of dicts from the runner execution result.

**Normalization rules:**
- `evidence_id` — if present in source, preserve. If missing, fill with `"evidence-{execution_result_id}-{index}"`.
- `kind` — preserve as-is.
- `summary` — preserve as-is.
- `status` — preserve as-is (one of: passed, failed, warning, skipped, not_run).
- `producer` — preserve as-is. If missing, set to `"execution_adapter"`.
- `supports` — preserve as-is if present.
- Do not require chain-of-thought or model internals.
- Do not read logs or files from disk.

**Output:** Normalized list of evidence dicts.

## Error Semantics

| Condition | Behavior |
|---|---|
| Valid request + result dicts | Returns envelope with `status` from result |
| `execution_request` is not a dict | Returns `{"envelope_id": "", "status": "failed", "errors": [...]}` |
| `execution_result` is not a dict | Returns `{"envelope_id": "", "status": "failed", "errors": [...]}` |
| Missing `execution_request_id` | Returns error: "execution_request_id is required" |
| Missing `execution_result_id` | Returns error: "execution_result_id is required" |
| Missing `run_id` | Returns error: "run_id is required" |
| Artifact with absolute `relative_path` | Warning field added to artifact; envelope still builds |
| Non-list `artifacts` input | Treat as empty list |
| Non-list `evidence` input | Treat as empty list |
| Repeated calls with same input | Return equal dicts |

Error shape:
```python
{
    "code": "invalid_envelope_input",
    "message": "Human-readable description.",
    "field": "<field name>",
}
```

## Test Plan

**Test file:** `services/runner/tests/test_execution_envelope.py`

| Test | Expectation |
|---|---|
| `test_valid_input_builds_envelope` | returns envelope with all sections |
| `test_envelope_includes_request_id` | envelope.execution_request_id matches input |
| `test_envelope_includes_result_id` | envelope.execution_result_id matches input |
| `test_envelope_includes_run_id` | envelope.run_id matches input |
| `test_envelope_status_matches_result` | envelope.status == result.status |
| `test_artifacts_normalized` | artifacts present as list |
| `test_evidence_normalized` | evidence present as list |
| `test_missing_artifact_ids_filled` | artifact without id gets deterministic id |
| `test_missing_evidence_ids_filled` | evidence without id gets deterministic id |
| `test_envelope_deterministic` | repeated calls return equal output |
| `test_json_serializable` | passes json.dumps(sort_keys=True) |
| `test_invalid_request_not_dict` | returns error envelope |
| `test_invalid_result_not_dict` | returns error envelope |
| `test_missing_execution_request_id` | returns error |
| `test_missing_execution_result_id` | returns error |
| `test_missing_run_id` | returns error |
| `test_absolute_path_warning` | artifact with `/tmp/file` gets warning |
| `test_non_list_artifacts_treated_as_empty` | None/null → empty list |
| `test_non_list_evidence_treated_as_empty` | None/null → empty list |
| `test_no_side_effects` | no filesystem/Docker/subprocess/network/uuid/datetime imports |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_execution_envelope.py services/runner/tests/test_adapter_registry.py services/runner/tests/test_noop_adapter.py -q
python -m compileall -f services/runner/src
grep -R -n "open(\\|write(\\|Path(\\|read_text(\\|write_text(\\|subprocess|os\\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |uuid|datetime\\.now|time\\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\\.grace|@grace-\|old Flask" services/runner/src/runner/execution_envelope.py services/runner/tests/test_execution_envelope.py || true
grep -R -n "\$(" services/runner/src/runner/execution_envelope.py services/runner/tests/test_execution_envelope.py || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/execution_envelope.py`
- `services/runner/tests/test_execution_envelope.py`

Precommit review may later write only:
- `.project-memory/pr/0073-execution-artifact-envelope/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0073-execution-artifact-envelope/PLAN.md` (planner only)
- `.project-memory/pr/0073-execution-artifact-envelope/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/**`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/artifacts.py`
- `services/runner/src/runner/models.py`
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
- no execution contract changes
- no HTTP changes
- no task-intake changes
- no handoff behavior changes
- no runner dispatcher changes
- no no-op adapter changes
- no existing artifact store rewrite
- no filesystem artifact collection
- no artifact manifest writing
- no file digest computation from disk
- no runtime filesystem reads/writes
- no real execution
- no Docker adapter
- no subprocess/shell/network
- no plugin discovery/dynamic imports
- no queue/persistence/database
- no model calls/provider integration
- no dependency/build changes
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to produce docs-only/schemas-only → stop
- no executable `.py` file → stop
- no test file → stop
- about to modify HTTP endpoint → stop
- about to modify task-intake handoff → stop
- about to modify runner dispatcher → stop
- about to modify no-op adapter → stop
- about to modify existing artifact store → stop
- about to implement filesystem artifact collection → stop
- about to read files at runtime → stop
- about to write files at runtime → stop
- about to compute digest from filesystem content → stop
- about to implement real runner execution → stop
- about to implement Docker adapter → stop
- about to add Docker files → stop
- about to call subprocess/shell → stop
- about to use network libraries → stop
- about to add plugin discovery/dynamic imports → stop
- about to add persistence/queue/database → stop
- about to add dependencies → stop
- about to modify schemas/docs as primary output → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- old names/examples → stop
- shell placeholders → stop

## Decisions Made

### selected_strategy

Executable Python code + tests in the runner package.

### implementation_files

```
services/runner/src/runner/execution_envelope.py
```

### test_files

```
services/runner/tests/test_execution_envelope.py
```

### public_functions

```python
build_execution_envelope(execution_request: dict, execution_result: dict) -> dict
```

### envelope_shape

`schema_version`, `envelope_id`, `execution_request_id`, `execution_result_id`, `run_id`, `status`, `artifacts`, `evidence`, `errors`, `warnings`, `metadata` (with adapter and execution_mode).

### artifact_shape

`artifact_id` (deterministic fill if missing), `kind`, `reference`, `relative_path`, `digest` (preserved if present), `producer` (defaults to `"execution_adapter"`). Warning if absolute path.

### evidence_shape

`evidence_id` (deterministic fill if missing), `kind`, `summary`, `status`, `producer` (defaults to `"execution_adapter"`), `supports` (preserved if present).

### error_semantics

Non-dict inputs → error envelope. Missing required IDs → error envelope. Non-list artifacts/evidence → treated as empty. Absolute paths → warning (not rejection).

### deterministic_id_strategy

Envelope ID: `env_<sha256(execution_request_id + execution_result_id)[:12]>`.
Artifact ID (filled): `artifact-{execution_result_id}-{index}`.
Evidence ID (filled): `evidence-{execution_result_id}-{index}`.

### validation_strategy

19 tests covering valid input, all required fields, determinism, JSON serialization, missing data handling, absolute path warning, side-effect safety.

### next_pr_notes

The next PR should integrate the envelope into the handoff flow. After calling `dispatch_execution` and getting the result, the handoff should call `build_execution_envelope` and include the envelope in the response alongside or instead of the raw execution result. This gives callers a normalized envelope rather than raw adapter output.

---

PLAN written: yes
