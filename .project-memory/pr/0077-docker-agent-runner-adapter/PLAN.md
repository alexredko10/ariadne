# PR 0077 — Docker Agent Runner Adapter Plan

## Goal

Plan an opt-in Docker agent runner adapter.

This PR must add executable Python code + tests.
Docs-only is invalid.
Schemas-only is invalid.
Smoke-test-only is invalid.

The Docker adapter must remain non-default.
The deterministic local/no-op test path from PR 0076 must remain unchanged.
The adapter must not require a Docker daemon for tests.
The adapter must not run Docker during planning, tests, or default execution.

## Implementation Decision

**Decision: New Docker adapter module in runner, register in dispatcher.**

### New files

1. **`services/runner/src/runner/docker_agent_adapter.py`** — Docker agent adapter.

2. **`services/runner/tests/test_docker_agent_adapter.py`** — focused tests.

### Modified files (justified)

3. **`services/runner/src/runner/adapter_registry.py`** — register the Docker adapter in `_ADAPTERS` and `get_supported_adapters()`.

**Justification for registry change:**
- The Docker adapter is not usable without being registered.
- The registry change is minimal: add one line to `_ADAPTERS` and one entry to `get_supported_adapters()`.
- The dispatcher's substring-matching strategy means `"docker-agent"` only matches when explicitly requested.
- No behavioral changes to the dispatcher itself.

**Not modified:**
- `services/task_intake/**` — no changes. test_mode still defaults to `"noop"`.
- `services/runner/src/runner/noop_adapter.py` — unchanged.
- `services/runner/src/runner/local_harness.py` — unchanged (calls dispatcher, not adapters directly).
- `services/runner/src/runner/execution_envelope.py`, `review_boundary.py` — unchanged.

## Public API

```python
# services/runner/src/runner/docker_agent_adapter.py

def run_docker_agent_execution(
    execution_request: dict,
    *,
    executor=None,
    allow_docker: bool = False,
) -> dict:
    """Run a Docker agent execution adapter.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    executor
        Callable for executing Docker commands.  If None, uses a default
        executor (currently returns a `requires_docker_daemon` result).
        In tests, inject a fake executor.
    allow_docker
        Must be True to attempt Docker execution.  Default False for safety.

    Returns
    -------
    dict
        A RunnerExecutionResult dict.
    """

def build_docker_agent_command(execution_request: dict) -> dict:
    """Build a deterministic Docker command metadata dict from an execution request.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.

    Returns
    -------
    dict
        Deterministic command metadata (never executes anything).
    """
```

## Opt-In Rule

**The adapter requires TWO things to execute:**

1. `execution_request["requested_adapter"]` must contain `"docker"` (case-insensitive substring match, handled by the dispatcher).
2. `allow_docker=True` must be passed to `run_docker_agent_execution()`.

**Without opt-in (default):**
- The adapter is never selected by the dispatcher for normal requests.
- `requested_adapter: "noop"` → no-op adapter runs (default).
- Even if selected, the adapter returns a deterministic `blocked` result with evidence that Docker is not enabled: status `"blocked"`, evidence `"Docker execution requires explicit opt-in (allow_docker=True)."`.

## Non-Default Guarantee

- The test-mode CLI defaults to `--adapter noop` (PR 0076). No change.
- The dispatcher selects `noop` unless `requested_adapter` contains `"docker"`. No change.
- The local harness calls the dispatcher, never an adapter directly. No change.
- No Docker daemon is required for tests.
- No subprocess/Docker SDK/os.system/popen is imported at module level.

## Executor Boundary

The adapter accepts an optional `executor` callable for test injection.

**Default executor:** A function that returns a standard "requires_docker_daemon" result. This is the safe default for development and test environments without Docker.

**Fake executor (for tests):** A callable that returns a deterministic dict representing what Docker would return.

**Real Docker executor (future):** A function that calls the Docker SDK or CLI. NOT IMPLEMENTED IN THIS PR.

The executor signature:
```python
def executor(command_metadata: dict) -> dict:
    # Returns a dict with at least:
    # {
    #     "exit_code": int,
    #     "stdout": str,
    #     "stderr": str,
    #     "success": bool,
    # }
```

## Docker Command Shape

`build_docker_agent_command(execution_request)` returns a deterministic dict:

```python
{
    "adapter": "docker-agent-v1",
    "container_image": "ariadne-agent-base:latest",
    "command": ["run", "agent", "--run-id", "<run_id>"],
    "workdir": "/workspace",
    "volumes": {
        "/workspace": {"bind": "/workspace", "mode": "rw"},
    },
    "environment": {
        "ARIADNE_RUN_ID": "<run_id>",
        "ARIADNE_TASK_GOAL": "<task_goal>",
        "ARIADNE_MODE": "<execution_mode>",
    },
    "network_mode": "none",
    "memory_limit": "4g",
    "cpu_count": 2,
    "timeout_seconds": 300,
}
```

All values derived deterministically from the execution request. No external calls.

## Result Shape

The adapter normalizes executor output into a `RunnerExecutionResult` dict:

```python
{
    "execution_result_id": f"{req_id}-result",
    "execution_request_id": req_id,
    "run_id": run_id,
    "status": "completed" if executor_output["success"] else "failed",
    "adapter": "docker-agent-v1",
    "artifacts": [...],
    "evidence": [
        {
            "evidence_id": f"{req_id}-docker-evidence",
            "evidence_kind": "execution_log",
            "summary": "Docker agent execution completed via executor.",
            "status": "passed" if executor_output["success"] else "failed",
        },
    ],
    "errors": [] if executor_output["success"] else [
        {"code": "execution_failed", "message": executor_output.get("stderr", "")},
    ],
    "warnings": [],
    "review_required": False,
    "next": f"/runs/{run_id}/status",
}
```

## Dispatcher Integration

In `services/runner/src/runner/adapter_registry.py`:

```python
# Add import at top
from runner.docker_agent_adapter import run_docker_agent_execution

# Add to _ADAPTERS list
_ADAPTERS: list[tuple[str, Any]] = [
    ("noop", run_noop_execution),
    ("docker", run_docker_agent_execution),
]

# Add to get_supported_adapters()
def get_supported_adapters() -> dict:
    return {
        "noop": {"version": "v1", "modes": ["dry_run", "preview"]},
        "docker-agent": {"version": "v1", "modes": ["dry_run", "execute", "preview"]},
    }
```

The dispatcher handles selection via substring matching. `requested_adapter: "docker-agent"` contains `"docker"`, so the Docker adapter is selected.

However, `run_docker_agent_execution` checks `allow_docker` internally. Without it, the adapter returns a "Docker not enabled" blocked result. This is a safety belt at the adapter level, not at the dispatcher level.

## Local/Test-Mode Preservation

- `python -m task_intake.test_mode --task "test"` still uses `requested_adapter: "noop"` (default). No change.
- `python -m task_intake.test_mode --task "test" --adapter docker-agent` would select the Docker adapter, which would return `blocked` (because `allow_docker` defaults to False). The user would need to modify the adapter code or inject a fake executor to get a completed result.
- The local harness (`run_local_execution_harness`) calls the dispatcher, which selects the Docker adapter only when explicitly requested. No change to harness behavior.

## Test Plan

**Test file:** `services/runner/tests/test_docker_agent_adapter.py`

| Test | Expectation |
|---|---|
| `test_no_opt_in_blocks` | No allow_docker → blocked result |
| `test_opt_in_with_fake_executor_completes` | allow_docker=True + fake executor → completed |
| `test_fake_executor_failure_returns_failed` | allow_docker=True + fake failing executor → failed |
| `test_build_command_returns_deterministic_dict` | build_docker_agent_command returns expected shape |
| `test_build_command_ids_match_request` | command metadata uses same run_id/ids as request |
| `test_result_json_serializable` | passes json.dumps(sort_keys=True) |
| `test_deterministic` | repeated calls with same executor output return equal result |
| `test_adapter_not_importing_subprocess` | module does not import subprocess/Docker SDK |
| `test_noop_default_unchanged` | test_mode with default adapter returns no-op result (via test_mode.py test) |

**Registry integration tests (in `test_adapter_registry.py`):**

Add a test:
- `test_get_supported_adapters_includes_docker` — `"docker-agent"` in returned dict.

## Validation Commands

```bash
git status --short
git diff --name-only
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  services/task_intake/tests/test_test_mode.py \
  -q
python -m compileall -f services/runner/src services/task_intake/src

# Verify test-mode default is unchanged
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.test_mode --task "Ariadne test run" --json

# Forbidden pattern guard
grep -R -n "subprocess|os\.system|popen|requests|httpx|urllib|socket|redis|sqlite|import docker|from docker|docker\.from_env|importlib|pkg_resources|entry_points|git |uuid|datetime\.now|time\.time|random|water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|\.grace|@grace-\|old Flask" \
  services/runner/src/runner/docker_agent_adapter.py \
  services/runner/tests/test_docker_agent_adapter.py || true
grep -R -n "open(\\|write(\\|Path(\\|read_text(\\|write_text(" \
  services/runner/src/runner/docker_agent_adapter.py \
  services/runner/tests/test_docker_agent_adapter.py || true
grep -R -n "\\$(" \
  services/runner/src/runner/docker_agent_adapter.py \
  services/runner/tests/test_docker_agent_adapter.py || true
```

## Future Allowed Write Paths

- `services/runner/src/runner/docker_agent_adapter.py` (new)
- `services/runner/tests/test_docker_agent_adapter.py` (new)
- `services/runner/src/runner/adapter_registry.py` (modify)
- `services/runner/tests/test_adapter_registry.py` (modify)

Precommit review may later write only:
- `.project-memory/pr/0077-docker-agent-runner-adapter/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0077-docker-agent-runner-adapter/PLAN.md` (planner only)
- `.project-memory/pr/0077-docker-agent-runner-adapter/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/task_intake/**`
- `services/runner/src/runner/noop_adapter.py`
- `services/runner/src/runner/local_harness.py`
- `services/runner/src/runner/execution_envelope.py`
- `services/runner/src/runner/review_boundary.py`
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

- docs-only/schemas-only/smoke-test-only outcome
- no executable Python file selected
- no test file selected
- Docker adapter becomes default
- PR requires Docker daemon for tests
- PR runs docker/docker compose during validation
- PR imports subprocess/os.system/popen
- PR imports Docker SDK or adds dependency
- PR modifies test-mode/local/no-op path as default behavior
- PR writes Dockerfiles or docker/**
- PR adds network/filesystem IO
- PR adds persistence/queue/database
- PR adds model/provider calls
- PR changes dependencies/build config
- PR writes `.ariadne/**` or `.grace/**`
- legacy examples/names appear
- shell placeholders appear

## Decisions Made

### selected_strategy

Executable Python + tests. New Docker adapter module. Register in dispatcher. Fake executor for tests.

### implementation_files

```
services/runner/src/runner/docker_agent_adapter.py (new)
services/runner/src/runner/adapter_registry.py (modify)
```

### test_files

```
services/runner/tests/test_docker_agent_adapter.py (new)
services/runner/tests/test_adapter_registry.py (modify)
```

### public_api

```python
run_docker_agent_execution(execution_request, *, executor=None, allow_docker=False) -> dict
build_docker_agent_command(execution_request) -> dict
```

### opt_in_rule

Two-layer opt-in:
1. Executor-level: `requested_adapter` must contain `"docker"` (dispatcher handles selection).
2. Adapter-level: `allow_docker=True` must be passed to `run_docker_agent_execution()`.

### non_default_rule

Default adapter remains `"noop"`. test_mode CLI defaults to `--adapter noop`. Dispatcher only selects Docker when explicitly requested. Adapter returns `blocked` without `allow_docker=True`.

### executor_boundary

Default executor returns `requires_docker_daemon` blocked result. Fake executor injected for tests. Real Docker executor deferred. Executor signature: `fn(command_metadata: dict) -> dict`.

### docker_command_shape

Deterministic dict with container_image, command, workdir, volumes, environment, network_mode (none), resource limits, timeout. All derived from execution request fields.

### result_shape

Standard `RunnerExecutionResult` with adapter `"docker-agent-v1"`, evidence, and errors based on executor output.

### dispatcher_integration

Add `("docker", run_docker_agent_execution)` to `_ADAPTERS`. Add `"docker-agent"` entry to `get_supported_adapters()`.

### local_test_mode_preservation

No changes to test_mode defaults, harness, or noop adapter. `--adapter noop` remains default.

### validation_strategy

8 focused tests + registry integration test + existing test compat + CLI validation + forbidden pattern guards.

### next_pr_notes

After PR 0077, the Docker adapter structure is in place but not yet executing real Docker. The next PR should add the real Docker executor (using `subprocess.run` or Docker SDK) behind the `allow_docker=True` flag, and add Dockerfiles for the agent container images.

---

PLAN written: yes
