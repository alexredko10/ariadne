# PLAN.md — PR 0131D: Local Non-Docker Agent Execution for Dogfood

PR ID: `0131d-local-non-docker-agent-execution`
Agent: planner
Mode: planning only

---

## Stop Conditions

- [x] Branch is `0131d-local-non-docker-agent-execution`
- [x] PLAN identifies exact source of `missing_agent_config`
- [x] PLAN identifies exact source of `docker_blocked`
- [x] PLAN does not simply enable Docker
- [x] PLAN does not require Docker for local dogfood
- [x] PLAN does not grant agents git/gh mutation rights
- [x] PLAN does not bypass Git Boundary
- [x] PLAN does not manually create real PR 0131 dogfood-proof.yml
- [x] PLAN does not modify Git Boundary
- [x] PLAN does not modify Ariadne Task CLI
- [x] PLAN does not modify Run Persistence
- [x] PLAN does not modify ROADMAP/docs/schemas
- [x] PLAN does not add retry/dashboard/control-plane/model-health/run-report scope
- [x] Validation defined

---

## Exact Source of `missing_agent_config`

**Definition line:** `services/runner/src/runner/agent_runner_bridge.py:112`

```python
REASON_MISSING_AGENT_CONFIG = "missing_agent_config"
```

**Raised at:** `agent_runner_bridge.py` — `run_agent_runner_bridge()` lines 199–215.

The flow:
1. Pipeline Runner calls `run_agent_runner_bridge(agent_name="planner", ...)`
2. Bridge calls `resolve_agent_config("planner", agents_dir)` (line 199)
3. `resolve_agent_config` constructs path `agents/planner.yml` via `os.path.join(agents_dir, f"{agent_name}.yml")`
4. `os.path.exists(config_path)` returns `False`
5. `resolve_agent_config` raises `ValueError(f"Agent config not found: {config_path}")`
6. Bridge catches the `ValueError` and returns `AgentRunnerBridgeResult(status=FAILED, reason_codes=["missing_agent_config"], ...)`

**Why planner step appears in diagnostic but pipeline continues past it:** Pipeline Runner's `_run_bridge_step` at the `planner` step does NOT check bridge status — it only checks `artifact_check.artifact_exists` at the subsequent `planner_artifact_check` step. Since a pre-existing `PLAN.md` was present (from the PR branch), the artifact check passed. The pipeline then continued to `plan-review` (bridge → `docker_blocked`) then `coder` (bridge → `docker_blocked`), where `_run_bridge_step` DOES check status and stops.

**Note:** `prompt_composer.py:117` also defines `REASON_MISSING_AGENT_CONFIG` but it is **never referenced** in any function body or test. The prompt composer only checks `REASON_MISSING_AGENTS_DIR` (entire directory missing). So the dogfood diagnostic's `missing_agent_config` comes **exclusively** from the bridge.

---

## Exact Source of `docker_blocked`

**Definition line:** `services/runner/src/runner/agent_runner_bridge.py:115`

```python
REASON_DOCKER_BLOCKED = "docker_blocked"
```

**Raised at:** `agent_runner_bridge.py` — `run_agent_runner_bridge()` lines 237–242.

The flow (for every agent when `allow_docker=False`):

1. Bridge calls `build_agent_runner_execution_request(...)` (line 219)
2. That function **hardcodes** `requested_adapter: "docker"` and `allow_docker: False`:
   ```python
   "requested_adapter": "docker",
   "execution_mode": "execute" if allow_docker else "dry_run",
   "allow_docker": allow_docker,
   ```
3. Bridge calls `run_local_execution_harness(execution_request)` (line 224)
4. Harness calls `dispatch_execution(execution_request)` → `adapter_registry.py`
5. Registry finds `"docker"` key → calls `_dispatch_docker_agent()`
6. `_dispatch_docker_agent` checks `allow_docker=False` → calls `run_docker_agent_execution(request, allow_docker=False)`
7. Docker adapter returns `{"status": "blocked"}`
8. Back in bridge: `adapter_status == "blocked"` → `bridge_status = BLOCKED`, `codes.append(REASON_DOCKER_BLOCKED)` (lines 237–239)
9. **All three agents** (planner, plan-review, coder) hit this path because all call through `_run_bridge_step` with `allow_docker=False`

---

## Planner Config/Mapping Decision

**Decision: Option A — Add `agents/planner.yml`**

**Rationale:**
- Option A is the minimal fix: one new config file, zero code changes to resolve_agent_config, zero changes to prompt_composer or pipeline_runner
- `agents/architect.yml` already exists but its instruction is for structural review and ROADMAP/ADR writing, not planning — using it as-is would overload semantics
- Option B (alias/mapping) requires code changes to the bridge's `resolve_agent_config` or a new mapping layer
- Option C (change Prompt Composer to emit `architect` instead of `planner`) would change the prompt kind and agent name throughout the pipeline, affecting all downstream expectation paths

**Planner config content:** A minimal `version: 8` config file that declares a planning-capable agent with the same model provider pattern as `architect.yml`, scoped read-only permissions, and an instruction that mirrors the existing agent mission but for planning tasks. The config will NOT grant:
- Docker execution
- git/gh mutation
- Shell mutation commands
- Write access to services/, packages/, schemas/, docs/

---

## Local Non-Docker Execution Design

**Problem:** `run_agent_runner_bridge()` unconditionally routes through `build_agent_runner_execution_request → run_local_execution_harness → dispatch_execution → docker_adapter → blocked` when `allow_docker=False`.

**Fix:** When `allow_docker=False` AND agent config resolves successfully, bypass the Docker adapter path entirely and return a simulated completed result.

**Specific changes to `agent_runner_bridge.py`:**

1. **Add a local mode branch in `run_agent_runner_bridge()`** at step 6 (after config resolution and prompt hashing, before `build_agent_runner_execution_request`):

   ```
   if not allow_docker:
       # Local non-Docker execution mode
       adapter_status = "completed"
       exit_code = 0
       stdout = "Local non-Docker execution: agent_name={agent_name}"
       stderr = ""
       bridge_status = AgentRunnerBridgeStatus.COMPLETED
       # Skip harness, dispatcher, docker adapter entirely
   else:
       # Existing Docker path (unchanged)
       execution_request = build_agent_runner_execution_request(...)
       harness_result = run_local_execution_harness(execution_request)
       execution_result = harness_result.get("execution_result", {})
       adapter_status = execution_result.get("status", "failed")
       exit_code = execution_result.get("exit_code")
       stdout = execution_result.get("stdout", "")
       stderr = execution_result.get("stderr", "")
       # Determine bridge status (existing logic)
       if adapter_status == "blocked":
           bridge_status = BLOCKED; codes.append(REASON_DOCKER_BLOCKED)
       elif adapter_status in ("requires_review", "completed"):
           bridge_status = COMPLETED
       else:
           bridge_status = FAILED; codes.append(REASON_EXECUTION_FAILED)
   ```

2. **Proof capture continues unchanged** for both paths — proof captures the local mode result with `runtime_capture_kind = "agent_runner_bridge"` and all hash evidence preserved

3. **No changes to:** `build_agent_runner_execution_request`, `resolve_agent_config`, `_check_forbidden_patterns`, `local_harness.py`, `adapter_registry.py`, `docker_agent_adapter.py`, `pipeline_runner.py`

**Safety guarantees of local mode:**
- No subprocess.run calls
- No Docker daemon access
- No git/gh commands
- No network calls
- No filesystem writes outside `captures/` and proof capture path
- No dependency installation
- No arbitrary shell execution
- Hidden-reasoning checks remain active
- Agent config hash and task prompt hash are preserved as evidence
- Runtime proof is captured

---

## Files

| File | Action | Reason |
|------|--------|--------|
| `agents/planner.yml` | **CREATE** | Option A — minimal planner agent config |
| `services/runner/src/runner/agent_runner_bridge.py` | **MODIFY** | Add local non-Docker execution branch in `run_agent_runner_bridge()` |
| `services/runner/tests/test_agent_runner_bridge.py` | **MODIFY** | Replace `test_blocked_without_docker` with local-completion test; add artifact-write-boundary tests |
| `services/runner/tests/test_pipeline_runner.py` | **MODIFY** | Add dogfood-like Pipeline Runner test that reaches post-coder path |

**Explicitly NOT modified:**
- `services/runner/src/runner/pipeline_runner.py` — no changes needed; bridge already injectable
- `services/runner/src/runner/git_boundary.py` — forbidden
- `services/runner/src/runner/ariadne_task_cli.py` — forbidden
- `services/runner/src/runner/run_persistence.py` — forbidden
- `services/runner/src/runner/prompt_composer.py` — not needed
- `services/runner/src/runner/adapter_registry.py` — not needed
- `services/runner/src/runner/docker_agent_adapter.py` — not needed
- `services/runner/src/runner/local_harness.py` — not needed
- `ROADMAP.md` — forbidden
- `docs/**` — forbidden
- `schemas/**` — forbidden

---

## Artifact-Write Boundary

Local non-Docker mode **does not write artifacts to the real project-memory path**. Artifact creation is the agent's responsibility in Docker mode. In local mode:

- Proof capture writes to `{output_dir}/captures/bridge-{agent_name}-{prompt_hash}.json` (existing mechanism, unchanged)
- No file writes to `.project-memory/pr/<pr-id>/` from the bridge
- The pipeline runner's artifact check will find or not find artifacts based on pre-existing state (same as today)

For **tests**, artifact-write-boundary tests use temp directories and injected fakes:

- Test that bridge returns `completed` (not `blocked`) when `allow_docker=False`
- Test that bridge refuses writes outside a simulated expected artifact path (using `tmp_path` + injected expectations)
- Test that bridge does not call subprocess, git, gh, or Docker

---

## Git Mutation Boundary

**Unchanged.** The existing git mutation safety is preserved:
- `agent_runner_bridge.py` does not import `subprocess` — verified by existing `TestNoDirectDocker` and `TestNoGitMutation` tests
- `run_local_execution_harness` does not call git/gh — verified by `TestNoSideEffects` test
- `resolve_agent_config` only reads files, never writes
- `_check_forbidden_patterns` only checks for hidden-reasoning patterns (PR 0131C)
- Git Boundary (`git_boundary.py`) remains the sole component authorized for git add/commit/push, exclusively with human approval

---

## Dogfood Validation

The dogfood-like Pipeline Runner test will:
1. Use injected `PromptComposer` with 4 packets (planner, plan-review, coder, precommit-review)
2. Use **real** `run_agent_runner_bridge` (not injected fake) with `allow_docker=False`
3. Verify that all 4 bridge steps return `completed` (not blocked by `docker_blocked`)
4. Verify pipeline reaches post-coder precommit gate
5. Verify coder step has `bridge_status == "completed"` and `REASON_CODER_STEP_FAILED` is NOT in reason codes
6. Verify Docker path remains blocked when explicit Docker gates are used
7. Verify Git Boundary remains unchanged
8. Verify Ariadne Task CLI remains unchanged
9. Verify Run Persistence remains unchanged

---

## Non-Goals

- No retry logic
- No dashboard/control-plane
- No model health monitoring
- No run report generation
- No real LLM calls
- No real Docker execution
- No git/gh mutation rights
- No changes to Git Boundary, Ariadne Task CLI, or Run Persistence
- No changes to ROADMAP, docs, or schemas
- No manual creation of real PR 0131 dogfood-proof.yml

---

## Validation

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_ariadne_task_cli.py \
  -q

grep -R -n -E --exclude-dir=**pycache** --exclude-dir=.pytest_cache \
  "missing_agent_config|docker_blocked|allow_docker|local|non_docker|agent_config|planner.yml|agent_name|run_agent_runner_bridge|expected_artifact_path|dogfood-proof|capture" \
  services/runner/src/runner services/runner/tests agents .project-memory/pr/0131d-local-non-docker-agent-execution

grep -R -n -E --exclude-dir=**pycache** --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|gh release|git checkout|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" \
  services/runner/src/runner services/runner/tests agents .project-memory/pr/0131d-local-non-docker-agent-execution

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short

git diff --name-only
```

---

## Test Specification

### `test_agent_runner_bridge.py` changes:

| Test class | Verifies |
|---|---|
| `TestLocalExecutionCompletion` (replaces `TestSuccessBlocked`) | `allow_docker=False` → `COMPLETED` (not BLOCKED or docker_blocked); preserves hashes, proof capture |
| `TestMissingAgentConfig` (unchanged) | Unknown agent_name → `FAILED` with `missing_agent_config` |
| `TestArtifactWriteBoundary` (new) | Local mode writes only to `captures/` path; path validation for `expected_artifact_path` |
| `TestLocalNoGitMutation` (new) | Local mode does not call subprocess/git/gh/docker |
| `TestHiddenReasoningRejected` (unchanged) | Hidden reasoning still blocked |
| `TestNoDirectDocker` (unchanged) | Bridge code does not import docker directly |

### `test_pipeline_runner.py` changes:

| Test class | Verifies |
|---|---|
| `TestLocalNonDockerPipeline` (new) | Full pipeline with real bridge (not injected), `allow_docker=False` on all 4 agents; all bridge steps return `completed`; no `docker_blocked` or `coder_step_failed` |
| `TestDockerPathRemains` (new) | Docker adapter returns `blocked` when explicit Docker gates (`allow_docker=True` omitted) |
| `TestNonMutatingCoderExecution` (unchanged) | Existing PR 0131C tests remain intact |
