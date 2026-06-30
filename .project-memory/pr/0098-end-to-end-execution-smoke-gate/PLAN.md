# PR 0098 — End-to-End Execution Smoke Gate Plan

## Goal

Plan an executable local end-to-end execution smoke gate for Ariadne that verifies the corrected execution/substrate path after PR 0094 (Docker execution wiring), PR 0095 (artifact collection), PR 0096 (human review boundary), and PR 0097 (drift audit). The smoke gate composes task intake handoff → runner dispatch → docker-agent safety → artifacts/evidence → review boundary → PR 0097 audit into one deterministic smoke path.

No Docker daemon. No new product features. No UI changes. No schema changes. No dependency changes.

---

## Scope reconciliation with ROADMAP.md

ROADMAP.md describes PR 0097 as "Local Docker End-to-End Smoke" and PR 0098 as "Stabilization: Error Handling & Edge Cases." The actual sequence inserted a drift/tech-debt audit at PR 0097 that is a pre-condition for the end-to-end smoke. This PR (0098) implements the end-to-end smoke as a deterministic local check — it is the *integration verification* step that ensures all prior PRs compose correctly. The stabilization pass shifts to PR 0099. This does not contradict the roadmap — it refines the sequence to include a necessary verification step between the audit and the stabilization pass.

---

## Files

### New implementation files

- `services/runner/src/runner/execution_smoke.py`

### New test files

- `services/runner/tests/test_execution_smoke.py`

### Immutable files (must not be modified by this PR)

- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/docker_agent_adapter.py`
- `services/runner/src/runner/docker_run_artifacts.py`
- `services/runner/src/runner/docker_subprocess_executor.py`
- `services/runner/src/runner/review_boundary.py`
- `services/runner/src/runner/local_harness.py`
- `services/runner/src/runner/execution_envelope.py`
- `services/runner/src/runner/execution_substrate_audit.py` (PR 0097 audit is imported, not modified)
- `services/runner/src/runner/doctor.py`
- `services/runner/src/runner/artifacts.py`
- `services/task_intake/` — completely untouched
- `services/task_intake/src/task_intake/test_mode.py` — the existing CLI entrypoint is used as a validation command, not modified
- `docs/**`, `schemas/**`, `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*`

### Forbidden implementation write paths

Any file not listed in "New implementation files" above.

---

## Phase 1: `execution_smoke.py` — smoke gate module

**Location:** `services/runner/src/runner/execution_smoke.py`

**Purpose:** Deterministic local smoke gate that runs the full execution pipeline (harness → envelope → boundary) through multiple fixture paths, validates the results against expected invariants, and returns a structured smoke report. The smoke gate does not require Docker daemon, network, filesystem access, or any external dependency. It calls `run_local_execution_harness` directly with dict fixtures.

**Public API:**

```python
def run_execution_smoke() -> SmokeReport:
```

No arguments. The smoke gate uses internal fixture data (hardcoded execution request dicts) so it is deterministic, self-contained, and runnable without any external state.

**Smoke result shape (`SmokeReport`):**

```python
class SmokeCheck(TypedDict):
    check_id: str
    description: str
    passed: bool
    details: str | None

class SmokeReport(TypedDict):
    timestamp: str          # ISO8601 UTC
    ok: bool                # True only if ALL smoke checks pass
    checks: list[SmokeCheck]
    summary: dict           # {"total": int, "passed": int, "failed": int}
```

---

## Phase 2: Smoke execution paths

### Path 1 — Local/noop execution produces completed

- **check_id:** `noop_completed`
- **Setup:** `execution_request` with `requested_adapter="noop-v1"`, no `allow_docker`.
- **Expected:** `runtime_status == "completed"`, `decision == "completed"`, `status == "completed"`.
- **Why:** Baseline — noop must always complete without review.

### Path 2 — Docker-agent blocked by default (no allow_docker, no env)

- **check_id:** `docker_blocked_by_default`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, no `allow_docker`.
- **Expected:** `runtime_status == "blocked"`, `decision == "blocked"`.
- **Why:** Docker-agent without opt-in must be blocked.

### Path 3 — Docker-agent blocked when only env is set (allow_docker missing)

- **check_id:** `docker_blocked_no_request_flag`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, no `allow_docker`, but env `ARIADNE_ALLOW_DOCKER_EXECUTION=1` set temporarily.
- **Expected:** `runtime_status == "blocked"`. Both gates required.
- **Note:** Uses `monkeypatch`-style env override in test.

### Path 4 — Docker-agent blocked when only request flag is set (no env)

- **check_id:** `docker_blocked_no_env_switch`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, `allow_docker=True`, but env `ARIADNE_ALLOW_DOCKER_EXECUTION` not set.
- **Expected:** `runtime_status == "blocked"`.
- **Why:** Per-request flag alone is insufficient.

### Path 5 — Docker-agent blocked when string "false" is passed

- **check_id:** `docker_blocked_false_string`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, `allow_docker="false"` (string).
- **Expected:** `runtime_status == "blocked"`. The env gate check in `_dispatch_docker_agent` does `execution_request.get("allow_docker") is True` — string `"false"` is not `True`.
- **Note:** Also test `allow_docker="true"` (string `"true"` is not `True`).

### Path 6 — Docker-agent blocked when env false string

- **check_id:** `docker_blocked_env_false_string`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, `allow_docker=True`, env `ARIADNE_ALLOW_DOCKER_EXECUTION=FALSE`.
- **Expected:** `runtime_status == "blocked"`.

### Path 7 — Docker-agent requires_review via fake executor

- **check_id:** `docker_requires_review`
- **Setup:** `execution_request` with `requested_adapter="docker-agent-v1"`, `allow_docker=True`, env `ARIADNE_ALLOW_DOCKER_EXECUTION=1`, plus an injected fake executor that returns `success=True`.
- **Expected:** `runtime_status == "requires_review"`, `decision == "requires_review"`.
- **Note:** This path tests that the adapter_registry wrapper (`_dispatch_docker_agent`) passes `executor=run_docker_subprocess` when both gates are open, and that `run_docker_agent_execution` produces `status="requires_review"`. Because `run_docker_subprocess` uses actual subprocess and will fail in a test environment (no Docker), this test uses a patched executor via the adapter's `executor` parameter mechanism. The smoke gate uses `unittest.mock.patch` to replace `runner.docker_subprocess_executor.run_docker_subprocess` with a fake that returns `success=True`.

### Path 8 — Docker-agent failed via fake executor

- **check_id:** `docker_failed`
- **Setup:** Same as Path 7 but fake executor returns `success=False`.
- **Expected:** `runtime_status == "failed"`, `decision == "failed"`.

### Path 9 — PR 0095 artifact kinds visible

- **check_id:** `artifact_kinds_visible`
- **Setup:** Use the execution result from Path 7 (requires_review path).
- **Expected:** `artifacts` list contains four entries with `kind` values: `docker_stdout`, `docker_stderr`, `docker_execution_metadata`, `docker_command_metadata`. `evidence` list contains `execution_log` and optionally `execution_note`.
- **Why:** PR 0095 artifacts must survive the full harness pipeline.

### Path 10 — PR 0095 artifact redaction

- **check_id:** `artifact_redaction`
- **Setup:** Use the execution result from Path 7.
- **Expected:** No environment variable values in artifact content. `docker_execution_metadata.content.environment_keys` is a list of key names only. Volume host paths are not present raw.
- **Why:** Redaction must survive the full pipeline.

### Path 11 — PR 0097 audit can be invoked as validation

- **check_id:** `audit_invocation`
- **Setup:** Call `run_execution_substrate_audit` from PR 0097 with actual source files (read via `inspect.getsource`).
- **Expected:** The audit function returns without error. All invariant checks pass or produce tech-debt warnings only. This is a meta-check: the audit itself must be usable as a validation command.
- **Note:** This is **not** a new module — it calls the existing `run_execution_substrate_audit` function and validates it runs.

---

## Phase 3: Integration with PR 0097 audit

The smoke gate treats the PR 0097 audit as an **imported validation step**, not a modified module:

- `execution_smoke.py` imports `run_execution_substrate_audit` from `runner.execution_substrate_audit`.
- During the smoke run, it invokes the audit with actual source files read via `inspect.getsource()` on the relevant modules.
- The audit results are included as additional checks in the SmokeReport (check_id prefix `audit_`).
- The review-process retro-check (diff-vs-FILES-READ comparison) is exercised via test fixtures, not during the smoke gate itself — it remains a warning-only diagnostic.

---

## Phase 4: Tests

### 4a — `test_execution_smoke.py` (new file)

**Unit tests for `run_execution_smoke`:**

- **Noop smoke check passes:** Call `run_execution_smoke()` — assert `noop_completed` check passes.
- **Docker blocked by default:** Assert `docker_blocked_by_default` passes.
- **Docker blocked when only env set:** Use `monkeypatch`/`patch.dict(os.environ, ...)` — assert `docker_blocked_no_request_flag` passes.
- **Docker blocked when only request flag set:** No env set — assert `docker_blocked_no_env_switch` passes.
- **Docker blocked with string "false":** `allow_docker="false"` — assert `docker_blocked_false_string` passes.
- **Docker blocked with string "true":** `allow_docker="true"` — assert blocked (string is not `True`).
- **Docker blocked with env "FALSE":** Set env to "FALSE" — assert `docker_blocked_env_false_string` passes.
- **Docker requires_review via fake executor:** Patch `run_docker_subprocess` with a success-returning fake — assert `docker_requires_review` passes.
- **Docker failed via fake executor:** Patch with failure-returning fake — assert `docker_failed` passes.
- **Artifact kinds visible:** From the requires_review result — assert all four artifact kinds present.
- **Artifact redaction:** From the requires_review result — assert env values redacted.
- **Audit invocation:** Patch `run_execution_substrate_audit` to verify it is called — or call it directly with fixture source text and assert it returns.
- **Overall smoke report ok=True when all checks pass:** Assert `SmokeReport.ok is True`.
- **Overall smoke report ok=False when a check fails:** Mock one check to fail — assert report.ok is False.
- **Deterministic:** Two calls produce identical `SmokeReport`.
- **JSON serializable:** Report passes `json.dumps`.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New smoke gate tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_smoke.py -q

# 3. Existing local harness tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py -q

# 4. PR 0097 audit tests (must all pass unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_substrate_audit.py -q

# 5. Existing docker_agent_adapter tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 6. Existing review_boundary tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py -q

# 7. Existing adapter_registry tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 8. Existing artifact/subprocess tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_docker_subprocess_executor.py -q

# 9. Task intake tests unchanged + source-string safety
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 10. Source-string safety selectors (existing tests)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py::TestSafety::test_no_forbidden_source_strings -q

# 11. Forbidden imports (adapter_registry + review_boundary + local_harness)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py::TestNoSideEffects::test_no_forbidden_imports -q

# 12. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30

# 13. Test-mode CLI integration (smoke gate via existing entrypoint)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m task_intake.test_mode --task "smoke test" --json \
  | python -c "import sys,json; d=json.load(sys.stdin); assert d['ok'], f'CLI not ok: {d}'; print('CLI test-mode smoke PASS')"
```

---

## Artifact readiness rule

The final precommit-review artifact for this PR must:

1. Record full validation results — all validation commands must be run, not skipped.
2. Contain both exact source-string safety selector strings literally in the review artifact:
   - `test_no_forbidden_source_strings` (server.py)
   - `test_no_forbidden_source_strings` (execution_handoff_http.py)
3. Not claim pass with validation skipped/not_run.
4. Enforce current-review diff completeness — all diff files present in FILES READ.
5. Treat intentional ignored dirty files as warnings only when explicitly named.

---

## Roadmap alignment

- **roadmap track:** substrate/execution drift catch-up before PR 0100
- **expected PR slot:** 0098 — End-to-End Execution Smoke Gate
- **why this PR is next:** Follows PR 0097 execution substrate audit; creates a deterministic smoke gate that composes the corrected execution path (noop, docker blocked, docker requires_review, docker failed, artifact visibility, audit invocation) before PR 0099 stabilization and PR 0100 release gate
- **batching policy check:** New smoke helper + focused end-to-end tests + PR 0097 audit import + existing validation selectors form one coherent substrate hardening batch. Not an isolated UI change. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger — this is execution substrate smoke/gate work in `services/runner/src/runner/`, not a frontend-only UI change.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if ROADMAP.md scope contradiction cannot be reconciled — reconciled above (smoke deferred to PR 0098 after PR 0097 audit pre-condition).
2. Block if implementation would be docs-only, schemas-only, smoke-only-without-tests, review-artifact-only, or frontend-only.
3. Block if Docker daemon/CLI is required — all smoke tests use fake executors.
4. Block if schema changes are required.
5. Block if dependency/build config changes are required.
6. Block if `server.py` or any frontend/UI file is modified.
7. Block if external capability integration is introduced.
8. Block if broad repository discovery is required.
9. Block if PR 0094 dual-gate behavior would change.
10. Block if PR 0095 artifact/evidence behavior would be removed or weakened.
11. Block if PR 0096 `requires_review` status behavior would change.
12. Block if PR 0097 audit behavior would change — the audit module is imported, not modified.
13. Block if `dispatch_execution` single-argument convention would change.
14. Block if subprocess is introduced outside `docker_subprocess_executor.py` or tests.
15. Block if task_intake forbidden source-string safety is weakened.
16. Block if tests require old PR branches to exist.
17. Block if precommit artifact could pass with validation skipped.
18. Block if source-string safety selectors are omitted from validation.
19. Block if forbidden legacy names/examples are introduced.
20. Block if shell placeholders are introduced.
21. Block if implementation modifies files outside exact planned scope.
22. Block if Roadmap alignment section is missing or incomplete.
