# PR 0078 — Local App Runtime Entrypoint Plan

## Goal

Plan the minimal local running state for Ariadne as an app runtime.

This PR must make the existing task-intake app runnable locally from one command and preserve the existing `/runs/execute` HTTP path.

Definition of done after implementation:

A developer can run:

```
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --host 127.0.0.1 --port 8000
```

Then call the existing endpoint:

```bash
curl -X POST http://127.0.0.1:8000/runs/execute \
  -H "content-type: application/json" \
  -d '{"task":"Ariadne local app run"}'
```

The response must include:
- ok
- runtime_status
- execution_request
- execution_result
- execution_envelope
- review_boundary
- errors
- warnings
- metadata

## Implementation Decision

**Decision: Add runtime entrypoint to existing `app.py`, add focused test.**

### Modified file

1. **`services/task_intake/src/task_intake/app.py`** — add `main(argv)` and `if __name__ == "__main__":` block.

### New test file

2. **`services/task_intake/tests/test_app_runtime.py`** — tests for the runtime entrypoint.

**Not modified:**
- `server.py` — no changes. The ASGI app is imported from server.py.
- `test_mode.py`, `execution_handoff.py` — no changes.
- `services/runner/**` — no changes.
- `schemas/`, `docs/` — no changes.
- `pyproject.toml` — uvicorn is already a dependency.

## Public API

```python
# app.py (modified)

def build_runtime_config(argv: list[str] | None = None) -> dict:
    """Build a deterministic runtime config dict from CLI arguments.

    Parameters
    ----------
    argv
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    dict
        A deterministic config dict with host, port, and check mode flag.
    """

def main(argv: list[str] | None = None) -> int:
    """Local app runtime entrypoint.

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

## Runtime Command

```
python -m task_intake.app --host 127.0.0.1 --port 8000
```

Host defaults to `127.0.0.1`, port defaults to `8000`.

The `main()` function:
1. Calls `build_runtime_config(argv)` to parse arguments.
2. If `--check` or `--check --json` is set, prints config as JSON and returns 0 (non-blocking).
3. Otherwise, imports `uvicorn` and the ASGI `app` from `server.py`.
4. Starts uvicorn with config.host and config.port.

## Check Command

```
python -m task_intake.app --check --json
```

Returns JSON config without starting the server:

```json
{
  "service": "task_intake",
  "host": "127.0.0.1",
  "port": 8000,
  "routes": ["/health", "/submit", "/task-intake/submit", "/task-intake/normalize", "/context/preview", "/runs", "/mock-loop", "/runs/execute"],
  "dependencies": ["uvicorn"],
  "default_adapter": "noop",
  "status": "ready"
}
```

The `--check` flag enables non-blocking validation of the runtime configuration.

## CLI Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--host` | string | `"127.0.0.1"` | Bind address |
| `--port` | int | `8000` | Bind port |
| `--check` | flag | False | Print config as JSON and exit (non-blocking) |
| `--json` | flag | False (implied by --check) | Format output as JSON |

## Existing Route Usage

The runtime **does not add any new routes**. It serves the existing ASGI application from `server.py`, which already has `/runs/execute`.

The `/runs/execute` endpoint accepts:
```json
{"task": "Ariadne local app run"}
```

And returns the full handoff response (via `execution_handoff.py` → `local_harness.py` → `adapter_registry.py` → `noop_adapter.py`).

## Test Plan

**Test file:** `services/task_intake/tests/test_app_runtime.py`

Tests use `argparse` and `build_runtime_config` — they do NOT start the server. Tests avoid binding real ports.

| Test | Expectation |
|---|---|
| `test_build_config_defaults` | No args → host=127.0.0.1, port=8000 |
| `test_build_config_custom` | Custom host/port → parsed correctly |
| `test_build_config_check` | --check → check=True |
| `test_build_config_check_json` | --check --json → check=True |
| `test_check_output_contains_routes` | --check JSON includes /runs/execute |
| `test_check_output_contains_service` | --check JSON includes service name |
| `test_check_output_default_adapter` | --check JSON includes "noop" |
| `test_check_no_server_start` | build_runtime_config returns dict, doesn't start server |
| `test_invalid_port` | Non-integer port → error |
| `test_mode_still_works` | `test_mode.main(["--task", "test", "--json"])` returns 0 |
| `test_no_docker_default` | Docker adapter not selected by default |

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/task_intake/tests/test_app_runtime.py \
  services/task_intake/tests/test_execution_handoff_http.py \
  services/task_intake/tests/test_test_mode.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_docker_agent_adapter.py \
  -q
python -m compileall -f services/task_intake/src services/runner/src

# Check command (non-blocking)
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json

# Test-mode still works
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json

# Forbidden pattern guard
grep -R -n "subprocess|os\.system|popen|docker compose|Dockerfile|requests|httpx|urllib|redis|sqlite|import docker|from docker|docker\.from_env|uuid|datetime\.now|time\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/task_intake/src/task_intake/app.py \
  services/task_intake/tests/test_app_runtime.py || true
grep -R -n "\\$(" \
  services/task_intake/src/task_intake/app.py \
  services/task_intake/tests/test_app_runtime.py || true
```

## Future Allowed Write Paths

- `services/task_intake/src/task_intake/app.py` (modify)
- `services/task_intake/tests/test_app_runtime.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0078-local-app-runtime-entrypoint/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0078-local-app-runtime-entrypoint/PLAN.md` (planner only)
- `.project-memory/pr/0078-local-app-runtime-entrypoint/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/src/task_intake/test_mode.py`
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
- no executable Python implementation file selected
- no app runtime entrypoint selected
- no test file selected
- no non-blocking `--check --json` validation path
- new `/runs/execute` route instead of using existing route
- bypassing execution_handoff/local_harness
- Docker adapter becomes default
- Docker daemon required
- Docker command required
- real agent execution required
- model/provider call required
- dependency/build change required
- broad write paths
- `.ariadne/**` or `.grace/**`
- legacy examples/names
- shell placeholders

## Decisions Made

### selected_strategy

Add runtime entrypoint to existing `app.py` using uvicorn. No new routes. Non-blocking `--check --json` mode.

### implementation_files

```
services/task_intake/src/task_intake/app.py (modify)
```

### test_files

```
services/task_intake/tests/test_app_runtime.py (new)
```

### public_api

```python
build_runtime_config(argv) -> dict
main(argv) -> int
```

### runtime_command

```
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --host 127.0.0.1 --port 8000
```

### check_command

```
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
```

### existing_route_usage

The runtime serves the existing ASGI `app` from `server.py`. No new routes. `/runs/execute` is preserved.

### request_shape

```json
{"task": "Ariadne local app run"}
```

Same shape as the test-mode payload. Passed to `run_mock_execution_handoff`.

### response_shape

Same shape as `/runs/execute` response: `ok`, `runtime_status`, `execution_request`, `execution_result`, `execution_envelope`, `review_boundary`, `errors`, `warnings`, `metadata`.

### local_test_mode_preservation

No changes to `test_mode.py`. `--adapter noop` remains default.

### docker_adapter_preservation

No changes. Docker adapter remains opt-in via `requested_adapter` containing `"docker"`. Default remains `"noop"`.

### validation_strategy

11 focused tests + full compatibility across all runner and task_intake test modules + CLI check command + test-mode CLI.

### next_pr_notes

After PR 0078, Ariadne runs as a local HTTP app with the full deterministic pipeline. The next PR could add a hello-world demo page or provide a richer startup config file for the runtime.

---

PLAN written: yes
