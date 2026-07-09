# PR 0134 — Commit Payload Cleanliness Gate Plan

## Summary

During PR 0133, two distinct states had to be distinguished:

1. **Known generated residue** (untracked, not commit payload): `captures`,
   `.ariadne`, `.project-memory/pr/test`, `.project-memory/pr/0127`,
   `.project-memory/pr/dogfood`, `test_stage_file.py`.

2. **Forbidden tracked changes** (must always block): `agents/plan-review.yml`,
   `agents/precommit-review.yml`, `.gitignore`, and any forbidden-path file
   that is modified or staged.

PR 0133 solved the isolation problem (tests must not write to real repo
root).  PR 0134 adds an explicit, testable commit payload cleanliness gate
that classifies every dirty file into one of three buckets — allowed
payload, known generated residue (untracked), or forbidden/unknown — and
blocks execution when forbidden or unknown files would be part of the
commit payload.

## Observed Problem

PR 0133 implementation validated that:

- Known generated residue paths (`captures`, `.ariadne`,
  `.project-memory/pr/test`, `.project-memory/pr/0127`,
  `.project-memory/pr/dogfood`, `test_stage_file.py`) exist as untracked
  files during test development.

- `agents/plan-review.yml` and `agents/precommit-review.yml` are
  forbidden tracked changes that must block any approved commit.

- The existing `_check_git_baseline()` function handles the case where a
  clean baseline is needed for execution, but does not produce a
  structured, reviewable result that distinguishes known generated residue
  from forbidden payload for pre-execution validation.

- No existing mechanism inspects `git diff --cached --name-only` to detect
  staged known residue or forbidden files before they enter the commit.

## Requirements

### Gate Behaviour

1. Inspect tracked changes (modified tracked files).
2. Inspect staged files (files in the index).
3. Inspect untracked files.
4. Classify known generated residue (allow only if untracked and not staged).
5. Classify forbidden tracked files (always block).
6. Classify unknown untracked files (always block).
7. Block if `agents/plan-review.yml` is modified (tracked change).
8. Block if `agents/precommit-review.yml` is modified (tracked change).
9. Block if `.gitignore` is modified (tracked change).
10. Block if known generated residue is staged.
11. Block if known generated residue is tracked (modified).
12. Block if unknown untracked files exist.
13. Do NOT block solely because known generated residue exists as untracked files.
14. Produce structured evidence suitable for reviews and run records.

### Known Generated Residue Paths

These paths are acceptable only when untracked and not staged:

```
captures
.ariadne
.project-memory/pr/test
.project-memory/pr/0127
.project-memory/pr/dogfood
test_stage_file.py
```

### Forbidden Tracked File Paths

These paths are always blockers when modified or staged:

```
agents/plan-review.yml
agents/precommit-review.yml
.gitignore
```

Plus any path matching the existing `_is_forbidden_path()` in
`git_boundary.py` (e.g., `agents/`, `schemas/`, `services/task_intake/`,
`.project-memory/post-0100/`, `ROADMAP.md`, `docs/`, `pyproject.toml`,
`package.json`, `Makefile`).

## Scope

### Implementation Files

| File | Changes | Justification |
|------|---------|---------------|
| `services/runner/src/runner/ariadne_task_cli.py` | Add `_check_payload_cleanliness()` function and call it from `run_ariadne_task()` after pipeline runs but before proof finalization. | Evidence: `run_ariadne_task()` at lines 753-985 is the orchestration point where all pre-execution validation happens. The gate must run after pipeline (so proof can be validated) but before git boundary planning (so blocked payload prevents git mutation). |
| `services/runner/tests/test_ariadne_task_cli.py` | Add tests for the payload cleanliness gate. | Evidence: primary test file for `ariadne_task_cli.py` functions; existing `_check_git_baseline` tests are here. |

### Files Excluded (with evidence)

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/src/runner/git_boundary.py` | Evidence: `git_boundary.py` does not track git status or classify files — it receives already-parsed `dirty_files` and `allowed_files` tuples. Adding staged/untracked classification here would break the separation of concerns. The gate inspects the working tree state; the boundary inspects the plan. |
| `services/runner/src/runner/run_persistence.py` | Evidence: Persistence stores what it receives; the gate produces evidence that can be passed to persistence via `reason_codes`, but persistence logic itself does not need changing. |
| `services/runner/tests/test_git_boundary.py` | Evidence: No `git_boundary.py` changes. |
| `services/runner/tests/test_run_persistence.py` | Evidence: No `run_persistence.py` changes. |

### Not Modified

- `ROADMAP.md` — not modified
- `docs/` — not modified
- `agents/` — not modified
- `schemas/` — not modified
- `pyproject.toml` — not modified
- `.gitignore` — not modified (no new ignore entries)
- `.project-memory/pr/0131-*` — not modified
- `.project-memory/pr/0132-*` — not modified
- `.project-memory/pr/0133-*` — not modified
- `services/runner/src/runner/git_boundary.py` — not modified
- `services/runner/src/runner/run_persistence.py` — not modified

## Design

### 1. Result Type

The gate produces a structured result:

```python
@dataclasses.dataclass(frozen=True)
class PayloadCleanlinessResult:
    clean: bool
    reason_codes: tuple[str, ...]
    tracked_changed_files: tuple[str, ...]
    staged_files: tuple[str, ...]
    unknown_untracked_files: tuple[str, ...]
    known_generated_residue_files: tuple[str, ...]
    forbidden_tracked_files: tuple[str, ...]
```

### 2. Reason Codes

| Code | Condition |
|------|-----------|
| `commit_payload_forbidden_tracked_change` | A forbidden tracked file (e.g., `agents/plan-review.yml`) is modified or staged |
| `commit_payload_staged_residue` | Known generated residue is staged |
| `commit_payload_unknown_untracked` | Unknown untracked files exist |
| `commit_payload_forbidden_cached_diff` | A forbidden file appears in `git diff --cached` |

### 3. Gate Function: `_check_payload_cleanliness()`

```python
def _check_payload_cleanliness(
    repo_root: str = ".",
) -> PayloadCleanlinessResult:
    """Check commit payload cleanliness.

    Inspects tracked changes, staged files, and untracked files, then
    classifies each into allowed payload, known generated residue, or
    forbidden/unknown.

    Returns
    -------
    PayloadCleanlinessResult
        Structured result with file lists and reason codes.
    """
```

The function:

1. Runs `git status --porcelain=v1` to get tracked+untracked files.
2. Runs `git diff --cached --name-only` to get staged files.
3. For each file, classifies:
   - If in `_FORBIDDEN_TRACKED_PATHS` → forbidden tracked change.
   - If a tracked change and in `_KNOWN_RESIDUE_PATHS` → staged or tracked
     residue (blocker).
   - If untracked and in `_KNOWN_RESIDUE_PATHS` → known generated residue
     (acceptable, not blocked).
   - If untracked and not in `_KNOWN_RESIDUE_PATHS` → unknown untracked
     (blocker).
   - If in `git diff --cached` and forbidden → cached diff blocker.

4. Assembles the result with all file lists and reason codes.

### 4. Integration in `run_ariadne_task()`

The gate runs **after pipeline execution** and **before git boundary
planning**.  Exact insertion point (between the existing steps):

```
# 4a. Cleanup runtime residue before proof finalization
_cleanup_runtime_residue(request.repo_root, request.pr_id)

# 4a-2. [NEW] Check payload cleanliness
if request.execute:
    payload_result = _check_payload_cleanliness(
        repo_root=request.repo_root,
    )
    if not payload_result.clean:
        codes.extend(payload_result.reason_codes)
        warnings.append(...)
        # persist and return BLOCKED

# 4b. Render dogfood proof (before baseline)
```

**Why after cleanup?** The cleanup removes known runtime residue
(`captures/`, `generated reviews`) before the cleanliness check runs.
This ensures that cleanup targets are not falsely classified as
"unknown untracked" files.

**Why before proof finalization?** The proof finalization writes the
stage file to disk.  After proof finalization, the stage file is
tracked/modified, so it would appear in `git status`.  The gate must
run *before* the proof is written so that:
- The stage file path is not yet classified as an unknown untracked file.
- The allowed stage file passes the gate because it is in `allowed_files`.

**Alternative integration point**: After proof finalization but before
git boundary planning.  This would require adding the stage file path to
an explicit allow list.  The before-proof-finalization approach is
simpler because no stage file exists yet, and the gate only classifies
pre-existing residue and forbidden tracked files.

**Decision**: Call before proof finalization (after cleanup, after pipeline).
The stage file will be validated by the existing proof validation and
baseline checks.

### 5. Injectable Provider Support

Like other boundary functions in `run_ariadne_task()`, the payload
cleanliness gate must accept an injectable provider:

```python
payload_cleanliness_fn: Optional[Callable] = None,
```

With default to `_check_payload_cleanliness`.  Tests inject a fake
provider that returns controlled `PayloadCleanlinessResult` values.

### 6. Staged File Detection

`git diff --cached --name-only` lists files in the index (staged).
The gate must check this to detect staged known residue (e.g., if a
user accidentally ran `git add captures/`).

If `git diff --cached` returns a file that is:
- In `_KNOWN_RESIDUE_PATHS` → `commit_payload_staged_residue`.
- In `_FORBIDDEN_TRACKED_PATHS` → `commit_payload_forbidden_tracked_change`.

### 7. Constants

```python
_KNOWN_RESIDUE_PATHS: tuple[str, ...] = (
    "captures",
    ".ariadne",
    ".project-memory/pr/test",
    ".project-memory/pr/0127",
    ".project-memory/pr/dogfood",
    "test_stage_file.py",
)

_FORBIDDEN_TRACKED_PATHS: tuple[str, ...] = (
    "agents/plan-review.yml",
    "agents/precommit-review.yml",
    ".gitignore",
)
```

Plus reuse `_is_forbidden_path` from `git_boundary.py` for the broader
forbidden path check (agents/, schemas/, etc.).

## Tests

### 1. Known generated residue as untracked does not block

Create `captures/`, `.ariadne/`, `.project-memory/pr/test/`,
`.project-memory/pr/0127/`, `.project-memory/pr/dogfood/`,
`test_stage_file.py` as untracked files.

Run `_check_payload_cleanliness()` with `repo_root=tmp_path`.

Assert `clean=True`, no `commit_payload_*` reason codes.

### 2. Known generated residue staged for commit blocks

Create `captures/` directory, run `git add captures/` in tmp_path repo.

Run `_check_payload_cleanliness()` with `repo_root=tmp_path`.

Assert `clean=False`, `commit_payload_staged_residue` in reason codes.

### 3. Known generated residue tracked as modified file blocks

Create `captures/` directory, commit it (in tmp_path repo), then modify it.

Run `_check_payload_cleanliness()` with `repo_root=tmp_path`.

Assert `clean=False`, `commit_payload_forbidden_tracked_change` in reason codes.

### 4. Unknown untracked files block

Create `unexpected_file.txt` in tmp_path repo.

Run `_check_payload_cleanliness()`.

Assert `clean=False`, `commit_payload_unknown_untracked` in reason codes.

### 5. `agents/plan-review.yml` modification blocks

Create and commit `agents/plan-review.yml`, then modify it.

Run `_check_payload_cleanliness()`.

Assert `clean=False`, `commit_payload_forbidden_tracked_change` in reason codes.

### 6. `agents/precommit-review.yml` modification blocks

Same pattern as above.

### 7. `.gitignore` modification blocks

Create and commit `.gitignore`, then modify it.

Run `_check_payload_cleanliness()`.

Assert `clean=False`, `commit_payload_forbidden_tracked_change` in reason codes.

### 8. Approved payload files pass

Create and commit `services/runner/src/runner/ariadne_task_cli.py`.

Run `_check_payload_cleanliness()`.

Assert `clean=True`, no blocker reason codes.

### 9. Gate reports evidence lists

Run the gate with a mix of known residue, forbidden tracked, and
unknown untracked files.

Assert the returned `PayloadCleanlinessResult` has non-empty
`known_generated_residue_files`, `forbidden_tracked_files`, and
`unknown_untracked_files` lists matching expectations.

### 10. Gate result is included in run record

Run `run_ariadne_task()` with an injectable payload cleanliness
provider that returns a blocked result.

Assert `reason_codes` contain the `commit_payload_*` code.
Assert the run record (run.json) contains the reason codes.

### 11. Integration in run_ariadne_task blocks before git boundary

Run `run_ariadne_task()` with a dirty tree containing a forbidden
tracked file.  Use injectable providers for all other boundaries.

Assert `status == BLOCKED`, `execution_attempted == False`.
Assert no git boundary planning was reached.

### 12. Known generated residue passes full run_ariadne_task

Run `run_ariadne_task()` with untracked `captures/` directory and
valid allowed/stage files.  Use injectable providers.

Assert the gate passes, pipeline proceeds to git boundary planning.

### 13. No real git mutation in tests

Assert tests use only fake git status providers, fake diff providers,
and temporary repositories — no `subprocess.run` for git mutation,
no `gh`, no Docker, no network.

## Validation Checklist

### 1. Compile Check

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

Expected: all Python files compile.
If not met: block.

### 2. Focused Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  -q
```

Expected: focused tests pass.
If not met: block.

### 3. Regression Subset

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
If not met: block.

### 4. Grep for Gate Behaviour

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "commit_payload|payload_clean|known_generated_residue|forbidden_tracked|staged_residue|unknown_untracked|diff --cached|agents/plan-review.yml|agents/precommit-review.yml|.gitignore" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0134-commit-payload-cleanliness-gate
```

Expected: gate behavior and tests are visible.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0134-commit-payload-cleanliness-gate
```

Expected: no unsafe real mutation authority added.
If unsafe new mutation is found: block.

### 6. Git Status

```bash
git status --short
```

Expected: only allowed files are dirty, plus untracked known generated
residue if produced by validation.
If forbidden tracked files are modified: block.
If unknown untracked files exist: block.

### 7. Git Diff

```bash
git diff --name-only
```

Expected: only allowed files are listed.
If not met: block.

### 8. Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty during review unless human staged expected files after
implementation.
If staged known residue or forbidden files appear: block.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131 dogfood behaviour | `_render_dogfood_proof_yaml`, `_validate_dogfood_proof_content`, proof finalization order unchanged |
| PR 0132 execution result persistence | `persist_run_record`, `_persist_and_return` unchanged |
| PR 0133 test residue isolation and cleanup fixture | `conftest.py` autouse fixture unchanged; `_cleanup_runtime_residue` unchanged |
| Git Boundary authority | `git_boundary.py` not modified; `_is_forbidden_path` reused but unchanged |
| Dirty-tree strictness | `_check_git_baseline` unchanged; `FORBIDDEN_PAYLOAD_PREFIXES` and `IGNORED_BASELINE_PREFIXES` unchanged |

## Non-Goals

- No .gitignore entries added
- No dirty-tree checks weakened
- No committed project-memory artifacts deleted
- No PR 0131/0132/0133 artifacts rewritten
- No real dogfood PR
- No dashboard, retry system, control plane, model health, run report,
  parallel queue, Decision Core, Context Warehouse, eval harness,
  faithfulness audit, frontend
- No `ORCHESTRATOR_STANDARD.txt`
- No changes to `git_boundary.py` or `run_persistence.py`

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0134-commit-payload-cleanliness-gate`
- PLAN does not state that PR 0133 exposed the distinction between generated residue and commit payload
- PLAN does not list known generated residue paths
- PLAN does not state that known generated residue is acceptable only when untracked and not staged
- PLAN does not state that forbidden tracked changes are always blockers
- PLAN adds .gitignore entries
- PLAN weakens dirty-tree checks
- PLAN deletes committed project-memory artifacts
- PLAN rewrites PR 0131/0132/0133 artifacts
- PLAN runs real dogfood, Docker, installs dependencies, or creates GitHub PRs
