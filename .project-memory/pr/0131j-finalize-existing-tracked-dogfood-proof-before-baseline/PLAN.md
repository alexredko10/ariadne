# PR 0131J — Finalize Existing Tracked Dogfood Proof Before Baseline Plan

## Summary

PR 0131G added the proof renderer.  PR 0131H added runtime proof finalization
and validation gate.  PR 0131I added runtime residue cleanup (captures/,
generated reviews, `.ariadne/` ignored in baseline).

After all three PRs, the next real dogfood attempt still produced:

- `status: blocked`
- `pipeline_status: completed`, `pipeline_final_action: continue`
- `reason_codes: ['dirty_tree_out_of_scope']`
- `execution_attempted: false`
- `git_boundary_status: null`
- `run.json` and `manifest.json` persisted

The dogfood-proof.yml on disk after the failed run was still the weak
bridge placeholder from PR #150:

```yaml
schema_version: "0.1"
pr_id: ""
dogfood_type: "local-non-docker"
status: "completed"
bridge_task_prompt_hash: "<hash>"
bridge_agent_config_hash: "<hash>"
proof_artifact_ref: ""
materialized_at: "<timestamp>"
```

**Root cause**: The step order in `run_ariadne_task()` after PR 0131I is:

1. Step 3 — Run pipeline (bridge may materialize weak proof at stage_file)
2. Step 4 — Check pipeline result
3. Step 4b — `_cleanup_runtime_residue()` ← removes captures/, reviews/
4. **Step 4c — Baseline check** ← runs BEFORE proof finalization
5. **Step 4c — Proof finalization (render, write, validate)** ← runs AFTER baseline

Because the baseline runs before proof finalization, when the requested
stage_file path still contains the bridge-materialized weak proof (or the
committed weak proof from #150), the baseline sees a dirty file.  If the
path is IN `allowed_files`, the baseline passes — but the weak proof then
fails `_validate_dogfood_proof_content` with `dogfood_proof_incomplete`.
If the path is NOT in `allowed_files`, it blocks with
`dirty_tree_out_of_scope`.  Either way, the proof on disk at baseline
time is still weak.

**Fix**: Move proof finalization (section `# 4c` render/write/validate)
to run **before** the baseline check.  The corrected order:

1. Step 3 — Run pipeline
2. Step 4 — Check pipeline result
3. Step 4a — `_cleanup_runtime_residue()` ← remove captures/, reviews/
4. Step 4b — **Proof finalization** (render complete proof, write to stage_file,
   validate content) ← runs BEFORE baseline
5. Step 4c — **Baseline check** ← sees complete finalized proof, not weak placeholder

## Context

| Field | Value |
|-------|-------|
| Committed weak proof | `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml` (PR #150) |
| After 0131I order | cleanup → **baseline** → proof finalization ← BUG |
| Corrected order | cleanup → **proof finalization** → baseline |
| Real dogfood outcome | `reason_codes: [dirty_tree_out_of_scope]`, weak proof on disk |
| Existing tracked proof | Modified by bridge materialization; seen by baseline before CLI overwrites it |

## Roadmap alignment

* **roadmap track**: Production Line — Stage 2 Closed Loop
* **expected PR slot**: PR 0131J (ordering correction after 0131I)
* **why this PR is next**: 0131I fixed runtime residue but left the ordering wrong — baseline still runs before proof finalization.  Dogfood cannot proceed until the proof is written and validated before baseline.
* **batching policy check**: Single-purpose ordering fix; no feature expansion.
* **drift heuristic check**: Does not touch frozen streams; does not add new product modules; does not modify ROADMAP/docs/agents/schemas/deplock.

## Design

### 1. Existing Tracked Proof Finalization

**Problem**: The existing tracked dogfood-proof.yml from #150 is a committed
file.  During the dogfood pipeline, the bridge materializer writes a new
weak placeholder to the same path (because `overwrite_allowed=True` for the
stage_file).  After the pipeline, `git status --porcelain` shows the file
as modified.

Before 0131J, the CLI proof finalizer (`_render_dogfood_proof_yaml` + write
+ `_validate_dogfood_proof_content`) runs AFTER the baseline check.  The
baseline sees the weak bridge content and either:
- Blocks as `dirty_tree_out_of_scope` (if stage_file not in `allowed_files`)
- Or lets it through as allowed, but then the Git Boundary planner sees the
  weak proof and blocks at the plan level

**Fix**: Move proof finalization before baseline so that by the time the
baseline runs, the stage_file path contains the complete CLI-finalized proof.

The `_render_dogfood_proof_yaml()` already has all runtime context (pipeline
status, artifact hashes, plan summary, run_id, run_record_path).  It
produces all 20 required fields with non-empty critical values.  The
overwrite via `open(full_path, "w")` works on both tracked files (committed
by #150) and untracked files.

**Edge cases**:
- **File does not exist**: `os.makedirs` creates parent directories, then
  `open(..., "w")` creates the file.  Stage-file existence check in Git
  Boundary planner then passes.
- **File exists as untracked**: Same overwrite path.
- **File exists as tracked (committed)**: Same overwrite path — `open(...,
  "w")` modifies in-place, git sees it as modified.
- **File exists as tracked modified by bridge**: Same overwrite path.

### 2. Ordering

**Corrected runtime order**:

```
1.  Validate task description
2.  Build pipeline request
3.  Run pipeline (bridge may materialize weak proof)
4.  Check pipeline result (early return on failure)
4a. _cleanup_runtime_residue()            ← remove captures/, generated reviews
4b. Proof finalization:
      - Compute plan_summary from request
      - Render complete proof YAML (all 20 fields)
      - Write to each files_to_stage path (overwrites bridge/committed weak proof)
      - Validate written proof content
      - If validation fails → block with dogfood_proof_incomplete
4c. Baseline + branch sync check:
      - baseline_fn sees complete CLI-finalized proof, not weak placeholder
      - If baseline fails → block with dirty_tree_out_of_scope
5.  Build GitBoundaryRequest
6.  Plan git boundary
7.  Check git boundary plan
8.  Check execution/approval requirements
9.  Execute git boundary
10. Determine final status
```

**Key invariant**: By the time `baseline_fn` runs at step 4c, the
stage_file path contains the complete CLI-proof content.  If the file is
tracked, it shows as modified by `git status` — but it is in `allowed_files`
and does not match any forbidden/ignored prefix, so it passes baseline.

**Proof validation and baseline do not conflict**: If proof validation
passes (all 20 fields, no weak patterns), the file is considered valid
dogfood payload.  The baseline then sees this file as a modified tracked
file in `allowed_files`.  If proof validation fails, the CLI returns before
baseline runs — no conflict.

**If proof validation passes but baseline still fails** (e.g., because
some other unrelated file is dirty): The CLI returns with
`dirty_tree_out_of_scope` and the proof remains on disk as a valid
committed-but-unpushed artifact.  The human can clean the unrelated file
and retry.

### 3. Dirty Baseline / Proof Validation Priority

When the requested stage_file contains weak proof content (bridge
placeholder), the task should block with:

```
reason_codes: ['dogfood_proof_incomplete']
```

not:

```
reason_codes: ['dirty_tree_out_of_scope']
```

This is because the dirty file IS the intended payload — it is at the
requested stage_file path and is listed in `allowed_files`.  The problem
is not that it's an unrelated dirty file; the problem is that the proof
content itself is incomplete.

**How this works in the corrected order**:

1. Proof finalizer runs (step 4b):
   - Renders complete proof YAML
   - Writes to stage_file path (overwrites weak bridge placeholder)
   - Calls `_validate_dogfood_proof_content(path)` on the written file
2. If validation fails → `codes.append(REASON_DOGFOOD_PROOF_INCOMPLETE)`
   → CLI returns BLOCKED with `dogfood_proof_incomplete`
3. If validation passes → flow continues to baseline (step 4c)
4. Baseline checks dirty tree:
   - stage_file path is in `allowed_files` → passes `allowed_set` check
   - If other dirty files exist → `dirty_tree_out_of_scope`

So: weak proof → `dogfood_proof_incomplete`.  Valid proof + other dirty
files → `dirty_tree_out_of_scope`.  Valid proof + clean tree → proceeds
to Git Boundary.

**Current code (0131I)**: The code already emits `REASON_DOGFOOD_PROOF_INCOMPLETE`
when proof validation fails.  The problem is that this validation happens
AFTER the baseline, so the baseline has already emitted
`dirty_tree_out_of_scope` for the weak proof file (if it's not in
`allowed_files`) or the baseline passes but then validation fails.  Moving
proof validation before baseline fixes the priority — `dogfood_proof_incomplete`
will be the first and only reason code for weak proof at the stage_file path.

### 4. Complete Proof Validation

Already implemented in `_validate_dogfood_proof_content()` (PR 0131H):

- All 20 required fields checked
- Critical non-empty fields checked: `pr_id`, `run_id`, `branch`,
  `proof_artifact_ref`
- Weak bridge placeholder patterns rejected
- `command_plan_summary: []` rejected
- Allowed sentinels: `pr_url: "pending-before-gh-pr-create"`,
  `run_json_hash: "pending"`

**Change needed**: Update `run_json_hash` sentinel check to also accept
`"pending-before-run-persist"` (the new sentinel value requested in this
task's spec).  Currently the sentinel is `"pending"`.  The task requires
`"pending-before-run-persist"`.  Either add the new sentinel as an
additional allowed value, or replace the old one.

Decision: Add `"pending-before-run-persist"` to `_ALLOWED_SENTINEL_VALUES`
for `run_json_hash`, keeping the original `"pending"` for backward
compatibility.

```python
_ALLOWED_SENTINEL_VALUES: dict[str, tuple[str, ...]] = {
    "pr_url": ("pending-before-gh-pr-create",),
    "run_json_hash": ("pending", "pending-before-run-persist"),
}
```

No change to the renderer itself — the current renderer outputs
`run_json_hash: "pending"`; the new sentinel is an additional accepted
value in validation, not a change to the rendered output (unless the
renderer is updated to output the new sentinel).  The task description
says both sentinels are acceptable, so allow both.

### 5. Preserve 0131I Hygiene

Do not regress any 0131I changes:

| 0131I feature | Preserved by |
|---------------|-------------|
| `_cleanup_runtime_residue()` | Still called at step 4a (before proof finalization) |
| `.ariadne/` ignored in baseline | `IGNORED_BASELINE_PREFIXES` unchanged |
| `captures/` forbidden payload | `FORBIDDEN_PAYLOAD_PREFIXES` unchanged |
| Generated reviews cleaned | `_cleanup_runtime_residue` removes them |
| Command plan stages only requested stage_file | Git Boundary plan unchanged |
| Unrelated dirty files still block | Baseline logic unchanged |

### 6. Scope

**Preferred implementation files**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Reorder steps 4b/4c — move proof finalization before baseline. Sentinel update for `run_json_hash`. |
| `services/runner/tests/test_ariadne_task_cli.py` | Add/update tests for ordering, weak-proof-before-baseline, dirty baseline result priority |

**Optional only with evidence**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/git_boundary.py` | Only if `_is_forbidden_path` needs changes for dogfood-proof.yml (it does not — path does not match any forbidden prefix) |
| `services/runner/tests/test_git_boundary.py` | Only if above |

**Not modified**:

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

### 7. Non-goals

- No new runtime modules
- No new architecture
- No retry/failure recovery loop (PR 0132)
- No model health live fallback (PR 0133)
- No run report (PR 0134)
- No parallel-safe queue (PR 0135)
- No dashboard or control plane
- No Decision Core / GRM / Context Warehouse / eval harness / frontend
- No ROADMAP/docs/agents/schemas/dependency modifications
- No Git Boundary modifications unless unavoidable
- No Docker enabling
- No agent git/gh mutation rights
- No real dogfood runs in tests
- No real git/gh/Docker/network/agents in tests
- No frozen stream starts

## Tests

### Ordering Tests (all in `test_ariadne_task_cli.py`)

1. **`test_existing_tracked_weak_proof_overwritten_before_baseline`**:
   - Create a committed (tracked) dogfood-proof.yml with weak bridge content
   - Run `run_ariadne_task()` with injectable baseline_fn that captures the
     content it sees
   - Verify the content captured by baseline_fn matches complete CLI proof,
     not bridge placeholder

2. **`test_bridge_materialized_weak_proof_overwritten_before_baseline`**:
   - Simulate bridge materialization: write weak placeholder to stage_file
   - Run `run_ariadne_task()` with injectable baseline_fn
   - Verify baseline_fn sees complete proof, not placeholder

3. **`test_baseline_sees_complete_proof_not_weak`**:
   - Inject baseline_fn that records the exact file content it received
   - Run full flow with fake pipeline
   - Assert recorded content has non-empty `pr_id`, non-empty
     `proof_artifact_ref`, non-empty `command_plan_summary`

### Dirty Baseline Priority Tests (all in `test_ariadne_task_cli.py`)

4. **`test_weak_proof_at_stage_file_blocks_with_dogfood_proof_incomplete`**:
   - Write weak bridge placeholder at the exact stage_file path
   - Ensure the path is in `allowed_files`
   - Run `run_ariadne_task()` with fake pipeline
   - Verify `reason_codes` contain `dogfood_proof_incomplete`
   - Verify `reason_codes` do NOT contain `dirty_tree_out_of_scope`

5. **`test_complete_proof_and_unrelated_dirty_file_blocks_with_dirty_tree_out_of_scope`**:
   - Write complete proof at stage_file path
   - Inject status provider showing unrelated dirty file
   - Run `run_ariadne_task()` with fake pipeline
   - Verify `reason_codes` contain `dirty_tree_out_of_scope`
   - Verify `reason_codes` do NOT contain `dogfood_proof_incomplete`

### Payload Allowance Tests (all in `test_ariadne_task_cli.py`)

6. **`test_exact_requested_stage_file_allowed_only_after_proof_validates`**:
   - Write complete proof at stage_file path
   - Inject status provider showing only the proof as modified
   - Run with fake pipeline and planner
   - Verify CLI proceeds to Git Boundary (not blocked at baseline or proof
     validation)

7. **`test_arbitrary_dogfood_proof_yml_path_still_blocks`**:
   - Write complete proof at a path NOT in `allowed_files`
   - Inject status provider showing that path as modified
   - Run with fake pipeline
   - Verify blocked with `dirty_tree_out_of_scope`

### 0131I Regression Tests (all in `test_ariadne_task_cli.py`)

8. **`test_generated_review_and_captures_not_staged_after_reorder`**:
   - Run full fake flow with captures/ and generated reviews in tree
   - Verify captures/ and reviews/ are removed (the cleanup before
     finalization still runs)

9. **`test_ariadne_ignored_in_baseline_after_reorder`**:
   - Inject status provider showing `.ariadne/runs/foo/run.json`
   - Verify baseline silently skips it (no warning, no code)

10. **`test_unrelated_dirty_file_still_blocks_after_reorder`**:
    - Inject status provider with unrelated untracked file
    - Verify `dirty_tree_out_of_scope` emitted

### Final Dogfood Regression (all in `test_ariadne_task_cli.py`)

11. **`test_fake_dogfood_run_proceeds_to_git_boundary_when_only_finalized_proof_is_dirty`**:
    - Write complete proof at stage_file path (path in `allowed_files`)
    - Inject clean status provider (only proof is dirty)
    - Run with fake pipeline and fake planner that returns valid plan
    - Verify CLI reaches Git Boundary (status not blocked at baseline or
      proof validation)

12. **`test_fake_dogfood_run_weak_proof_blocks_at_proof_gate`**:
    - Write weak placeholder at stage_file path (path in `allowed_files`)
    - Run with fake pipeline
    - Verify blocked with `dogfood_proof_incomplete`
    - Verify `execution_attempted` is False

13. **`test_fake_dogfood_run_completes_when_only_intended_proof_is_dirty`**:
    - Write complete proof at stage_file path (path in `allowed_files`)
    - Inject clean baseline (only proof is modified)
    - Run with fake pipeline and fake planner
    - Verify `status` is COMPLETED or COMPLETED_WITH_WARNING
    - Verify `git_boundary_status` is not None

### No Real Dogfood / Git / Gh / Docker / Network / Agents

14. **`test_no_real_git_gh_docker_network_agents_in_order_tests`**:
    - grep for forbidden patterns in test file returns 0

## Implementation Steps

1. **Reorder proof finalization before baseline in `run_ariadne_task()`**:
   - Current order (after 0131I):
     ```
     # 4b. Cleanup runtime residue
     _cleanup_runtime_residue(...)
     
     # 4c. Git baseline check
     if request.execute:
         ...
     
     # 4c. Render dogfood proof
     if request.files_to_stage:
         ...
     ```
   - Corrected order:
     ```
     # 4a. Cleanup runtime residue
     _cleanup_runtime_residue(...)
     
     # 4b. Render dogfood proof (before baseline)
     if request.files_to_stage:
         render_proof -> write -> validate
         if validation fails -> BLOCKED with dogfood_proof_incomplete
     
     # 4c. Git baseline check (sees complete proof)
     if request.execute:
         baseline_fn(..., allowed_files=...) -> proof is in allowed_set
         branch_sync check
         if baseline fails -> BLOCKED with dirty_tree_out_of_scope
     ```

2. **Update `_ALLOWED_SENTINEL_VALUES`**:
   - Add `"pending-before-run-persist"` to `run_json_hash` tuple:
     ```python
     "run_json_hash": ("pending", "pending-before-run-persist"),
     ```

3. **Add/update tests** in `test_ariadne_task_cli.py`:
   - Ordering tests (1-3)
   - Dirty baseline priority tests (4-5)
   - Payload allowance tests (6-7)
   - 0131I regression tests (8-10)
   - Final dogfood regression tests (11-13)
   - No real side effects test (14)

4. **Validate with compile and pytest commands**

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0131j-finalize-existing-tracked-dogfood-proof-before-baseline`
- PLAN does not acknowledge the remaining single `dirty_tree_out_of_scope` after 0131I
- PLAN does not address existing tracked weak proof from PR #150
- PLAN allows dirty baseline to run before proof finalization
- PLAN allows weak proof to be classified only as generic dirty tree
- PLAN weakens unrelated dirty-file blocking
- PLAN allows arbitrary dogfood-proof.yml paths
- PLAN allows generated reviews/captures/.ariadne to be staged
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

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "finalize|dogfood-proof.yml|dogfood_proof_incomplete|dirty_tree_out_of_scope|_cleanup_runtime_residue|IGNORED_BASELINE_PREFIXES|FORBIDDEN_PAYLOAD_PREFIXES|_validate_dogfood_proof_content|_compute_plan_summary|proof_artifact_ref|pending-before-gh-pr-create|pending-before-run-persist|command_plan_summary|stage_file|allowed_file" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131j-finalize-existing-tracked-dogfood-proof-before-baseline

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git init|git checkout|git add|git commit|git push|gh pr create|gh release|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131j-finalize-existing-tracked-dogfood-proof-before-baseline

git status --short
git diff --name-only
```
