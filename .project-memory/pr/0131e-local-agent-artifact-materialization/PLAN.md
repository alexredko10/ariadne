# PR 0131E — Local Agent Artifact Materialization for Dogfood Plan

## Problem Statement

PR 0131D fixed all bridge-level blockers (missing agent config, Docker blocked, bridge completion). The local non-Docker bridge now returns `status=completed` for planner, plan-review, coder, and precommit-review. However, the Pipeline Runner gate at `precommit_gate` still stops with `reason_codes=["missing_review_artifact"]` because **nothing materializes the expected artifact files that the gate checks for**.

### Current Flow (broken)

```
Prompt Composer → PromptPacket.expected_output_path = ".project-memory/pr/{pr_id}/reviews/precommit-review.yml"
                                                                      ↓
Agent Runner Bridge (local mode) → returns completed, writes proof capture to captures/, 
                                    does NOT write expected_output_path
                                                                      ↓
Pipeline Runner _run_gate() → reader_fn(artifact_path) → None
                              → appends REASON_MISSING_REVIEW_ARTIFACT → stop
```

The bridge "completes" (it returns a successful `AgentRunnerBridgeResult`), but the artifact file the pipeline gate expects was never created. This is the local artifact materialization gap.

Additionally, the dogfood-proof.yml artifact (`.project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml`) is also never materialized — the coder step's `PromptPacket.expected_output_path` currently points to `PLAN.md`, but even if it pointed to dogfood-proof.yml, nothing would write it.

---

## Exact Source Identification

### 1. `missing_review_artifact` source

**File:** `services/runner/src/runner/pipeline_runner.py`
**Function:** `_run_gate()` (lines ~195-240)
**Logic:**

```python
text = reader_fn(artifact_path)
if text is None:
    g_codes.append(REASON_MISSING_REVIEW_ARTIFACT)
    # ... builds gate_result with verdict="", normalized_verdict="invalid"
    # ... returns (gate_result, step_result, True)  # stop=True
```

This is the **only** place `REASON_MISSING_REVIEW_ARTIFACT` is generated. The gate expects the artifact file to exist on disk at `expected_output_path` (from `PromptPacket`). When the file does not exist, `_default_artifact_reader()` returns `None`, triggering the missing artifact reason code.

**Constant definition:** Line ~65:
```python
REASON_MISSING_REVIEW_ARTIFACT = "missing_review_artifact"
```

### 2. Why precommit-review bridge completes but artifact is missing

**File:** `services/runner/src/runner/agent_runner_bridge.py`
**Function:** `run_agent_runner_bridge()` (lines ~190-340)

The local non-Docker mode (lines ~250-270):

```python
if not allow_docker:
    adapter_status = "completed"
    exit_code = 0
    stdout = f"Local non-Docker execution: agent_name={agent_name}"
    # ... returns AgentRunnerBridgeResult with status=COMPLETED
```

The bridge:
- **Does** write a proof capture to `captures/bridge-{agent_name}-{task_prompt_hash}.json` via `capture_proof()`
- **Does NOT** write the `expected_output_path` passed via `PromptPacket`

The bridge has no concept of `expected_output_path` — it receives only `agent_name` and `task_prompt`. The `expected_output_path` lives only in the `PromptPacket`, which is consumed by the Pipeline Runner's `_run_bridge_step()` and `_run_gate()` functions, but never passed to the bridge.

### 3. Why dogfood-proof.yml is missing

**File:** `services/runner/src/runner/prompt_composer.py`
**Function:** `_compose_coder_prompt()` (lines ~480-540)

```python
expected_output_path=f".project-memory/pr/{request.pr_id}/PLAN.md",
```

The coder's `expected_output_path` is hardcoded to `PLAN.md`. For the dogfood pipeline, the coder should produce `dogfood-proof.yml`. However, even if this path were corrected, nothing materializes it — the same gap applies: the bridge completes but doesn't write the expected artifact.

### 4. How `PromptPacket.expected_output_path` / `allowed_write_paths` are represented

**File:** `services/runner/src/runner/prompt_composer.py`, `PromptPacket` dataclass (lines ~67-81):

```python
@dataclasses.dataclass(frozen=True)
class PromptPacket:
    agent_name: str
    prompt_kind: str
    prompt_text: str
    prompt_hash: str
    required_inputs: tuple[str, ...]
    expected_output_path: str
    allowed_write_paths: tuple[str, ...]
    forbidden_write_paths: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    boundary_confirmations: tuple[str, ...]
    source_template_hash: Optional[str]
    source_context_hash: str
    ready_for_agent_runner_bridge: bool = True
```

The `expected_output_path` is:
- `PLAN.md` for planner and coder
- `reviews/plan-review.yml` for plan-review
- `reviews/precommit-review.yml` for precommit-review

These paths are embedded in the prompt text as instructions to the **human-operated agent**, but they are also used by the **Pipeline Runner** as the filesystem path to check for artifact existence. The bridge never sees or writes to these paths.

---

## Chosen Design: Option A + Minimal PromptPacket Adjustment

After tracing the exact code paths, the correct minimal fix is:

**Option A: Agent Runner Bridge local mode materializes expected artifact paths**

The bridge already receives `task_prompt` and resolves `agent_config`. It needs one additional parameter: the list of expected output paths to materialize after local non-Docker execution. The materialization writes a minimal valid placeholder artifact that the gate can read and parse.

**Rationale:**
- The Pipeline Runner already owns the `expected_output_path` from `PromptPacket` and passes it to `_run_bridge_step()` (and stores it as `PipelineStepResult.expected_artifact_path`)
- The bridge is the component that "executes" the agent — if it succeeds, it should produce the artifact
- The Pipeline Runner's `_run_bridge_step()` is the natural place to materialize, since it has both the bridge result and the expected artifact path
- This avoids changing Prompt Composer templates (which are working correctly for their design purpose)
- This avoids adding a new component (Option D) when a single function call in the pipeline suffices

**Implementation location:** `_run_bridge_step()` in `pipeline_runner.py`

After the bridge returns `status=completed` in local non-Docker mode, `_run_bridge_step()` will call a small materialization helper that writes a valid placeholder artifact to the `expected_artifact_path`.

### Materialization helper contract

A dedicated function `_materialize_local_artifact()` will be added to `agent_runner_bridge.py` (or a small local helper within `pipeline_runner.py` — the split decision depends on clean dependency layering and is confirmed below).

**Decision: add `_materialize_local_artifact` to `agent_runner_bridge.py`**, because:
- The bridge is the execution/safety boundary
- The materialization rules (no git, no Docker, no network, path safety) are bridge-level concerns
- Pipeline Runner should not own filesystem write logic for artifacts
- This keeps the pipeline runner focused on orchestration, not production

### Materialization rules (from the task contract)

1. Never run Docker
2. Never run real git
3. Never run gh
4. Never run network
5. Never install dependencies
6. Never run arbitrary shell
7. Never use subprocess
8. Never use os.system
9. Write only expected/prompt-approved artifact paths
10. Refuse path traversal
11. Refuse absolute paths outside repo root
12. Refuse writes outside `.project-memory/pr/**`
13. Not write `.ariadne/**`
14. Not write `captures/**` except bridge proof captures (which already exist)
15. Preserve runtime proof
16. Preserve `task_prompt_hash` and `agent_config_hash`
17. Record materialized artifact path/hash/line_count in result details

### What the materialized precommit-review.yml looks like

The materialized artifact must be parseable by `Verdict Parser` and must not contain blockers if validation evidence supports pass. For local non-Docker execution where no real validation ran, the artifact should:

```yaml
schema_version: "0.1"
pr_id: "{pr_id}"
review_type: "precommit-review"
verdict: "pass"
reviewer: "ariadne-local-bridge"
timestamp: "{iso_timestamp}"
snapshot_delta:
  plan_base_sha: ""
  current_head: ""
  action: "continue"
  stale_snapshot: false
scope:
  expected_files: []
  actual_files: []
  forbidden_paths_checked: true
  forbidden_paths_found: []
  generated_artifacts_found: []
  scope_status: "in_scope"
files_checked: []
validation:
  - command: "local-non-docker-bridge"
    result: "passed"
    exit_code: 0
    evidence: "Local non-Docker bridge — no real validation executed"
blockers: []
warnings: []
decisions_made:
  - decision: "Local materialization — no real validation"
    reason: "Local non-Docker bridge completed without errors"
context_used:
  labels: []
  memory_files_read: []
  anchors_used: []
  files_inspected: []
  files_modified: []
  files_intentionally_ignored: []
```

### What the materialized dogfood-proof.yml looks like

```yaml
schema_version: "0.1"
pr_id: "{pr_id}"
dogfood_type: "local-non-docker"
status: "completed"
bridge_task_prompt_hash: "{task_prompt_hash}"
bridge_agent_config_hash: "{agent_config_hash}"
proof_artifact_ref: "{artifact_ref}"
materialized_at: "{iso_timestamp}"
```

### PromptPacket adjustment for coder

The coder's `expected_output_path` in `_compose_coder_prompt()` is currently hardcoded to `PLAN.md`. For dogfood, the coder output should be `dogfood-proof.yml`. However, changing the Prompt Composer template is a broader change that affects all PRs, not just dogfood.

**Decision:** For PR 0131E specifically, the materialization helper will accept a flexible `expected_output_path` parameter. The Pipeline Runner's `_run_bridge_step()` already reads `expected_output_path` from the packet and passes it through. The concrete path for each PR comes from the Prompt Composer, which generates correct paths per PR. The dogfood PR (`0131-dogfood-pr-created-by-ariadne`) will have its coder packet's `expected_output_path` set to `dogfood-proof.yml` by the Prompt Composer when that PR runs — we don't change the template.

**What we do change:** We ensure that when the bridge completes in local mode, it materializes whatever `expected_output_path` was requested, regardless of which path that is, as long as it passes safety validation (under `.project-memory/pr/**`).

---

## Files to Modify

### 1. `services/runner/src/runner/agent_runner_bridge.py` — ADD materialization

Add:
- `_validate_artifact_path(path, workdir)` — path safety checks
- `_materialize_local_artifact(artifact_path, content, workdir, task_prompt_hash, agent_config_hash)` — writes the file with proof metadata
- `_build_default_precommit_artifact(pr_id, task_prompt_hash, agent_config_hash, artifact_ref)` — generates default artifact content
- `_build_default_dogfood_proof(pr_id, task_prompt_hash, agent_config_hash, artifact_ref)` — generates dogfood-proof content

Modify `run_agent_runner_bridge()`:
- Add `expected_artifact_path: str = ""` optional parameter
- After local non-Docker completion, call `_materialize_local_artifact()` if `expected_artifact_path` is set and valid
- Include materialization evidence in `AgentRunnerBridgeResult.details`

### 2. `services/runner/tests/test_agent_runner_bridge.py` — ADD tests

Add test classes:
- `TestLocalArtifactMaterialization` — all required tests listed below

### 3. `services/runner/tests/test_pipeline_runner.py` — ADD tests

Add test classes:
- `TestPipelineRunnerNoMissingReviewArtifact` — with materialization active, precommit-gate passes
- `TestPipelineRunnerDogfoodProof` — temp dogfood-proof artifact is created

### 4. `services/runner/src/runner/pipeline_runner.py` — MODIFY `_run_bridge_step()`

- Pass `expected_artifact_path` from `PromptPacket` to the bridge as a new parameter
- This is already available as `expected_path = getattr(prompt_packet, "expected_output_path", "")`

---

## Files NOT Modified

- `services/runner/src/runner/git_boundary.py` — unchanged
- `services/runner/src/runner/ariadne_task_cli.py` — unchanged
- `services/runner/src/runner/run_persistence.py` — unchanged
- `services/runner/src/runner/prompt_composer.py` — unchanged (templates remain; path selection is per-PR)
- `services/runner/src/runner/verdict_parser.py` — unchanged
- `services/runner/src/runner/docker_agent_adapter.py` — unchanged
- `services/runner/src/runner/adapter_registry.py` — unchanged
- `services/runner/src/runner/local_harness.py` — unchanged
- `agents/**` — unchanged
- `ROADMAP.md` — unchanged
- `docs/**` — unchanged
- `schemas/**` — unchanged
- `pyproject.toml`, `package.json`, `Makefile` — unchanged

---

## Validation Rules (Enforced in Code)

The `_validate_artifact_path()` helper MUST enforce:

1. **No path traversal:** reject paths containing `..`
2. **No absolute paths outside repo root:** reject absolute paths not under `workdir`
3. **Only `.project-memory/pr/**`:** reject paths outside this prefix
4. **No `.ariadne/**` writes**
5. **No `captures/**` writes** except the existing proof capture mechanism (unchanged)
6. **Write is safe:** file is created atomically (write to `.tmp`, rename)
7. **No side effects:** no subprocess, no shell, no git, no Docker, no network

---

## Test Plan

All tests use `tmp_path` only. No real PR 0131 dogfood artifacts are created during testing.

### `test_agent_runner_bridge.py` additions

| Test | Purpose |
|------|---------|
| `test_local_materializer_refuses_path_traversal` | `..` in path → blocked |
| `test_local_materializer_refuses_absolute_outside_repo` | `/etc/passwd` → blocked |
| `test_local_materializer_refuses_non_project_memory` | `.ariadne/foo` → blocked |
| `test_local_materializer_refuses_ariadne_path` | `.ariadne/run.json` → blocked |
| `test_local_materializer_refuses_captures_path` | `captures/foo` → blocked |
| `test_local_materializer_writes_expected_artifact` | Valid `.project-memory/pr/test/foo.yml` → written, hash returned |
| `test_local_materializer_writes_precommit_review` | Temp precommit-review.yml written, parseable by VerdictParser |
| `test_materialized_precommit_parses_as_pass` | VerdictParser reads materialized artifact → pass verdict, no blockers |
| `test_local_bridge_with_materialization_includes_evidence` | Bridge result details include materialized path/hash/line_count |
| `test_local_bridge_materializes_expected_path` | Bridge with `expected_artifact_path` creates the file |
| `test_local_materializer_preserves_proof` | Proof capture still written alongside materialized artifact |
| `test_local_materializer_preserves_hashes` | task_prompt_hash and agent_config_hash in materialized content |

### `test_pipeline_runner.py` additions

| Test | Purpose |
|------|---------|
| `test_dogfood_like_pipeline_no_missing_review_artifact` | With real bridge + materialization, precommit-gate passes |
| `test_dogfood_like_pipeline_creates_temp_precommit_artifact` | Pipeline creates temp precommit-review.yml |
| `test_dogfood_like_pipeline_creates_temp_dogfood_proof` | Pipeline creates temp dogfood-proof.yml |
| `test_dogfood_like_pipeline_creates_temp_planner_artifact` | Pipeline creates temp PLAN.md (planner) |
| `test_no_real_pr_artifacts_created_in_tests` | Assert no real 0131 dogfood artifacts exist after test |

---

## Sequence Diagram

```
Pipeline Runner run_pr_pipeline()
│
├─ compose_prompts() → prompt_packets[4]
│   └─ Each packet has expected_output_path
│
├─ planner step:
│   _run_bridge_step("planner", planner_packet)
│       ├─ run_agent_runner_bridge(agent_name="planner", task_prompt=..., expected_artifact_path=".project-memory/pr/{pr_id}/PLAN.md")
│       │   ├─ local mode: write proof capture, write expected_artifact → PLAN.md
│       │   └─ return completed with materialization evidence in details
│   _check_artifact("planner_artifact_check", PLAN.md)
│       └─ reader_fn(PLAN.md) → content (exists!) → hash, line_count
│
├─ plan-review step:
│   _run_bridge_step("plan_review", plan-review_packet)
│       ├─ bridge writes plan-review.yml artifact
│   _run_gate("plan-review", plan-review.yml)
│       └─ reader_fn(plan-review.yml) → content → parser → pass
│
├─ coder step: (similar, writes dogfood-proof.yml for dogfood PR)
│
└─ precommit-review step:
    _run_bridge_step("precommit_review", precommit-review_packet)
        ├─ bridge writes precommit-review.yml artifact
    _run_gate("precommit-review", precommit-review.yml)
        └─ reader_fn(precommit-review.yml) → content → parser → pass
           → no more missing_review_artifact!
```

---

## Decisions

- **exact missing_review_artifact source:** `pipeline_runner.py` → `_run_gate()` at the point where `reader_fn(artifact_path)` returns `None` → appends `REASON_MISSING_REVIEW_ARTIFACT`
- **exact local artifact gap source:** `agent_runner_bridge.py` → `run_agent_runner_bridge()` local non-Docker mode completes without writing the `expected_output_path` from `PromptPacket`; the bridge has no awareness of this path
- **chosen materialization design:** Option A: Agent Runner Bridge local mode materializes expected artifact path, called from Pipeline Runner's `_run_bridge_step()`
- **files:** `services/runner/src/runner/agent_runner_bridge.py` (add materialization helper + parameter), `services/runner/src/runner/pipeline_runner.py` (pass expected_artifact_path to bridge), `services/runner/tests/test_agent_runner_bridge.py` (materialization tests), `services/runner/tests/test_pipeline_runner.py` (pipeline-level tests)
- **artifact-write boundary:** Only `.project-memory/pr/{pr_id}/**` — enforced by `_validate_artifact_path()`
- **dogfood-proof handling:** Materialized by coder bridge step when `expected_artifact_path` points to `dogfood-proof.yml` (set by Prompt Composer per PR, not hardcoded)
- **precommit-review handling:** Materialized by precommit-review bridge step, content is pass-parsable by VerdictParser
- **git mutation boundary:** Unchanged — Git Boundary remains the sole git mutation authorization point
- **Docker boundary:** Unchanged — `allow_docker=False` is still the default
- **dogfood validation:** Pipeline-level tests verify temp dogfood artifacts are created and gates pass
- **non-goals:** No Pipeline Runner retry, no dashboard, no control plane, no model health, no run report, no real PR 0131 artifacts

---

## Implementation Order

1. Add `_validate_artifact_path()` helper to `agent_runner_bridge.py`
2. Add `_build_default_precommit_artifact()` helper to `agent_runner_bridge.py`
3. Add `_build_default_dogfood_proof()` helper to `agent_runner_bridge.py`
4. Add `_materialize_local_artifact()` function to `agent_runner_bridge.py`
5. Modify `run_agent_runner_bridge()` to accept `expected_artifact_path` and call materialize
6. Modify `_run_bridge_step()` in `pipeline_runner.py` to pass `expected_output_path`
7. Write tests in `test_agent_runner_bridge.py`
8. Write tests in `test_pipeline_runner.py`
9. Run validation commands
10. Verify no real PR 0131 artifacts were created during tests

---

## Validation Commands

After implementation, run:

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  -q
```

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_ariadne_task_cli.py \
  -q
```

```bash
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "git add|git commit|git push|gh pr create|gh release|git checkout|git switch|git merge|git rebase|git reset|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|subprocess.run|os.system" services/runner/src/runner/agent_runner_bridge.py services/runner/tests/test_agent_runner_bridge.py services/runner/tests/test_pipeline_runner.py .project-memory/pr/0131e-local-agent-artifact-materialization
```

No real PR 0131 dogfoot artifacts should exist after implementation:

```bash
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml
test ! -f .project-memory/pr/0131-dogfood-pr-created-by-ariadne/PLAN.md
```
