# PR 0131K — Fix Dot-Prefixed Path Normalization in Baseline Matching Plan

## Summary

PR 0131J fixed the ordering of proof finalization before baseline.  The next
dogfood attempt produced:

```
status: blocked
reason_codes: ['dirty_tree_out_of_scope']
warning: Unrelated dirty file: project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
```

The actual `--allowed-file` and `--stage-file` arguments are dot-prefixed:

```
.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
```

The warning path lost the leading dot:

```
project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
```

The dirty baseline check in `_check_git_baseline()` compares the `filename`
from `git status --porcelain=v1` against `allowed_set`.  Because the leading
dot is stripped from the git status output, the dot-prefixed path in
`allowed_set` never matches, causing the intended dogfood stage file to be
classified as an unrelated dirty file.

## Context

| Field | Value |
|-------|-------|
| `--allowed-file` value | `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml` |
| git status line | ` M .project-memory/pr/.../dogfood-proof.yml` |
| Warning path (after parse) | `project-memory/pr/.../dogfood-proof.yml` |
| Root cause | `line.strip()` + `line[3:]` in `_check_git_baseline` |

## Root Cause (Exact Code Path)

The bug is in `_check_git_baseline()` at lines 653-658:

```python
for line in status_result.stdout.splitlines():
    line = line.strip()          # <-- BUG: strips leading space (index status char)
    if not line:
        continue
    if len(line) < 4:
        continue
    filename = line[3:].strip()  # <-- BUG: wrong offset after strip()
```

**What happens with real git porcelain output**:

`git status --porcelain=v1` for a tracked file modified in the worktree:

```
 M .project-memory/pr/0131-.../dogfood-proof.yml
```

Position 0: ` ` (space — index unmodified)
Position 1: `M`    (worktree modified)
Position 2: ` ` (separator space)
Position 3: `.`    (start of path)

After `line.strip()` (line 653), the leading space is removed:

```
M .project-memory/pr/0131-.../dogfood-proof.yml
```

Now `line[3:]` starts at the original position 4 (skipping `M`, ` `, `.`):

```
project-memory/pr/0131-.../dogfood-proof.yml
```

**The dot is lost**.  The canonical `allowed_set` contains
`.project-memory/pr/.../dogfood-proof.yml` — the comparison fails.

**Why existing tests don't catch this**: The injectable baseline provider
(`status_provider`) returns pre-formatted results directly.  Tests that
call `_check_git_baseline()` with a `status_provider` skip the
`subprocess.run` + `line[3:].strip()` path entirely.  Tests that use the
real code path exercise git on `tmp_path` repos with repo-relative filenames
that don't start with a dot (e.g., `allowed.py`, `unrelated.py`).

**Why dot-prefix matters specifically for dogfood**: The stage file path
`.project-memory/pr/.../dogfood-proof.yml` is the only path that:
1. Starts with a dot
2. Is the intended dogfood payload
3. Must match exactly against `allowed_set`

Non-dot-prefixed paths like `services/runner/src/...` are unaffected.

## Fix

Replace the `line.strip()` + arbitrary-slice approach with proper porcelain
line parsing:

**Current (broken)**:
```python
line = line.strip()
if not line:
    continue
if len(line) < 4:
    continue
filename = line[3:].strip()
```

**Corrected**:
```python
line = line.strip()
if not line:
    continue
if len(line) < 4:
    continue
# Porcelain format: XY filename
# X = index status, Y = worktree status, third char = separator space
# The filename starts after the separator at index 3
filename = line[3:].strip()
```

Wait — the strip() is still there. The real issue is: `line.strip()` at
line 653 removes the leading space (position 0), shifting everything left.
After that, `[3:]` skips positions 0, 1, 2 of the stripped string, which
correspond to positions 1, 2, 3 of the original — skipping the first
character of the path in some cases.

**Correct fix**: Do NOT `strip()` the line before slicing.  Only `.strip()`
the extracted filename:

```python
for line in status_result.stdout.splitlines():
    raw = line.rstrip('\n\r')
    if not raw:
        continue
    if len(raw) < 4:
        continue
    filename = raw[3:].rstrip()
    if not filename:
        continue
```

This preserves the leading whitespace so that `raw[3:]` reliably extracts
from position 3 of the original porcelain output, which is the start of
the filename.

**Alternative fix using `removeprefix`** (preferred for readability):

```python
for line in status_result.stdout.splitlines():
    raw = line.rstrip('\n\r')
    if not raw:
        continue
    # Porcelain: "XY filename" — skip the two status chars + separator space
    filename = raw[3:].rstrip()
    if not filename:
        continue
```

Either approach is equivalent.  The key change: no `line.strip()` before
the slice.

## Roadmap alignment

- **roadmap track**: Production Line — Stage 2 Closed Loop
- **expected PR slot**: PR 0131K (dot-prefix path normalization fix)
- **why this PR is next**: PR 0131J fixed ordering but the path matching
  still fails for dot-prefixed `.project-memory/` paths due to the
  `line.strip()` bug in `_check_git_baseline`.
- **batching policy check**: Single-purpose path normalization fix; no
  feature expansion.
- **drift heuristic check**: Does not touch frozen streams; does not add
  new product modules; does not modify ROADMAP/docs/agents/schemas/deplock.

## Design

### 1. Canonical Repo Path Behavior

After the fix, `_check_git_baseline` normalizes paths as follows:

| git status line | `filename` after fix | Notes |
|----------------|---------------------|-------|
| ` M .project-memory/foo` | `.project-memory/foo` | Dot-prefix preserved |
| `?? .project-memory/foo` | `.project-memory/foo` | Untracked with dot |
| ` M foo.py` | `foo.py` | Non-dot file |
| `?? foo.py` | `foo.py` | Untracked non-dot |
| `M  foo.py` | `foo.py` | Index-staged file |
| `MM foo.py` | `foo.py` | Both staged & worktree mod |
| `R  old->new.py` | `old->new.py` | Renamed (handled as-is) |

The `allowed_set` already contains the canonical form (e.g.,
`.project-memory/pr/.../dogfood-proof.yml`).  The git filename now matches
exactly: both have the leading dot.

### 2. Dirty Baseline Matching

The matching logic in `_check_git_baseline` compares:

```
filename in allowed_set
```

Where:
- `filename` comes from `raw[3:].rstrip()` (git porcelain output)
- `allowed_set` comes from `set(allowed_files)` (CLI `--allowed-file` values)

After the fix, both `.project-memory/pr/.../dogfood-proof.yml` values match
correctly.

**No additional normalization is needed** because:
- Git porcelain paths are repo-root-relative
- CLI `--allowed-file` values are repo-root-relative
- No `./` prefix or backslash normalization is needed for this codebase
  (Linux/macOS only, repo_root defaults to `"."`)

### 3. Fix Location

The only code change is in `_check_git_baseline()` at lines 653-658 of
`services/runner/src/runner/ariadne_task_cli.py`.

No changes to `git_boundary.py` — the `prepare_git_boundary_plan` function
receives already-parsed `dirty_files` and `allowed_files` tuples; the
comparison is exact string matching which is correct for both dot-prefixed
and non-dot-prefixed paths.

### 4. Preserve Previous Fixes

Do not regress PR 0131H/0131I/0131J:

| Feature | Preserved by |
|---------|-------------|
| Complete proof finalization before baseline | Order unchanged |
| `_cleanup_runtime_residue()` | Unchanged |
| `IGNORED_BASELINE_PREFIXES = (".ariadne/",)` | Unchanged — this check is AFTER the filename is extracted, so it still works with properly parsed paths |
| `FORBIDDEN_PAYLOAD_PREFIXES = ("captures/",)` | Unchanged |
| Generated reviews not staged | Unchanged |
| Captures not staged | Unchanged |
| `dogfood_proof_incomplete` priority | Unchanged |
| Command plan stages only requested dogfood-proof.yml | Unchanged |

### 5. Scope

**Implementation files**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Fix `line.strip()` bug in `_check_git_baseline()` (lines 653-658) |

**Test files**:

| File | Changes |
|------|---------|
| `services/runner/tests/test_ariadne_task_cli.py` | Add normalization tests; update existing tests to cover dot-prefixed paths |

**Not modified**:

- `git_boundary.py` — no change needed (receives already-parsed tuples)
- `agent_runner_bridge.py` — no change needed
- `pipeline_runner.py` — no change needed
- `run_persistence.py` — no change needed
- `prompt_composer.py` — no change needed
- `verdict_parser.py` — no change needed
- `ROADMAP.md` — not modified
- `docs/` — not modified
- `agents/` — not modified
- `schemas/` — not modified
- Dependencies — not modified

### 6. Non-goals

- No broad path alias workaround (accepting both `.project-memory` and
  `project-memory` as equivalent is explicitly forbidden)
- No new runtime modules
- No new architecture
- No retry/failure recovery loop (PR 0132)
- No model health live fallback (PR 0133)
- No frozen stream starts
- No real dogfood in tests
- No real git/gh/Docker/network/agents in tests

## Tests

### Normalization Tests

1. **`test_path_normalizer_preserves_dot_project_memory`**:
   - Simulate git porcelain line ` M .project-memory/pr/test/dogfood-proof.yml`
   - Run through the corrected parser
   - Assert `filename == ".project-memory/pr/test/dogfood-proof.yml"`

2. **`test_path_normalizer_strips_leading_dot_slash`**:
   - If git ever outputs `./foo.py` (unlikely in porcelain, but defensive):
     Simulate porcelain line with `./` prefix
   - Assert filename does not start with `./`

3. **`test_path_normalizer_preserves_regular_file`**:
   - Simulate ` M services/runner/src/file.py`
   - Assert `filename == "services/runner/src/file.py"`

4. **`test_path_normalizer_untracked_dot_file`**:
   - Simulate `?? .project-memory/pr/test/dogfood-proof.yml`
   - Assert dot preserved

5. **`test_path_normalizer_staged_modified_file`**:
   - Simulate `MM .project-memory/pr/test/dogfood-proof.yml`
   - Assert dot preserved

### Dirty Baseline Matching Tests

6. **`test_allowed_dogfood_proof_matches_dot_prefixed`**:
   - Inject status provider that simulates real git porcelain output with
     dot-prefixed paths
   - Set `allowed_files` containing the dot-prefixed path
   - Run `_check_git_baseline()` with the corrected parser
   - Verify it passes (no `dirty_tree_out_of_scope` for the proof path)

7. **`test_allowed_dogfood_proof_no_longer_appears_as_project_memory_only`**:
   - Same scenario as above
   - Verify no warning contains `project-memory` (without leading dot)

8. **`test_arbitrary_project_memory_without_dot_not_accepted`**:
   - Inject status provider showing file starting with `project-memory/`
     (without dot) — a path that git would NOT normally produce but tests
     the scenario
   - Verify it does NOT match the dot-prefixed allowed file
   - Verify it blocks with `dirty_tree_out_of_scope`

### Regression Tests

9. **`test_unrelated_dirty_file_still_blocks_after_normalization_fix`**:
   - Inject status provider with unrelated untracked file
   - Verify `dirty_tree_out_of_scope` emitted

10. **`test_captures_still_blocked_after_normalization_fix`**:
    - Inject status provider showing `captures/bridge.json`
    - Verify `Forbidden payload path` emitted

11. **`test_ariadne_still_ignored_after_normalization_fix`**:
    - Inject status provider showing `.ariadne/runs/foo/run.json`
    - Verify silently skipped (no warning, no code)

12. **`test_0131j_proof_before_baseline_still_works_with_dot_prefix`**:
    - Write complete proof at dot-prefixed stage_file path
    - Run full fake CLI flow with corrected baseline
    - Verify CLI reaches Git Boundary (not blocked at baseline or proof
      validation)

13. **`test_dogfood_proof_incomplete_still_blocks_with_dot_prefix`**:
    - Write weak proof at dot-prefixed stage_file path (path in
      `allowed_files`)
    - Run full fake CLI flow
    - Verify blocked with `dogfood_proof_incomplete`, not
      `dirty_tree_out_of_scope`

## Implementation Steps

1. **Fix `_check_git_baseline()` parsing** in `ariadne_task_cli.py`:
   - Replace:
     ```python
     line = line.strip()
     ...
     filename = line[3:].strip()
     ```
   - With:
     ```python
     raw = line.rstrip('\n\r')
     ...
     filename = raw[3:].rstrip()
     ```

2. **Add normalization tests** to `test_ariadne_task_cli.py`:
   - Test the exact `_check_git_baseline()` function with simulated
     porcelain lines containing dot-prefixed paths
   - Test that `allowed_set` matching works correctly after fix

3. **Update existing dirty baseline tests** to explicitly cover dot-prefixed
   scenarios:
   - Add a test case where `allowed_files` contains a dot-prefixed path
     and the simulated porcelain output also contains the same path

4. **Validate with compile and pytest commands**

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0131k-fix-dot-prefix-path-normalization`
- PLAN does not acknowledge the observed path mismatch (`.project-memory/`
  vs `project-memory/`)
- PLAN does not identify the actual normalization site (`line.strip()` at
  line 653 in `_check_git_baseline`)
- PLAN proposes accepting both dot-prefixed and non-dot-prefixed
  project-memory paths as a workaround
- PLAN weakens dirty baseline matching
- PLAN allows arbitrary dogfood-proof.yml paths
- PLAN regresses proof finalization before baseline
- PLAN allows generated reviews/captures/.ariadne to be staged
- PLAN modifies ROADMAP/docs/agents/schemas/dependencies
- PLAN starts frozen streams
- PLAN requires real dogfood in tests
- PLAN requires real git/gh/Docker/network/agents in tests

## Validation Commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
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

# Verify no lstrip("./") or strip("./") path normalization exists
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  'lstrip\(\./"\)|lstrip\(\./'\''\)|strip\("\./"\)|strip\('\''\./'\''\)' \
  services/runner/src/runner services/runner/tests || true
# Expected: no matches

# Verify the fix uses raw[3:] not line.strip()[3:]
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  'removeprefix\("\./"\)|removeprefix\('\''\./'\''\)|\.project-memory|project-memory/pr|dirty_tree_out_of_scope|Unrelated dirty file|allowed_file|stage_file|dogfood-proof.yml|_cleanup_runtime_residue|dogfood_proof_incomplete' \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131k-fix-dot-prefix-path-normalization

git status --short
git diff --name-only
```
