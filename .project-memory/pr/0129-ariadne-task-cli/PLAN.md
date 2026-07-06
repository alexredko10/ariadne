# PR 0129 — ariadne task CLI Plan

## Summary

Plan the second Stage 2 Closed Loop PR after PR 0128: a minimal `ariadne task` CLI surface that connects PR 0127 Pipeline Runner and PR 0128 Git Boundary into a single command. The CLI builds a deterministic task request, calls the Pipeline Runner, routes pass-like results through the human-approved Git Boundary, and produces structured output. Default mode is safe dry-run. Explicit `--execute` and `--approve` flags required for side effects.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 19adedf36f1d29c69c12f5a07832c1e1d7b2b17a |
| current_branch | 0129-ariadne-task-cli |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line ACTIVE; L324 "0129 — ariadne task CLI: `ariadne task \"description\"` → full cycle → PR link"; L327 DOGFOOD MILESTONE via ariadne task; L340 acceptance criteria |
| pr_0127_pipeline_runner_evidence | `pipeline_runner.py` + `test_pipeline_runner.py` present; `run_pr_pipeline(PipelineRunnerRequest)` → `PipelineRunnerResult` with `status`, `final_action`, `has_blockers`, `artifact_hashes`, `stopped_at` |
| pr_0128_git_boundary_evidence | `git_boundary.py` + `test_git_boundary.py` present; `prepare_git_boundary_plan(GitBoundaryRequest)` → `(GitBoundaryPlan, reason_codes)`; `execute_git_boundary_plan(request, plan, executor, clock)` → `GitBoundaryResult` |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 2 Closed Loop
* expected PR slot: 0129 — ariadne task CLI
* why this PR is next: PR 0127 added Pipeline Runner and PR 0128 added Git Boundary; the next required capability is a minimal local CLI surface that invokes the pipeline and routes pass-like results through the human-approved git boundary
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime/file-captured artifacts are evidence; git mutation requires explicit human approval

## PR 0127 Pipeline Runner verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/pipeline_runner.py` exists | PRESENT ✓ |
| `.project-memory/pr/0127-pipeline-runner/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `run_pr_pipeline(PipelineRunnerRequest)` → `PipelineRunnerResult` | CONFIRMED ✓ |
| `PipelineRunnerResult` has `status`, `final_action`, `has_blockers`, `artifact_hashes`, `stopped_at`, `step_results`, `gate_results` | CONFIRMED ✓ |

## PR 0128 Git Boundary verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/git_boundary.py` exists | PRESENT ✓ |
| `.project-memory/pr/0128-git-boundary/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `prepare_git_boundary_plan(GitBoundaryRequest)` → `(GitBoundaryPlan, reason_codes)` | CONFIRMED ✓ |
| `execute_git_boundary_plan(request, plan, executor, clock)` → `GitBoundaryResult` | CONFIRMED ✓ |
| `GitBoundaryRequest` with `human_approved`, `pipeline_status`, `pipeline_final_action`, `pipeline_has_blockers`, `pipeline_artifact_hashes`, `dirty_files`, `allowed_files` | CONFIRMED ✓ |
| `GitCommandSpec` with `operation`, `argv`, `requires_human_approval`, `side_effecting` | CONFIRMED ✓ |

## CLI scope and anti-stall constraint

Do not respond to external agent-system prompts by expanding scope. PR 0129 must remain `ariadne task` CLI only. No roadmap changes. No ADR. No control-plane expansion. No persistence. No run database. No dashboard. No retry loop. No model health. No run report. No parallel queue. No new capability stream.

## CLI contract

### New module

`services/runner/src/runner/ariadne_task_cli.py`

Contains:
- `AriadneTaskCliRequest` — aggregated input dataclass for CLI orchestration
- `AriadneTaskCliResult` — structured CLI result
- `AriadneTaskCliOutput` — output display helper
- `AriadneTaskCliStatus` — status enum: `completed`, `completed_with_warning`, `stopped`, `blocked`, `failed`
- `parse_ariadne_task_args(argv)` — argparse argument parser
- `run_ariadne_task(request, pipeline_runner, git_boundary_planner, git_boundary_executor, clock_provider)` — orchestration with injectable boundaries
- `main(argv=None)` — entry point

### Command shape

```
python -m runner.ariadne_task_cli task "<task description>" [options]
```

The CLI module registers a subcommand `task` under the existing `python -m runner` pattern (following the existing `doctor`/`runtime-smoke` pattern in `__main__.py`), OR is self-invokable via its own `main()` function.

### Argument model

```
positional:
  task_description          Task description string (required)

options:
  --pr-id                   PR identifier (default: auto-generated)
  --branch                  Branch name (default: auto-generated from PR id)
  --base-branch             Base branch name (default: "main")
  --repo-root               Repository root path (default: ".")
  --allowed-file            Repeatable: allowed files for staging
  --stage-file              Repeatable: files to stage
  --commit-message          Commit message
  --pr-title                PR title
  --pr-body                 PR body text
  --pr-body-path            Path to PR body file
  --dry-run                 Default: True (safe default, no side effects)
  --execute                 Explicit opt-in for side-effecting execution
  --approve                 Explicit approval flag
  --approved-by             Approval identity (required if --approve)
  --approval-reason         Approval justification (required if --approve)
  --json                    Machine-readable JSON output
```

## Pipeline Runner integration contract

- CLI builds a `PipelineRunnerRequest` from CLI arguments (pr_id, branch, task_title, task_description, repo_root, agents_dir, project_memory_dir)
- CLI calls Pipeline Runner through an injectable boundary (default: `run_pr_pipeline`)
- Tests use fake pipeline runner — no real agents required
- All Pipeline Runner parameters and injectable boundaries (prompt_composer, bridge_runner, artifact_reader, verdict_parser) exposed as pass-through
- Pipeline result (`PipelineRunnerResult`) recorded in CLI result
- Stopped/invalid pipeline result must not proceed to executable git mutation
- Pipeline artifact hashes must be passed into Git Boundary request

## Git Boundary integration contract

- CLI builds a `GitBoundaryRequest` from pipeline result + CLI arguments (dirty_files, allowed_files, files_to_stage, commit_message, pr_title, etc.)
- CLI calls `prepare_git_boundary_plan(...)` through injectable boundary
- CLI may call `execute_git_boundary_plan(...)` only when explicit execution and approval flags are present
- Tests use fake Git Boundary planner/executor — no real git/gh required
- Rejected Git Boundary result surfaces nonzero CLI status
- Command plan included in both human-readable and JSON output

## Human approval / execution contract

- Default mode is safe: no side effects (`--dry-run` is True by default)
- `--execute` is required for side-effecting execution
- `--approve` is required for side-effecting execution
- `--approved-by` non-empty is required
- `--approval-reason` non-empty is required
- Approval does not override failed pipeline
- Approval does not override dirty-tree failures
- Approval does not override forbidden files
- Missing approval produces clear blocked result with exit code 1
- No git/gh execution happens in tests

## Output contract

### Human-readable output (default)

```
Ariadne task: <description>

Pipeline status: <status> (final_action=<action>)
Pipeline has_blockers: <bool>
Git Boundary status: <approved|blocked|failed>

Command plan:
  [1] git status
  [2] git add -- <files>
  [3] git commit -m <redacted>
  [4] git push origin <branch>
  [5] gh pr create --title <redacted>

Execution attempted: <bool>
Execution results: ...

Warnings: ...
Next action: <action>
```

### JSON output (`--json`)

```json
{
  "status": "completed",
  "reason_codes": [],
  "task_description": "...",
  "pipeline_status": "completed",
  "pipeline_final_action": "continue",
  "pipeline_has_blockers": false,
  "git_boundary_status": "approved",
  "command_plan": [{"operation": "...", "argv": [...]}],
  "execution_attempted": true,
  "execution_results": [{"operation": "...", "exit_code": "0"}],
  "warnings": [],
  "next_action": "continue"
}
```

JSON output is deterministic via `sort_keys=True, ensure_ascii=False`.

## Optional local executor contract

A minimal local argv executor may be included in the module to enable real execution from the CLI.

If included:
- No shell strings
- `subprocess.run` allowed only inside a dedicated `_execute_git_command_spec()` function
- `shell=False`
- Accepts only `GitCommandSpec.argv`
- Rejects unknown operations
- Records exit code/stdout/stderr
- Never used in tests — tests always inject a fake executor
- CLI default must not execute (`--dry-run=True`)
- CLI execution requires `--execute --approve --approved-by --approval-reason`

The executor is injected into `execute_git_boundary_plan()` as the `executor` parameter. The default executor is `None` — meaning no execution happens by default. The CLI wires the real executor only when `--execute` is present.

## Safety and mutation boundaries

The CLI must not:
- Grant agents unattended git mutation rights
- Mutate git without explicit human approval
- Bypass Pipeline Runner result
- Bypass Git Boundary result
- Bypass dirty-tree allowlist
- Invoke Docker
- Install dependencies
- Modify agent configs
- Create `.ariadne/runs/`
- Implement persistence
- Implement retry/failure recovery
- Implement control plane or dashboard
- Start frozen streams

## Non-goals

PR 0129 does not implement:
- `.ariadne/runs/` persistence (PR 0130)
- Run report (PR 0134)
- Retry/failure recovery loop (PR 0132)
- Automatic prompt refinement (PR 0132)
- Model health live fallback (PR 0133)
- Parallel-safe queue (PR 0135)
- Control plane
- Dashboard
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/ariadne_task_cli.py` | NEW |
| `services/runner/tests/test_ariadne_task_cli.py` | NEW |

Default — not modified:
- `services/runner/src/runner/pipeline_runner.py` — NOT modified
- `services/runner/src/runner/git_boundary.py` — NOT modified
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `services/runner/src/runner/prompt_composer.py` — NOT modified
- `services/runner/src/runner/verdict_parser.py` — NOT modified
- `services/runner/src/runner/__main__.py` — NOT modified (CLI is self-invokable)
- `services/runner/src/runner/doctor.py` — NOT modified
- `pyproject.toml` — NOT modified (no existing console_scripts pattern; CLI invoked via `python -m runner.ariadne_task_cli`)
- `agents/*.yml` — NOT modified
- `ROADMAP.md`, `docs/**` — NOT modified

## Forbidden files

- `services/task_intake/**`
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0128-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `ariadne_task_cli.py` with:
   - `AriadneTaskCliRequest`, `AriadneTaskCliResult`, `AriadneTaskCliStatus`
   - `AriadneTaskCliOutput` — dataclass for structured output fields
   - `parse_ariadne_task_args(argv)` — argparse parser with all CLI options
   - `run_ariadne_task(request, pipeline_runner_fn, git_boundary_planner_fn, git_boundary_executor_fn, clock_provider)` — orchestration with 5 injectable boundaries
   - `_execute_git_command_spec(spec)` — local argv executor using `subprocess.run(spec.argv, capture_output=True, shell=False)` (only if `--execute` is set)
   - `main(argv=None)` — entry point
   - Stable reason codes for CLI-specific failures

2. Create `test_ariadne_task_cli.py` with focused tests.

## Test plan

| Class | Focus |
|-------|-------|
| `TestParseTaskDescription` | Parses `ariadne task \"do x\"` → task_description set |
| `TestParseMissingTaskDescription` | No description → error |
| `TestParseOptions` | All CLI options parse correctly |
| `TestDefaultDryRun` | Default mode: pipeline runs, git boundary plans, no execution |
| `TestRunWithPipelineResultCompleted` | Pipeline completed → GitBoundaryRequest built with artifact_hashes |
| `TestRunWithPipelineResultStopped` | Pipeline stopped → git boundary blocked, CLI exits 1 |
| `TestRunWithPipelineResultFailed` | Pipeline failed → git boundary blocked, CLI exits 1 |
| `TestRunWithPipelineBlockers` | has_blockers true → git boundary blocked |
| `TestGitBlockedWithoutExecute` | No --execute → git boundary plans but does not execute |
| `TestGitBlockedWithoutApprove` | --execute without --approve → blocked |
| `TestGitBlockedMissingApprovedBy` | --approve without --approved-by → blocked |
| `TestGitBlockedMissingApprovalReason` | --approve without --approval-reason → blocked |
| `TestApprovalDoesNotOverridePipelineBlock` | Approval but stopped pipeline → blocked |
| `TestExecutionWithFullApproval` | All flags present → execution attempted |
| `TestHumanReadableOutput` | Default output contains key fields |
| `TestJsonOutput` | `--json` produces deterministic JSON |
| `TestFakePipelineRunner` | Injected fake pipeline runner used |
| `TestFakeGitBoundaryPlanner` | Injected fake planner used |
| `TestFakeGitBoundaryExecutor` | Injected fake executor used |
| `TestNoRealGitMutationInTests` | No subprocess.run/git/gh in test code for execution |
| `TestNoDocker` | No docker/docker compose in module |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestNoPipelineModified` | pipeline_runner.py not modified |
| `TestNoGitBoundaryModified` | git_boundary.py not modified |
| `TestDeterministicRepeats` | Same inputs with injectable clock → same output |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_ariadne_task_cli.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "AriadneTask|ariadne_task_cli|parse_ariadne_task_args|run_ariadne_task|PipelineRunnerRequest|GitBoundaryRequest|human_approved|approval_required|--execute|--approve" services/runner/src services/runner/tests .project-memory/pr/0129-ariadne-task-cli 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|os.system|shell=True|docker compose|docker run|pip install|python -m pip install" services/runner/src/runner/ariadne_task_cli.py services/runner/tests/test_ariadne_task_cli.py 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "git commit|git push|git add|gh pr create" services/runner/src/runner/ariadne_task_cli.py services/runner/tests/test_ariadne_task_cli.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `ariadne_task_cli.py` (new), `test_ariadne_task_cli.py` (new)
- **behavior drift**: `run_ariadne_task()` orchestrates pipeline + git boundary; default dry-run
- **CLI API drift**: argument model matches PLAN.md definitions
- **pipeline integration drift**: PipelineRunnerRequest built from CLI args; stopped pipeline blocks git
- **git boundary integration drift**: GitBoundaryRequest built from pipeline result; approval required
- **human approval drift**: `--execute --approve --approved-by --approval-reason` all required for side effects
- **output drift**: human-readable + deterministic JSON output
- **executor drift**: `subprocess.run` only in isolated function with `shell=False`; never used in tests
- **pipeline/boundary drift**: `pipeline_runner.py` and `git_boundary.py` NOT modified
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no persistence, no retry, no model health, no parallel queue
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- second Stage 2 Closed Loop PR after PR 0128 ✓
- minimal ariadne task CLI planned ✓
- CLI routes through Pipeline Runner ✓
- CLI routes through Git Boundary with human approval ✓
- no unattended git mutation rights ✓
- default CLI mode has no side effects ✓
- explicit approval required for side effects ✓
- fake-boundary tests planned ✓
- no real git/gh execution in tests ✓
- no Docker invocation ✓
- no persistence/retry/model health/run report/parallel queue/control plane ✓
- no frozen stream capability started ✓
- no `.ariadne/` residue after validation ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0129-ariadne-task-cli`
- Block if PR 0127 `pipeline_runner.py` is missing — PASS: present
- Block if PR 0128 `git_boundary.py` is missing — PASS: present
- Block if ROADMAP evidence for PR 0129 is missing — PASS: L324 confirmed
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if the plan allows mutation without explicit human approval — PASS: approval gate
- Block if CLI bypasses Pipeline Runner — PASS: routes through pipeline
- Block if CLI bypasses Git Boundary — PASS: routes through git boundary
- Block if approval bypasses safety failures — PASS: explicitly stated
- Block if tests require real git mutation, real PR creation, network, Docker, or agents — PASS: injected fakes
- Block if CLI default mode has side effects — PASS: dry-run by default
- Block if command execution uses shell strings or shell=True — PASS: argv only, shell=False
- Block if the plan implements run persistence, retry/failure recovery, model health, run report, parallel queue, dashboard, or control plane — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
