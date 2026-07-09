# PR 0133 — Runner Test Runtime Residue Isolation Plan

## Summary

During the PR 0132 cycle, local test and fake runtime execution produced
unmanaged repo-root residue including:

- `.project-memory/pr/0127`
- `.project-memory/pr/dogfood`
- `test_stage_file.py`
- `.ariadne`
- `captures`

These artifacts are not runtime-approved dogfood proofs; they are test
hygiene residue left by runner tests that operate on the real repository
root instead of isolated `tmp_path` directories.

PR 0133 hardens runner test isolation so that:

1. All runner tests use `tmp_path` or `tempfile.mkdtemp()` as an isolated
   repository root.

2. Fake CLI execution writes runtime artifacts (runs, captures, stage
   files) only inside the isolated root.

3. No test creates or mutates files under the real `.project-memory/pr/`
   tree, the real `.ariadne/` directory, the real `captures/` directory,
   or unmanaged root-level stage files.

4. Post-test residue checks prove no known residue paths exist after
   focused and regression test runs.

## Root Cause

The `_valid_request()` helper in `test_ariadne_task_cli.py` defaults
`repo_root="."` (the real repository root):

```python
def _valid_request(**overrides: Any) -> AriadneTaskCliRequest:
    kwargs = {
        "repo_root": ".",
        "allowed_files": ("test_stage_file.py",),
        ...
    }
    kwargs.update(overrides)
    return AriadneTaskCliRequest(**kwargs)
```

Any test that calls `_valid_request()` without explicitly overriding
`repo_root` with a `tmp_path` operates on the real repository.  When
`run_ariadne_task()` invokes proof render + write, or when persistence
auto-defaults `runs_root=".ariadne/runs"`, files are written to the real
repo root.

Additional hardcoded repo-relative paths exist in:

- `test_pipeline_runner.py`: `.project-memory/pr/0127/PLAN.md`,
  `.project-memory/pr/dogfood/dogfood-proof.yml`

- `test_agent_runner_bridge.py`: `.project-memory/pr/dogfood/dogfood-proof.yml`

These paths are not isolated by `tmp_path` in the fixture setup.

## Distinction: Runtime-Approved vs. Unmanaged Test Residue

| Artifact | Status | Reason |
|----------|--------|--------|
| `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/` | Runtime-approved | Committed dogfood proof from PR #150 |
| `.project-memory/pr/0127/` | Unmanaged residue | Left by test fake runtime execution |
| `.project-memory/pr/dogfood/` | Unmanaged residue | Left by test fake runtime execution |
| `test_stage_file.py` | Unmanaged residue | Root-level stage file from tests not using isolated root |
| `.ariadne/` | Unmanaged residue | Runtime runs root auto-created by persistence default |
| `captures/` | Unmanaged residue | Created by test or fake runtime flow |

## Scope

### Primary Implementation File

| File | Changes |
|------|---------|
| `services/runner/tests/test_ariadne_task_cli.py` | Fix all tests that call `_valid_request()` without isolated `repo_root`. Add post-test residue assertions. |

### Secondary Test Files (only if evidence shows they leak)

| File | Changes | Condition |
|------|---------|-----------|
| `services/runner/tests/test_pipeline_runner.py` | Fix hardcoded `.project-memory/pr/0127/` and `.project-memory/pr/dogfood/` paths | Evidence: hardcoded paths at lines 179, 476, 547, 706, 1705 |
| `services/runner/tests/test_agent_runner_bridge.py` | Fix hardcoded `.project-memory/pr/dogfood/` path | Evidence: hardcoded path at line 1138 |
| `services/runner/tests/test_git_boundary.py` | Include only if evidence shows it leaks | Evidence: no current leak — tests use `tmp_path` or injectable providers |
| `services/runner/tests/test_local_harness.py` | Include only if evidence shows it leaks | Evidence: no current leak — tests use `tmp_path` |

### Production Code (only if it forces repo-root writes)

| File | Changes | Condition |
|------|---------|-----------|
| `services/runner/src/runner/ariadne_task_cli.py` | None needed — production `runs_root` auto-default is correct behaviour; tests must isolate | No change |
| `services/runner/src/runner/run_persistence.py` | None needed — tests control `runs_root` | No change |
| `services/runner/src/runner/git_boundary.py` | None needed — fake executors control repo_root | No change |

### Not Modified

- `ROADMAP.md` — not modified
- `docs/` — not modified
- `agents/` — not modified
- `schemas/` — not modified
- `pyproject.toml` — not modified
- `.gitignore` — not modified (no broad ignores)
- `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/` — not modified
- `.project-memory/pr/0132-persist-final-execution-results/` — not modified
- `.project-memory/pr/0131*` — not modified
- `services/runner/src/runner/ariadne_task_cli.py` — not modified

## Implementation Steps

### Step 1: Change `_valid_request()` default `repo_root`

Change the default from `"."` to a sentinel that forces callers to
provide an isolated root, OR add a test-scoped `_isolated_request()`
helper that always uses `tmp_path`.

**Preferred approach**: Change `_valid_request()` to accept a `tmp_path`
fixture or default to `tempfile.mkdtemp()`:

```python
def _valid_request(**overrides: Any) -> AriadneTaskCliRequest:
    kwargs = {
        "repo_root": tempfile.mkdtemp(prefix="ariadne-test-"),
        "allowed_files": ("test_stage_file.py",),
        ...
    }
    kwargs.update(overrides)
    return AriadneTaskCliRequest(**kwargs)
```

**Alternative approach**: Add `_isolated_request()` helper that always
uses `tmp_path`:

```python
def _isolated_request(tmp_path, **overrides):
    overrides.setdefault("repo_root", str(tmp_path))
    return _valid_request(**overrides)
```

Either approach ensures tests that don't explicitly set `repo_root` still
operate in an isolated directory.

### Step 2: Change `allowed_files` default in `_valid_request()`

Change the default `allowed_files` from `("test_stage_file.py",)` to
`()`.  Tests that need a specific allowed file should set it explicitly
in overrides.  This prevents accidental creation of `test_stage_file.py`
at the (now isolated) root.

### Step 3: Audit and fix all `_valid_request()` call sites

For every test in `test_ariadne_task_cli.py` that calls
`_valid_request()`:

1. **Tests that currently pass `repo_root=tempfile.mkdtemp()`**: Already
   safe.  No change needed.

2. **Tests that pass `repo_root=repo_root` from `tempfile.mkdtemp()` in
   the test body**: Already safe.  No change needed.

3. **Tests that call `_valid_request()` without `repo_root`**: These
   currently use `"."` (real repo root).  After Step 1, they
   automatically use an isolated root.  No explicit override needed.

4. **Tests that call `_valid_request()` with `repo_root="."`**:
   Change to `repo_root=tempfile.mkdtemp()`.

5. **Tests that expect to read/write specific paths relative to
   repo_root**: These continue to work correctly because the isolated
   root replaces `"."` transparently.

### Step 4: Fix `test_pipeline_runner.py` hardcoded paths

Replace hardcoded `.project-memory/pr/0127/PLAN.md` and
`.project-memory/pr/dogfood/dogfood-proof.yml` with paths relative to
`tmp_path`:

```python
# Before:
"expected_output_path": ".project-memory/pr/0127/PLAN.md",

# After:
"expected_output_path": ".project-memory/pr/test/PLAN.md",
```

The `test_no_real_pr_artifacts_created_in_tests` test in
`test_pipeline_runner.py` explicitly snapshots real dogfood-proof.yml
to assert it is not mutated.  This test must be preserved but converted
to use `tmp_path`-based isolation — it should snapshot the cloned
content into `tmp_path` rather than reading from the real repo root.

### Step 5: Fix `test_agent_runner_bridge.py` hardcoded path (if in scope)

Replace:
```python
artifact_path = ".project-memory/pr/dogfood/dogfood-proof.yml"
```
with a `tmp_path`-relative path.

### Step 6: Add post-test residue assertions in main test file

Add a top-level test or pytest fixture that enforces no known residue
paths exist after each test:

```python
@pytest.fixture(autouse=True)
def assert_no_repo_root_residue():
    """Assert runner tests do not create unmanaged repo-root residue."""
    yield
    residue_paths = [
        ".project-memory/pr/0127",
        ".project-memory/pr/dogfood",
        "test_stage_file.py",
        ".ariadne",
        "captures",
    ]
    for path in residue_paths:
        assert not os.path.exists(path), f"Unmanaged repo-root residue: {path}"
```

This fixture runs after every test in the file and blocks if residue
exists.

### Step 7: Add focused residue-proof tests

Add test functions proving specific residue scenarios are handled:

1. **`test_focused_test_does_not_create_pr_0127()`**:
   - Run `_valid_request()` with defaults
   - Assert `.project-memory/pr/0127` does not exist in real repo root after return

2. **`test_focused_test_does_not_create_pr_dogfood()`**:
   - Run `_valid_request()` with defaults
   - Assert `.project-memory/pr/dogfood` does not exist in real repo root

3. **`test_focused_test_does_not_create_test_stage_file()`**:
   - Run `_valid_request()` with defaults
   - Assert `test_stage_file.py` does not exist in real repo root

4. **`test_focused_test_does_not_create_ariadne()`**:
   - Run `_valid_request()` with defaults
   - Assert `.ariadne` does not exist in real repo root

5. **`test_focused_test_does_not_create_captures()`**:
   - Run `_valid_request()` with defaults
   - Assert `captures` does not exist in real repo root

6. **`test_fake_cli_artifacts_under_tmp_path()`**:
   - Run full `run_ariadne_task()` with fake pipeline and isolated repo_root
   - Assert any generated artifacts are under tmp_path, not real repo root

7. **`test_cleanup_does_not_delete_real_project_memory()`**:
   - Run with isolated root containing `.project-memory/pr/test/`
   - Assert cleanup only removes test artifacts, not committed ones
   - (This is a regression guard)

### Step 8: Cleanup residue removal command (pre-test)

Add pre-test cleanup command:
```bash
rm -rf .project-memory/pr/0127 .project-memory/pr/dogfood test_stage_file.py .ariadne captures
```

### Step 9: Post-test residue check validation

Add validation steps that prove no expected residue paths exist after
test runs.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131I runtime residue cleanup | `_cleanup_runtime_residue()` unchanged |
| PR 0131J proof finalization before baseline | Order unchanged; tests use fake baseline providers |
| PR 0131K dot-prefix path normalization | `raw[3:].rstrip()` in `_check_git_baseline` unchanged |
| PR 0132 execution result persistence & readback | Persistence tests use explicit `runs_root` — still work with isolated root |
| Git Boundary authority | Dirty-tree checks, forbidden path prefixes unchanged |
| No broad .gitignore | No new .gitignore rules |
| No weakened dirty-tree checks | Existing `_check_git_baseline` logic unchanged |

## Non-Goals

- No new runtime features
- No product behavior changes
- No schema changes
- No Git Boundary authority changes
- No dogfood rerun
- No GitHub PR creation
- No Docker changes
- No dashboard, retry, control plane, model health, run report, parallel queue,
  Decision Core, Context Warehouse, eval harness, faithfulness audit, frontend
- No `ORCHESTRATOR_STANDARD.txt`

## Validation Design

### Pre-Test Cleanup

```bash
rm -rf .project-memory/pr/0127 .project-memory/pr/dogfood test_stage_file.py .ariadne captures
```

Expected: local unmanaged residue removed before validation.

### Compile Check

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

Expected: all Python files compile.

### Focused Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  -q
```

Expected: focused tests pass.

### Post-Focused-Tests Residue Check

```bash
test ! -e .project-memory/pr/0127 && \
test ! -e .project-memory/pr/dogfood && \
test ! -e test_stage_file.py && \
test ! -e .ariadne && \
test ! -e captures
```

Expected: no known repo-root residue after focused tests.

### Regression Subset

```bash
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

Expected: regression subset passes.

### Post-Regression Residue Check

```bash
test ! -e .project-memory/pr/0127 && \
test ! -e .project-memory/pr/dogfood && \
test ! -e test_stage_file.py && \
test ! -e .ariadne && \
test ! -e captures
```

Expected: no known repo-root residue after regression tests.

### Grep for Residue Prevention and Temp-Root Evidence

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  ".project-memory/pr/0127|.project-memory/pr/dogfood|test_stage_file.py|tmp_path|TemporaryDirectory|chdir|cwd|project_root|runs_root|captures" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0133-runner-test-runtime-residue-isolation
```

Expected: residue prevention and temp-root evidence are visible.

### Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0133-runner-test-runtime-residue-isolation
```

Expected: no unsafe real mutation authority added.

### Git Status and Diff Check

```bash
git status --short
git diff --name-only
```

Expected: only allowed PR files are dirty.

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0133-runner-test-runtime-residue-isolation`
- PLAN does not state that repo-root residue was observed during PR 0132
- PLAN does not list the observed residue paths
- PLAN does not distinguish runtime-approved dogfood artifacts from unmanaged test residue
- PLAN does not state that unmanaged repo-root residue is a test hygiene problem
- PLAN claims residue came from a specific function without evidence
- PLAN adds broad .gitignore rules
- PLAN weakens dirty-tree checks
- PLAN modifies PR 0131 dogfood proof
- PLAN modifies PR 0132 artifacts
- PLAN modifies ROADMAP.md, docs/**, agents/**, schemas/**, dependency files
- PLAN runs real dogfood, Docker, installs dependencies, or creates GitHub PRs

## Validation Checklist (from SPECIFICATION)

1. `rm -rf .project-memory/pr/0127 .project-memory/pr/dogfood test_stage_file.py .ariadne captures`
   Expected: local unmanaged residue removed before validation.
   If not met: block.

2. `python -m compileall -f services/runner/src services/task_intake/src`
   Expected: all Python files compile.
   If not met: block.

3. Run focused tests.
   Expected: focused tests pass.
   If not met: block.

4. Post-focused-tests residue check.
   Expected: no known repo-root residue.
   If not met: block.

5. Run regression subset.
   Expected: regression subset passes.
   If not met: block.

6. Post-regression residue check.
   Expected: no known repo-root residue.
   If not met: block.

7. Grep for residue prevention and temp-root evidence.
   Expected: residue prevention and temp-root evidence visible.
   If not met: block.

8. Grep for unsafe mutation.
   Expected: no unsafe real mutation authority added.
   If not met: block.

9. `git status --short`
   Expected: only allowed files are dirty.
   If not met: block.

10. `git diff --name-only`
    Expected: only allowed files are listed.
    If not met: block.
