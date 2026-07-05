# PR 0124 — Agent Runner Bridge Plan

## Summary

Plan the first executable Production Line PR: an Agent Runner Bridge that runs one configured Docker agent from Ariadne code through the existing runner substrate. Accepts `agent_name` + `task_prompt`, loads a real `agents/*.yml` config, invokes `docker_agent_adapter` through the existing adapter registry and local harness, captures a runtime proof artifact, and returns a structured bridge result. Executable-first, not docs-only. No full four-agent pipeline. No unattended git mutation rights.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 27e28f820f5d664dec31c836c04c4420fd058bcf |
| current_branch | 0124-agent-runner-bridge |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md contains Production Line Stream, PR 0124 Agent Runner Bridge, DOGFOOD MILESTONE, frozen streams, stop conditions |
| docker_agent_adapter_evidence | `services/runner/src/runner/docker_agent_adapter.py` present |
| agents_config_evidence | 9 agent configs present (architect.yml, coder.yml, plan-review.yml, precommit-review.yml, etc.) |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 1 Orchestrator
* expected PR slot: 0124 — Agent Runner Bridge
* why this PR is next: PR 0123 locked the Production Line roadmap and defined PR 0124 as the first executable PR; the next required capability is running one configured Docker agent from Ariadne code and capturing runtime proof
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime-captured proof is evidence

## PR 0123 / Production Line verification

| Check | Result |
|-------|--------|
| ROADMAP.md contains Production Line Stream | CONFIRMED ✓ |
| ROADMAP.md contains PR 0124 Agent Runner Bridge | CONFIRMED ✓ |
| ROADMAP.md contains DOGFOOD MILESTONE at PR 0131 | CONFIRMED ✓ |
| ROADMAP.md contains frozen-until-0136 list | CONFIRMED ✓ |
| ROADMAP.md contains stream stop conditions | CONFIRMED ✓ |
| PR 0123 precommit-review.yml exists, verdict pass | CONFIRMED ✓ |

Production Line roadmap is locked. PR 0124 proceeds.

## Existing runner substrate inventory

| Component | File | Role for bridge |
|-----------|------|----------------|
| `docker_agent_adapter.py` | Present | `run_docker_agent_execution(execution_request, *, executor, allow_docker)` — Docker agent adapter with dual-gate opt-in |
| `adapter_registry.py` | Present | `dispatch_execution()` — dispatcher selecting adapter by `requested_adapter` substring |
| `local_harness.py` | Present | `run_local_execution_harness()` — composes dispatcher + envelope + review boundary |
| `execution_envelope.py` | Present | `build_execution_envelope()` — normalizes artifacts and evidence from request/result |
| `proof_capture.py` | Present | `capture_proof()` — deterministic proof capture to `.ariadne/captures/` |
| `handoff_packet.py` | Present | `validate_handoff_packet()` — validates gate-ready handoff packets |
| `acceptance_criteria.py` | Present | `freeze_acceptance_criteria()` — deterministic acceptance criteria freeze |
| `gate_evidence.py` | Present | `build_gate_evidence_bundle()` — gate evidence bundle |
| `artifacts.py` | Present | `ArtifactStore` — content-addressed artifact storage |
| `docker_subprocess_executor.py` | Present | `run_docker_subprocess()` — real Docker subprocess executor (for production, not tests) |
| `noop_adapter.py` | Present | `run_noop_execution()` — no-op adapter for tests |

## Agent config inventory

| File | Role for bridge |
|------|----------------|
| `agents/architect.yml` | Config for architect agent |
| `agents/coder.yml` | Config for coder agent |
| `agents/plan-review.yml` | Config for plan-review agent |
| `agents/precommit-review.yml` | Config for precommit-review agent |
| `agents/chief-architect.yml` | Config for chief architect |

All configs follow a consistent YAML structure with `agents.root.model`, `agents.root.instruction`, `permissions`, and `toolsets`.

## Proposed Agent Runner Bridge contract

### New module

`services/runner/src/runner/agent_runner_bridge.py`

Contains:
- `AgentRunnerBridgeRequest` — input dataclass
- `AgentRunnerBridgeResult` — result dataclass
- `AgentRunnerBridgeArtifact` — captured artifact shape
- `AgentRunnerBridgeStatus` — status enum: `completed`, `blocked`, `failed`
- `run_agent_runner_bridge()` — main function
- `build_agent_runner_execution_request()` — build execution_request from agent config + task prompt
- `resolve_agent_config()` — load and validate agent config by `agent_name`
- Stable reason codes

### `run_agent_runner_bridge()` API

```python
def run_agent_runner_bridge(
    agent_name: str,
    task_prompt: str,
    agents_dir: str = "agents",
    workdir: str | None = None,
    allow_docker: bool = False,
) -> AgentRunnerBridgeResult:
```

The function:
1. Validate `agent_name` (reject path traversal, must match a file in `agents/`)
2. Resolve and load agent config from `agents/{agent_name}.yml`
3. Hash agent config content (SHA256)
4. Hash task prompt (SHA256)
5. Build `execution_request` dict with agent config fields
6. Dispatch through `run_local_execution_harness()` (which uses `dispatch_execution()` → `_dispatch_docker_agent()` → `run_docker_agent_execution()`)
7. If `allow_docker=False` and Docker is blocked: return blocked result with proof artifact showing blocked status
8. If `allow_docker=True`: attempt execution through the adapter pipeline
9. Capture runtime proof via `capture_proof()` — writes artifact to `output_dir`
10. Build and return `AgentRunnerBridgeResult`

### `AgentRunnerBridgeRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeRequest:
    agent_name: str
    task_prompt: str
    agents_dir: str = "agents"
    workdir: str | None = None
    allow_docker: bool = False
```

### `AgentRunnerBridgeArtifact` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeArtifact:
    artifact_ref: str                    # deterministic SHA256[:16]
    proof_capture_path: str | None       # path to captured proof artifact
    proof_capture_ref: str | None        # ref from proof_capture
    executor_output_path: str | None     # path to executor output
    has_proof: bool                      # true if runtime proof was captured
    proof_source: str = "runtime-captured"
```

### `AgentRunnerBridgeResult` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeResult:
    status: str                          # "completed" | "blocked" | "failed"
    reason_codes: tuple[str, ...]
    agent_name: str
    task_prompt_hash: str
    agent_config_path: str
    agent_config_hash: str
    docker_adapter_status: str           # "blocked" | "requires_review" | "failed" | "completed"
    exit_code: int | None
    captured_stdout_hash: str | None
    captured_stderr_hash: str | None
    captured_artifact: AgentRunnerBridgeArtifact | None
    proof_summary: str
    started_at: str | None               # deterministic injected clock or None
    finished_at: str | None              # deterministic injected clock or None
    details: str | None
```

## Runtime proof artifact contract

The captured proof artifact (via `capture_proof()`) must include:

```json
{
  "ariadne_capture_version": "1",
  "product_state_ref": "",
  "acceptance_criteria_ref": "",
  "runtime_capture_kind": "agent_runner_bridge",
  "phase_id": "agent-runner-bridge-0124",
  "run_id": "...",
  "payload": {
    "agent_name": "...",
    "task_prompt_hash": "...",
    "agent_config_hash": "...",
    "adapter_status": "...",
    "exit_code": -1,
    "stdout_hash": "...",
    "stderr_hash": "...",
    "adapter_result": { ... }
  },
  "summary": "Agent Runner Bridge proof capture",
  "tags": ["agent-runner-bridge", "runtime-captured"],
  "captured_at": null
}
```

Key proof principle: Agent output is not evidence. Runtime-captured proof is evidence.
- The task prompt hash and agent config hash are computed before execution
- The adapter result, stdout/stderr hashes, and exit code are captured at runtime
- The proof artifact is written by `capture_proof()`, not by the agent
- The `proof_source` is `"runtime-captured"` — not `"agent-reported"`

## Docker adapter boundary

- The bridge calls `run_local_execution_harness()` which calls `dispatch_execution()` which selects the docker adapter via the `"docker"` key in `requested_adapter`
- The docker adapter requires `allow_docker=True` in the execution request AND `ARIADNE_ALLOW_DOCKER_EXECUTION` env var
- No direct Docker CLI invocation in the bridge module
- No Docker commands in tests — use injected/fake executor
- When Docker is blocked/disabled, the bridge returns a structured `"blocked"` result with proof artifact
- The existing `docker_agent_adapter.py` `_DEFAULT_EXECUTOR` returns a blocked result — tests can inject a fake executor

## Agent config boundary

- Config resolved by `agent_name` → `agents/{agent_name}.yml`
- Path traversal rejected — allowed names must match `^[a-zA-Z0-9_\-]+$`
- Missing config → structured `"failed"` with reason code `missing_agent_config`
- Config content is hashed (SHA256) for proof, never modified
- No permissions inferred from agent output — only config fields used for execution_request construction

## Git mutation boundary

The bridge must not include any code that calls:
- `git add`, `git commit`, `git push`, `git checkout`, `git switch`, `git merge`, `git rebase`, `git reset`, `git clean`, `git tag`
- `gh pr create`, `gh release`

Agents must not receive unattended git mutation rights in PR 0124.

## Non-goals

PR 0124 does not implement:
- Full four-agent pipeline (PR 0127)
- Prompt composer (PR 0125)
- Verdict parser (PR 0126)
- Git boundary (PR 0128)
- `ariadne task` CLI (PR 0129)
- Run persistence in `.ariadne/runs/` (PR 0130)
- Retry/failure recovery loop (PR 0132)
- Model health live fallback (PR 0133)
- Run report (PR 0134)
- Parallel-safe queue (PR 0135)
- Decision Core / GRM (frozen until PR 0136)
- Context Warehouse (frozen until PR 0136)
- Eval harness / benchmarks (frozen until PR 0136)
- Faithfulness audit (frozen until PR 0136)
- Frontend (frozen until PR 0136)
- New product-iteration surface features (frozen until PR 0136)
- Any frozen stream capability

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/agent_runner_bridge.py` | NEW |
| `services/runner/tests/test_agent_runner_bridge.py` | NEW |

Default — not modified:
- `services/runner/src/runner/docker_agent_adapter.py` — NOT modified
- `services/runner/src/runner/proof_capture.py` — NOT modified
- `services/runner/src/runner/handoff_packet.py` — NOT modified
- `services/runner/src/runner/acceptance_criteria.py` — NOT modified
- `services/runner/src/runner/gate_evidence.py` — NOT modified
- `services/runner/src/runner/adapter_registry.py` — NOT modified
- `services/runner/src/runner/local_harness.py` — NOT modified
- `services/runner/src/runner/execution_envelope.py` — NOT modified
- `services/runner/src/runner/artifacts.py` — NOT modified
- `services/runner/src/runner/__init__.py` — NOT modified (unless strict import needed)
- `agents/*.yml` — NOT modified

## Forbidden files

- `services/task_intake/**` — out of scope for Production Line
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0123-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/` (configs not modified)
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `agent_runner_bridge.py` with:
   - `AgentRunnerBridgeRequest`, `AgentRunnerBridgeResult`, `AgentRunnerBridgeArtifact`, `AgentRunnerBridgeStatus`
   - Stable reason codes for: `missing_agent_config`, `unbounded_agent_name`, `missing_task_prompt`, `docker_blocked`, `execution_failed`, `proof_capture_failed`, `hidden_reasoning_not_allowed`
   - `resolve_agent_config()` — load and validate agent config
   - `build_agent_runner_execution_request()` — construct execution_request from config + prompt
   - `run_agent_runner_bridge()` — main function

2. Create `test_agent_runner_bridge.py` with focused tests (see test plan below).

## Test plan

| Class | Focus |
|-------|-------|
| `TestSuccessBlocked` | `allow_docker=False` → `"blocked"` with proof artifact |
| `TestSuccessWithExecutor` | Injected fake executor → `"completed"` with captured proof |
| `TestMissingAgentConfig` | Unknown agent_name → `"failed"` with `missing_agent_config` |
| `TestPathTraversal` | `agent_name="../../etc/passwd"` → `"failed"` with unbounded error |
| `TestEmptyTaskPrompt` | Empty prompt → `"failed"` |
| `TestTaskPromptHash` | Deterministic SHA256 hash of task prompt |
| `TestAgentConfigHash` | Deterministic SHA256 hash of agent config file content |
| `TestCapturedArtifact` | Proof artifact contains runtime-captured fields |
| `TestProofSource` | `proof_source == "runtime-captured"` |
| `TestNoDirectDocker` | No `subprocess.run`, `docker`, `docker compose` calls in bridge code |
| `TestNoGitMutation` | No `git add/commit/push` calls in bridge code |
| `TestAdapterBlockedStructure` | Blocked result has structured reason codes, not crash |
| `TestHideenReasoningRejected` | Hidden reasoning in task prompt → rejected |
| `TestDeterministicRefs` | Same inputs → same hashes and refs |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestPreservedAdapterTests` | Existing `test_docker_agent_adapter.py` still passes |
| `TestPreservedExecutionEnvelope` | Existing `test_execution_envelope.py` still passes |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_agent_runner_bridge.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_execution_envelope.py \
  services/runner/tests/test_backlog_surface.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "AgentRunnerBridge|agent_runner_bridge|run_agent_runner_bridge|runtime-captured|task_prompt_hash|agent_config_hash|unattended git mutation" services/runner/src services/runner/tests .project-memory/pr/0124-agent-runner-bridge 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|docker compose|gh pr create|git push|git commit|git add" services/runner/src/runner/agent_runner_bridge.py services/runner/tests/test_agent_runner_bridge.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `agent_runner_bridge.py` (new), `test_agent_runner_bridge.py` (new)
- **behavior drift**: `run_agent_runner_bridge()` runs one configured agent through existing substrate; no full pipeline
- **bridge API drift**: input/output shapes match the PLAN.md definitions
- **docker adapter boundary drift**: no direct Docker invocation; passes through existing adapter
- **git mutation drift**: no git command calls; no unattended git mutation rights
- **agent config drift**: configs loaded but not modified
- **proof drift**: captured proof includes runtime-captured fields, not agent narrative
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no full pipeline, no frozen stream, no `ariadne task` CLI
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- first executable Production Line PR ✓
- runs one configured agent through existing runner substrate ✓
- proof artifact is runtime-captured, not agent-reported ✓
- no direct Docker invocation ✓
- no unattended git mutation rights ✓
- agent configs loaded but not modified ✓
- no full four-agent pipeline ✓
- no prompt composer / verdict parser / git boundary / ariadne task CLI ✓
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

- Block if current branch is not `0124-agent-runner-bridge`
- Block if PR 0123 Production Line roadmap evidence is missing from ROADMAP.md — PASS: confirmed
- Block if `docker_agent_adapter.py` is missing — PASS: present
- Block if no real `agents/*.yml` config exists to use as input — PASS: 9 configs present
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if the plan invokes Docker directly instead of through `docker_agent_adapter` — PASS: uses adapter pipeline
- Block if the plan requires a real Docker daemon in tests — PASS: injected/fake executor
- Block if runtime proof artifact is missing or based only on agent narrative — PASS: runtime-captured
- Block if the plan implements the full four-agent pipeline — PASS: deferred to PR 0127
- Block if the plan implements prompt composer, verdict parser, git boundary, `ariadne task` CLI, or run persistence — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included
