# PR 0094 — Docker Execution Wiring Plan

## Goal

Wire real Docker execution behind a layered opt-in:
1. New subprocess-based executor module in the runner package.
2. Registry-level wiring driven by per-request `allow_docker` flag plus independent environment master switch.
3. Explicit UI opt-in control that sends `allow_docker` in the POST body and replaces the hardcoded boundary copy with status-conditional text.

**No** existing contract, function signature, or test is modified — only additions behind new and modified files.

---

## Files

### New implementation files

- `services/runner/src/runner/docker_subprocess_executor.py`

### Modified implementation files

- `services/runner/src/runner/adapter_registry.py`
- `services/task_intake/src/task_intake/server.py`

### New test files

- `services/runner/tests/test_docker_subprocess_executor.py`

### Extended test files

- `services/runner/tests/test_adapter_registry.py` — add new test class only; **do not modify existing tests**
- `services/task_intake/tests/test_local_runner_selection.py` — add new test class only; **do not modify existing tests**

### Immutable files (must not be modified by implementation)

- `services/runner/src/runner/docker_agent_adapter.py` — contract, signature, imports, and `test_no_forbidden_imports` must remain unchanged
- `services/runner/tests/test_docker_agent_adapter.py` — all existing tests must pass unchanged
- `services/runner/src/runner/local_harness.py` — unchanged
- `services/runner/src/runner/noop_adapter.py` — unchanged
- `services/runner/src/runner/execution_envelope.py` — unchanged
- `services/runner/src/runner/review_boundary.py` — unchanged
- `services/runner/tests/test_local_harness.py` — unchanged
- `services/task_intake/tests/test_execution_handoff_http.py` — unchanged
- `services/task_intake/tests/test_task_intake_http.py` — unchanged
- `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*` — unchanged

### Forbidden implementation write paths

Any file not explicitly listed in "New implementation files" or "Modified implementation files" above. In particular, `docker_agent_adapter.py` and `test_docker_agent_adapter.py` are strictly off-limits.

---

## Phase 1: `docker_subprocess_executor.py` (new module)

**Location:** `services/runner/src/runner/docker_subprocess_executor.py`

**Public API:** A single function matching `Callable[[dict], dict]`:

```python
def run_docker_subprocess(command_metadata: dict) -> dict
```

**Input shape** — the dict produced by `build_docker_agent_command()` in `docker_agent_adapter.py`:
- `container_image: str` — Docker image name/tag
- `container_command: list[str]` — already a list of command parts
- `workdir: str` — working directory path
- `volumes: dict[str, dict]` — volume mount specs
- `environment: dict[str, str]` — env vars
- `network_mode: str` — network mode
- `memory_limit: str` — memory limit
- `cpu_count: int` — CPU count
- `timeout_seconds: int` — timeout in seconds

**Output shape** (same dict shape used by existing `_fake_successful_executor` / `_fake_failing_executor` in test_docker_agent_adapter.py):
```python
{"exit_code": int, "stdout": str, "stderr": str, "success": bool}
```

**argv construction** — build a list-form argument list from `command_metadata`:

```python
argv = ["docker", "run", "--rm"]
if workdir:
    argv += ["--workdir", workdir]
# volumes is a dict of {host_path: {bind: container_path, mode: ...}}
for host_path, vol_cfg in volumes.items():
    container_path = vol_cfg.get("bind", "")
    mode = vol_cfg.get("mode", "")
    bind_spec = f"{host_path}:{container_path}"
    if mode:
        bind_spec += f":{mode}"
    argv += ["--volume", bind_spec]
for key, val in environment.items():
    argv += ["--env", f"{key}={val}"]
if network_mode:
    argv += ["--network", network_mode]
if memory_limit:
    argv += ["--memory", memory_limit]
if cpu_count:
    argv += ["--cpus", str(cpu_count)]
argv.append(container_image)
argv.extend(container_command)   # container_command is already a list
```

**Non-negotiable security rules:**
- `subprocess.run(argv, capture_output=True, text=True, timeout=timeout_seconds)` — list-form only
- `shell=True` is **never** used under any code path
- Shell commands are **never** built via string interpolation or string concatenation
- All arguments are passed as list elements

**Timeout handling:**
```python
import subprocess

def run_docker_subprocess(command_metadata: dict) -> dict:
    # ... build argv as list ...
    timeout = command_metadata.get("timeout_seconds", 300)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Docker execution timed out after {timeout} seconds",
            "success": False,
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Docker executable not found. Is Docker installed and in PATH?",
            "success": False,
        }
```

- `subprocess.TimeoutExpired` is caught and returns a structured failure — never an uncaught exception.
- `FileNotFoundError` is caught for when the `docker` binary is absent.
- No `check=True` — non-zero exit codes are communicated through the return dict, not exceptions.

**Import rules:**
- `import subprocess` is correct and expected for this module.
- The module must NOT import from `task_intake`, `task_intake.*`, or any HTTP-layer module.

---

## Phase 2: `adapter_registry.py` modification

**Add top-level imports:**

```python
import os

from runner.docker_subprocess_executor import run_docker_subprocess
```

**Source-string conflict check result:** The existing `test_no_forbidden_imports` in `test_adapter_registry.py` inspects the *source text* of only `dispatch_execution` and `get_supported_adapters` via `inspect.getsource()`. A module-level `import` statement does NOT appear in those functions' source. Therefore, adding `from runner.docker_subprocess_executor import run_docker_subprocess` at the top level is safe and does not violate any existing test.

The `os.environ` access is also safe — reading an env var is not "subprocess" or "filesystem access" as constrained by the module docstring.

**Add wrapper function `_dispatch_docker_agent(execution_request: dict) -> dict`:**

```python
def _dispatch_docker_agent(execution_request: dict) -> dict:
    """Dispatch docker-agent with dual-gate opt-in.

    Both ``execution_request.allow_docker`` and the
    ``ARIADNE_ALLOW_DOCKER_EXECUTION`` environment variable must be truthy
    for real Docker execution. Otherwise returns the existing blocked result.
    """
    allow_docker = execution_request.get("allow_docker", False)
    env_raw = os.environ.get("ARIADNE_ALLOW_DOCKER_EXECUTION", "")
    env_allowed = env_raw.lower() not in ("", "0", "false", "no")

    executor = run_docker_subprocess if (allow_docker and env_allowed) else None

    return run_docker_agent_execution(
        execution_request,
        executor=executor,
        allow_docker=allow_docker and env_allowed,
    )
```

**Dual-gate logic summary:**

| `allow_docker` (request) | `ARIADNE_ALLOW_DOCKER_EXECUTION` (env) | Behavior |
|---|---|---|
| false / absent | any | Existing blocked result |
| true | absent / "0" / "false" / "no" | Blocked (env gate not satisfied) |
| true | any other value (e.g. "1", "true", "yes") | Real Docker execution via `run_docker_subprocess` |

**No bypass path exists:** both gates must be truthy. If either is false, `executor=None` and `allow_docker=False` are passed, producing the existing blocked result.

**Replace registry entry:**

```python
_ADAPTERS: list[tuple[str, Any]] = [
    ("noop", run_noop_execution),
    ("docker", _dispatch_docker_agent),  # was: run_docker_agent_execution
]
```

**Preserved invariants:**
- `dispatch_execution(execution_request)` still calls `adapter_fn(execution_request)` with a single positional argument — unchanged.
- `run_docker_agent_execution` itself is unmodified.
- `build_docker_agent_command` is unmodified.
- `docker_agent_adapter.py` is not imported directly by any new code — the import goes through the registry wrapper.
- No dynamic imports, no plugin discovery, no filesystem access (reading an env var is not filesystem access).

---

## Phase 3: UI wiring in `server.py`

### 3a — Add `allow_docker` opt-in control in the HTML

Near the existing Docker agent radio button (around the current copy "Docker agent (opt-in — does not run Docker)"):

```html
<label><input type="radio" name="runner" value="docker-agent"> Docker agent (opt-in)</label>
<br>
<label><input type="checkbox" id="allow-docker-checkbox"> Enable real Docker execution (requires ARIADNE_ALLOW_DOCKER_EXECUTION environment variable)</label>
```

- The checkbox defaults to **unchecked**.
- Selecting the docker-agent radio does NOT auto-check the allow_docker checkbox.
- The copy makes clear that enablement requires both the checkbox AND the environment variable.

### 3b — Include `allow_docker` in POST body

In the submit handler JavaScript (~line 829 area):

```javascript
var body = {
    task: task,
    requested_adapter: runnerValue,
    allow_docker: document.getElementById("allow-docker-checkbox").checked,
};
```

### 3c — Replace hardcoded "boundary" copy with conditional status-driven text

In `renderSummaryCard`, the current hardcoded text:

```javascript
"Docker opt-in boundary — completed without Docker. Enable Docker with allow_docker=True to execute."
```

Must be replaced with conditional logic driven by the actual `execution_result.status` returned:

```javascript
if (runtimeStatus === "completed" && !isNoop) {
    whatHappened = "Docker execution completed. See execution trace for details.";
} else if (runtimeStatus === "failed" && !isNoop) {
    whatHappened = "Docker execution failed. Check the errors section for details.";
} else if (runtimeStatus === "blocked" && !isNoop) {
    whatHappened = "Docker execution blocked. You must select the Docker opt-in checkbox and set the ARIADNE_ALLOW_DOCKER_EXECUTION environment variable to proceed.";
}
```

The other branches (noop, completed, etc.) remain as-is.

### 3d — Preserve all existing page functionality

- Local/noop remains the default runner.
- Docker-agent remains opt-in and non-default.
- All existing scenarios, feedback panels, confusion signals, run history, checklists, session reports, and export features remain unchanged.

---

## Phase 4: Tests

### 4a — `test_docker_subprocess_executor.py` (new file)

Tests for the `run_docker_subprocess` function, mocking `subprocess.run` so no real Docker daemon is needed:

- **argv construction test:** Assert that the produced argv is a list (not a string), does not contain `shell=True`, and maps command_metadata fields to correct docker CLI flags.
- **Success path test:** Mock `subprocess.run` to return `completed_process(returncode=0, stdout="...", stderr="")` — assert `success: True`.
- **Non-zero exit test:** Mock returncode=1 — assert `success: False`, stderr captured.
- **Timeout test:** Mock `subprocess.TimeoutExpired` — assert `success: False`, stderr contains "timed out".
- **FileNotFoundError test:** Mock missing docker binary — assert `success: False`, stderr mentions "Docker executable not found".
- **Security test:** Assert that argv has no `shell=True` (directly inspect the arg construction, not mock). Assert that all arguments are list elements — no string concatenation.
- **Full argv construction with all fields test:** Feed a full command_metadata dict, assert specific docker flags present in produced argv.

### 4b — `test_adapter_registry.py` extension (new test class only)

Add a new test class (e.g., `TestDockerDualGate`) with tests that do NOT modify existing test classes or methods:

- **Env False + allow_docker False -> blocked:** Clear `ARIADNE_ALLOW_DOCKER_EXECUTION` env, set `allow_docker=False` — assert blocked status.
- **Env False + allow_docker True -> blocked:** Clear env, set `allow_docker=True` — assert still blocked.
- **Env True + allow_docker False -> blocked:** Set env to "1", set `allow_docker=False` — assert blocked.
- **Env True + allow_docker True -> real executor invoked:** Set env to "1", set `allow_docker=True` — assert executor was actually called (mock `run_docker_subprocess`).
- **dispatch_execution signature preserved:** Existing `test_dispatch_noop` tests prove the single-argument call convention is preserved.
- **No bypass path:** Any combination except both-true produces blocked.

Note: The env var tests must save/restore the real environment (using `os.environ` patching or `monkeypatch` if available, or manual save/restore in fixture).

### 4c — `test_local_runner_selection.py` extension (new test class only)

Add a new test class (e.g., `TestDockerOptInControl`) with tests that do NOT modify existing test classes or methods:

- **GET / page contains allow_docker checkbox:** Assert `enable Docker execution` or similar text in the HTML.
- **allow_docker checkbox defaults unchecked:** Assert `type="checkbox"` without `checked` attribute.
- **docker-agent radio does not auto-check allow_docker:** Submit via `POST /runs/execute` with `docker-agent` selected but no `allow_docker` in body — assert the registered wrapper receives `allow_docker=False` (blocked).
- **POST body includes allow_docker=true when checked:** Submit with `allow_docker: true` — assert the execution result shape reflects the Docker adapter, not noop.
- **Conditional copy replaces hardcoded boundary text:** Assert the HTML no longer contains the old static string "completed without Docker" or "Enable Docker with allow_docker=True".
- **Existing test classes are not modified:** All existing TestExplanationPanel, TestRunnerSelection, TestRunsExecuteWithNoop, TestRunsExecuteWithDocker tests must pass unchanged.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New executor tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_subprocess_executor.py -q

# 3. Extended adapter registry tests (new dual-gate class only)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 4. Existing docker_agent_adapter tests (must all pass unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 5. Extended local runner selection tests
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_local_runner_selection.py -q

# 6. All other task_intake tests unchanged
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 7. Source-string safety test (server.py must not contain "subprocess")
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q

# 8. Forbidden imports test (adapter_registry dispatch/get_supported_adapters must not contain subprocess in their function source)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q

# 9. Full runner test suite (optional — quick sanity)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30
```

---

## Roadmap alignment

- **roadmap track:** substrate/execution track
- **expected PR slot:** 0094 — Docker Execution Wiring
- **why this PR is next:** First item in the corrected 0094-0100 execution/substrate sequence per ROADMAP.md and ADR 0011; resumes runner/execution track after the Local Interaction UX track (PR 0079-0092) was closed in PR 0093's roadmap correction.
- **batching policy check:** This PR spans four coordinated components (executor module, registry wiring, env master switch, UI opt-in) delivering one coherent substrate capability — real Docker execution behind layered opt-in. Not an isolated UI control. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger. This PR touches `services/runner/src/runner/` (new executor module) and `services/task_intake/src/task_intake/` (UI wiring and backend behavior), not an isolated single UI file change.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if `docker_agent_adapter.py`'s contract, signature, or `test_no_forbidden_imports` is modified or weakened.
2. Block if `test_docker_agent_adapter.py` must be modified.
3. Block if `dispatch_execution`'s single-argument `adapter_fn(execution_request)` calling convention changes.
4. Block if real Docker execution becomes reachable with only one of the two gates (per-request `allow_docker`, env master switch) true.
5. Block if `subprocess` is invoked with `shell=True` or via string-built commands.
6. Block if the existing `test_no_forbidden_imports` in `test_adapter_registry.py` fails because the top-level import of `run_docker_subprocess` in `adapter_registry.py` is found in `dispatch_execution` or `get_supported_adapters` source (confirmed by analysis: it won't — the test inspects function source only, not module-level imports).
7. Block if the UI opt-in checkbox defaults to checked, or if selecting docker-agent auto-checks it.
8. Block if implementation modifies files outside the exact planned scope (new: `docker_subprocess_executor.py`; modified: `adapter_registry.py`, `server.py`; test files as listed).
9. Block if any dependency file (`pyproject.toml`, `package.json`, `Makefile`) is modified.
10. Block if forbidden legacy names or shell placeholders are introduced.
11. Block if `server.py`'s existing `test_no_forbidden_source_strings` fails (server.py must not contain "subprocess" in its source — the string `allow_docker` is fine, and the UI copy text is HTML/JS, not Python source).
12. Block if tests require a real Docker daemon or Docker CLI execution — all subprocess tests must mock `subprocess.run`.
