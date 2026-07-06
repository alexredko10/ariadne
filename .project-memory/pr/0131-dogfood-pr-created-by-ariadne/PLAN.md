# PR 0131 — DOGFOOD PR Created by Ariadne Plan

## Summary

Plan PR 0131 as the first real dogfood PR created through the Ariadne production line. No new product modules, no architecture expansion. Proves that the existing substrate (Pipeline Runner → Git Boundary → Run Persistence → human-approved git/gh) can execute `ariadne task`, produce a tiny project-memory proof artifact, commit/push/PR through the Ariadne Git Boundary path, and leave a persisted local run record as proof.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | ecac1bda691b66b3876569a817ed5731a573ab52 |
| current_branch | 0131-dogfood-pr-created-by-ariadne |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line ACTIVE; L326 "0131 — DOGFOOD MILESTONE: PR 0131 is created by Ariadne itself via ariadne task" |
| pr_0127_pipeline_runner_evidence | `pipeline_runner.py` + tests present |
| pr_0128_git_boundary_evidence | `git_boundary.py` + tests present |
| pr_0129_ariadne_task_cli_evidence | `ariadne_task_cli.py` + tests present; CLI has `--execute`, `--approve`, `--approved-by`, `--approval-reason`, `--runs-root`, `--run-id` |
| pr_0130_run_persistence_evidence | `run_persistence.py` + tests present; `persist_run_record()` + `load_run_record()` available |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 2 Closed Loop
* expected PR slot: 0131 — DOGFOOD PR created by Ariadne
* why this PR is next: PR 0127 added Pipeline Runner, PR 0128 added Git Boundary, PR 0129 added ariadne task CLI, and PR 0130 added Run Persistence; the next required capability is to prove the closed loop by creating one real PR through Ariadne
* batching policy check: operational dogfood proof PR; not a feature expansion; not docs drift
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; persisted run records and created PR evidence are runtime/file-captured proof

## PR 0127 Pipeline Runner verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/pipeline_runner.py` exists | PRESENT ✓ |
| `run_pr_pipeline()` → `PipelineRunnerResult` with `status`, `final_action`, `has_blockers`, `artifact_hashes` | CONFIRMED ✓ |

## PR 0128 Git Boundary verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/git_boundary.py` exists | PRESENT ✓ |
| `prepare_git_boundary_plan()` → plan with git add/commit/push/gh_pr_create | CONFIRMED ✓ |
| `execute_git_boundary_plan()` → execution through injected executor | CONFIRMED ✓ |
| GitCommandSpec uses argv, not shell strings | CONFIRMED ✓ |

## PR 0129 ariadne task CLI verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/ariadne_task_cli.py` exists | PRESENT ✓ |
| `--execute`, `--approve`, `--approved-by`, `--approval-reason` flags present | CONFIRMED ✓ |
| `--runs-root`, `--run-id` flags present | CONFIRMED ✓ |
| `persistence_fn` injectable parameter in `run_ariadne_task()` | CONFIRMED ✓ |
| `AriadneTaskCliResult` includes `run_record_path` field | CONFIRMED ✓ |

## PR 0130 Run Persistence verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/run_persistence.py` exists | PRESENT ✓ |
| `persist_run_record(RunPersistenceRequest)` → `RunPersistenceResult` | CONFIRMED ✓ |
| `load_run_record(runs_root, run_id)` → `RunPersistenceReadResult` | CONFIRMED ✓ |
| `run.json` + `manifest.json` written under `runs_root/<run_id>/` | CONFIRMED ✓ |
| Filesystem-safe run_id validation (`^[a-zA-Z0-9_\-]{1,64}$`) | CONFIRMED ✓ |
| Deterministic JSON with `sort_keys=True` | CONFIRMED ✓ |

## Dogfood goal

Prove that the Ariadne production line can create one real PR through the full path:
1. `ariadne task` CLI with a dogfood task description
2. Prompt Composer → Agent Runner Bridge → Pipeline Runner
3. Git Boundary plan + execution with human approval
4. Run Persistence for local run record
5. Real PR on GitHub with a small dogfood proof artifact

## Dogfood target artifact

`.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`

Content:
```yaml
# DOGFOOD PROOF — PR 0131 created by Ariadne itself
pr_id: "0131"
run_id: "pr-0131-dogfood"
branch: "0131-dogfood-pr-created-by-ariadne"
task_description_hash: "<SHA256[:16]>"
pipeline_status: "completed"
pipeline_final_action: "continue"
pipeline_has_blockers: false
git_boundary_status: "approved"
command_plan_summary:
  - operation: "git_status"
  - operation: "git_add"
  - operation: "git_commit"
  - operation: "git_push"
  - operation: "gh_pr_create"
execution_attempted: true
pr_created: true
pr_url: "https://github.com/<owner>/<repo>/pull/<number>"
run_record_path: ".ariadne/runs/pr-0131-dogfood/run.json"
run_json_hash: "<SHA256[:16]>"
artifact_hashes:
  ".project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml": "<SHA256[:16]>"
approval_summary: "Approved by operator for PR 0131 dogfood"
note: "This artifact is dogfood proof, not a new product feature. No source code was modified."
```

## Ariadne command contract

The human operator executes:

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m runner.ariadne_task_cli task \
  "Create dogfood proof artifact for PR 0131: create file .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml with a summary of the Ariadne dogfood run, commit it, push it, and create a PR on GitHub." \
  --branch "0131-dogfood-pr-created-by-ariadne" \
  --base-branch main \
  --repo-root . \
  --runs-root .ariadne/runs \
  --run-id pr-0131-dogfood \
  --allowed-file .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml \
  --stage-file .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml \
  --commit-message "chore(project-memory): dogfood ariadne task proof" \
  --pr-title "chore(project-memory): dogfood ariadne task" \
  --pr-body "This PR was created by Ariadne through the Production Line closed loop:\n\n1. ariadne task CLI with task description\n2. Pipeline Runner (prompt composer → bridge → planner → review → coder → precommit)\n3. Verdict Parser gates\n4. Git Boundary with human approval\n5. Run Persistence for local proof\n\nSee .ariadne/runs/pr-0131-dogfood/ for the full run record." \
  --execute --approve --approved-by "<human operator name>" --approval-reason "PR 0131 roadmap dogfood: create one proof PR through Ariadne" \
  --json
```

The `gh pr create` must be invoked only by the Git Boundary through the Ariadne CLI path, not manually.

## Human approval contract

- `--execute` required
- `--approve` required
- `--approved-by` required (human operator name)
- `--approval-reason` required
- Approval does not override failed pipeline
- Approval does not override Git Boundary block
- Approval does not override dirty-tree allowlist failure
- Approval does not override forbidden file changes

## Git Boundary execution contract

The Git Boundary executes these operations in deterministic order:
1. `git status`
2. `git add -- .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`
3. `git commit -m "chore(project-memory): dogfood ariadne task proof"`
4. `git push origin 0131-dogfood-pr-created-by-ariadne`
5. `gh pr create --title "chore(project-memory): dogfood ariadne task" --body "..."`

All operations use argv command specs with `shell=False`. No shell strings.

## Run Persistence proof contract

After execution:
- `.ariadne/runs/pr-0131-dogfood/run.json` exists locally
- `.ariadne/runs/pr-0131-dogfood/manifest.json` exists locally
- `load_run_record(".ariadne/runs", "pr-0131-dogfood")` returns `RunPersistenceReadResult` with `status="read_ok"`
- `run_json_hash` is present in manifest
- Pipeline status/final_action/blockers recorded
- Git Boundary status recorded
- Command plan summary includes all 5 operations
- `execution_attempted=true`
- PR URL is recorded if returned by execution
- The run record proves Git Boundary performed PR creation, not manual `gh pr create`

## Expected local proof files

Local (may be untracked, under `.ariadne/runs/`):
- `.ariadne/runs/pr-0131-dogfood/run.json`
- `.ariadne/runs/pr-0131-dogfood/manifest.json`

## Expected staged PR payload

Committed in the PR:
- `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`

Review artifact (written after pipeline):
- `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml`

Planning artifacts (already present):
- `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/PLAN.md` (this file)
- `.project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/plan-review.yml`

Blocked:
- No source-code changes staged
- No ROADMAP/docs/agents/schemas/services changes staged
- No runtime module modifications

## Precommit evidence requirements

The precommit review must verify:
- `test -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`
- `test -f .ariadne/runs/pr-0131-dogfood/run.json`
- `test -f .ariadne/runs/pr-0131-dogfood/manifest.json`
- `load_run_record()` readback succeeds with `status="read_ok"`
- `run_json_hash` is present
- `pipeline_status` is `"completed"` or `"completed_with_warning"`
- `git_boundary_status` is `"approved"`
- `execution_attempted` is `true`
- `pr_created` is `true` or `pr_url` is present
- Dogfood proof artifact contains expected fields
- No source code changes present (`git diff --name-only` shows only the proof artifact and review artifacts)
- No `.ariadne/` residue outside expected `runs/` directory

## Safety and mutation boundaries

PR 0131 must not:
- Implement new runtime modules
- Modify existing runtime modules
- Modify tests
- Modify ROADMAP
- Modify docs
- Modify agents
- Modify schemas
- Grant unattended git mutation rights
- Manually create PR outside Ariadne path
- Run manual `gh pr create`
- Bypass Pipeline Runner
- Bypass Git Boundary
- Bypass Run Persistence
- Add retry/model health/dashboard/control plane/run report
- Start frozen streams

## Non-goals

PR 0131 does not implement:
- New runtime modules
- New architecture
- Retry/failure recovery loop (PR 0132)
- Model health live fallback (PR 0133)
- Run report (PR 0134)
- Parallel-safe queue (PR 0135)
- Dashboard or control plane
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Dogfood execution steps for the human operator

1. Verify branch is `0131-dogfood-pr-created-by-ariadne`
2. Verify all four predecessor PRs (0127–0130) are in place
3. Create the dogfood proof artifact file first (empty or template)
4. Run `ariadne task` CLI command with `--execute --approve --approved-by`
5. Verify CLI exit code is 0
6. Verify `load_run_record()` readback succeeds
7. Verify PR was created on GitHub
8. Update `dogfood-proof.yml` with actual PR URL
9. Run precommit validation commands
10. Submit precommit review

## Validation commands

```bash
git rev-parse --verify HEAD
git branch --show-current
git status --short
git diff --name-only

test -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml && echo "DOGFOOD_ARTIFACT_PRESENT" || echo "DOGFOOD_ARTIFACT_MISSING"
test -f .ariadne/runs/pr-0131-dogfood/run.json && echo "RUN_JSON_PRESENT" || echo "RUN_JSON_MISSING"
test -f .ariadne/runs/pr-0131-dogfood/manifest.json && echo "MANIFEST_JSON_PRESENT" || echo "MANIFEST_JSON_MISSING"

PYTHONPATH=services/runner/src:services/task_intake/src python - <<'PY'
from pathlib import Path
from runner.run_persistence import load_run_record
result = load_run_record(Path(".ariadne/runs"), "pr-0131-dogfood")
print("load_run_record status:", result.status)
print("run_id:", result.run_id)
print("run_json_hash:", result.run_json_hash)
print("stored_hash:", result.stored_hash)
print("recomputed_hash:", result.recomputed_hash)
print("hash_match:", result.hash_match)
print("pipeline_status:", result.record.pipeline_status if result.record else None)
print("git_boundary_status:", result.record.git_boundary_status if result.record else None)
print("execution_attempted:", result.record.execution_attempted if result.record else None)
PY

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "pr-0131-dogfood|run_json_hash|git_boundary_status|pipeline_status|execution_attempted|pr_created|run_record_path" .project-memory/pr/0131-dogfood-pr-created-by-ariadne .ariadne/runs/pr-0131-dogfood 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "dashboard|control plane|retry|model health|parallel queue|Decision Core|Context Warehouse|eval harness|faithfulness|frontend" .project-memory/pr/0131-dogfood-pr-created-by-ariadne 2>/dev/null || true

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only dogfood proof artifact + review artifact; no source code changes
- **behavior drift**: no new runtime modules; no existing module modifications
- **dogfood scope drift**: single small proof artifact; no architecture expansion
- **dogfood path drift**: PR created through Ariadne CLI → Pipeline Runner → Git Boundary → Run Persistence, not manually
- **git mutation drift**: git/gh performed by Git Boundary with human approval, not manually
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no retry/model health/dashboard/control plane/frozen streams

## NO-DRIFT CHECK

The implementation precommit-review must confirm:
- dogfood proof PR, not feature expansion ✓
- no new runtime modules ✓
- no existing module modifications ✓
- Ariadne CLI path used for PR creation ✓
- Git Boundary performs git/gh with human approval ✓
- Run Persistence proves the path ✓
- reads back run record with integrity check ✓
- no source code changes staged ✓
- no manual `gh pr create` ✓
- no dashboard/retry/model health/control plane ✓

## Dirty-Tree Expectations

After execution:
- `.ariadne/runs/pr-0131-dogfood/run.json` exists locally (may be untracked)
- `.ariadne/runs/pr-0131-dogfood/manifest.json` exists locally (may be untracked)
- No other `.ariadne/` residue

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Verify `load_run_record()` readback succeeds
3. Read back the artifact after writing
4. Verify the artifact is listed by `find` and `test -f` exits 0
5. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0131-dogfood-pr-created-by-ariadne`
- Block if PR 0127 Pipeline Runner is missing — PASS: present
- Block if PR 0128 Git Boundary is missing — PASS: present
- Block if PR 0129 ariadne task CLI is missing — PASS: present
- Block if PR 0130 Run Persistence is missing — PASS: present
- Block if ROADMAP evidence for PR 0131 DOGFOOD is missing — PASS: L326 confirmed
- Block if plan adds new runtime modules — PASS: not planned
- Block if plan modifies existing runtime modules — PASS: not planned
- Block if plan modifies ROADMAP/docs/agents/schemas — PASS: not planned
- Block if plan uses manual `gh pr create` instead of Ariadne Git Boundary path — PASS: Ariadne path only
- Block if plan uses manual git mutation instead of Ariadne Git Boundary path — PASS: Ariadne path only
- Block if dogfood lacks explicit human approval — PASS: --approve required
- Block if dogfood lacks local persisted run record — PASS: Run Persistence planned
- Block if dogfood lacks readback validation — PASS: load_run_record() verified
- Block if dogfood PR payload includes source-code changes — PASS: only proof artifact
- Block if plan expands into dashboard/control plane/retry/model health/run report/parallel queue/frozen streams — PASS: none
- Block if artifact write/readback expectations are missing — PASS: included
