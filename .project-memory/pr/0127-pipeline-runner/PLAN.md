# PR 0127 — Pipeline Runner Plan

## Summary

Plan the fourth executable Production Line PR: a deterministic Pipeline Runner that connects PR 0124 (Agent Runner Bridge), PR 0125 (Prompt Composer), and PR 0126 (Verdict Parser) into a single call that executes the full agent sequence: compose prompts → planner → plan-review → gate → coder → precommit-review → gate. Stops on block. Returns structured pipeline result. No git boundary, no CLI, no persistence, no retry execution. Executable-first.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 41d50e9d1df20682e00b97885833bee3070cb499 |
| current_branch | 0127-pipeline-runner |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line Stream ACTIVE; L315 "0127 — Pipeline Runner" |
| pr_0124_agent_runner_bridge_evidence | `agent_runner_bridge.py` + `test_agent_runner_bridge.py` present; `run_agent_runner_bridge(agent_name, task_prompt, ...)` API available with `AgentRunnerBridgeResult`, `AgentRunnerBridgeArtifact`, `AgentRunnerBridgeStatus.COMPLETED/BLOCKED/FAILED` |
| pr_0125_prompt_composer_evidence | `prompt_composer.py` + `test_prompt_composer.py` present; `compose_pr_prompts()` returns 4 `PromptPacket` objects with `ready_for_agent_runner_bridge=True` |
| pr_0126_verdict_parser_evidence | `verdict_parser.py` + `test_verdict_parser.py` present; `parse_review_artifact()`, `decide_next_action()`, `VerdictDecisionStatus.CONTINUE/CONTINUE_WITH_WARNING/STOP/INVALID`, `ParsedReviewArtifact`, `VerdictDecision` with `is_retry_candidate` and `human_required` |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 1 Orchestrator
* expected PR slot: 0127 — Pipeline Runner
* why this PR is next: PR 0124 added Agent Runner Bridge, PR 0125 added Prompt Composer, and PR 0126 added Verdict Parser; the next required capability is a one-call runner that executes planner → plan-review → gate → coder → precommit-review → gate and stops on block
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime/file-captured artifacts are evidence

## PR 0124 Agent Runner Bridge verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/agent_runner_bridge.py` exists | PRESENT ✓ |
| `.project-memory/pr/0124-agent-runner-bridge/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `run_agent_runner_bridge(agent_name, task_prompt, ...)` API | CONFIRMED ✓ |
| `AgentRunnerBridgeResult` with status/reason_codes/agent_name/task_prompt_hash/captured_artifact | CONFIRMED ✓ |

## PR 0125 Prompt Composer verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/prompt_composer.py` exists | PRESENT ✓ |
| `.project-memory/pr/0125-prompt-composer/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `compose_pr_prompts()` returns 4 PromptPackets (planner, plan-review, coder, precommit-review) | CONFIRMED ✓ |
| Packets have `ready_for_agent_runner_bridge=True`, `prompt_text`, `prompt_hash`, `expected_output_path` | CONFIRMED ✓ |

## PR 0126 Verdict Parser verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/verdict_parser.py` exists | PRESENT ✓ |
| `.project-memory/pr/0126-verdict-parser/reviews/precommit-review.yml` verdict pass | PRESENT ✓ |
| `parse_review_artifact()` and `decide_next_action()` | CONFIRMED ✓ |
| `VerdictDecisionStatus.CONTINUE`, `CONTINUE_WITH_WARNING`, `STOP`, `INVALID` | CONFIRMED ✓ |
| `ParsedReviewArtifact` with `review_type`, `raw_verdict`, `normalized_verdict`, `blockers`, `artifact_hash` | CONFIRMED ✓ |
| `VerdictDecision` with `next_action`, `is_retry_candidate`, `human_required`, `has_blockers` | CONFIRMED ✓ |

## Competitive pressure / anti-stall constraint

Do not respond to external agent-system prompts by expanding scope. The correct response is to close the Ariadne dogfood loop faster. PR 0127 must remain Pipeline Runner only. No roadmap changes. No ADR. No control-plane expansion. No persistence. No git boundary. No CLI. No retry loop. No model health. No run report. No parallel queue. No new capability stream.

## Pipeline Runner contract

### New module

`services/runner/src/runner/pipeline_runner.py`

Contains:
- `PipelineRunnerRequest` — input dataclass
- `PipelineStepResult` — single step result
- `PipelineGateResult` — gate result
- `PipelineRunnerResult` — final result
- `PipelineRunnerStatus` — status enum: `completed`, `completed_with_warning`, `stopped`, `failed`
- `run_pr_pipeline()` — main function
- Stable reason codes

### `PipelineRunnerRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PipelineRunnerRequest:
    pr_id: str
    branch: str
    task_title: str
    task_description: str
    repo_root: str = "."
    agents_dir: str = "agents"
    project_memory_dir: str = ".project-memory"
    workdir: str | None = None
    allow_docker: bool = False
    prompt_composer: Callable | None = None   # injectable boundary
    bridge_runner: Callable | None = None      # injectable boundary
    artifact_reader: Callable | None = None    # injectable boundary
    verdict_parser: Callable | None = None     # injectable boundary
    clock_provider: Callable | None = None     # deterministic clock
```

### `PipelineStepResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PipelineStepResult:
    step_name: str
    status: str                           # "completed" | "blocked" | "failed" | "skipped"
    reason_codes: tuple[str, ...]
    agent_name: str | None
    prompt_hash: str | None
    expected_artifact_path: str | None
    artifact_exists: bool
    artifact_hash: str | None
    artifact_line_count: int | None
    bridge_status: str | None
    bridge_proof_summary: str | None
    parsed_verdict: str | None
    next_action: str | None
    started_at: str | None
    finished_at: str | None
    details: str | None
```

### `PipelineGateResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PipelineGateResult:
    gate_name: str                        # "plan-review" | "precommit-review"
    verdict: str
    normalized_verdict: str
    has_blockers: bool
    next_action: str
    is_retry_candidate: bool
    human_required: bool
    artifact_hash: str
    parsed: dict | None                   # serialized ParsedReviewArtifact fields
```

### `PipelineRunnerResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PipelineRunnerResult:
    status: str
    reason_codes: tuple[str, ...]
    pr_id: str
    branch: str
    task_title: str
    prompt_order: tuple[str, ...]
    step_results: tuple[PipelineStepResult, ...]
    gate_results: tuple[PipelineGateResult, ...]
    final_action: str
    stopped_at: str | None
    stop_reason: str | None
    has_blockers: bool
    warnings: tuple[str, ...]
    artifact_hashes: dict[str, str]
    proof_summary: str
    started_at: str | None
    finished_at: str | None
    details: str | None
```

## Pipeline step model

The pipeline executes exactly these steps in order:

1. **compose_prompts** — call injected `prompt_composer` or `compose_pr_prompts()`
2. **planner** — call injected `bridge_runner` or `run_agent_runner_bridge("planner", planner_packet.prompt_text, ...)`
3. **planner_artifact_check** — verify `PLAN.md` exists at expected path
4. **plan_review** — call injected `bridge_runner` or `run_agent_runner_bridge("plan-review", plan_review_packet.prompt_text, ...)`
5. **plan_review_gate** — call injected `verdict_parser` or `parse_review_artifact()` + `decide_next_action()`; stop on block
6. **coder** — call injected `bridge_runner` or `run_agent_runner_bridge("coder", coder_packet.prompt_text, ...)`
7. **precommit_review** — call injected `bridge_runner` or `run_agent_runner_bridge("precommit-review", precommit_packet.prompt_text, ...)`
8. **precommit_gate** — call injected `verdict_parser` or `parse_review_artifact()` + `decide_next_action()`; stop on block

Each `PipelineStepResult` records `started_at`, `finished_at`, `status`, `reason_codes`, and step-specific fields.

## Artifact proof and gate contract

The pipeline must not treat agent stdout/stderr or bridge narrative as gate evidence.

Gate evidence requires:
- Expected artifact path from prompt packet (e.g., `.project-memory/pr/{pr_id}/reviews/plan-review.yml`)
- Artifact file exists (`os.path.exists()`)
- Artifact is readable
- Artifact hash recorded (SHA256[:16])
- Artifact line count recorded
- Verdict parser result recorded via `parse_review_artifact()` + `decide_next_action()`
- `next_action` recorded

Missing artifact rules:
- If expected planner artifact (`PLAN.md`) is missing → stop before plan-review with reason `missing_planner_artifact`
- If expected review artifact is missing → gate status `failed`, final action `stop`, reason `missing_review_artifact`
- If coder step fails → stop before precommit-review with reason `coder_step_failed`

## Stop-on-block gate rules

| Plan-review gate verdict | Action |
|-------------------------|--------|
| `continue` | Run coder |
| `continue_with_warning` | Run coder, record warning |
| `stop` | Stop before coder |
| `invalid` | Stop before coder |

| Precommit-review gate verdict | Action |
|------------------------------|--------|
| `continue` | Pipeline status = `completed` |
| `continue_with_warning` | Pipeline status = `completed_with_warning` |
| `stop` | Pipeline status = `stopped` |
| `invalid` | Pipeline status = `stopped` |

Additional rules:
- Any blockers from verdict parser → `stop`
- Any safety boundary violation (`human_required=True`) → `stop`
- `is_retry_candidate` is recorded as metadata only — do not execute retry

## Injection and fake-boundary strategy for tests

All external dependencies must be injectable:

| Dependency | Default | Test injection |
|-----------|---------|----------------|
| prompt composer | `compose_pr_prompts()` from `prompt_composer` | Fake returning fixed `PromptComposerResult` |
| bridge runner | `run_agent_runner_bridge()` from `agent_runner_bridge` | Fake returning fixed `AgentRunnerBridgeResult` with proof artifact |
| artifact reader | `os.path.exists()` + `open()` | Fake returning fixed artifact text |
| verdict parser | `parse_review_artifact()` + `decide_next_action()` from `verdict_parser` | Fake returning fixed `ParsedReviewArtifact` + `VerdictDecision` |
| clock | `datetime.utcnow()` or None | Injected `clock_provider` returning fixed timestamp |

Tests must NOT require:
- Real Docker daemon
- Real agent execution
- Network access
- Git mutation
- `.ariadne/runs/` persistence

## Safety and mutation boundaries

The pipeline runner must not:
- Call Docker directly
- Run shell commands
- Execute git mutation
- Create commits
- Push branches
- Create GitHub PRs
- Install dependencies
- Edit `agents/*.yml`
- Create `.ariadne/runs/`
- Start frozen streams

The pipeline may call `run_agent_runner_bridge(...)` only through an injectable boundary. Generated/running agents must not receive unattended git mutation rights.

## Non-goals

PR 0127 does not implement:
- Git boundary (PR 0128)
- PR creation (PR 0128)
- `ariadne task` CLI (PR 0129)
- `.ariadne/runs/` persistence (PR 0130)
- Retry/failure recovery loop (PR 0132)
- Automatic prompt refinement (PR 0132)
- Model health live fallback (PR 0133)
- Run report (PR 0134)
- Parallel-safe queue (PR 0135)
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/pipeline_runner.py` | NEW |
| `services/runner/tests/test_pipeline_runner.py` | NEW |

Default — not modified:
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `services/runner/src/runner/prompt_composer.py` — NOT modified
- `services/runner/src/runner/verdict_parser.py` — NOT modified
- `services/runner/src/runner/docker_agent_adapter.py` — NOT modified
- `services/runner/src/runner/proof_capture.py` — NOT modified
- `services/runner/src/runner/handoff_packet.py` — NOT modified
- `services/runner/src/runner/acceptance_criteria.py` — NOT modified
- `services/runner/src/runner/gate_evidence.py` — NOT modified
- `agents/*.yml` — NOT modified
- `ROADMAP.md`, `docs/**` — NOT modified

## Forbidden files

- `services/task_intake/**` — out of scope for Production Line
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0126-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `pipeline_runner.py` with:
   - `PipelineRunnerRequest`, `PipelineStepResult`, `PipelineGateResult`, `PipelineRunnerResult`, `PipelineRunnerStatus`
   - `run_pr_pipeline()` — main orchestration function
   - Default composers: use `compose_pr_prompts()`, `run_agent_runner_bridge()`, `parse_review_artifact()` + `decide_next_action()`
   - All injectable boundaries via function parameters
   - Stable reason codes for: `missing_planner_artifact`, `missing_review_artifact`, `coder_step_failed`, `gate_stop`, `pipeline_stopped`, `pipeline_completed`

2. Create `test_pipeline_runner.py` with focused tests using injected fakes (see test plan below).

## Test plan

| Class | Focus |
|-------|-------|
| `TestFullSequencePass` | 8 steps complete → status `completed`, final_action `continue` |
| `TestPromptOrder` | Steps in order: compose_prompts → planner → planner_artifact_check → plan_review → plan_review_gate → coder → precommit_review → precommit_gate |
| `TestPlannerArtifactRequired` | Missing planner artifact → stop at planner_artifact_check with `missing_planner_artifact` |
| `TestPlanReviewBlock` | Plan-review gate block → stop before coder |
| `TestPlanReviewWarning` | Plan-review warning → `continue_with_warning`, coder still runs |
| `TestPrecommitPass` | Precommit gate pass → status `completed` |
| `TestPrecommitWarning` | Precommit gate warning → status `completed_with_warning` |
| `TestPrecommitBlock` | Precommit gate block → status `stopped` |
| `TestInvalidReviewArtifact` | Invalid verdict → stop |
| `TestMissingReviewArtifact` | Missing review artifact → `missing_review_artifact` |
| `TestCoderStepFailure` | Coder bridge fails → stop before precommit with `coder_step_failed` |
| `TestBlockersForceStop` | Blockers present → stop regardless of verdict |
| `TestSafetyViolation` | `human_required=True` → stop |
| `TestRetryCandidateMetadata` | `is_retry_candidate` recorded but not executed |
| `TestNoDirectDocker` | No subprocess.run, docker, docker compose in pipeline code |
| `TestNoDirectGit` | No git add/commit/push commands in pipeline code |
| `TestInjectedComposer` | Fake composer → pipeline uses injected output |
| `TestInjectedBridge` | Fake bridge runner → pipeline uses injected output |
| `TestInjectedParser` | Fake verdict parser → pipeline uses injected output |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestDeterministicRepeats` | Same inputs with injectable clock → identical output |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_pipeline_runner.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_docker_agent_adapter.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "PipelineRunner|pipeline_runner|run_pr_pipeline|PipelineStepResult|PipelineGateResult|stop_reason|missing_review_artifact|runtime/file-captured|retry_candidate" services/runner/src services/runner/tests .project-memory/pr/0127-pipeline-runner 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|docker compose|docker run|gh pr create|git push|git commit|git add|pip install|python -m pip install" services/runner/src/runner/pipeline_runner.py services/runner/tests/test_pipeline_runner.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `pipeline_runner.py` (new), `test_pipeline_runner.py` (new)
- **behavior drift**: `run_pr_pipeline()` orchestrates 8 steps; no git boundary, no CLI, no persistence
- **pipeline API drift**: input/output shapes match PLAN.md definitions
- **step model drift**: 8 steps in correct order with correct gate routing
- **gate rules drift**: stop-on-block rules match PLAN.md (continue/cw/stop/invalid per review type)
- **artifact proof drift**: gates use verdict parser, not agent narrative; artifact path/hash/line count required
- **injection boundary drift**: all external dependencies injectable in tests
- **bridge/composer/parser drift**: `agent_runner_bridge.py`, `prompt_composer.py`, `verdict_parser.py` NOT modified
- **git mutation drift**: no git commands in pipeline code
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no git boundary, no CLI, no persistence, no retry execution, no model health
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- fourth executable Production Line PR after PR 0126 ✓
- composes PR 0124 + PR 0125 + PR 0126 into one call ✓
- full 8-step sequence: compose → planner → artifact check → review → gate → coder → review → gate ✓
- stops on block per deterministic gate rules ✓
- gates use verdict parser, not agent narrative ✓
- artifact path/hash/line count required for gate evidence ✓
- retry_candidate metadata only; no retry execution ✓
- no git boundary, no CLI, no persistence, no model health ✓
- no direct Docker invocation, no real Docker in tests ✓
- injected boundaries for all external dependencies ✓
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

- Block if current branch is not `0127-pipeline-runner`
- Block if PR 0123 Production Line roadmap evidence is missing from ROADMAP.md — PASS: confirmed
- Block if PR 0124 `agent_runner_bridge.py` is missing — PASS: present
- Block if PR 0125 `prompt_composer.py` is missing — PASS: present
- Block if PR 0126 `verdict_parser.py` is missing — PASS: present
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan invokes Docker directly — PASS: uses injectable bridge boundary
- Block if the plan requires a real Docker daemon in tests — PASS: injected fakes
- Block if the plan runs shell commands directly — PASS: no subprocess.run in pipeline code
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if pipeline treats raw agent output as gate evidence — PASS: gates use verdict parser + artifact files
- Block if pipeline does not require file-captured artifacts for gates — PASS: artifact path/hash/line count required
- Block if pipeline does not stop on plan-review block — PASS: deterministic gate rules
- Block if pipeline does not stop on precommit-review block — PASS: deterministic gate rules
- Block if parser retry_candidate causes retry execution — PASS: metadata only
- Block if the plan implements git boundary, PR creation, `ariadne task` CLI, run persistence, retry/failure recovery, model health, run report, or parallel queue — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
