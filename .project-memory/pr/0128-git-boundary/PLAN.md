# PR 0128 — Git Boundary Plan

## Summary

Plan the first Stage 2 Closed Loop PR after PR 0127: a deterministic Git Boundary that makes git mutation possible only through an explicit human-approved boundary. Validates pipeline result eligibility, dirty-tree allowlist, approval fields, and produces argv-based command specs. Execution is possible only through an injected fakeable executor and only when explicit human approval is present. No unattended git mutation rights.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 21cc311992bc30281e37092a63a4e31a1998299c |
| current_branch | 0128-git-boundary |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line ACTIVE; L322 "0128 — Git Boundary: commit/push/PR creation only after explicit human approve" |
| pr_0124_agent_runner_bridge_evidence | `agent_runner_bridge.py` + tests present |
| pr_0125_prompt_composer_evidence | `prompt_composer.py` + tests present |
| pr_0126_verdict_parser_evidence | `verdict_parser.py` + tests present |
| pr_0127_pipeline_runner_evidence | `pipeline_runner.py` + `test_pipeline_runner.py` present; `PipelineRunnerResult` with `status`, `final_action`, `has_blockers`, `artifact_hashes`, `stopped_at`, `stop_reason`, `step_results`, `gate_results` |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 2 Closed Loop
* expected PR slot: 0128 — Git Boundary
* why this PR is next: PR 0124–0127 added Agent Runner Bridge, Prompt Composer, Verdict Parser, and Pipeline Runner; the next required capability is an explicit human-approved git mutation boundary so future CLI/dogfood runs can commit, push, and create PRs without granting agents unattended git mutation rights
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime/file-captured artifacts are evidence; git mutation requires explicit human approval

## PR 0124–0127 verification

| Check | Result |
|-------|--------|
| PR 0124 `agent_runner_bridge.py` + tests present | PRESENT ✓ |
| PR 0125 `prompt_composer.py` + tests present | PRESENT ✓ |
| PR 0126 `verdict_parser.py` + tests present | PRESENT ✓ |
| PR 0127 `pipeline_runner.py` + tests present | PRESENT ✓ |
| `PipelineRunnerResult` with `status`/`final_action`/`has_blockers`/`artifact_hashes`/`stopped_at` | CONFIRMED ✓ |

All predecessor PRs are fully implemented.

## Competitive pressure / anti-stall constraint

Do not respond to external agent-system prompts by expanding scope. PR 0128 must remain Git Boundary only. No roadmap changes. No ADR. No control-plane expansion. No CLI. No persistence. No retry loop. No model health. No run report. No parallel queue. No new capability stream.

## Git Boundary contract

### New module

`services/runner/src/runner/git_boundary.py`

Contains:
- `GitBoundaryRequest` — input dataclass
- `GitCommandSpec` — single command specification
- `GitBoundaryPlan` — command plan
- `GitBoundaryResult` — operation result
- `GitBoundaryStatus` — status enum: `approved`, `blocked`, `failed`
- `prepare_git_boundary_plan()` — validate eligibility, build command plan
- `execute_git_boundary_plan()` — execute through injected executor
- Stable reason codes

### `GitBoundaryRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GitBoundaryRequest:
    repo_root: str
    base_branch: str
    head_branch: str
    current_branch: str
    pipeline_status: str                  # from PipelineRunnerResult.status
    pipeline_final_action: str            # from PipelineRunnerResult.final_action
    pipeline_has_blockers: bool           # from PipelineRunnerResult.has_blockers
    pipeline_artifact_hashes: dict[str, str]  # from PipelineRunnerResult.artifact_hashes
    dirty_files: tuple[str, ...]
    allowed_files: tuple[str, ...]
    files_to_stage: tuple[str, ...]
    commit_message: str
    pr_title: str | None = None
    pr_body: str | None = None
    pr_body_path: str | None = None
    human_approved: bool = False
    approved_by: str | None = None
    approval_reason: str | None = None
```

### `GitCommandSpec` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GitCommandSpec:
    operation: str                        # "git_status" | "git_add" | "git_commit" | "git_push" | "gh_pr_create"
    argv: tuple[str, ...]                 # command arguments (no shell=True)
    cwd: str
    allowed_files: tuple[str, ...]        # for git_add
    requires_human_approval: bool
    side_effecting: bool                  # true for commit/push/pr-create
    redacted_display: str                 # display string with secrets redacted
    details: str | None = None
```

### `GitBoundaryPlan` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GitBoundaryPlan:
    command_specs: tuple[GitCommandSpec, ...]
    command_count: int
    files_to_stage: tuple[str, ...]
    rejected_files: tuple[str, ...]
    pipeline_eligible: bool
    dirty_tree_valid: bool
    approval_summary: str
```

### `GitBoundaryResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GitBoundaryResult:
    status: str
    reason_codes: tuple[str, ...]
    approved: bool
    blocked: bool
    command_plan: GitBoundaryPlan | None
    command_count: int
    files_to_stage: tuple[str, ...]
    rejected_files: tuple[str, ...]
    pipeline_eligible: bool
    dirty_tree_valid: bool
    approval_summary: str
    execution_attempted: bool
    execution_results: tuple[dict[str, str], ...]  # operation, exit_code, stdout, stderr
    artifact_hashes: dict[str, str]
    started_at: str | None
    finished_at: str | None
    details: str | None
```

### `GitBoundaryStatus` (enum)

```python
class GitBoundaryStatus(str, enum.Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    FAILED = "failed"
```

### `prepare_git_boundary_plan()` function

```python
def prepare_git_boundary_plan(
    request: GitBoundaryRequest,
) -> tuple[GitBoundaryPlan, list[str]]:
```

Validates:
1. Pipeline eligibility (`pipeline_status in ("completed", "completed_with_warning")`, `pipeline_final_action in ("continue", "continue_with_warning")`, `pipeline_has_blockers == False`)
2. Dirty tree validity (every dirty file in `allowed_files`, no forbidden paths)
3. File staging validity (every file in `files_to_stage` is both dirty and allowed)
4. Commit message non-empty
5. PR title non-empty if PR is requested

Builds command specs in deterministic order:
1. `git status` — `["git", "status"]`
2. `git add` — `["git", "add", "--"] + files_to_stage`
3. `git commit` — `["git", "commit", "-m", commit_message]` (side_effecting)
4. `git push` — `["git", "push", "origin", head_branch]` (side_effecting)
5. `gh_pr_create` — `["gh", "pr", "create", "--title", pr_title, ...]` (side_effecting, only if pr_title present)

### `execute_git_boundary_plan()` function

```python
def execute_git_boundary_plan(
    request: GitBoundaryRequest,
    plan: GitBoundaryPlan,
    executor: Callable | None = None,
    clock_provider: Callable | None = None,
) -> GitBoundaryResult:
```

- Without `human_approved=True` → returns blocked result immediately
- Without execution or with `dry_run` → returns plan without executing
- With executor → runs each command spec sequentially, records results
- Returns `status="approved"` on success, `status="failed"` on execution failure

## Human approval contract

No git mutation plan may be executable unless:
- `human_approved=True`
- `approved_by` is non-empty
- `approval_reason` is non-empty

Approval is recorded in `GitBoundaryResult.approval_summary`.

Approval does NOT override:
- Pipeline ineligibility (`pipeline_status` blocked)
- Forbidden dirty files (agents/*.yml, schemas/**, etc.)
- Missing commit message or PR title
- Safety failures

## Dirty tree and allowed-file contract

Every dirty file must be inside `allowed_files`. Forbidden paths always block:

```python
_FORBIDDEN_PATHS: tuple[str, ...] = (
    "agents/",
    "schemas/",
    "services/task_intake/",
    ".project-memory/post-0100/",
)
```

Additionally, the following paths are blocked unless the task explicitly allows them:
- `ROADMAP.md`
- `docs/`
- `pyproject.toml`
- `package.json`
- `Makefile`

Missing expected implementation artifacts (from `pipeline_artifact_hashes` keys that do not exist as files) also block.

## Pipeline result eligibility contract

Git mutation is blocked unless pipeline result shows:
- `pipeline_status` is `"completed"` or `"completed_with_warning"`
- `pipeline_final_action` is `"continue"` or `"continue_with_warning"`
- `pipeline_has_blockers` is `False`
- Pipeline artifact hashes are present (non-empty `artifact_hashes`)
- Plan-review and precommit-review artifacts were file-captured

If pipeline result is `"stopped"`, `"failed"`, or has blockers → `status="blocked"` with reason code `pipeline_not_eligible`.

## Command plan model

Command plans use `GitCommandSpec` with argv lists, not shell strings:

| Operation | argv | side_effecting |
|-----------|------|----------------|
| `git_status` | `["git", "status"]` | No |
| `git_add` | `["git", "add", "--"] + files` | No |
| `git_commit` | `["git", "commit", "-m", msg]` | Yes |
| `git_push` | `["git", "push", "origin", branch]` | Yes |
| `gh_pr_create` | `["gh", "pr", "create", "--title", title, "--body", body]` | Yes |

Order is deterministic.

`gh_pr_create` is included only when `pr_title` and (`pr_body` or `pr_body_path`) are present.

## Optional injected executor model

- No `subprocess.run`, no `os.system`, no `shell=True`
- No real git/gh execution in tests
- Execution allowed only through injected executor
- Executor receives `GitCommandSpec` objects, not shell strings
- Execution is skipped when `dry_run=True` or no executor is provided
- Tests use fake executor only
- Execution results recorded as `(operation, exit_code, stdout, stderr)`

## Safety and mutation boundaries

Git Boundary must not:
- Grant agents unattended git mutation rights
- Allow mutation without explicit human approval
- Execute shell strings
- Invoke Docker
- Install dependencies
- Modify agent configs
- Bypass pipeline gates
- Bypass dirty-tree allowlist
- Create `.ariadne/runs/`
- Implement CLI
- Implement persistence
- Implement retry/failure recovery
- Implement control plane

## Non-goals

PR 0128 does not implement:
- `ariadne task` CLI (PR 0129)
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
| `services/runner/src/runner/git_boundary.py` | NEW |
| `services/runner/tests/test_git_boundary.py` | NEW |

Default — not modified:
- `agent_runner_bridge.py`, `prompt_composer.py`, `verdict_parser.py`, `pipeline_runner.py` — NOT modified
- `docker_agent_adapter.py`, `proof_capture.py`, `handoff_packet.py`, `acceptance_criteria.py`, `gate_evidence.py` — NOT modified
- `agents/*.yml` — NOT modified
- `ROADMAP.md`, `docs/**` — NOT modified

## Forbidden files

- `services/task_intake/**`
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0127-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `git_boundary.py` with:
   - All dataclass shapes (request, command spec, plan, result, status)
   - Stable reason codes: `pipeline_not_eligible`, `dirty_tree_invalid`, `forbidden_path`, `rejected_file`, `missing_commit_message`, `missing_pr_title`, `human_approval_required`, `missing_approved_by`, `missing_approval_reason`, `execution_failed`
   - `prepare_git_boundary_plan()` with all eligibility checks
   - `execute_git_boundary_plan()` with injected executor
   - Deterministic command order, argv specs
   - Forbidden path constants
   - No `subprocess.run`, `os.system`, `shell=True` in code

2. Create `test_git_boundary.py` with focused tests using injected fake executor.

## Test plan

| Class | Focus |
|-------|-------|
| `TestValidPipelinePlan` | Completed pipeline → plan produced with 3+ command specs |
| `TestBlockedWithoutApproval` | No human_approved → `blocked` |
| `TestBlockedMissingApprovedBy` | approved_by empty → `blocked` |
| `TestBlockedMissingApprovalReason` | approval_reason empty → `blocked` |
| `TestApprovalDoesNotOverridePipelineBlock` | human_approved but pipeline stopped → `blocked` with `pipeline_not_eligible` |
| `TestBlockedPipelineHasBlockers` | pipeline has blockers → `blocked` |
| `TestBlockedPipelineFinalActionStop` | final_action=stop → `blocked` |
| `TestBlockedDirtyFileOutsideAllowed` | dirty file not in allowed → `blocked` with `dirty_tree_invalid` |
| `TestBlockedForbiddenPath` | agents/*.yml dirty → `blocked` with `forbidden_path` |
| `TestBlockedEmptyCommitMessage` | empty commit_message → `blocked` |
| `TestBlockedEmptyPrTitle` | pr_title empty but PR requested → `blocked` |
| `TestDeterministicCommandOrder` | git status → git add → git commit → (git push) → (gh pr create) |
| `TestCommandSpecsAreArgv` | All command specs use tuple argv, not shell strings |
| `TestSideEffectingFlags` | commit/push/pr marked side_effecting=true |
| `TestGitAddIncludesAllowedFiles` | git add only files_to_stage |
| `TestGhPrCreateIncludedOnlyWithTitle` | PR command present only when pr_title is set |
| `TestDryRunSkipsExecution` | No executor → no execution |
| `TestInjectedFakeExecutor` | Fake executor records received command specs |
| `TestExecutionResultsRecorded` | Execution results include operation, exit_code |
| `TestExecutionFailure` | Executor returns non-zero → `failed` |
| `TestNoSubprocessRunOsSystemShell` | No subprocess.run/os.system/shell=True in module |
| `TestNoDocker` | No docker/docker compose in module |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestNoPipelineModified` | pipeline_runner.py not modified |
| `TestDeterministicRepeats` | Same inputs with injectable clock → same output |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_git_boundary.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "GitBoundary|git_boundary|prepare_git_boundary_plan|execute_git_boundary_plan|GitCommandSpec|human_approved|pipeline_not_eligible|gh_pr_create|requires_human_approval" services/runner/src services/runner/tests .project-memory/pr/0128-git-boundary 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|os.system|shell=True|docker compose|docker run|pip install|python -m pip install" services/runner/src/runner/git_boundary.py services/runner/tests/test_git_boundary.py 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "git commit|git push|git add|gh pr create" services/runner/src/runner/git_boundary.py services/runner/tests/test_git_boundary.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `git_boundary.py` (new), `test_git_boundary.py` (new)
- **behavior drift**: `prepare_git_boundary_plan()` + `execute_git_boundary_plan()` only; no unattended git mutation
- **Git Boundary API drift**: input/output shapes match PLAN.md definitions
- **human approval drift**: no mutation without `human_approved=True` + `approved_by` + `approval_reason`
- **pipeline eligibility drift**: stopped/failed/blocked pipeline → blocked
- **dirty-tree drift**: forbidden paths always blocked; dirty files must be in allowed_files
- **command plan drift**: argv specs, not shell strings; deterministic order
- **executor drift**: no subprocess.run/os.system/shell=True; injected fakeable executor
- **bridge/composer/parser/pipeline drift**: all predecessor modules NOT modified
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no CLI, no persistence, no retry, no model health, no parallel queue
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- first Stage 2 Closed Loop PR after PR 0127 ✓
- human-approved git mutation boundary planned ✓
- no unattended git mutation rights ✓
- pipeline eligibility gate enforced ✓
- dirty-tree allowlist enforced ✓
- argv command specs, not shell strings ✓
- injected fake executor in tests ✓
- no real git mutation required in tests ✓
- no Docker invocation ✓
- no CLI/run persistence/retry/model health/run report/parallel queue ✓
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

- Block if current branch is not `0128-git-boundary`
- Block if PR 0123 Production Line roadmap evidence is missing from ROADMAP.md — PASS: confirmed
- Block if PR 0124 `agent_runner_bridge.py` is missing — PASS: present
- Block if PR 0125 `prompt_composer.py` is missing — PASS: present
- Block if PR 0126 `verdict_parser.py` is missing — PASS: present
- Block if PR 0127 `pipeline_runner.py` is missing — PASS: present
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if the plan allows mutation without explicit human approval — PASS: human_approved gate
- Block if approval bypasses safety failures — PASS: explicitly stated
- Block if pipeline stopped/block result can still mutate git — PASS: pipeline eligibility gate
- Block if dirty-tree allowlist is missing — PASS: forbidden paths + allowed_files check
- Block if command plan uses raw shell strings instead of argv command specs — PASS: argv only
- Block if tests require real git mutation, real PR creation, network, or Docker — PASS: fake executor only
- Block if implementation requires direct `subprocess.run`, `os.system`, or `shell=True` — PASS: explicitly prohibited
- Block if the plan implements `ariadne task` CLI, run persistence, retry/failure recovery, model health, run report, parallel queue, or control plane — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
