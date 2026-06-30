# PR 0096 — Human Review Boundary for Real Docker Runs Plan

## Goal

Apply the existing human review boundary to real Docker-backed executions. After PR 0094 wired real Docker execution behind layered opt-in and PR 0095 added structured artifact collection, successful real Docker runs currently produce `status="completed"` — which bypasses human review. This PR changes that single status value to `status="requires_review"`, which the existing `derive_review_boundary()` in `review_boundary.py` already maps to `decision="requires_review"`.

No other behavior changes. No new modules. No schema changes.

---

## Files

### Modified implementation file

- `services/runner/src/runner/docker_agent_adapter.py`

### Extended test files (new test classes only — do not modify existing tests)

- `services/runner/tests/test_docker_agent_adapter.py`
- `services/runner/tests/test_review_boundary.py`

### Immutable files (must not be modified by this PR)

- `services/runner/src/runner/review_boundary.py` — untouched; its status→decision mapping already handles `requires_review`
- `services/runner/src/runner/local_harness.py` — untouched; it composes dispatch→envelope→boundary; no changes needed
- `services/runner/src/runner/execution_envelope.py` — untouched; envelope passes through status unchanged
- `services/runner/src/runner/adapter_registry.py` — untouched; dual-gate wrapper unchanged
- `services/runner/src/runner/docker_subprocess_executor.py` — untouched; subprocess isolation unchanged
- `services/runner/src/runner/docker_run_artifacts.py` — untouched; artifact/evidence shapes unchanged
- `services/runner/src/runner/artifacts.py` — untouched
- `services/runner/src/runner/noop_adapter.py` — untouched
- `services/task_intake/` — completely untouched
- `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*` — untouched

### Forbidden implementation write paths

Any file not listed in "Modified implementation file" above.

---

## Implementation Plan

### Phase 1: `docker_agent_adapter.py` — one-line status change

In `run_docker_agent_execution`, the execution branch (reached when `allow_docker=True`) currently sets `status` based on the executor result:

```python
# Current code (lines ~93-107):
success = executor_result.get("success", False)

return {
    ...
    "status": "completed" if success else "failed",
    ...
}
```

**Change to:**

```python
success = executor_result.get("success", False)

if success:
    status = "requires_review"
else:
    status = "failed"

return {
    ...
    "status": status,
    ...
}
```

**No other changes to the file.** The function signature (`execution_request`, `executor=None`, `allow_docker=False`), the blocked branch, the `build_docker_agent_command` call, the artifact/evidence builders, and the return dict structure all remain unchanged.

### Why `status="requires_review"` is the correct approach

The existing `derive_review_boundary()` in `review_boundary.py` decides based on `execution_result["status"]`:

| `result_status` | `decision` | `requires_review` |
|---|---|---|
| `"completed"` | `"completed"` | `False` |
| `"requires_review"` | `"requires_review"` | `True` |
| `"blocked"` | `"blocked"` | `False` |
| `"failed"` | `"failed"` | `False` |
| `"error"` | `"failed"` | `False` |

The `review_required` field in the execution result is **not** read by `derive_review_boundary()`. The `approval` field in the execution request is an alternative path, but the architectural decision (from the task prompt) mandates using `status` as the mechanism — because:

- `status="requires_review"` maps directly through the existing boundary function.
- No change to `review_boundary.py` is needed.
- No change to `local_harness.py` is needed (it already calls `derive_review_boundary` on the result).
- No change to `execution_envelope.py` is needed (envelope normalizes status as-is).
- The mapping is explicit, visible in the adapter output, and verifiable in tests.

### Three-state matrix

| Execution path | `execution_result.status` | `derive_review_boundary` decision |
|---|---|---|
| Blocked (allow_docker=False) | `"blocked"` | `"blocked"`, `blocked=True` |
| Real Docker success (allow_docker=True, executor success=True) | `"requires_review"` | `"requires_review"`, `requires_review=True` |
| Real Docker failure (allow_docker=True, executor success=False) | `"failed"` | `"failed"`, `failed=True` |

All three states are distinct. No path allows a successful real Docker execution to reach `decision="completed"`.

---

## Phase 2: Tests

### 2a — `test_docker_agent_adapter.py` extension (new test class only)

Add a new test class (e.g., `TestHumanReviewBoundary`) that does NOT modify existing `TestOptIn`, `TestBuildCommand`, `TestResultShape`, `TestRunArtifacts`, or `TestNoSideEffects` classes:

- **Successful real execution produces status="requires_review":** Call `run_docker_agent_execution(_valid_request(), allow_docker=True, executor=_fake_successful_executor)` — assert `status == "requires_review"`.
- **Failed real execution produces status="failed":** Call with `executor=_fake_failing_executor` — assert `status == "failed"`.
- **Blocked execution produces status="blocked":** Call with `allow_docker=False` — assert `status == "blocked"`.
- **Review not required field remains False:** Even though status is `requires_review`, the `review_required` field in the execution result is `False` by default in the current code — confirm this is unchanged (the boundary function ignores it).
- **PR 0095 artifacts/evidence shapes preserved:** Confirm the result dict still contains the same four artifact kinds (`docker_stdout`, `docker_stderr`, `docker_execution_metadata`, `docker_command_metadata`) and the same evidence kinds (`execution_log`, `execution_note`) as before the status change.
- **PR 0094 dual-gate compatibility:** Confirm `allow_docker=False` still produces blocked; `allow_docker=True` with fake executor still produces something other than blocked.

### 2b — `test_review_boundary.py` extension (new test class only)

Add a new test class (e.g., `TestRealDockerBoundaryIntegration`) that does NOT modify existing `TestCompleted`, `TestRequiresReview`, `TestBlocked`, `TestFailed`, `TestError`, `TestGeneral`, or `TestNoSideEffects` classes:

- **Real Docker requires_review status → requires_review decision:** Call `derive_review_boundary(_valid_request(), _valid_result(status="requires_review", adapter="docker-agent-v1"))` — assert `decision == "requires_review"`, `requires_review is True`, `reason_code == "requires_review"`.
- **Real Docker failed status → failed decision:** Call with `status="failed"` — assert `decision == "failed"`, `failed is True`.
- **Real Docker blocked status → blocked decision:** Call with `status="blocked"` — assert `decision == "blocked"`, `blocked is True`.
- **Three states are distinct:** Assert that `"requires_review"`, `"failed"`, and `"blocked"` each produce different `decision` values.
- **Noop/local completed status unchanged:** Call with `status="completed"`, `adapter="noop-v1"` — assert `decision == "completed"`, confirming noop behavior is unaffected.
- **Full harness integration test:** Call `run_local_execution_harness` with a docker-agent execution request (via the real adapter_registry) that includes `allow_docker=True` and uses a fake executor — assert the harness result's `runtime_status` is `"requires_review"` rather than `"completed"`. This tests the full pipeline: dispatch → result → envelope → boundary.

### Validation-only tests (no new test files needed)

- **Existing `test_docker_agent_adapter.py` tests pass unchanged:** All existing test classes (`TestOptIn`, `TestBuildCommand`, `TestResultShape`, `TestRunArtifacts`, `TestNoSideEffects`) must still pass.
- **Existing `test_review_boundary.py` tests pass unchanged:** All existing test classes must still pass (noop always `completed`, blocked always `blocked`, failed always `failed`).
- **Existing `test_adapter_registry.py` tests pass unchanged:** Dual-gate tests must still pass.
- **Existing `test_docker_run_artifacts.py` tests pass unchanged:** Artifact shapes must be preserved.
- **Existing `test_docker_subprocess_executor.py` tests pass unchanged.**
- **Source-string safety tests pass unchanged.**

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. Extended docker_agent_adapter tests (including new TestHumanReviewBoundary)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 3. Extended review_boundary tests (including new TestRealDockerBoundaryIntegration)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py -q

# 4. Full harness integration (tests run_local_execution_harness with docker-agent)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py -q

# 5. Existing adapter registry tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 6. Existing artifact tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py -q

# 7. Existing subprocess executor tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_subprocess_executor.py -q

# 8. Source-string safety tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q

# 9. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30
```

---

## Roadmap alignment

- **roadmap track:** substrate/execution track
- **expected PR slot:** 0096 — Human Review Boundary for Real Docker Runs
- **why this PR is next:** Follows PR 0094 (Docker execution wiring) and PR 0095 (artifact collection), and addresses the third substrate gap ("Human review boundary for real runs") in the corrected 0094-0100 sequence per ROADMAP.md. PR 0094 made Docker execution possible; PR 0095 collected artifacts; this PR ensures successful real executions require human review — completing the execution→artifact→review pipeline.
- **batching policy check:** One-line status-value change in the adapter plus full matrix test coverage across review_boundary integration forms one coherent, narrowly-scoped substrate capability batch. Not a UI toggle. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger. This PR touches only `services/runner/src/runner/` backend files — no UI, no `server.py`, no isolated frontend change.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if `review_boundary.py` is modified. It does not need to change — the status→decision mapping already handles `"requires_review"`.
2. Block if `local_harness.py` is modified. It does not need to change — it already composes dispatch→envelope→boundary.
3. Block if `execution_envelope.py` is modified. It does not need to change — it passes through status unmodified.
4. Block if `adapter_registry.py` is modified. Dual-gate wrapper unchanged.
5. Block if `docker_subprocess_executor.py` is modified. Subprocess isolation unchanged.
6. Block if `docker_run_artifacts.py` is modified. Artifact/evidence shapes unchanged.
7. Block if any file outside `docker_agent_adapter.py` is modified for implementation.
8. Block if the change is anything other than the single status value in the real-execution branch.
9. Block if any successful real Docker execution can still reach `decision="completed"`.
10. Block if blocked/default docker-agent behavior changes (must remain `status="blocked"`).
11. Block if noop/local behavior changes (must remain `status="completed"`).
12. Block if failed real execution changes (must remain `status="failed"`).
13. Block if schema files are modified.
14. Block if dependency/build config files are modified.
15. Block if Docker daemon or Docker CLI execution is required for validation.
16. Block if forbidden runtime source strings are introduced into `docker_agent_adapter.py`.
17. Block if forbidden legacy names/examples are introduced.
18. Block if shell placeholders are introduced.
19. Block if implementation modifies files outside the exact planned scope.
20. Block if Roadmap alignment section is missing or incomplete.
21. Block if `services/task_intake/` is modified in any way.
