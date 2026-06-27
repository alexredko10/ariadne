# PR 0076 — Test Mode Execution Entrypoint Plan

## Goal

Plan a runnable Ariadne test-mode execution entrypoint.

This PR must make Ariadne runnable in local test mode from one command, not merely add smoke tests.

Definition of done after implementation:

A user can run:

```
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json
```

and receive a deterministic JSON result containing:

- ok
- runtime_status
- execution_request
- execution_result
- execution_envelope
- review_boundary
- errors
- warnings

## Implementation Decision

**Decision: New test_mode module in task_intake, directly runnable.**

### New files

1. **`services/task_intake/src/task_intake/test_mode.py`** — test mode execution entrypoint.

2. **`services/task_intake/tests/test_test_mode.py`** — focused tests.

**No `__main__.py` needed.** The module is runnable directly via `python -m task_intake.test_mode` using a standard `if __name__ == "__main__": main()` block. This is simpler than adding a `__main__.py` that would need to be kept in sync with subcommands.

**No changes to existing files.** The test mode calls the existing handoff path (`run_mock_execution_handoff`). It doesn't modify server.py, execution_handoff.py, local_harness.py, or any runner modules.

## Public API

```python
# services/task_intake/src/task_intake/test_mode.py

def run_test_mode(payload: dict) -> dict:
    """Run Ariadne in test mode with a given payload.

    Parameters
    ----------
    payload
        A dict with at least a ``task`` string.  May also include
        ``requested_adapter``, ``execution_mode``, ``execution_approval``.

    Returns
    -------
    dict
        Deterministic test-mode result from the execution handoff path.
    """

def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for test mode.

    Parameters
    ----------
    argv
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = success).
    """
```

## CLI Command

```
python -m task_intake.test_mode --task "Ariadne test run"
python -m task_intake.test_mode --task "Ariadne test run" --json
python -m task_intake.test_mode --task "Ariadne test run" --json --adapter noop --mode dry_run
```

**CLI arguments:**

| Argument | Type | Required | Description |
|---|---|---|---|
| `--task` / `-t` | string | Yes | Task description text |
| `--json` | flag | No | Print JSON output to stdout |
| `--adapter` | string | No | Adapter id (default `"noop"`) |
| `--mode` | string | No | Execution mode (default `"dry_run"`) |
| `--approval-status` | string | No | Approval status: `"not_required"`, `"pending"`, `"approved"`, `"denied"` |

**Behavior:**
1. Parse arguments.
2. Build payload dict: `{"task": "<task text>", "requested_adapter": "...", "execution_mode": "...", "execution_approval": {...}}`.
3. Call `run_test_mode(payload)`.
4. If `--json` flag, print JSON to stdout.
5. Return 0 on success, 1 on CLI error, handler error, or invalid payload.

## Payload Shape

```python
{
    "task": "Implement JWT authentication middleware",
    "requested_adapter": "noop",
    "execution_mode": "dry_run",
    "execution_approval": None,  # or {"required": True, "status": "pending"}
}
```

The `run_test_mode()` function maps `payload["task"]` to the `raw_task` field expected by `run_mock_execution_handoff` and calls it with the appropriate execution overrides.

## Response Shape

```python
{
    "ok": True,
    "mode": "test",
    "runtime_status": "completed",
    "execution_request": {...},        # RunnerExecutionRequest
    "execution_result": {...},         # RunnerExecutionResult from no-op adapter
    "execution_envelope": {...},       # from build_execution_envelope
    "review_boundary": {...},          # from derive_review_boundary
    "errors": [],
    "warnings": [],
    "metadata": {
        "entrypoint": "test_mode",
        "version": "0.1",
    },
}
```

When `--json` is used, the CLI prints `json.dumps(result, indent=2, sort_keys=True)`.

## Handoff Usage

`run_test_mode()` calls `run_mock_execution_handoff()` from `execution_handoff.py`. It does NOT call any runner module directly. This ensures the test mode exercises the same code path as the HTTP `POST /runs/execute` endpoint.

```python
def run_test_mode(payload: dict) -> dict:
    # Map payload to handoff input
    raw = {
        "raw_task": payload.get("task", ""),
        "requested_adapter": payload.get("requested_adapter", "noop"),
        "execution_mode": payload.get("execution_mode", "dry_run"),
    }
    # Add approval if provided
    approval_status = payload.get("execution_approval")
    if approval_status:
        raw["execution_approval"] = approval_status

    # Call handoff
    handoff_result = run_mock_execution_handoff(raw)

    # Build test mode response
    return {
        "ok": handoff_result.get("ok", False),
        "mode": "test",
        "runtime_status": handoff_result.get("runtime_status") or (
            "error" if not handoff_result.get("ok") else "unknown"
        ),
        "execution_request": handoff_result.get("execution_request"),
        "execution_result": handoff_result.get("execution_result"),
        "execution_envelope": handoff_result.get("execution_envelope"),
        "review_boundary": handoff_result.get("review_boundary"),
        "errors": handoff_result.get("errors", []),
        "warnings": handoff_result.get("warnings", []),
        "metadata": {"entrypoint": "test_mode", "version": "0.1"},
    }
```

## Test Plan

**Test file:** `services/task_intake/tests/test_test_mode.py`

| Test | Expectation |
|---|---|
| `test_run_test_mode_returns_ok` | Valid task → ok: true |
| `test_run_test_mode_mode_is_test` | response.mode == "test" |
| `test_run_test_mode_has_runtime_status` | runtime_status present |
| `test_run_test_mode_has_execution_request` | execution_request present |
| `test_run_test_mode_has_execution_result` | execution_result present with completed status |
| `test_run_test_mode_has_execution_envelope` | execution_envelope present |
| `test_run_test_mode_has_review_boundary` | review_boundary present |
| `test_run_test_mode_deterministic` | Repeated calls return equal output |
| `test_run_test_mode_json_serializable` | Passes json.dumps(sort_keys=True) |
| `test_main_cli_with_task_returns_0` | `main(["--task", "test"])` returns 0 |
| `test_main_cli_prints_json` | `main(["--task", "test", "--json"])` returns 0 |
| `test_main_cli_missing_task_returns_1` | `main([])` returns 1 |
| `test_main_cli_invalid_approval_returns_1` | Bad approval value → 1 |
| `test_no_direct_runner_call` | test_mode does not import runner modules directly |
| `test_no_side_effects` | No filesystem/Docker/subprocess imports |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_test_mode.py \
  services/task_intake/tests/test_execution_handoff.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_review_boundary.py \
  services/runner/tests/test_execution_envelope.py \
  -q
python -m compileall -f services/task_intake/src services/runner/src

# Test the actual CLI command
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json

grep -R -n "subprocess|os\.system|popen|docker|docker compose|Dockerfile|requests|httpx|urllib|socket|redis|sqlite|importlib|pkg_resources|entry_points|git |uuid|datetime\.now|time\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/test_mode.py \
  services/task_intake/tests/test_test_mode.py || true
grep -R -n "open(\\|write(\\|Path(\\|read_text(\\|write_text(" \
  services/task_intake/src/task_intake/test_mode.py \
  services/task_intake/tests/test_test_mode.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/test_mode.py \
  services/task_intake/tests/test_test_mode.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/test_mode.py`
- `services/task_intake/tests/test_test_mode.py`

Precommit review may later write only:
- `.project-memory/pr/0076-test-mode-execution-entrypoint/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0076-test-mode-execution-entrypoint/PLAN.md` (planner only)
- `.project-memory/pr/0076-test-mode-execution-entrypoint/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/src/task_intake/execution_handoff.py`
- `services/runner/**`
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

## Stop Conditions

- docs-only or schemas-only outcome
- smoke-test-only outcome
- no runnable CLI/test-mode entrypoint
- no Python implementation file selected
- no test file selected
- broad write paths
- new HTTP route
- server.py change without narrow justification
- bypassing handoff path
- direct runner/no-op adapter call from test_mode
- Docker/subprocess/network/filesystem IO
- real agent execution
- model/provider calls
- persistence/queue/database
- dependency/build changes
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Executable Python + tests. New test_mode module in task_intake, directly runnable via `python -m task_intake.test_mode`. Calls existing handoff path.

### implementation_files

```
services/task_intake/src/task_intake/test_mode.py
```

### test_files

```
services/task_intake/tests/test_test_mode.py
```

### public_api

```python
run_test_mode(payload: dict) -> dict
main(argv: list[str] | None = None) -> int
```

### cli_command

```
python -m task_intake.test_mode --task "Ariadne test run" [--json] [--adapter noop] [--mode dry_run] [--approval-status pending]
```

### payload_shape

`task` (required), `requested_adapter` (default `"noop"`), `execution_mode` (default `"dry_run"`), `execution_approval` (optional dict).

### response_shape

`ok`, `mode: "test"`, `runtime_status`, `execution_request`, `execution_result`, `execution_envelope`, `review_boundary`, `errors`, `warnings`, `metadata`.

### handoff_usage

Calls `run_mock_execution_handoff(raw)`. Does NOT call any runner module directly.

### validation_strategy

15 tests covering callable, CLI, determinism, serialization, side-effect safety. Full compatibility with handoff, HTTP, harness, envelope, and review boundary tests. Actual CLI invocation as validation.

### next_pr_notes

With PR 0076, Ariadne is runnable from a single CLI command. The next PR could add a richer local execution adapter (beyond no-op) that performs simple file operations, or add a `--plan` mode that shows the full pipeline output without execution.

---

PLAN written: yes
