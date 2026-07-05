# PR 0125 — Prompt Composer Plan

## Summary

Plan the second executable Production Line PR after PR 0124: a deterministic Prompt Composer that generates the four agent task prompts (planner, plan-review, coder, precommit-review) from templates, PR context, and repository evidence. The composed prompt packets are structured for direct use as `task_prompt` inputs to `run_agent_runner_bridge(...)`. No agent execution, no Docker, no full pipeline. Executable-first.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | f398c5b30ce058861eec8db977f22f33f2ec4622 |
| current_branch | 0125-prompt-composer |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md contains Production Line Stream, PR 0124, PR 0125 Prompt Composer, DOGFOOD, frozen streams |
| pr_0124_agent_runner_bridge_evidence | `services/runner/src/runner/agent_runner_bridge.py` present; `run_agent_runner_bridge(agent_name, task_prompt, ...)` API available |
| agents_config_evidence | 9 agent configs present including coder.yml, plan-review.yml, precommit-review.yml |
| optional_missing_files | agents/planner.yml not found (does not exist as `agents/planner.yml` — the planner agent uses `agents/01_platform_architect.md`; composer must handle missing planner config gracefully) |

## Roadmap alignment

* roadmap track: Production Line — Stage 1 Orchestrator
* expected PR slot: 0125 — Prompt Composer
* why this PR is next: PR 0124 added the Agent Runner Bridge with `run_agent_runner_bridge(agent_name, task_prompt, ...)`. The next required capability is composing planner, plan-review, coder, and precommit-review task prompts from templates and PR context so they can be passed to the bridge.
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime-captured proof is evidence

## PR 0124 bridge verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/agent_runner_bridge.py` exists | PRESENT ✓ |
| `services/runner/tests/test_agent_runner_bridge.py` exists | PRESENT ✓ |
| `.project-memory/pr/0124-agent-runner-bridge/reviews/precommit-review.yml` exists, verdict pass | PRESENT ✓ |
| `run_agent_runner_bridge(agent_name, task_prompt, ...)` API available | CONFIRMED ✓ |
| `AgentRunnerBridgeResult` includes `task_prompt_hash`, `agent_config_hash`, `captured_artifact` | CONFIRMED ✓ |
| Real `agents/*.yml` configs exist for coder, plan-review, precommit-review | CONFIRMED ✓ |

PR 0124 Agent Runner Bridge is fully implemented. PR 0125 proceeds.

## Existing prompt / agent config inventory

| File | Role for composer |
|------|-------------------|
| `agents/coder.yml` | Config for coder agent — version 8, coder_model, max_iterations 12, toolsets, permissions |
| `agents/plan-review.yml` | Config for plan-review agent — version 1, plan_review_model, max_tokens 8000, temperature 0 |
| `agents/precommit-review.yml` | Config for precommit-review agent — version 1 with required contexts and section-by-section instructions |
| `agents/architect.yml` | Config for architect agent |
| `agents/chief-architect.yml` | Config for chief-architect agent |
| `agents/01_platform_architect.md` | Markdown agent spec (legacy format — not a .yml config) |
| `agents/02_repository_scaffolder.md` | Markdown agent spec (legacy format) |
| `agents/03_runner_patch_engineer.md` | Markdown agent spec (legacy format) |
| `agents/04_qa_contracts_reviewer.md` | Markdown agent spec (legacy format) |
| `services/runner/src/runner/agent_runner_bridge.py` | Target for prompt packets — `run_agent_runner_bridge(agent_name, task_prompt)` |
| `.project-memory/review-artifact.schema.yml` | Schema for review artifact — defines plan-review and precommit-review artifact shapes |
| `ROADMAP.md` | Contains Production Line Stream, PR 0124–0136, DOGFOOD, frozen streams |

## Proposed Prompt Composer contract

### New module

`services/runner/src/runner/prompt_composer.py`

Contains:
- `PromptComposerRequest` — input dataclass
- `PromptPacket` — single prompt packet
- `PromptComposerResult` — result dataclass
- `PromptComposerStatus` — status enum: `ready`, `blocked`, `failed`
- `compose_pr_prompts()` — main function that generates all four prompt packets
- `_compose_planner_prompt()` — compose planner prompt
- `_compose_plan_review_prompt()` — compose plan-review prompt
- `_compose_coder_prompt()` — compose coder prompt
- `_compose_precommit_review_prompt()` — compose precommit-review prompt
- Stable reason codes

### `PromptComposerRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PromptComposerRequest:
    pr_id: str
    branch: str
    task_title: str
    task_description: str
    roadmap_path: str = "ROADMAP.md"
    agents_dir: str = "agents"
    project_memory_dir: str = ".project-memory"
    repo_root: str = "."
    included_context_paths: tuple[str, ...] = ()
    clock_provider: Callable[[], str] | None = None
```

### `PromptPacket` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PromptPacket:
    agent_name: str
    prompt_kind: str                    # "planner" | "plan-review" | "coder" | "precommit-review"
    prompt_text: str                    # the full composed task prompt text
    prompt_hash: str                    # SHA256[:16] of prompt_text
    required_inputs: tuple[str, ...]
    expected_output_path: str
    allowed_write_paths: tuple[str, ...]
    forbidden_write_paths: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    boundary_confirmations: tuple[str, ...]
    source_template_hash: str | None    # SHA256[:16] of the template used
    source_context_hash: str            # SHA256[:16] of context evidence
    ready_for_agent_runner_bridge: bool = True
```

### `PromptComposerResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class PromptComposerResult:
    status: str                         # "ready" | "blocked" | "failed"
    reason_codes: tuple[str, ...]
    pr_id: str
    branch: str
    task_title: str
    task_description_hash: str          # SHA256[:16]
    context_hash: str                   # SHA256[:16] of all context files read
    source_evidence: dict[str, str]     # evidence key → value
    prompt_packets: tuple[PromptPacket, ...]
    prompt_order: tuple[str, ...]       # ["planner", "plan-review", "coder", "precommit-review"]
    warnings: tuple[str, ...]
    details: str | None
```

### `compose_pr_prompts()` API

```python
def compose_pr_prompts(
    request: PromptComposerRequest,
) -> PromptComposerResult:
```

The function:
1. Hash `task_description`
2. Read ROADMAP.md evidence (Production Line Stream, PR 0124 Agent Runner Bridge)
3. Read `agents/*.yml` config inventory
4. Read included context paths, hash them
5. Compute `context_hash` from all evidence files
6. Compose four prompt packets using built-in deterministic templates
7. Assign `prompt_order` = `("planner", "plan-review", "coder", "precommit-review")`
8. Return `PromptComposerResult` with all four packets

## Prompt packet contract

Each prompt packet must contain a `prompt_text` that is suitable as `task_prompt` for `run_agent_runner_bridge(agent_name, task_prompt=packet.prompt_text, ...)`.

### Planner prompt

```
Agent: planner (agent_name)
Task: Plan the next Ariadne PR for: {task_description}

PR context:
- PR ID: {pr_id}
- Branch: {branch}
- Title: {task_title}
- Task: {task_description}

Roadmap evidence:
{roadmap_evidence}

Repository evidence:
{agent_config_inventory}
{context_paths}

Expected output path: .project-memory/pr/{pr_id}/PLAN.md

Allowed write paths:
- .project-memory/pr/{pr_id}/PLAN.md

Forbidden write paths:
- ROADMAP.md, docs/**, schemas/**, agents/**, pyproject.toml, package.json, Makefile
- .project-memory/pr/{pr_id}/reviews/**
- .project-memory/post-0100/**

Forbidden commands:
- git add, git commit, git push, git checkout, git switch, git merge, git rebase, git reset, git clean, git tag
- gh pr create, gh release
- docker, docker compose
- pip install

Safety boundaries:
- Do not execute commands.
- Do not mutate git state.
- Do not call providers/network/LLM from code.
- Agent output is not evidence. Runtime-captured proof is evidence.
- You are the planner, not the coder, not the reviewer.

Evidence requirements to include in PLAN.md:
- PR 0124 Agent Runner Bridge presence
- PR 0125 Prompt Composer presence
- agents/*.yml inventory
- Frozen streams until PR 0136
```

### Plan-review prompt

```
Agent: plan-review (agent_name)
Task: Review the PLAN.md for PR {pr_id}: {task_description}

PR context:
- PR ID: {pr_id}
- Branch: {branch}
- Title: {task_title}
- Task: {task_description}

Expected output path: .project-memory/pr/{pr_id}/reviews/plan-review.yml

[Similar structure to planner with review-appropriate boundaries]
```

### Coder prompt

```
Agent: coder (agent_name)
Task: Implement PR {pr_id}: {task_description}

PR context:
- PR ID: {pr_id}
- Branch: {branch}
- Title: {task_title}
- Task: {task_description}

Approved PLAN.md path: .project-memory/pr/{pr_id}/PLAN.md

Expected output paths:
(per PLAN.md)

Allowed write paths:
(per PLAN.md)

[Similar structure with implementation-appropriate boundaries]
```

### Precommit-review prompt

```
Agent: precommit-review (agent_name)
Task: Review implementation for PR {pr_id}: {task_description}

PR context:
- PR ID: {pr_id}
- Branch: {branch}
- Title: {task_title}
- Task: {task_description}

Expected output path: .project-memory/pr/{pr_id}/reviews/precommit-review.yml

[Similar structure with precommit-appropriate boundaries, including PLAN DRIFT GATE, verification commands]
```

## Template and context evidence contract

The composer must not invent context. It must record evidence for:

| Evidence key | Source | Plan |
|--------------|--------|------|
| `roadmap_production_line` | ROADMAP.md Production Line Stream | grep-confirmed, SHA256 hashed |
| `roadmap_pr_0124` | ROADMAP.md PR 0124 Agent Runner Bridge entry | grep-confirmed, SHA256 hashed |
| `roadmap_frozen_streams` | ROADMAP.md frozen-until-0136 list | grep-confirmed, SHA256 hashed |
| `agent_configs` | `agents/*.yml` file listing | directory listing, SHA256 hashed |
| `agent_config_hash_{name}` | SHA256 hash of individual agent config | read-only, SHA256 hashed |
| `review_artifact_schema` | `.project-memory/review-artifact.schema.yml` | SHA256 hashed |
| `context_paths_{n}` | Each `included_context_paths` entry | read, SHA256 hashed |

The `source_context_hash` is the SHA256 of a sorted, deterministic JSON object containing all evidence key-value pairs.

The `source_template_hash` per packet is the SHA256 of the built-in template string used for that `prompt_kind`.

Templates are built-in deterministic Python f-strings in PR 0125. External template persistence is not required yet.

## Safety and mutation boundaries

Generated prompts must forbid (unless the specific future human-approved git boundary PR 0128 exists):

```
- git add, git commit, git push, git checkout, git switch, git merge, git rebase, git reset, git clean, git tag
- gh pr create, gh release
- docker, docker compose
- pip install, python -m pip install
```

Generated prompts must also forbid:
- editing `agents/*.yml`
- editing `ROADMAP.md` unless the task explicitly is a roadmap PR
- editing `docs/**` unless the task explicitly allows docs
- editing `schemas/**` unless the task explicitly allows schemas
- editing `.project-memory/post-0100/**`

## Non-goals

PR 0125 does not implement:
- Agent execution or Docker execution (PR 0124 does this)
- Full four-agent pipeline runner (PR 0127)
- Verdict parser (PR 0126)
- Git boundary (PR 0128)
- `ariadne task` CLI (PR 0129)
- Run persistence in `.ariadne/runs/` (PR 0130)
- Retry/failure recovery loop (PR 0132)
- Model health live fallback (PR 0133)
- Run report (PR 0134)
- Parallel-safe queue (PR 0135)
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/prompt_composer.py` | NEW |
| `services/runner/tests/test_prompt_composer.py` | NEW |

Default — not modified:
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `services/runner/src/runner/docker_agent_adapter.py` — NOT modified
- `services/runner/src/runner/proof_capture.py` — NOT modified
- `services/runner/src/runner/handoff_packet.py` — NOT modified
- `services/runner/src/runner/acceptance_criteria.py` — NOT modified
- `services/runner/src/runner/gate_evidence.py` — NOT modified
- `agents/*.yml` — NOT modified

## Forbidden files

- `services/task_intake/**` — out of scope for Production Line
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0124-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/` (configs not modified)
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `prompt_composer.py` with:
   - `PromptComposerRequest`, `PromptPacket`, `PromptComposerResult`, `PromptComposerStatus`
   - `compose_pr_prompts()` — main function
   - Built-in deterministic templates for planner, plan-review, coder, precommit-review
   - Context/evidence collection from ROADMAP.md, `agents/*.yml`, included context paths
   - Deterministic hashing (SHA256[:16]) for `task_description_hash`, `context_hash`, `prompt_hash`, `source_template_hash`, `source_context_hash`
   - Safety boundaries in generated prompts
   - Stable reason codes for missing evidence, missing agent configs, path traversal

2. Create `test_prompt_composer.py` with focused tests (see test plan below).

## Test plan

| Class | Focus |
|-------|-------|
| `TestComposeFourPackets` | `compose_pr_prompts()` returns exactly four prompt packets |
| `TestPromptOrder` | Packets in order: planner → plan-review → coder → precommit-review |
| `TestPacketFields` | Each packet has agent_name, prompt_kind, prompt_text, prompt_hash, required_inputs, expected_output_path |
| `TestPromptHashStable` | Same request → same prompt_hash per packet |
| `TestTaskDescriptionHash` | `task_description_hash` is deterministic SHA256[:16] |
| `TestContextHash` | `context_hash` includes ROADMAP, agents configs, context paths |
| `TestSourceTemplateHash` | Same prompt_kind → same source_template_hash |
| `TestPlannerTemplate` | Planner prompt includes roadmap evidence and agent config inventory |
| `TestPlanReviewTemplate` | Plan-review prompt includes reference to PLAN.md |
| `TestCoderTemplate` | Coder prompt includes reference to approved PLAN.md paths |
| `TestPrecommitTemplate` | Precommit-review prompt includes PLAN DRIFT GATE |
| `TestForbiddenGitCommands` | Generated prompts forbid git add/commit/push, gh pr create, gh release |
| `TestForbiddenDockerCommands` | Generated prompts forbid docker, docker compose |
| `TestForbiddenAgentModification` | Generated prompts forbid editing agents/*.yml |
| `TestMissingRoadmapEvidence` | ROADMAP.md missing Production Line → warning in result |
| `TestMissingAgentConfigs` | Missing agents directory → blocked/failed with evidence |
| `TestReadyForBridge` | All packets have `ready_for_agent_runner_bridge=True` |
| `TestPromptTextIsString` | Each prompt_text is a non-empty string suitable for run_agent_runner_bridge |
| `TestNoRawAgentOutput` | Composer does not reference raw agent output as evidence |
| `TestDeterministicRepeats` | Same inputs → identical output |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_prompt_composer.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_execution_envelope.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "PromptComposer|prompt_composer|compose_pr_prompts|PromptPacket|prompt_hash|context_hash|source_template_hash|ready_for_agent_runner_bridge" services/runner/src services/runner/tests .project-memory/pr/0125-prompt-composer 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "git push|git commit|git add|gh pr create|docker compose|docker run|pip install|python -m pip install" services/runner/src/runner/prompt_composer.py services/runner/tests/test_prompt_composer.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `prompt_composer.py` (new), `test_prompt_composer.py` (new)
- **behavior drift**: `compose_pr_prompts()` generates four prompt packets; no agent execution, no Docker
- **composer API drift**: input/output shapes match the PLAN.md definitions
- **prompt packet drift**: each packet has all required fields (agent_name, prompt_kind, prompt_text, prompt_hash, etc.)
- **bridge integration drift**: packets have `ready_for_agent_runner_bridge=True` and suitable prompt_text
- **git mutation drift**: generated prompts forbid git mutation commands
- **agent config drift**: configs loaded but not modified
- **evidence drift**: context recorded from ROADMAP.md, agents files, context paths — not invented
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no agent execution, no full pipeline, no verdict parser, no git boundary
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- second executable Production Line PR after PR 0124 ✓
- composes exactly four prompt packets (planner, plan-review, coder, precommit-review) ✓
- prompt packets are suitable for `run_agent_runner_bridge(...)` ✓
- packets include prompt_hash, source_template_hash, source_context_hash ✓
- evidence is recorded from filesystem (ROADMAP.md, agents/*.yml), not invented ✓
- no agent execution, no Docker invocation ✓
- generated prompts forbid git mutation, Docker, agent config modification ✓
- no full four-agent pipeline ✓
- no verdict parser / git boundary / ariadne task CLI / run persistence ✓
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

- Block if current branch is not `0125-prompt-composer`
- Block if PR 0123 Production Line roadmap evidence is missing from ROADMAP.md — PASS: confirmed
- Block if PR 0124 `agent_runner_bridge.py` is missing — PASS: present
- Block if no real `agents/*.yml` config exists to use as input evidence — PASS: 5 .yml configs present
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan runs agents — PASS: no agent execution
- Block if the plan invokes Docker — PASS: explicit prohibition
- Block if the plan requires a real Docker daemon in tests — PASS: no Docker in tests
- Block if generated prompts grant unattended git mutation rights — PASS: explicitly forbidden
- Block if prompt packets do not include hashes and source evidence — PASS: hash+evidence required
- Block if generated prompts are not suitable for `run_agent_runner_bridge(...)` — PASS: ready_for_agent_runner_bridge=True
- Block if raw agent output is treated as evidence — PASS: composer does not reference agent output
- Block if the plan implements the full four-agent pipeline — PASS: deferred to PR 0127
- Block if the plan implements verdict parser, git boundary, PR creation, `ariadne task` CLI, or run persistence — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
