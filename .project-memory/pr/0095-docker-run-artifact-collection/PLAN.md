# PR 0095 — Docker Run Artifact Collection Plan

## Goal

Add deterministic runner-side artifact collection for Docker-backed executions. After PR 0094 wired real Docker execution behind a layered opt-in, the execution result currently returns only static "in-memory" artifact/evidence entries. This PR replaces those static entries with structured artifacts derived from the executor result (exit_code, stdout, stderr, success) and command metadata — without persisting to disk, without adding Docker commands, without schema changes, and without turning this into a frontend-only PR.

The collected artifacts are **in-envelope deterministic** — they live in the `RunnerExecutionResult` dict and flow through the existing `execution_envelope` pipeline. Disk persistence via `ArtifactStore` is deferred to a later PR.

---

## Files

### New implementation files

- `services/runner/src/runner/docker_run_artifacts.py`

### Modified implementation files

- `services/runner/src/runner/docker_agent_adapter.py`

### New test files

- `services/runner/tests/test_docker_run_artifacts.py`

### Extended test files (new test classes only — do not modify existing tests)

- `services/runner/tests/test_docker_agent_adapter.py`

### Immutable files (must not be modified by this PR)

- `services/runner/src/runner/adapter_registry.py` — dual-gate wrapper unchanged
- `services/runner/src/runner/docker_subprocess_executor.py` — subprocess isolation unchanged
- `services/runner/tests/test_docker_subprocess_executor.py` — unchanged
- `services/runner/tests/test_adapter_registry.py` — existing tests unchanged (TestDockerDualGate already covers dual-gate behavior)
- `services/runner/src/runner/artifacts.py` — ArtifactStore unchanged; disk persistence not wired
- `services/runner/src/runner/local_harness.py` — unchanged
- `services/runner/src/runner/noop_adapter.py` — unchanged
- `services/runner/src/runner/execution_envelope.py` — unchanged
- `services/task_intake/` — no changes; artifact enrichment is transparent to the HTTP layer
- `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*` — unchanged

### Forbidden implementation write paths

Any file not listed in "New implementation files" or "Modified implementation files" above.

---

## Phase 1: `docker_run_artifacts.py` (new module)

**Location:** `services/runner/src/runner/docker_run_artifacts.py`

**Purpose:** Deterministic helper that produces structured artifact and evidence entries from a Docker execution result and its command metadata. No filesystem writes, no subprocess calls, no state.

**Public API — two functions:**

```python
def build_docker_artifacts(
    executor_result: dict,
    command_metadata: dict,
    execution_request_id: str,
) -> list[dict]
```

```python
def build_docker_evidence(
    executor_result: dict,
    command_metadata: dict,
    execution_request_id: str,
) -> list[dict]
```

### Artifact shape

Each artifact entry follows the existing `RunnerExecutionResult.artifacts[]` shape:

```python
{
    "artifact_id": str,           # deterministic, e.g. f"{req_id}-docker-stdout"
    "kind": str,                  # e.g. "docker_stdout", "docker_command_metadata"
    "reference": str,             # "in-memory" (disk persistence deferred)
    "summary": str,               # human-readable description
    "content": Any | None,        # the actual artifact payload (JSON-serializable)
}
```

### Evidence shape

Each evidence entry follows the existing `RunnerExecutionResult.evidence[]` shape:

```python
{
    "evidence_id": str,           # deterministic
    "evidence_kind": str,         # e.g. "execution_log", "execution_note"
    "summary": str,
    "status": str,                # "passed" | "failed" | "skipped"
    "details": Any | None,        # optional structured details
}
```

### Artifact model/shape details

| Artifact ID suffix | kind | content |
|---|---|---|
| `-docker-stdout` | `docker_stdout` | `executor_result.stdout` (bounded — see bounding policy) |
| `-docker-stderr` | `docker_stderr` | `executor_result.stderr` (bounded — see bounding policy) |
| `-docker-exec-metadata` | `docker_execution_metadata` | Dict with: `exit_code`, `success`, `container_image`, `network_mode`, `execution_mode`, `timeout_seconds` (redacted — see redaction policy) |
| `-docker-command-meta` | `docker_command_metadata` | Summary dict: `container_image`, `workdir`, `network_mode`, `memory_limit`, `cpu_count`, `volume_count` (integer), `env_var_count` (integer), `timeout_seconds` (no secret values) |

### Evidence details

| Evidence ID suffix | evidence_kind | status | summary |
|---|---|---|---|
| `-docker-evidence` | `execution_log` | `"passed"` if success, `"failed"` if not | Summary derived from status |
| `-docker-blocked-evidence` | `execution_note` | `"skipped"` | Only included for blocked results — explains opt-in is required |

### Artifact redaction policy

- **Environment variables:** Do **not** include raw `environment` dict values. Instead, include `env_var_count: <N>` and list only safe key names (no values). Do not include `ARIADNE_TASK_GOAL` value if present (it may contain task details). Include only non-sensitive standard keys like `ARIADNE_RUN_ID`, `ARIADNE_REQUEST_ID`, `ARIADNE_MODE` as a list of key names.
- **Volumes:** Record volume count and a normalized/summarized form (e.g. `"/workspace mapped", "N additional volumes"`). Do not include raw host paths — only container-side mount points.
- **No secrets:** Presume all environment values may contain secrets. Include them as key-count + key-names only, never values.

### stdout/stderr bounding policy

- If `stdout` length exceeds 10,000 characters, truncate to 10,000 chars and append `"\n... [truncated at 10000 characters]"`.
- Same for `stderr`.
- The bounding is applied in `build_docker_artifacts`, not in the executor module.
- The executor module itself passes through raw output unchanged (it may be needed elsewhere unbounded).

### Deterministic naming/id policy

- All artifact IDs are derived from `execution_request_id`: `f"{execution_request_id}-docker-stdout"`, etc.
- All evidence IDs are derived from `execution_request_id`: `f"{execution_request_id}-docker-evidence"`, etc.
- Deterministic, no randomness, no UUIDs.

### Blocked/completed/failed behavior

| Result status | Artifacts | Evidence |
|---|---|---|
| blocked | `-docker-command-meta` artifact (static "not executed" summary) | `-docker-blocked-evidence` with `"skipped"` status and "Docker execution requires explicit opt-in" summary |
| completed (success=True) | All four artifacts as described above | `-docker-evidence` with `"passed"` status |
| failed (success=False) | All four artifacts as described above | `-docker-evidence` with `"failed"` status; stderr content available in the stderr artifact |

---

## Phase 2: `docker_agent_adapter.py` modification

**Modify the `run_docker_agent_execution` function** to use the new artifact and evidence builders instead of the current static entries.

The current code produces static entries:
```python
"artifacts": [
    {
        "artifact_id": f"{req_id}-docker-command-meta",
        "kind": "docker_command_metadata",
        "reference": "in-memory",
        "summary": "Docker command metadata (not executed).",
    },
],
"evidence": [
    {
        "evidence_id": f"{req_id}-docker-evidence",
        "evidence_kind": "execution_log",
        "summary": "...",
        "status": "...",
    },
],
```

**Replace with calls to the new module:**

1. **Add import at top of file:**
   ```python
   from runner.docker_run_artifacts import build_docker_artifacts, build_docker_evidence
   ```

2. **In the blocked (`allow_docker=False`) branch, replace artifacts/evidence:**
   ```python
   artifacts = build_docker_artifacts(
       {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
       command_metadata,
       req_id,
   )
   evidence = build_docker_evidence(
       {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
       command_metadata,
       req_id,
   )
   ```
   Note: Even though the blocked branch doesn't execute Docker, `build_docker_agent_command` is called inside `run_docker_agent_execution` and `command_metadata` is available through a function-local variable. Currently, the function has `command_metadata` available as a local after the `build_docker_agent_command` call. The blocked branch currently returns before that call. The implementation must either (a) call `build_docker_agent_command` earlier, or (b) pass command metadata through both branches. Option (b) is cleaner: restructure so `command_metadata = build_docker_agent_command(execution_request)` is called once at the top, before the opt-in check, so both branches have access.

3. **In the execution (`allow_docker=True`) branch, replace artifacts/evidence:**
   ```python
   artifacts = build_docker_artifacts(executor_result, command_metadata, req_id)
   evidence = build_docker_evidence(executor_result, command_metadata, req_id)
   ```

4. **No other changes to `docker_agent_adapter.py`:** The function signature (`execution_request`, `executor=None`, `allow_docker=False`), the opt-in check, the `build_docker_agent_command` logic, the return dict structure, and the `_DEFAULT_EXECUTOR` all remain unchanged.

### Source-string safety check

Importing `from runner.docker_run_artifacts import build_docker_artifacts, build_docker_evidence` at the top of `docker_agent_adapter.py` is safe because:

- The existing `test_no_forbidden_imports` in `test_docker_agent_adapter.py` removes **all** string literals (including the import string `"runner.docker_run_artifacts"`) before checking for forbidden terms. The test uses `re.sub(r"'[^']*'", "", clean)` which strips all single-quoted strings, and `re.sub(r'"[^"]*"', "", clean)` which strips double-quoted strings. A module-level `from ... import` statement contains only bare identifiers after string removal, so no subprocess or docker SDK term appears in the cleaned source.
- The new module `docker_run_artifacts.py` will not import subprocess, docker SDK, or any forbidden modules.

---

## Phase 3: Tests

### 3a — `test_docker_run_artifacts.py` (new file)

Unit tests for `build_docker_artifacts` and `build_docker_evidence` with fake executor results (no subprocess, no Docker daemon):

- **Completed artifact shape:** `build_docker_artifacts` with `success=True`, mock stderr/stdout — assert four artifacts returned with correct kinds, deterministic IDs, bounded content.
- **Failed artifact shape:** Same but `success=False` — assert four artifacts returned.
- **Blocked artifact shape:** `build_docker_artifacts` with `success=False`, no stdout/stderr — assert `docker_command_metadata` kind only.
- **stdout bounding:** Call with stdout > 10k chars — assert truncated with "... [truncated" suffix.
- **stderr bounding:** Same test for stderr.
- **Redaction — no env values:** Assert `content` of `docker_execution_metadata` does not contain raw environment variable values. Assert `env_var_count` is an integer, and only key names are listed, never values.
- **Redaction — volume host paths:** Assert volume host paths are not present raw; only container-side mount points or count.
- **Evidence shape — completed:** `build_docker_evidence` with `success=True` — assert `"passed"` status, `"execution_log"` kind.
- **Evidence shape — failed:** `build_docker_evidence` with `success=False` — assert `"failed"` status.
- **Evidence shape — blocked:** `build_docker_evidence` with `exit_code=-1`, `success=False` — assert `"skipped"` status, `"execution_note"` kind.
- **Deterministic IDs:** Same inputs produce same artifact/evidence IDs.
- **JSON serializable:** All outputs pass `json.dumps`.
- **No secrets in blocked evidence:** Blocked evidence summary does not contain metadata that could leak secrets.

### 3b — `test_docker_agent_adapter.py` extension (new test class only)

Add a new test class (e.g., `TestRunArtifacts`) that does NOT modify existing `TestOptIn`, `TestBuildCommand`, `TestResultShape`, or `TestNoSideEffects` classes:

- **Blocked result has new artifact shape:** Call `run_docker_agent_execution(_valid_request())` — assert `artifacts` contain `docker_command_metadata` kind.
- **Completed result has four artifacts:** Call with `allow_docker=True`, `executor=_fake_successful_executor` — assert 4 artifacts: stdout, stderr, exec metadata, command metadata.
- **Failed result has four artifacts:** Call with `allow_docker=True`, `executor=_fake_failing_executor` — assert 4 artifacts.
- **Artifact content matches executor output:** Assert stdout artifact content matches `_fake_successful_executor` stdout.
- **Evidence status matches result:** Completed → `"passed"`, failed → `"failed"`, blocked → `"skipped"`.
- **Existing `test_no_forbidden_imports` still passes:** The import of `docker_run_artifacts` must not break this test. Verified by analysis — string literals are stripped before forbidden-term checks, so the import string `"runner.docker_run_artifacts"` is removed.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New artifact collector tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py -q

# 3. Existing docker_agent_adapter tests + new artifact test class
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 4. Existing docker_subprocess_executor tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_subprocess_executor.py -q

# 5. Existing adapter registry tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 6. Task intake tests (unchanged — artifact enrichment is transparent to HTTP layer)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 7. Source-string safety test (server.py must not contain "subprocess")
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q

# 8. Forbidden imports test (adapter_registry must not contain subprocess in dispatch/get_supported_adapters source)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q

# 9. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30
```

---

## Roadmap alignment

- **roadmap track:** substrate/execution track
- **expected PR slot:** 0095 — Docker Run Artifact Collection
- **why this PR is next:** Follows PR 0094 Docker Execution Wiring and addresses the second substrate gap ("Run Artifact Collection") in the corrected 0094-0100 sequence per ROADMAP.md. PR 0094 wired the execution path; this PR enriches the result with structured, bounded, redacted artifacts and evidence that flow through the existing execution envelope pipeline.
- **batching policy check:** New artifact helper module + docker_agent_adapter wiring + focused tests form one coherent substrate capability batch. Not an isolated UI control. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger. This PR touches only `services/runner/src/runner/` files — no UI, no `server.py`, no isolated frontend change. All changes are backend artifact/evidence enrichment.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if `docker_agent_adapter.py`'s function signature (`execution_request`, `executor=None`, `allow_docker=False`) changes.
2. Block if `build_docker_agent_command` in `docker_agent_adapter.py` is modified.
3. Block if `adapter_registry.py` must be modified (dual-gate wrapper must remain unchanged from PR 0094).
4. Block if `docker_subprocess_executor.py` must be modified (subprocess isolation must remain unchanged).
5. Block if `test_no_forbidden_imports` in `test_docker_agent_adapter.py` fails due to the new import (confirmed safe by analysis — string literals are stripped before forbidden-term checks).
6. Block if ArtifactStore disk persistence is attempted (deferred to later PR).
7. Block if schema files are modified.
8. Block if dependency/build config files are modified.
9. Block if Docker daemon or Docker CLI execution is required for tests — all artifact tests use fake executor results.
10. Block if `execution_result.artifacts[]` or `execution_result.evidence[]` shape changes from the existing RunnerExecutionResult contract schema.
11. Block if secret environment values are stored in artifact content.
12. Block if stdout/stderr in artifact content are unbounded.
13. Block if artifact payloads are not JSON-serializable.
14. Block if forbidden runtime source strings are introduced into `docker_agent_adapter.py` (subprocess, docker SDK, etc.).
15. Block if implementation modifies files outside the exact planned scope.
16. Block if Roadmap alignment section is missing or incomplete.
17. Block if `services/task_intake/` is modified in any way.
