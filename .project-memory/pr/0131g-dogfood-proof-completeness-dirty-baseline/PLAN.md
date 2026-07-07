# PR 0131G — Dogfood Proof Completeness and Dirty Baseline Enforcement Plan

## Summary

One narrow hardening PR before PR 0131 dogfood can be considered clean and
mergeable.  PR 0131F (real dogfood) succeeded in reaching GitHub PR creation
(PR #150, `ARIADNE_DOGFOOD_EXIT=0`, pipeline completed, git/gh side effects
executed), but left two quality gaps:

1. **Incomplete committed dogfood proof** — The committed
   `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`
   had empty/placeholder fields (`pr_id: ""`, `proof_artifact_ref: ""`) instead
   of real runtime evidence fields (run_id, pipeline status, execution
   attempted, command plan summary, PR URL, run record path, hashes,
   approval summary, timestamp).

2. **Missing dirty baseline enforcement** — Real execution proceeded even
   though `git status` showed unrelated untracked files (`.project-memory/pr/0127/`,
   `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/`,
   `.project-memory/pr/0131f-*`, `.project-memory/pr/dogfood/`, `captures/`).
   The Git Boundary remained approved.  Branch was ahead of origin by 3
   commits.  No pre-execution baseline check blocked.

This PR does **not** change the dogfood path.  It enforces what the path
should have required before real side effects.

## Context

| Field | Value |
|-------|-------|
| Real dogfood PR URL | https://github.com/alexredko10/ariadne/pull/150 |
| Dogfood exit | `ARIADNE_DOGFOOD_EXIT=0` |
| pipeline_status | completed |
| pipeline_final_action | continue |
| pipeline_has_blockers | false |
| git_boundary_status | approved |
| execution_attempted | true |
| Committed proof had empty `pr_id` and `proof_artifact_ref` | Observed |
| Untracked residue during execution | `.project-memory/pr/0127/`, `.project-memory/pr/0131-*/reviews/`, `.project-memory/pr/0131f-*`, `.project-memory/pr/dogfood/`, `captures/` |
| Branch ahead of origin | 3 commits before execution |
| Stale PR 0131f review files observed | `plan-review.yml`, `precommit-review.yml` under 0131f path |
| Base branch | main |

## Roadmap alignment

- **track**: Production Line — Stage 2 Closed Loop
- **expected PR slot**: PR 0131G (hardening gate before final dogfood merge)
- **why this PR is next**: PR 0131F proved the loop executes; this PR proves
  the loop executes *cleanly*.  Without it, the dogfood proof artifact is not
  self-validating and the baseline enforcement gap would repeat.
- **batching policy check**: Single-purpose hardening; no feature expansion.
- **drift heuristic check**: Does not touch frozen streams; does not add new
  product modules; does not modify ROADMAP/docs/agents/schemas/deplock.

## Design

### A. Dogfood Proof Completeness

**Design choice**: CLI post-run proof renderer (Option 1 from requirements).

After the pipeline completes and before Git Boundary execution, render a
dogfood proof artifact from runtime context (pipeline result, Git Boundary
plan, run persistence metadata, approval fields).  The proof file is written
to the stage-file path(s) so Git Boundary can stage and commit it.

**Renderer location**: `ariadne_task_cli.py` — a new function
`_render_dogfood_proof_yaml(result, git_plan, request)` that returns a YAML
string.  Called in `run_ariadne_task()` between pipeline completion and Git
Boundary planning.

**Proof fields** (all required):

| Field | Source |
|-------|--------|
| `schema_version` | `"0.1"` (constant) |
| `pr_id` | `request.pr_id` |
| `run_id` | `request.run_id` or auto-generated |
| `branch` | `request.branch` |
| `invocation_mode` | `"cli"` (constant for CLI path) |
| `pipeline_status` | `pipeline_result.status` |
| `pipeline_final_action` | `pipeline_result.final_action` |
| `pipeline_has_blockers` | `pipeline_result.has_blockers` |
| `git_boundary_status` | `"pending"` (before execution) |
| `command_plan_summary` | `[spec.operation for spec in git_plan.command_specs]` |
| `execution_attempted` | `False` at this point (before execution) |
| `pr_created` | `False` (before execution) |
| `pr_url` | `"pending-before-gh-pr-create"` |
| `run_record_path` | `.ariadne/runs/<run_id>/run.json` |
| `run_json_hash` | `"pending"` if not yet persisted |
| `artifact_hashes` | `pipeline_artifact_hashes` |
| `approval_summary` | Sanitized from `request.approval_reason` and `request.approved_by` |
| `timestamp` | Current UTC time |
| `note` | `"dogfood proof artifact, not a product feature"` |

**pr_url handling strategy**:
The committed proof cannot contain a final PR URL because `gh pr create`
runs **after** `git add/commit/push`.  Use the explicit sentinel value
`pr_url: "pending-before-gh-pr-create"` in the committed artifact.  The real
PR URL is captured by Git Boundary execution and recorded in `run.json`
(persisted locally, not committed).  A `pr_url` value other than the known
sentinel or a valid URL is a blocker at precommit-review time.

This is a **single-phase flow**: the proof is rendered once, before any git
mutation.  No follow-up update to the committed proof.

**Sanitization rules**:
- No raw full task prompt
- No secrets
- No raw full stdout/stderr except PR URL (sentinel) and operation summaries
- `approval_summary` sanitizes `approved_by` and `approval_reason` to
  avoid embedding raw identity strings if they contain secrets
- `artifact_hashes` summary only (SHA256[:16] values)

**Place in runtime flow**:
1. Pipeline completes → `pipeline_result` available
2. `_render_dogfood_proof_yaml(result, git_plan, request)` renders YAML
3. Proof YAML written to each path in `files_to_stage` (or first eligible
   path if multiple)
4. Git Boundary plan proceeds with the file now existing on disk
5. Git Boundary executes `git add/commit/push/gh pr create`
6. PR URL captured in execution results, persisted to `run.json`

**Edge case — no stage file**: If no `files_to_stage` is set, the proof
renderer is skipped.  The CLI still completes but without dogfood proof.

### B. Real Dirty Baseline Enforcement

**Design**: Pre-execution check in `run_ariadne_task()` that runs **before**
Git Boundary approval/execution, after pipeline completion.  This check
examines the actual git working tree, not just the `files_to_stage` list.

**Current gap**: The existing `git status --short` check at step 4b in
`ariadne_task_cli.py` is wrapped in `if request.repo_root and
request.repo_root != "."` — it does **not** run for the default repo_root
`"."`.  The fix: **always run the check** when `--execute` is set.

**Required checks** (in order, all must pass before Git Boundary proceeds):

1. **Unrelated untracked files check**
   - Run `git status --porcelain=v1` via injected status provider
   - For each line, parse status character and filename
   - Filenames starting with `.ariadne/` or `captures/` are blocked with
     clear error (these must never be committed payload)
   - Generated PR 0131 precommit-review.yml (`reviews/precommit-review.yml`)
     under current PR path is explicitly **excluded** from this check
     (it is a review artifact, not dogfood payload — but it also must not
     be staged by Git Boundary)
   - All other untracked/tracked-modified files not in `allowed_files` are
     blocked
   - Reason code: `dirty_tree_out_of_scope`

2. **Unrelated staged files check**
   - Run `git diff --cached --name-only` or parse `git status` porcelain
   - Any staged file not in `allowed_files` is blocked
   - Reason code: `dirty_tree_out_of_scope`

3. **Branch match check**
   - Run `git branch --show-current`
   - Must equal `request.branch`
   - Reason code: `branch_mismatch`

4. **Branch sync check**
   - Run `git status --porcelain=v1 --branch` and parse ahead/behind counts
   - If branch is ahead of upstream: block
   - If branch is behind upstream: block
   - If no upstream is configured: block with clear message requiring
     upstream
   - Reason code: `branch_ahead_or_behind` or `branch_not_clean`

5. **Stage-file existence check**
   - Already exists in `prepare_git_boundary_plan()` as `REASON_STAGE_FILE_MISSING`
   - Preserved as-is
   - Reason code: `stage_file_missing`

**Forbidden payload patterns** (blocked even if in `allowed_files`):
- `.ariadne/**`
- `captures/**`
- Any file under `reviews/` (precommit-review.yml is NOT a commit payload)

**Allowed files**: Only the explicit dogfood-proof.yml path(s) passed via
`--allowed-file` and `--stage-file`.

**Execution gate**: If any of the above checks fail:
- `execution_attempted` remains `False`
- `git_boundary_status` is set to `"blocked"` (not `"approved"`)
- CLI returns `status="blocked"` with specific reason codes
- Human must clean the tree and retry

**All five reason codes**:

| Code | When emitted |
|------|-------------|
| `dirty_tree_out_of_scope` | Unrelated untracked/modified/staged files found |
| `stage_file_missing` | Stage file does not exist on disk |
| `branch_not_clean` | Current branch has unrelated dirty state |
| `branch_ahead_or_behind` | Branch ahead of or behind upstream |
| `branch_mismatch` | Current branch != requested branch |

### C. Branch / Upstream Sync Check

**Implementation**: A helper function `_check_branch_sync(repo_root, expected_branch, status_provider)` that:

1. Gets current branch via `git branch --show-current` (or injected provider)
2. Gets branch status via `git status --porcelain=v1 --branch`
3. Parses ahead/behind from `## branch_name...upstream [ahead N] [behind M]`
4. Returns dict with `{branch_match: bool, ahead: int, behind: int, has_upstream: bool, block_reason: str or None}`

**Behavior table**:

| State | Action |
|-------|--------|
| Branch matches, clean, synced | Proceed |
| Branch matches, ahead > 0 | Block: `branch_ahead_or_behind` |
| Branch matches, behind > 0 | Block: `branch_ahead_or_behind` |
| Branch matches, no upstream | Block (requires push -u first) |
| Branch doesn't match | Block: `branch_mismatch` |

**No real git mutation in tests**: The status provider is injected.
Tests use a fake provider that returns controlled results.

### D. Dry-run / No-dry-run Behavior

- `--dry-run` (default): Dirty baseline check still runs, blocks if dirty.
  Side effects (git/gh) are skipped.  This is the safe mode.
- `--no-dry-run --execute --approve`: Full execution after baseline passes.
  If baseline fails, blocks before any side effect.
- `--no-dry-run` without `--execute`: Still safe — execution not attempted.

### E. Implementation Scope

**Allowed implementation files**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Add `_render_dogfood_proof_yaml()`, add always-run baseline check, add branch sync check |
| `services/runner/src/runner/git_boundary.py` | Add `REASON_BRANCH_MISMATCH`, `REASON_BRANCH_AHEAD_OR_BEHIND` constants (for plan, no structural change needed — reason codes are already extensible) |
| `services/runner/tests/test_ariadne_task_cli.py` | Tests for proof renderer, dirty baseline, branch sync |
| `services/runner/tests/test_git_boundary.py` | Tests for new reason codes if added to git_boundary |

**Only if necessary**:

| File | Changes |
|------|---------|
| `services/runner/src/runner/run_persistence.py` | Only if proof renderer needs to read persisted run hashes |
| `services/runner/tests/test_run_persistence.py` | Only if above |

**Prefer not modifying**:

- `prompt_composer.py`
- `verdict_parser.py`
- `docker_agent_adapter.py`
- `adapter_registry.py`
- `local_harness.py`
- `agent_runner_bridge.py`
- `pipeline_runner.py`

### F. Non-goals

- No new runtime modules
- No new architecture
- No retry/failure recovery loop (PR 0132)
- No model health live fallback (PR 0133)
- No run report (PR 0134)
- No parallel-safe queue (PR 0135)
- No dashboard or control plane
- No Decision Core / GRM / Context Warehouse / eval harness / frontend
- No ROADMAP/docs/agents/schemas/dependency modifications
- No Docker enabling
- No agent git/gh mutation rights
- No real PR 0131 dogfood artifacts created or modified
- No two-phase proof update after `gh pr create`

## Tests

### Dogfood Proof Completeness Tests

All in `test_ariadne_task_cli.py`:

1. `test_proof_renderer_creates_required_fields`:
   - Call `_render_dogfood_proof_yaml` with realistic runtime context
   - Verify all required fields present (schema_version, pr_id, run_id,
     branch, invocation_mode, pipeline_status, pipeline_final_action,
     pipeline_has_blockers, git_boundary_status, command_plan_summary,
     execution_attempted, pr_created, pr_url, run_record_path,
     run_json_hash, artifact_hashes, approval_summary, timestamp, note)

2. `test_proof_renderer_sanitizes_task_prompt`:
   - Render with task description containing secrets
   - Verify raw task description not in output
   - Verify approval_summary sanitized

3. `test_proof_renderer_no_raw_stdout_stderr`:
   - Verify raw stdout/stderr not in rendered proof
   - Only operation summaries and sanitized hashes

4. `test_proof_renderer_pr_url_pending_before_gh_pr_create`:
   - Verify `pr_url` is `"pending-before-gh-pr-create"`
   - Verify not empty, not a real URL

5. `test_proof_renderer_includes_command_plan_summary`:
   - Verify `command_plan_summary` contains operation names

6. `test_proof_renderer_includes_execution_attempted`:
   - Verify `execution_attempted` is `False` at render time

7. `test_proof_renderer_includes_run_record_path`:
   - Verify `run_record_path` is correctly formatted

8. `test_proof_renderer_run_json_hash_pending_if_not_persisted`:
   - Verify `run_json_hash` is `"pending"` if not yet persisted

9. `test_proof_renderer_incomplete_proof_blocks`:
   - Attempt to stage proof without required fields
   - Verify block via stage_file_missing or dirty_tree_out_of_scope

10. `test_proof_written_before_git_boundary_execution`:
    - Full CLI flow with fake executor
    - Verify proof file exists on disk before Git Boundary runs

### Dirty Baseline Tests

All in `test_ariadne_task_cli.py`:

1. `test_dirty_baseline_unrelated_untracked_file_blocks`:
   - Inject status provider with untracked file not in allowed_files
   - Verify `dirty_tree_out_of_scope` in reason codes
   - Verify `execution_attempted` is False

2. `test_dirty_baseline_unrelated_tracked_modification_blocks`:
   - Inject status provider with modified tracked file
   - Verify blocked

3. `test_dirty_baseline_staged_file_before_run_blocks`:
   - Inject status provider with staged file
   - Verify blocked

4. `test_dirty_baseline_precommit_review_yml_blocked_as_payload`:
   - Inject stage-file pointing to precommit-review.yml
   - Verify blocked (reviews/ is not commit payload)

5. `test_dirty_baseline_ariadne_path_blocked`:
   - Inject dirty file `.ariadne/runs/foo/run.json`
   - Verify blocked

6. `test_dirty_baseline_captures_path_blocked`:
   - Inject dirty file `captures/foo.json`
   - Verify blocked

7. `test_dirty_baseline_prevents_execution_attempted_true`:
   - Dirty tree → blocked
   - Verify `execution_attempted` stays False in result

8. `test_dirty_baseline_returns_dirty_tree_out_of_scope_code`:
   - Verify code `dirty_tree_out_of_scope` present

### Branch Baseline Tests

All in `test_ariadne_task_cli.py`:

1. `test_branch_mismatch_blocks`:
   - Inject `current_branch="wrong-branch"`, `expected_branch="right-branch"`
   - Verify `branch_mismatch` reason code
   - Verify blocked

2. `test_branch_ahead_of_upstream_blocks`:
   - Inject ahead=3, behind=0
   - Verify `branch_ahead_or_behind` reason code

3. `test_branch_behind_upstream_blocks`:
   - Inject ahead=0, behind=2
   - Verify `branch_ahead_or_behind`

4. `test_branch_no_upstream_blocks`:
   - Inject no upstream config
   - Verify blocked with clear message

5. `test_branch_clean_synced_proceeds`:
   - Inject ahead=0, behind=0, branch matches
   - Verify no branch-related reason codes

### Stage-file and Command Plan Tests

Already exist in `test_git_boundary.py` for `prepare_git_boundary_plan`.
Preserve existing tests:

- `test_stage_file_missing_blocks` — already present
- Proof payload is staged — already tested via `files_to_stage`
- Command plan only stages dogfood-proof.yml — already tested
- Precommit-review.yml not staged — already tested via `_is_forbidden_path`

### Dry-run / No-dry-run Tests

1. `test_dry_run_still_non_mutating_with_clean_baseline`:
   - --dry-run with clean status provider
   - Verify no execution side effects

2. `test_no_dry_run_dirty_baseline_blocks_before_execution`:
   - --no-dry-run with dirty baseline
   - Verify blocked, execution_attempted=False

3. `test_no_dry_run_clean_baseline_fake_git_gh_proceeds`:
   - --no-dry-run, clean baseline, fake git executor
   - Verify CLI status completed, execution_attempted=True

## Implementation Steps

1. Add `_render_dogfood_proof_yaml()` function to `ariadne_task_cli.py`
   - Takes `AriadneTaskCliResult` (or relevant fields), `GitBoundaryPlan`,
     and `AriadneTaskCliRequest`
   - Returns YAML string
   - Sanitizes all fields as specified

2. Add `_check_git_baseline()` function to `ariadne_task_cli.py`
   - Injected status provider (callable returning porcelain output)
   - Checks untracked files, tracked modifications, staged files,
     `.ariadne/` and `captures/` prefixes, branch match, ahead/behind
   - Returns `(ok, reason_codes, warnings)`

3. Integrate both into `run_ariadne_task()` flow:
   - After pipeline completion (step 3), before Git Boundary (step 5)
   - Call `_check_git_baseline()` — block if dirty
   - Call `_render_dogfood_proof_yaml()` — write proof files
   - Proceed to Git Boundary planning and execution

4. Add reason codes to `git_boundary.py` if needed:
   - `REASON_BRANCH_MISMATCH = "branch_mismatch"`
   - `REASON_BRANCH_AHEAD_OR_BEHIND = "branch_ahead_or_behind"`
   (Or define in `ariadne_task_cli.py` — whichever is cleaner)

5. Add tests to `test_ariadne_task_cli.py`

6. Validate with compile and pytest commands

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0131g-dogfood-proof-completeness-dirty-baseline`
- PLAN ignores real dogfood PR #150 evidence
- PLAN does not distinguish "loop executed" from "proof is complete"
- PLAN does not address incomplete committed dogfood-proof.yml
- PLAN does not address out-of-scope untracked residue
- PLAN does not address branch ahead/behind baseline
- PLAN pretends committed proof can include final PR URL before gh pr create without valid flow
- PLAN hardcodes PR 0131 in production code
- PLAN bypasses Git Boundary
- PLAN grants agents git/gh mutation rights
- PLAN requires Docker
- PLAN modifies ROADMAP/docs/agents/schemas/dependencies
- PLAN creates real PR 0131 artifacts during tests
- Tests require real git/gh/Docker/network/agents
- Validation is missing
- Dirty tree includes `.ariadne/**`, `captures/**`, or real PR 0131 artifacts as commit payload

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

# Grep safety — no forbidden patterns
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "dogfood_proof|proof_completeness|pr_url|pending-before-gh-pr-create|command_plan_summary|execution_attempted|run_record_path|run_json_hash|approval_summary|dirty_tree_out_of_scope|branch_not_clean|branch_ahead_or_behind|branch_mismatch|stage_file_missing|status --porcelain|porcelain=v1|upstream|ahead|behind|no-dry-run|payload" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131g-dogfood-proof-completeness-dirty-baseline

# Grep safety — no git mutation in test code
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|gh release|git checkout|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131g-dogfood-proof-completeness-dirty-baseline

# Verify no real PR 0131 artifacts created
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml

# .ariadne and captures residue
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi
if [ -d captures ]; then find captures -maxdepth 5 -type f | sort; else echo "captures absent"; fi

git status --short
git diff --name-only
```
