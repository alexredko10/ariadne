# PR 0131I — Dogfood Artifact Hygiene and Existing Proof Test Boundary Plan

## Summary

PR 0131G added the dogfood proof renderer and dirty baseline. PR 0131H added
runtime proof finalization, proof validation gate, and run persistence
auto-default.  The next real dogfood attempt produced:

- `captures/` and generated `reviews/precommit-review.yml` under the dogfood
  PR path — both blocked by dirty baseline as `dirty_tree_out_of_scope`
- `.ariadne/` run records — blocked as `Forbidden payload path`
- `execution_attempted=false`, `git_boundary_status=null`, `status=blocked`

Additionally, PR #150 (commit `cec039c`) merged `dogfood-proof.yml` into
main as a committed file.  Two existing tests (`test_no_real_pr_artifacts_created`
and `test_no_real_pr_artifacts_created_in_tests`) assert that these artifacts
MUST NOT EXIST — an assertion that is no longer valid.

This PR fixes three gaps:

1. **Runtime residue hygiene** — clean up `captures/` and generated
   `reviews/precommit-review.yml` before dirty baseline.  Ignore `.ariadne/`
   silently in baseline (was: blocked as forbidden payload).
2. **Intended dogfood stage_file allowance** — the finalized proof at the
   requested `stage_file` path passes baseline because it is in
   `allowed_files` and does not match forbidden payload prefixes.
3. **Existing proof test boundary** — two tests update from `assert not
   ...exists()` to snapshot-and-assert-unchanged.

## Context

| Field | Value |
|-------|-------|
| Committed weak proof | `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml` (from #150) |
| PR #150 commit | `cec039c chore(project-memory): add ariadne dogfood proof (#150)` |
| Weak proof fields | `pr_id: ""`, `proof_artifact_ref: ""`, `dogfood_type: "local-non-docker"`, 8 fields |
| Baseline blockers | `captures/` → `Forbidden payload path`; generated `reviews/` → dirty out-of-scope; `.ariadne/` → forbidden |
| Tests broken by #150 | `test_agent_runner_bridge.py::test_no_real_pr_artifacts_created` (line 1156) |
|  | `test_pipeline_runner.py::test_no_real_pr_artifacts_created_in_tests` (line 1506) |

## Roadmap alignment

- **roadmap track**: Production Line — Stage 2 Closed Loop
- **expected PR slot**: PR 0131I (hygiene correction after 0131G and 0131H)
- **why this PR is next**: Dogfood CLI cannot proceed through dirty baseline
  because of runtime residue (captures/, reviews/, .ariadne/).  Test safety
  contract is broken by committed #150 artifact.
- **batching policy check**: Single-purpose runtime correction; no feature
  expansion.
- **drift heuristic check**: Does not touch frozen streams; does not add new
  product modules; does not modify ROADMAP/docs/agents/schemas/deplock.

## Design

### 1. Intended Dogfood Stage_File Allowance

The dirty baseline already has the correct mechanism:

- `_check_git_baseline()` receives `allowed_files: tuple[str, ...]`
- A dirty file passes baseline if:
  1. It does NOT start with any `FORBIDDEN_PAYLOAD_PREFIX` (`.ariadne/`,
     `captures/`, `reviews/`)
  2. It IS in `allowed_files` (the `allowed_set`)

**The dogfood-proof.yml path** (`.project-memory/pr/<pr_id>/dogfood-proof.yml`)
does NOT start with `.ariadne/`, `captures/`, or `reviews/`.  When the CLI
includes the proof path in `--allowed-file`, the finalized proof passes
baseline.

**Commit-then-modify scenario**: The committed weak proof from #150 exists
on disk.  After CLI proof finalization overwrites it with the complete proof,
`git status --porcelain` shows the file as modified.  Because the path is in
`allowed_files` and does not match forbidden prefixes, it passes baseline.

**No change needed to the baseline check logic** for this part.  The fix is
in the dogfood CLI invocation — the stage_file path must be listed in both
`--allowed-file` and `--stage-file`.  This is an invocation-side contract,
not a code change.

**One code change IS needed**: The `_check_git_baseline` function currently
applies `FORBIDDEN_PAYLOAD_PREFIXES` checks BEFORE the `allowed_set` check.
This means even if `captures/` were in `allowed_files`, it would still be
blocked as forbidden.  This is correct for captures/ and .ariadne/, but for
the `reviews/` prefix, we need to understand whether a generated review under
`.project-memory/pr/<pr-id>/reviews/precommit-review.yml` matches.

The prefix `"reviews/"` matches only paths that START with `reviews/`.
The actual path `.project-memory/pr/<pr-id>/reviews/precommit-review.yml`
starts with `.project-memory/`, not `reviews/`.  So the forbidden prefix
does NOT catch it — it gets caught by the `allowed_set` check as an
unrelated dirty file.  This is correct — generated reviews that happen to
have `reviews/` in their path are not forbidden by prefix; they are simply
out of scope.

### 2. Runtime Residue Hygiene

**Design**: Add a cleanup/sanitization step in `run_ariadne_task()` between
pipeline completion (step 3) / proof finalization (step 4c) and dirty
baseline check (step 4b).

The cleanup step removes known runtime residue files that are:
- **Not commit payload** — they are diagnostic evidence or gate-passing
  artifacts from the current run
- **Already hashed/recorded** in bridge results or pipeline results
- **Safe to remove** because their content is already captured in memory

**Residue types to clean**:

| Path | Reason | Action |
|------|--------|--------|
| `captures/` | Bridge diagnostic captures (already hashed in bridge result) | Remove entire `captures/` directory under repo_root |
| `.project-memory/pr/<pr_id>/reviews/precommit-review.yml` | Generated by pipeline for gate-passing (already recorded in pipeline result) | Remove if exists |
| `.ariadne/runs/<run-id>/` | Persisted run records — must never be staged | **Ignore in baseline** (change: from forbidden to silently ignored) |

**Cleanup implementation**:

```python
def _cleanup_runtime_residue(repo_root: str, pr_id: str) -> None:
    """Remove runtime residue before dirty baseline check.

    Removes captures/ and generated reviews that are runtime artifacts,
    not commit payload.
    """
    # 1. Remove captures/ directory
    captures_dir = os.path.join(repo_root, "captures")
    if os.path.isdir(captures_dir):
        import shutil
        shutil.rmtree(captures_dir)

    # 2. Remove generated precommit-review.yml under current PR path
    review_path = os.path.join(
        repo_root, ".project-memory", "pr", pr_id, "reviews", "precommit-review.yml"
    )
    if os.path.exists(review_path):
        os.remove(review_path)
```

**Baseline change for `.ariadne/` files**:

Current behavior in `_check_git_baseline`:

```python
FORBIDDEN_PAYLOAD_PREFIXES = (".ariadne/", "captures/", "reviews/")
```

Files matching `.ariadne/` are treated as `FORBIDDEN_PAYLOAD` — they emit
`dirty_tree_out_of_scope` with `Forbidden payload path:` warning.

New behavior: `.ariadne/` files should be **silently ignored** — they are
runtime persistence records created by the CLI itself.  The dirty baseline
should not block because the CLI persisted run records.  They must also
never be staged (controlled by Git Boundary, not baseline).

Change: Move `.ariadne/` from `FORBIDDEN_PAYLOAD_PREFIXES` to a new
`IGNORED_BASELINE_PREFIXES` tuple.  Files matching ignored prefixes are
skipped entirely — no code added, no warning emitted.

```python
FORBIDDEN_PAYLOAD_PREFIXES = ("captures/",)
IGNORED_BASELINE_PREFIXES = (".ariadne/",)
```

The loop logic becomes:

```python
for line in status_result.stdout.splitlines():
    ...
    # Skip ignored baseline prefixes (e.g., .ariadne/ run records)
    if any(filename.startswith(p) for p in IGNORED_BASELINE_PREFIXES):
        continue
    
    # Check forbidden payload prefixes
    is_forbidden = any(filename.startswith(p) for p in FORBIDDEN_PAYLOAD_PREFIXES)
    if is_forbidden:
        codes.append("dirty_tree_out_of_scope")
        warnings.append("Forbidden payload path: " + filename)
        continue
    
    # Check allowed set
    if filename not in allowed_set:
        codes.append("dirty_tree_out_of_scope")
        warnings.append("Unrelated dirty file: " + filename)
```

**Placement in the flow** (updated step numbering):

```
1. Validate task description
2. Detect payload artifact path + build pipeline request
3. Run pipeline
4. Check pipeline result (early return on failure)
4b. **Cleanup runtime residue**  ← NEW
4c. Git baseline check — dirty + branch sync
4d. Proof finalization (render, write, validate)
5-9. Git Boundary (unchanged)
10. Persist + return
```

**Why cleanup before baseline, not before proof finalization**: The
generated precommit-review.yml must exist for the gate to pass.  Cleanup
after all gates have passed but before the baseline check is the correct
point.

**Why `captures/` removal is safe**: The bridge proof capture has already
been written to `captures/`, but its content (hashes, agent name, prompt
hash) is already captured in the `AgentRunnerBridgeResult` object.  The
file on disk is a diagnostic duplicate with no downstream consumer.

**Why `reviews/` removal is safe**: The pipeline gate has already parsed
and recorded the verdict.  The file on disk is a generated artifact for
gate-passing only.

### 3. Existing Proof Test Boundary

**Problem**: Two tests assert that real PR 0131 dogfood artifacts must not
exist.  After PR #150 merged, these artifacts ARE committed files.

**Affected tests**:

1. `test_agent_runner_bridge.py::TestLocalArtifactMaterialization::test_no_real_pr_artifacts_created`
   (line 1156)

   Current assertion:
   ```python
   real_dogfood_proof = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml")
   real_precommit = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml")
   assert not real_dogfood_proof.exists()
   assert not real_precommit.exists()
   ```

2. `test_pipeline_runner.py::TestPipelineRunnerNoMissingReviewArtifact::test_no_real_pr_artifacts_created_in_tests`
   (line 1506)

   Current assertion:
   ```python
   real_dogfood_proof = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml")
   real_precommit = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml")
   assert not real_dogfood_proof.exists()
   assert not real_precommit.exists()
   ```

**Correct contract**: Tests must assert they do not CREATE or MUTATE real
PR 0131 artifacts.  Not that real PR 0131 artifacts are absent from the
repository.

**Implementation**: Replace `assert not ...exists()` with a
snapshot-and-assert-unchanged pattern:

```python
# Snapshot existing real dogfood proof (committed by #150)
real_dogfood_proof = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml")
real_precommit = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml")

dogfood_snapshot = real_dogfood_proof.read_text(encoding="utf-8") if real_dogfood_proof.exists() else None
precommit_snapshot = real_precommit.read_text(encoding="utf-8") if real_precommit.exists() else None

# ... run the test ...

# Assert unchanged: if artifact existed before test, it must still exist
# with identical content.  If it did not exist, it must still not exist.
if dogfood_snapshot is not None:
    assert real_dogfood_proof.exists()
    assert real_dogfood_proof.read_text(encoding="utf-8") == dogfood_snapshot
else:
    assert not real_dogfood_proof.exists()

if precommit_snapshot is not None:
    assert real_precommit.exists()
    assert real_precommit.read_text(encoding="utf-8") == precommit_snapshot
else:
    assert not real_precommit.exists()
```

This pattern:
- Passes whether the artifact exists or not
- Passes after PR #150 (artifact exists, snapshot captures committed content)
- Passes before PR #150 (artifact does not exist, snapshot is None)
- Catches test mutation (if test writes to the real path, content differs)
- Does not require real dogfood artifact absence

**Additional assertion**: Both tests also need to verify that no files were
created under the REAL PR path during the test:

```python
# Verify no new files were created under real PR path during test
real_pr_dir = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne")
expected_files = {"PLAN.md", "dogfood-proof.yml", "reviews/plan-review.yml"}
actual_files = set()
if real_pr_dir.exists():
    for f in real_pr_dir.rglob("*"):
        if f.is_file():
            rel = f.relative_to(real_pr_dir)
            actual_files.add(str(rel))
# Only expected committed files; no new generated artifacts
assert actual_files.issubset(expected_files), f"Unexpected files: {actual_files - expected_files}"
```

### 4. Preserve Safety

Do not weaken dirty baseline globally:

| Scenario | After this PR | 
|----------|--------------|
| Unrelated untracked file | Still blocks (`dirty_tree_out_of_scope`) |
| Unrelated tracked modification | Still blocks |
| Unrelated staged file | Still blocks (via `git diff --cached`) |
| Unrelated `.project-memory/pr/**` directory | Still blocks |
| `captures/` not cleaned by cleanup | Still blocks (forbidden payload prefix) |
| Generated review outside current PR path | Still blocks |
| Unrelated user file | Still blocks |

**What does not block anymore**:

| Scenario | Why safe |
|----------|---------|
| `.ariadne/runs/<run-id>/run.json` | Ignored prefix — never staged (Git Boundary controls staging) |
| `.ariadne/manifest.json` | Same as above |
| Cleaned `captures/` (removed before baseline) | Already removed — not in working tree |
| Cleaned generated review (removed before baseline) | Already removed — not in working tree |

### 5. Scope

**Preferred implementation files**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Add `_cleanup_runtime_residue()`; change `.ariadne/` from forbidden to ignored prefix; call cleanup before baseline |
| `services/runner/tests/test_ariadne_task_cli.py` | Tests for runtime residue cleanup, `.ariadne/` ignored, captures removed, reviews removed |
| `services/runner/tests/test_agent_runner_bridge.py` | Update `test_no_real_pr_artifacts_created` to snapshot pattern |
| `services/runner/tests/test_pipeline_runner.py` | Update `test_no_real_pr_artifacts_created_in_tests` to snapshot pattern |

**Optional only with evidence** (only if `_check_git_baseline` logic needs
to change to support ignored prefixes):

| File | Changes |
|------|---------|
| `services/runner/src/runner/git_boundary.py` | Only if `_is_forbidden_path` needs `IGNORED_BASELINE_PREFIXES` (it does not — baseline is CLI-only) |
| `services/runner/tests/test_git_boundary.py` | Only if above |

**Not modified**:

- `agent_runner_bridge.py` — no change needed
- `pipeline_runner.py` — no change needed
- `run_persistence.py` — no change needed
- `ROADMAP.md` — not modified
- `docs/` — not modified
- `agents/` — not modified
- `schemas/` — not modified
- Dependencies — not modified

### 6. Non-goals

- No new runtime modules
- No new architecture
- No retry/failure recovery loop (PR 0132)
- No model health live fallback (PR 0133)
- No run report (PR 0134)
- No parallel-safe queue (PR 0135)
- No dashboard or control plane
- No Decision Core / GRM / Context Warehouse / eval harness / frontend
- No ROADMAP/docs/agents/schemas/dependency modifications
- No Git Boundary modifications (unless unavoidable for ignored prefix)
- No Docker enabling
- No agent git/gh mutation rights
- No real dogfood runs in tests
- No real git/gh/Docker/network/agents in tests
- No frozen stream starts

## Tests

### Runtime Hygiene Tests (all in `test_ariadne_task_cli.py`)

1. **`test_finalized_dogfood_proof_at_stage_file_allowed`**:
   - Write complete proof at stage_file path (path in `allowed_files`)
   - Inject status provider showing the proof as modified
   - Verify baseline passes (no `dirty_tree_out_of_scope`)

2. **`test_weak_proof_not_allowed_through_baseline`**:
   - Write weak bridge placeholder at stage_file path
   - Inject status provider showing weak proof as modified
   - Verify CLi blocks with `dogfood_proof_incomplete` (existing test, ensure passes)

3. **`test_generated_precommit_review_removed_before_baseline`**:
   - Create generated precommit-review.yml under current PR path
   - Call `_cleanup_runtime_residue`
   - Verify file does not exist after cleanup

4. **`test_captures_directory_removed_before_baseline`**:
   - Create `captures/` dir with files
   - Call `_cleanup_runtime_residue`
   - Verify `captures/` dir does not exist

5. **`test_ariadne_run_records_ignored_in_baseline`**:
   - Inject status provider showing `.ariadne/runs/foo/run.json` as modified
   - Verify baseline does NOT emit `dirty_tree_out_of_scope` for `.ariadne/`
   - Verify `.ariadne/` file is silently skipped

6. **`test_runtime_residue_never_staged`**:
   - Run full fake CLI flow with captures/, reviews/, .ariadne/ residue
   - Verify command_plan only includes dogfood-proof.yml paths
   - Verify captures/, reviews/, .ariadne/ not in files_to_stage

7. **`test_unrelated_untracked_file_still_blocks`**:
   - Inject status provider with unrelated untracked file
   - Verify `dirty_tree_out_of_scope` emitted
   - Verify blocked

8. **`test_unrelated_tracked_modification_still_blocks`**:
   - Inject status provider with unrelated tracked modification
   - Verify blocked

9. **`test_unrelated_staged_file_still_blocks`**:
   - Inject status provider with staged file not in allowed_files
   - Verify blocked

10. **`test_unrelated_project_memory_pr_directory_still_blocks`**:
    - Inject status provider with file under unrelated `.project-memory/pr/other-pr/`
    - Verify blocked

### Existing Proof Boundary Tests

11. **`test_bridge_snapshots_existing_dogfood_proof_and_asserts_unchanged`**
    (in `test_agent_runner_bridge.py`, replaces `test_no_real_pr_artifacts_created`):
    - Snapshot committed real PR 0131 dogfood proof (if exists)
    - Run bridge test
    - Assert dogfood proof unchanged (content identical)
    - Assert no new files created under real PR path

12. **`test_pipeline_snapshots_existing_dogfood_proof_and_asserts_unchanged`**
    (in `test_pipeline_runner.py`, replaces `test_no_real_pr_artifacts_created_in_tests`):
    - Snapshot committed real PR 0131 dogfood proof (if exists)
    - Run pipeline test
    - Assert dogfood proof unchanged
    - Assert no new files created under real PR path

13. **`test_tests_pass_whether_real_dogfood_proof_exists_or_not`**
    (in both test files, parametrized or separate):
    - Same test logic — snapshot-based assertion works both ways

14. **`test_tests_create_artifacts_only_under_tmp_path`**
    (in both test files, verify existing tmp_path-only pattern):
    - Assert no files written outside `tmp_path`

### Final Dogfood Regression Tests (all in `test_ariadne_task_cli.py`)

15. **`test_fake_dogfood_run_overwrites_weak_tracked_proof`**:
    - Create committed weak proof at stage_file path
    - Run full CLI with fake pipeline and planner
    - Verify proof on disk is complete (not weak placeholder)

16. **`test_fake_dogfood_run_captures_residue_not_staged`**:
    - Run full CLI with captures/ and generated review residue
    - Verify command plan stages only dogfood-proof.yml
    - Verify captures/ and reviews/ not in files_to_stage

17. **`test_fake_dogfood_run_still_persists_run_json_locally`**:
    - Run full CLI with explicit `--run-id` and no `--runs-root` (auto-defaults)
    - Verify `.ariadne/runs/` directory exists
    - Verify `run.json` exists after run

## Implementation Steps

1. **Add `_cleanup_runtime_residue()` to `ariadne_task_cli.py`**:
   - Remove `captures/` directory under repo_root
   - Remove generated `precommit-review.yml` under `.project-memory/pr/<pr_id>/reviews/`
   - Uses `shutil.rmtree` for directory, `os.remove` for single file
   - Wrapped in `try/except` to not crash on missing paths

2. **Change `.ariadne/` baseline handling**:
   - Add `IGNORED_BASELINE_PREFIXES = (".ariadne/",)` at module level
   - In `_check_git_baseline()`, add early `continue` for ignored prefixes
     **before** the forbidden payload prefix check
   - Remove `.ariadne/` from `FORBIDDEN_PAYLOAD_PREFIXES`

3. **Integrate cleanup into `run_ariadne_task()` flow**:
   - After pipeline result check (step 4), before baseline (step 4b):
     ```python
     # 4a. Cleanup runtime residue
     _cleanup_runtime_residue(request.repo_root, request.pr_id)
     ```

4. **Update test `test_no_real_pr_artifacts_created`** in
   `test_agent_runner_bridge.py`:
   - Replace `assert not ...exists()` with snapshot-and-unchanged pattern
   - Add directory-level assertion for no new files under real PR path

5. **Update test `test_no_real_pr_artifacts_created_in_tests`** in
   `test_pipeline_runner.py`:
   - Same pattern as above

6. **Add new tests** to `test_ariadne_task_cli.py`:
   - Runtime hygiene tests (items 1-10 above)
   - Final dogfood regression tests (items 15-17 above)

7. **Validate with compile and pytest commands**

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0131i-dogfood-artifact-hygiene-existing-proof-boundary`
- PLAN allows arbitrary dirty files through baseline
- PLAN allows generated precommit-review.yml to be staged
- PLAN allows captures/ to be staged
- PLAN ignores that #150 already committed dogfood-proof.yml
- PLAN keeps asserting real dogfood artifact must not exist
- PLAN does not preserve unrelated dirty file blocking
- PLAN bypasses Git Boundary
- PLAN grants agents git/gh mutation authority
- PLAN requires real dogfood in tests
- PLAN requires real git/gh/Docker/network/agents in tests
- PLAN modifies ROADMAP/docs/agents/schemas/dependencies
- PLAN starts frozen streams

## Validation Commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
  -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py::TestLocalArtifactMaterialization::test_no_real_pr_artifacts_created \
  services/runner/tests/test_pipeline_runner.py::TestPipelineRunnerNoMissingReviewArtifact::test_no_real_pr_artifacts_created_in_tests \
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
  "dirty_tree_out_of_scope|Forbidden payload path|captures|precommit-review.yml|dogfood-proof.yml|allowed_file|stage_file|command_plan_summary|dogfood_proof_incomplete|_validate_dogfood_proof_content|_compute_plan_summary|run_record_path|run_json_hash|proof_artifact_ref|snapshot|unchanged|exists|_cleanup_runtime_residue|IGNORED_BASELINE_PREFIXES" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131i-dogfood-artifact-hygiene-existing-proof-boundary

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git init|git checkout|git add|git commit|git push|gh pr create|gh release|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131i-dogfood-artifact-hygiene-existing-proof-boundary

git status --short
git diff --name-only
```
