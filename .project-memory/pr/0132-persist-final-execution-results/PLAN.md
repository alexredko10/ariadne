# PR 0132 — Persist Final Execution Results After Approved Dogfood Run Plan

## Summary

PR 0131 dogfood gate passed. PR 156 was created by the Ariadne task CLI path, CI passed, and the proof artifact was merged into main. The runtime gate reached Git Boundary approval and execution was attempted. A telemetry gap remains: the local final run record showed `status: completed`, `git_boundary_status: approved`, `execution_attempted: true`, and `reason_codes: []`, but `execution_results_summary` (the persisted field in `run.json`) was empty.

**Root cause**: After PR 0131J/0131K, the `_persist_and_return()` function is called once — after execution completes — and passes `execution_results_summary=result.execution_results` to `RunPersistenceRequest`. However, no test verifies that the **persisted run.json** contains non-empty `execution_results_summary` after a successful fake execution. Additionally, the final `AriadneTaskCliResult` is constructed at step 10 with `execution_results=execution_results` which may be an empty tuple `()` if the `executor_fn` return was not captured correctly. The observed dogfood run persisted `execution_results_summary: []` because the `GitBoundaryResult.execution_results` tuple, though populated with per-operation dicts, was either empty at capture time or the `_persist_and_return` path used stale data.

The committed proof artifact correctly shows `pr_url: "pending-before-gh-pr-create"` and `run_json_hash: "pending"` — these sentinels are expected because the proof is committed before execution completes. The remaining defect is in **final run persistence**, not in proof generation.

This PR adds:
1. A mandatory final persistence write after `execution_results` are known, ensuring `execution_results_summary` is non-empty in `run.json`
2. `stdout`/`stderr` preservation in execution results
3. `pr_url` extraction from `gh_pr_create` stdout when it succeeds
4. Tests proving the persisted `run.json` contains non-empty `execution_results_summary`

## Context

| Field | Value |
|-------|-------|
| PR 0131 dogfood gate | Passed. PR 156 merged into main. |
| Observed gap | `execution_attempted=true`, `execution_results=[]` in persisted `run.json` |
| Proof sentinels | `pr_url: pending-before-gh-pr-create`, `run_json_hash: pending` — expected |
| Scope | Final run persistence only; no proof, no Git Boundary authority changes |
| Fix target | `ariadne_task_cli.py` (primary), `test_ariadne_task_cli.py` (primary) |
| Optional | `run_persistence.py` + `test_run_persistence.py` only if evidence proves API change needed |

## Current Code Path (Evidence)

**Step 9 in `run_ariadne_task()`** (`ariadne_task_cli.py`):

```python
execution_attempted = False
execution_results: tuple[dict[str, str], ...] = ()

if not request.dry_run:
    execution_attempted = True
    git_result = executor_fn(git_request, git_plan, executor=_execute_git_command_spec)

    if git_result.status == GitBoundaryStatus.FAILED.value:
        codes.append(REASON_EXECUTION_FAILED)
        execution_results = git_result.execution_results
        # returns immediately with execution_results
        return _persist_and_return(...)

    execution_results = git_result.execution_results
```

**Step 10** constructs `AriadneTaskCliResult` with `execution_results=execution_results`.

**`_persist_and_return()`** passes `execution_results_summary=result.execution_results`.

**`persist_run_record()`** writes `"execution_results_summary": list(request.execution_results_summary)` to `run.json`.

**The data path exists** but no readback test validates it. The observed empty `execution_results_summary` may occur because:
- The `GitBoundaryResult.execution_results` is populated by `execute_git_boundary_plan` line 514-531 only when the real executor runs each spec. If the executor fails to return per-operation dicts, or if an exception causes partial collection, the results are empty.
- The `execution_results` variable in step 9 is initialized as `()` and only reassigned when `not request.dry_run`. If execution runs but `git_result.execution_results` is empty (because the operation-level executor did not produce results), the final empty tuple persists.

## Design

### 1. Guarantee Final Persistence After Execution

**Current**: `_persist_and_return` is called at the terminal point of each branch. In the success path (step 10), the `AriadneTaskCliResult` is constructed with `execution_results=execution_results` and passed to `_persist_and_return`.

**Fix**: Ensure that `_persist_and_return` is always called after execution results are known and that the `execution_results_summary` in the persisted record is sourced from the **completed** execution. Add a readback assertion in tests.

No architectural change — the data path exists. The fix is to:
1. Add a **readback check** in the `run_ariadne_task` flow (or in tests) that proves `run.json` contains non-empty `execution_results_summary` after successful fake execution
2. Add explicit `pr_url` extraction from `gh_pr_create` stdout to the execution result dict

### 2. PR URL Extraction

**Problem**: When `gh_pr_create` succeeds, the stdout typically contains the PR URL (e.g., `https://github.com/owner/repo/pull/123`). This URL is currently not captured in the execution result.

**Fix**: In `_execute_git_command_spec()` (or in the Git Boundary result builder), when `spec.operation == "gh_pr_create"` and `exit_code == 0`, extract the PR URL from stdout and include it in the execution result dict.

**Decision: Add PR URL to the `gh_pr_create` execution result dict** under the key `pr_url`. This keeps the existing field structure and does not require a new top-level field.

Example execution result for `gh_pr_create`:
```python
{
    "operation": "gh_pr_create",
    "exit_code": "0",
    "stdout": "https://github.com/owner/repo/pull/123\n",
    "stderr": "",
    "pr_url": "https://github.com/owner/repo/pull/123"
}
```

The `pr_url` key is optional — present only when `gh_pr_create` succeeds. The proof artifact retains its `pr_url: pending-before-gh-pr-create` sentinel; the PR URL in the execution result is a runtime telemetry field, not a proof field.

**Alternative considered**: Adding a top-level `pr_url` field to `AriadneTaskCliResult`. Rejected — the proof is a pre-execution artifact and must not be rewritten after execution. The PR URL belongs in `execution_results` as a per-operation detail.

### 3. stdout / stderr Preservation

**Current**: Each execution result includes `stdout` and `stderr` with a 2000-char bound (in `_execute_git_command_spec`).

```python
return {
    "exit_code": result.returncode,
    "stdout": result.stdout[:2000] if result.stdout else "",
    "stderr": result.stderr[:2000] if result.stderr else "",
}
```

**No change needed** — bounded summaries are already present. However, add tests proving stdout/stderr are actually persisted.

### 4. Persistence Ordering

**Current order** in `run_ariadne_task()`:
1. Steps 1-4: Pre-execution checks, proof finalization
2. Steps 5-8: Git Boundary planning and approval checks
3. Step 9: Execution (git add, commit, push, gh pr create)
4. Step 10: Construct final `AriadneTaskCliResult` with `execution_results`
5. `_persist_and_return()` — single persistence call with all data

**No reordering needed** — there is only one persistence call, and it already receives `execution_results`. The fix is to verify this path with tests and add explicit readback.

### 5. Manifest and Hash Preservation

**No change to manifest creation or run_json_hash behavior.** The hash is computed after all data is written, so it will correctly include `execution_results_summary`.

## Tests

All tests use fake execution functions only. No real git, gh, Docker, network, or agents.

### Persistence Readback Tests

1. **`test_persisted_run_json_contains_non_empty_execution_results`**:
   - Run full fake CLI flow with `execute=True, dry_run=False, approve=True`
   - Fake executor returns `{exit_code: 0, stdout: "ok", stderr: ""}`
   - After `run_ariadne_task`, read back `run.json` from the persisted path
   - Assert `execution_results_summary` is non-empty
   - Assert each result has `operation` and `exit_code`

2. **`test_persisted_execution_results_contain_operation_and_exit_code`**:
   - Same setup
   - Verify each item in persisted `execution_results_summary` has `operation` key
   - Verify each has `exit_code` key

3. **`test_persisted_execution_results_contain_stdout_and_stderr`**:
   - Fake executor returns `{exit_code: 0, stdout: "output text", stderr: ""}`
   - Verify persisted results contain `stdout` and `stderr` fields
   - Verify `stdout` is "output text"

### PR URL Extraction Tests

4. **`test_gh_pr_create_stdout_url_in_execution_result`**:
   - Fake executor for `gh_pr_create` returns `{exit_code: 0, stdout: "https://github.com/owner/repo/pull/123\n", stderr: ""}`
   - Verify persisted execution result for `gh_pr_create` has `pr_url` key
   - Verify `pr_url` equals `"https://github.com/owner/repo/pull/123"`

5. **`test_gh_pr_create_url_in_persisted_run_json`**:
   - Run full flow with fake executor that returns URL for `gh_pr_create`
   - Read back `run.json`
   - Verify `execution_results_summary` contains the `pr_url` field

### Execution Attempted Implies Non-Empty Results

6. **`test_execution_attempted_true_implies_non_empty_execution_results`**:
   - Fake execution with `--no-dry-run --execute --approve`
   - Assert `result.execution_attempted is True`
   - Assert `len(result.execution_results) > 0`
   - Assert persisted `run.json` has `execution_results_summary` non-empty

### Failed Execution Tests

7. **`test_failed_execution_persists_partial_execution_results`**:
   - Fake executor fails on the third command (e.g., `git_commit`)
   - Fake executor returns `{exit_code: 0}` for first two, `{exit_code: 1}` for third
   - Verify persisted results contain entries for all attempted operations
   - Verify `exit_code` reflects the failure
   - Verify `reason_codes` contains `execution_failed`

8. **`test_partial_execution_results_still_persist`**:
   - Fake executor fails after `git_add` (before `git_commit` and `git_push`)
   - Verify at least the `git_status` and `git_add` results are persisted
   - Verify `reason_codes` not empty

### Pre-Execution Blocked Tests

9. **`test_pre_execution_blocked_run_has_empty_execution_results`**:
   - Run without `--approve` → blocked at approval check
   - Assert `execution_attempted is False`
   - Assert `execution_results` is empty tuple `()`
   - Assert persisted `run.json` has `execution_results_summary: []`

10. **`test_dry_run_has_empty_execution_results`**:
    - Run with `--dry-run` (default True)
    - Assert `execution_attempted is False`
    - Assert `execution_results` is empty tuple `()`

### Proof Artifact Preservation Tests

11. **`test_proof_artifact_not_rewritten_after_execution`**:
    - Read the rendered proof file before execution
    - Run full fake execution
    - Read the proof file again
    - Assert proof file is NOT modified (pr_url still `pending-before-gh-pr-create`)
    - Assert proof `execution_attempted` is still `false`

12. **`test_run_json_hash_stable_between_reads`**:
    - Run full flow
    - Read `run.json` and `manifest.json`
    - Assert `manifest.json` contains `run_json_hash`
    - Compute hash of `run.json` content
    - Assert hash matches manifest (proves deterministic ordering preserved)

### Regression Tests

13. **`test_persistence_does_not_break_existing_dogfood_proof`**:
    - Existing proof rendering tests still pass
    - Existing `_validate_dogfood_proof_content` tests still pass
    - Existing baseline ordering tests still pass
    - Existing dry-run / approval / execute tests still pass

14. **`test_no_real_git_gh_docker_network_in_tests`**:
    - grep for forbidden patterns returns 0

## Implementation Steps

### Step 1: Add PR URL extraction in `_execute_git_command_spec()` (optional enhancement)

In `ariadne_task_cli.py`, modify `_execute_git_command_spec()` to extract PR URL from `gh_pr_create` stdout:

```python
def _execute_git_command_spec(spec: GitCommandSpec) -> dict[str, Any]:
    """Execute a single git command spec locally."""
    try:
        result = subprocess.run(
            spec.argv,
            capture_output=True,
            text=True,
            shell=False,
            cwd=spec.cwd,
        )
        output = {
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
        }
        # Extract PR URL from gh_pr_create stdout
        if spec.operation == "gh_pr_create" and result.returncode == 0 and result.stdout:
            url = result.stdout.strip().split("\n")[0]
            if url.startswith("http"):
                output["pr_url"] = url
        return output
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": f"Command not found: {spec.argv[0]}"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}
```

**Expected evidence after change**: `git_result.execution_results` for `gh_pr_create` includes `pr_url`.

### Step 2: Add readback verification in test flow

Add a readback helper in tests (or inline) that reads `run.json` from the persisted path and asserts `execution_results_summary` is non-empty.

### Step 3: Add or update tests in `test_ariadne_task_cli.py`

Add all 14 test classes / test functions above to `test_ariadne_task_cli.py`.

### Step 4: Validate with compile and pytest commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  -q
```

## Scope

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Optional: Add PR URL extraction in `_execute_git_command_spec()` |
| `services/runner/tests/test_ariadne_task_cli.py` | Add persistence readback tests, PR URL extraction tests, execution result tests |

**Not modified**:
- `run_persistence.py` — no change needed; the data path already passes `execution_results_summary`
- `test_run_persistence.py` — no change needed unless tests fail on existing field semantics
- `git_boundary.py` — no change needed; execution results are already built per-operation
- `test_git_boundary.py` — no change needed
- `agent_runner_bridge.py`, `pipeline_runner.py`, `prompt_composer.py`, `verdict_parser.py`
- `ROADWAY.md`, `docs/`, `agents/`, `schemas/`, dependencies

## Non-goals

- No rewrite of PR 156 proof
- No rerun of real dogfood
- No new GitHub PR through the runtime
- No change to proof schema
- No change to Git Boundary authority rules
- No dashboard, retry system, control plane, model health, run report, parallel queue, Decision Core, Context Warehouse, eval harness, faithfulness audit, frontend
- No modification of ROADMAP.md
- No ORCHESTRATOR_STANDARD.txt addition

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0132-persist-final-execution-results`
- PLAN treats committed proof sentinels (`pr_url: pending-before-gh-pr-create`, `run_json_hash: pending`) as defects
- PLAN rewrites the already committed dogfood proof
- PLAN adds a new top-level `pr_url` field to `AriadneTaskCliResult` or `PersistedRunRecord`
- PLAN modifies Git Boundary authority rules
- PLAN requires real git/gh/Docker/network/agents in tests
- PLAN modifies ROADMAP.md, docs, agents, schemas, dependencies
- PLAN does not require readback verification in tests

## Validation Commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "execution_results|execution_attempted|gh_pr_create|git_boundary_status|run_record_path|manifest|persist|run_json_hash|pending-before-gh-pr-create|pending-before-run-persist" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0132-persist-final-execution-results

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0132-persist-final-execution-results

git status --short
git diff --name-only
```
