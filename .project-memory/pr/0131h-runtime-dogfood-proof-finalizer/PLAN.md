# PR 0131H — Runtime Dogfood Proof Finalizer Plan

## Summary

PR 0131G passed tests and added a complete dogfood proof renderer
(`_render_dogfood_proof_yaml`), dirty baseline enforcement
(`_check_git_baseline`), and branch sync enforcement
(`_check_branch_sync`).  The next real dogfood attempt still produced the
old weak bridge materializer proof:

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

Expected complete 0131G proof fields did not appear.  Additionally,
`.ariadne/runs/pr-0131-dogfood/run.json` and `manifest.json` were absent
after stopped/failed attempts.

**Root cause**: The 0131G `_render_dogfood_proof_yaml` is called with
`git_plan=None` hardcoded, so `command_plan_summary` renders as `[]`.
The proof renders 18 non-git fields correctly, but the bridge placeholder
is overwritten *too early* and no proof validation gate blocks the
incomplete content.  Additionally, when `--run-id` is provided without
`--runs-root`, `_persist_and_return` skips persistence entirely because
`request.runs_root` is `None`.

This PR fixes three gaps:
1. Proof finalization — render complete proof (with command_plan_summary
   from request params, not from nonexistent git_plan)
2. Proof validation gate — block if proof is incomplete
3. Run persistence guarantee — auto-default `runs_root` when `run_id`
   is explicitly provided

## Context

| Field | Value |
|-------|-------|
| PR 0131G renderer call | `_render_dogfood_proof_yaml(..., git_plan=None, ...)` at step 4c |
| Bridge placeholder fields | `pr_id: ""`, `proof_artifact_ref: ""`, `dogfood_type: "local-non-docker"`, no runtime context |
| CLI render overwrite | `open(full_path, "w")` — overwrites bridge placeholder, but `command_plan_summary` empty because `git_plan=None` |
| Missing validation gate | `REASON_DOGFOOD_PROOF_INCOMPLETE` defined at ariadne_task_cli.py L135 but never emitted |
| Missing persistence | `_persist_and_return` checks `if not request.runs_root or not persistence_fn: return result`. Dogfood CLI without `--runs-root` skips persistence entirely |
| Git plan ordering | Proof rendered before Git Boundary plan (step 4c before step 5-6), so git_plan is unavailable |

## Roadmap alignment

- **track**: Production Line — Stage 2 Closed Loop
- **expected PR slot**: PR 0131H (runtime correction after 0131G)
- **why this PR is next**: 0131G added the renderer but the real path
  still produces weak bridge proof.  Until 0131H, the dogfood path
  cannot produce a self-validating committed proof and cannot persist
  failed attempts.
- **batching policy check**: Single-purpose runtime correction;
  no feature expansion.
- **drift heuristic check**: Does not touch frozen streams; does not add
  new product modules; does not modify ROADMAP/docs/agents/schemas/deplock.

## Design

### 1. Runtime Proof Finalization

**Problem**: `_render_dogfood_proof_yaml` is called at step 4c with
`git_plan=None`.  The function computes `command_plan_summary` from
`git_plan.command_specs` — which is `None` — so the summary is `[]`.

**Fix**: Change the proof renderer call site to compute
`command_plan_summary` from request parameters, not from `git_plan`.
The operations are deterministic from the CLI arguments:

| Operation | Condition |
|-----------|-----------|
| `git_status` | Always |
| `git_add` | `files_to_stage` non-empty |
| `git_commit` | Always (needs commit_message) |
| `git_push` | Always |
| `gh_pr_create` | `pr_title` non-empty |

The helper `_compute_plan_summary(request)` returns `list[str]` and is
called before `prepare_git_boundary_plan`.

**Bridge placeholder overwrite**: Already works — `_render_dogfood_proof_yaml`
writes to `files_to_stage[0]` via `open(full_path, "w")` which overwrites
the bridge materialized placeholder.  No change needed to overwrite behavior.

**Proof field `proof_artifact_ref`**: Currently set from
`request.files_to_stage[0]` or `"pending-before-proof-hash"`.  This is
correct — `proof_artifact_ref` must be the path of the proof artifact
itself (self-referencing).  In the current code, `proof_artifact_ref`
is set correctly as the first stage-file path.  No change needed.

**Proof field `run_json_hash`**: Currently hardcoded as `"pending"`.
This is acceptable because at render time the proof has not yet been
persisted.  The run_json_hash will be computed and stored in
`manifest.json` after `_persist_and_return` runs.  No change needed.

**All 20 required fields** — current `_render_dogfood_proof_yaml` renders:

| Field | Current source | Status |
|-------|---------------|--------|
| `schema_version` | `"0.1"` constant | ✓ |
| `pr_id` | `request.pr_id` | ✓ |
| `run_id` | `run_id` param | ✓ |
| `branch` | `request.branch` | ✓ |
| `invocation_mode` | `"cli"` constant | ✓ |
| `pipeline_status` | `pipeline_status` param | ✓ |
| `pipeline_final_action` | `pipeline_final_action` param | ✓ |
| `pipeline_has_blockers` | `pipeline_has_blockers` param | ✓ |
| `git_boundary_status` | `"pending"` constant | ✓ |
| `command_plan_summary` | From `git_plan` (now `None`) | **FIX**: from request params |
| `execution_attempted` | `false` constant | ✓ |
| `pr_created` | `false` constant | ✓ |
| `pr_url` | `"pending-before-gh-pr-create"` constant | ✓ |
| `run_record_path` | Computed from runs_root + run_id | ✓ |
| `run_json_hash` | `"pending"` constant | ✓ (acceptable sentinel) |
| `artifact_hashes` | From `pipeline_artifact_hashes` | ✓ |
| `approval_summary` | Sanitized from approved_by + approval_reason | ✓ |
| `timestamp` | Clock provider | ✓ |
| `note` | Constant string | ✓ |
| `proof_artifact_ref` | First stage-file path | ✓ |

### 2. Proof Validation Gate

**Problem**: After rendering and writing the proof, there is no gate that
validates the written content before Git Boundary planning.  The
`REASON_DOGFOOD_PROOF_INCOMPLETE` constant is defined but never emitted.

**Fix**: Add `_validate_dogfood_proof_content(path)` function that:

1. Reads the written proof file from disk
2. Checks for all 20 required fields
3. Validates critical non-empty values:
   - `pr_id` must not be empty
   - `run_id` must not be empty
   - `branch` must not be empty
   - `proof_artifact_ref` must not be empty
   - `run_record_path` must not be empty
   - `command_plan_summary` must not be empty (at minimum `["git_status"]`)
4. Rejects weak bridge placeholder patterns:
   - `pr_id: ""` → block
   - `proof_artifact_ref: ""` → block
   - `dogfood_type: "local-non-docker"` without runtime fields → block
5. Returns `(ok, reason_codes, warnings)`

**Place in flow**: Called immediately after proof rendering (step 4c),
before Git Boundary planning (step 5).  If validation fails:
- `REASON_DOGFOOD_PROOF_INCOMPLETE` emitted
- CLI returns `status="blocked"`
- `execution_attempted` remains `False`
- Run record is persisted with the failure

**Allowed sentinel values**:
- `pr_url: "pending-before-gh-pr-create"` — valid before gh pr create
- `run_json_hash: "pending"` — valid before run persistence
- `proof_artifact_ref` pointing to the proof file itself — always valid

### 3. Run Persistence Guarantee

**Problem**: `_persist_and_return` checks `if not request.runs_root or
not persistence_fn: return result`.  The old-style dogfood command
(`--run-id pr-0131-dogfood` without `--runs-root`) skips persistence
even when `--run-id` is explicitly provided.

**Fix**: In `run_ariadne_task()`, after building the request, if
`request.run_id` is explicitly provided (non-empty, not auto-generated)
and `request.runs_root` is `None`, auto-default `runs_root` to
`.ariadne/runs`.

Detection of "explicitly provided": The auto-generated run_id in
`_build_cli_request` follows `f"run-{task_description_hash[:8]}"`
pattern.  If the user passed `--run-id`, the value is whatever they
provided (e.g. `"pr-0131-dogfood"`).  The simplest check is
`request.run_id is not None and request.run_id != ""` — if the user
explicitly passed `--run-id`, it will be non-empty at this point.

Alternatively, modify `_build_cli_request` to set a flag when
`--run-id` was explicitly passed.  But the simplest approach:
**if `request.run_id` is non-empty and `request.runs_root` is `None`,
default `runs_root` to `.ariadne/runs`**.

This ensures:
- Missing task description with explicit `--run-id` persists `run.json`
- `dogfood_proof_incomplete` block persists `run.json`
- `dirty_tree_out_of_scope` block persists `run.json`
- `stage_file_missing` block persists `run.json`
- Successful execution persists `run.json` and `manifest.json`

### 4. Finalization Order (Corrected)

Current order in `run_ariadne_task()`:
1. Validate task description
2. Build pipeline request
3. Run pipeline (bridge may materialize weak placeholder)
4. Check pipeline result (early return on failure — persisted)
4b. Baseline check (block on dirty — persisted)
4c. **Render and write complete proof** (fix: compute plan_summary from
    request, not git_plan; add validation gate after write)
5. Build GitBoundaryRequest
6. Plan git boundary (stage-file existence check will see proof on disk)
7. Check git boundary plan
8. Check execution/approval requirements
9. Execute git boundary
10. Determine final status

**Corrected flow for step 4c**:
```
4c. Render complete proof with command_plan_summary from request params
    4c.1 Build plan_summary from request parameters
    4c.2 Render proof YAML with all 20 fields
    4c.3 Write to each files_to_stage path (overwrites bridge placeholder)
    4c.4 Validate written proof content
    4c.5 If validation fails → REASON_DOGFOOD_PROOF_INCOMPLETE → block,
          persist run record, return
```

Proof finalization happens **before** Git Boundary planning.  Git Boundary
stage-file existence check observes complete proof on disk.  Git Boundary
executor never sees weak placeholder.

### 5. Implementation Scope

| File | Changes |
|------|---------|
| `services/runner/src/runner/ariadne_task_cli.py` | Fix `_render_dogfood_proof_yaml` call (compute plan_summary from request); add `_validate_dogfood_proof_content`; add proof validation gate; add auto-default `runs_root` |
| `services/runner/tests/test_ariadne_task_cli.py` | Tests for runtime finalization, incomplete proof gate, run persistence |

**Optional only if unavoidable**:
- `services/runner/src/runner/run_persistence.py` — only if the
  `_persist_and_return` flow needs changes beyond `runs_root` defaulting
- `services/runner/tests/test_run_persistence.py` — only if above

**Not modified**:
- `agent_runner_bridge.py` — no change needed (bridge placeholder is
  overwritten by CLI)
- `pipeline_runner.py`
- `git_boundary.py`
- `prompt_composer.py`
- `verdict_parser.py`

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
- No Git Boundary modifications
- No Docker enabling
- No agent git/gh mutation rights
- No real PR 0131 dogfood artifacts created or modified in tests

## Tests

### Runtime Finalization Tests

All in `test_ariadne_task_cli.py`:

1. `test_bridge_placeholder_overwritten_by_cli_proof_before_git_plan`:
   - Write bridge placeholder to stage-file path
   - Call `run_ariadne_task` with fake pipeline and fake planner
   - Read back the stage-file after step 4c
   - Verify `pr_id` is non-empty (not `""`), `proof_artifact_ref` non-empty,
     `command_plan_summary` non-empty
   - Verify weak bridge fields (`dogfood_type`, `bridge_task_prompt_hash`)
     are absent

2. `test_root_weak_proof_content_with_empty_pr_id_blocked`:
   - Inject a fake rendered proof that contains `pr_id: ""`
   - Call `_validate_dogfood_proof_content` on it
   - Verify returns `ok=False` with `dogfood_proof_incomplete`

3. `test_root_weak_proof_content_with_empty_proof_artifact_ref_blocked`:
   - Inject proof with `proof_artifact_ref: ""`
   - Verify `ok=False` with `dogfood_proof_incomplete`

4. `test_complete_proof_contains_all_20_required_fields`:
   - Call `_render_dogfood_proof_yaml` with realistic params
   - Parse YAML, verify all 20 fields present
   - Verify `command_plan_summary` non-empty (at minimum `["git_status"]`)

5. `test_proof_artifact_ref_non_empty`:
   - Verify `proof_artifact_ref` equals first stage-file path

6. `test_pr_id_equals_requested_pr_id`:
   - Verify `pr_id` matches `request.pr_id`

7. `test_run_id_equals_requested_run_id`:
   - Verify `run_id` matches requested `run_id` parameter

8. `test_stage_file_path_remains_dogfood_proof_yml`:
   - Verify proof written to `.project-memory/pr/<pr_id>/dogfood-proof.yml`

9. `test_git_boundary_planner_observes_complete_proof_on_disk`:
   - After step 4c, verify `os.path.exists(stage_file)` is `True`
   - Call `prepare_git_boundary_plan` with `files_to_stage` pointing to
     the proof
   - Verify `dirty_tree_valid` is `True` and no `REASON_STAGE_FILE_MISSING`

10. `test_git_boundary_executor_never_sees_weak_placeholder`:
    - Run full flow with fake executor
    - Verify executor receives command spec with proof path that contains
      complete fields (not bridge placeholder)

### Incomplete Proof Gate Tests

All in `test_ariadne_task_cli.py`:

1. `test_missing_proof_artifact_ref_blocks`:
   - Inject proof with `proof_artifact_ref` removed
   - Call `_validate_dogfood_proof_content`
   - Verify `dogfood_proof_incomplete` reason code

2. `test_empty_pr_id_blocks`:
   - Inject proof with `pr_id: ""`
   - Verify blocked

3. `test_missing_run_id_blocks`:
   - Inject proof without `run_id`
   - Verify blocked

4. `test_missing_proof_field_blocks`:
   - Inject proof missing `schema_version`
   - Verify blocked

5. `test_dogfood_proof_incomplete_reason_code_emitted`:
   - Run full flow with incomplete proof
   - Verify `dogfood_proof_incomplete` in `result.reason_codes`

### Run Persistence Tests

All in `test_ariadne_task_cli.py`:

1. `test_missing_task_description_with_explicit_run_id_persists`:
   - Call `run_ariadne_task` with empty task description, `--run-id foo`,
     and fake persistence_fn
   - Verify `persistence_fn` was called (run.json would be written)

2. `test_dogfood_proof_incomplete_persists_run_record`:
   - Inject incomplete proof, run flow
   - Verify `run_record_path` is present in result

3. `test_dirty_tree_out_of_scope_persists_run_record`:
   - Inject dirty tree, run flow
   - Verify `run_record_path` is present

4. `test_stage_file_missing_persists_run_record`:
   - Point stage-file to nonexistent path
   - Verify `run_record_path` is present

5. `test_successful_fake_execution_persists_run_json_and_manifest`:
   - Run full flow with fake executor
   - Verify `run_record_path` non-empty

6. `test_persisted_run_path_uses_explicit_run_id`:
   - Run with `--run-id my-custom-id`
   - Verify `run_record_path` contains `"my-custom-id"`

### Regression Tests

All in `test_ariadne_task_cli.py`:

1. `test_dirty_baseline_still_blocks_unrelated_untracked_files`:
   - Existing test — verify it still passes

2. `test_branch_mismatch_still_blocks`:
   - Existing test — verify it still passes

3. `test_stage_file_preflight_still_blocks_missing_file`:
   - Existing test — verify it still passes

4. `test_dry_run_remains_non_mutating`:
   - `--dry-run` with clean baseline → no execution side effects

5. `test_execute_no_dry_run_remains_required_for_side_effects`:
   - Without `--execute --no-dry-run`, no side effects

6. `test_no_real_git_gh_docker_network_agents_in_tests`:
   - grep for forbidden patterns returns 0

## Implementation Steps

1. Add `_compute_plan_summary(request)` to `ariadne_task_cli.py`:
   - Returns `list[str]` of operation names deterministically from
     `request.files_to_stage`, `request.commit_message`,
     `request.pr_title`
   - Always includes `"git_status"`
   - Includes `"git_add"` if `files_to_stage` non-empty
   - Includes `"git_commit"`, `"git_push"` unconditionally
   - Includes `"gh_pr_create"` if `pr_title` non-empty

2. Fix `_render_dogfood_proof_yaml` call site (step 4c):
   - Replace `git_plan=None` with computed `command_plan_summary`
   - Remove `git_plan` parameter if no longer needed

3. Add `_validate_dogfood_proof_content(path)` to `ariadne_task_cli.py`:
   - Reads file, parses as YAML (or line-oriented)
   - Checks all 20 fields present
   - Validates critical non-empty values
   - Returns `(ok, reason_codes, warnings)`

4. Add proof validation gate after proof rendering (step 4c.4):
   - Call `_validate_dogfood_proof_content` for each stage-file
   - If validation fails, emit `REASON_DOGFOOD_PROOF_INCOMPLETE`, return
     blocked result with persisted run record

5. Fix run persistence auto-default:
   - After request construction, if `request.run_id` is provided and
     `request.runs_root` is `None`, set `runs_root = ".ariadne/runs"`
   - This ensures all early-return paths in `run_ariadne_task` will
     persist through `_persist_and_return`

6. Add tests to `test_ariadne_task_cli.py`

7. Validate with compile and pytest commands

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0131h-runtime-dogfood-proof-finalizer`
- PLAN treats weak bridge proof as acceptable (placeholder with empty
  `pr_id` and empty `proof_artifact_ref`)
- PLAN does not require CLI to overwrite/finalize bridge placeholder
  proof before Git Boundary
- PLAN does not validate all 20 proof fields
- PLAN does not block empty `pr_id` or empty `proof_artifact_ref`
- PLAN does not address absent `run.json`/`manifest.json` for
  failed/stopped attempts
- PLAN allows persistence gaps for explicit `--run-id`
- PLAN requires real dogfood in tests
- PLAN requires real git/gh/Docker/network/agents in tests
- PLAN modifies ROADMAP/docs/agents/schemas/dependencies
- PLAN starts frozen streams
- PLAN bypasses Git Boundary
- PLAN grants agents git/gh mutation authority

## Validation Commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
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
  "proof_artifact_ref|dogfood_proof_incomplete|pending-before-gh-pr-create|pending-before-run-persist|run_record_path|run_json_hash|bridge_task_prompt_hash|bridge_agent_config_hash|materialized_at|pr_id: \"\"|proof_artifact_ref: \"\"|dirty_tree_out_of_scope|branch_ahead_or_behind|stage_file_missing|persist|run_id" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131h-runtime-dogfood-proof-finalizer

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git init|git checkout|git add|git commit|git push|gh pr create|gh release|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" \
  services/runner/src/runner services/runner/tests .project-memory/pr/0131h-runtime-dogfood-proof-finalizer

test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi
if [ -d captures ]; then find captures -maxdepth 5 -type f | sort; else echo "captures absent"; fi

git status --short
git diff --name-only
```
