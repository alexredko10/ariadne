# Ariadne Roadmap

## PR Cadence & Track Architecture

This roadmap describes two kinds of work:

- **Substrate/execution PRs** — multi-step coherent units that deliver backend
  contracts, runner behavior, artifact contracts, schema changes, or platform
  infrastructure.
- **UX-hardening PRs** — frontend-only page additions that improve local
  testing ergonomics. These are explicitly gated and may only proceed under
  architect sign-off.

**PR batching policy (effective PR 0094 onward):** Every PR must deliver a
coherent multi-step substrate capability unit. Single isolated UI control/
toggle/copy PRs must be merged into an adjacent backlog item or rejected by
the planner. The planner must block PRs that touch only
`services/task_intake/src/task_intake/server.py` for isolated UI additions
unless architect sign-off is cited.

**Drift-detection heuristic:** If 4 or more consecutive PRs touch only one
runtime UI file (`services/task_intake/src/task_intake/server.py`) and
introduce no backend contract, runner behavior, artifact contract, or schema
change, architect review is required before next PR planning.

---

## Roadmap Alignment Gate

From PR 0094 onward, every new PR must pass a roadmap alignment check before
planning is approved.

### Planner responsibilities

- Read ROADMAP.md and ADR 0011 before writing PLAN.md.
- Identify the current roadmap track.
- Identify the expected next PR number or accepted batch slot.
- State why the proposed PR is the next coherent roadmap step.
- State whether the PR is substrate/execution, stabilization/acceptance, or
  explicitly architect-approved exception.
- Reject or block any PR that is a single isolated frontend-only UI/copy/
  control change unless explicit architect sign-off is cited.

### PLAN.md required section

Every PLAN.md from PR 0094 onward must include the following section:

```markdown
### Roadmap alignment

* roadmap track:
* expected PR slot:
* why this PR is next:
* batching policy check:
* drift heuristic check:
* architect sign-off required: yes | no
* architect sign-off reference if required:
```

### Plan-review responsibilities

- Block if PLAN.md lacks the Roadmap alignment section.
- Block if the PR does not match the active ROADMAP.md sequence.
- Block if batching policy is not satisfied.
- Block if drift heuristic triggers and no architect sign-off is cited.
- Block if the PR continues a closed track.

### Implementation and precommit-review responsibilities

- Implementation follows the approved PLAN.md only.
- Precommit-review verifies no implementation drift beyond approved PLAN.md
  scope.
- Roadmap reinterpretation must not happen during implementation.

---

## Phase 0: Architecture Contracts

**Deliverables:** Platform schemas, ADRs, architecture documentation.
**Status:** Complete in PR 0041.

- `schemas/*.yml` — 13 platform artifact schemas
- `docs/adr/0005-rubrics-as-runtime-contracts.md`
- `docs/adr/0006-model-replaceability.md`
- `docs/adr/0007-cached-repository-understanding.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`

**Acceptance criteria:**
- All 13 schemas parse as valid YAML with `schema_version: "0.1"`
- All ADRs accepted
- Architecture document covers all 19 sections
- No model-specific logic, no runtime implementation

**Dependencies:** None.
**Estimated PR count:** 1.
**Risks:** None — contract-only.

---

## Local Interaction UX Track (CLOSED)

**What this track delivered:** A complete local browser interaction page at
`GET /` served by `services/task_intake/src/task_intake/server.py` that lets
an operator submit a task, select a runner (noop default, docker-agent opt-in),
inspect the result, summary card, execution trace, structured view, raw JSON,
run history, and generate session reports, feedback, run reports, and confusion
signals.

**PRs:** PR 0079 through PR 0092 (14 PRs).
- PR 0079 — First user-facing local interaction
- PR 0080 — Local result structured view
- PR 0081 — Explicit local runner selection
- PR 0082 — Visible local execution trace
- PR 0083 — Local run summary card
- PR 0084 — Local user test feedback panel
- PR 0085 — Guided local user test scenarios
- PR 0086 — Local user test session report
- PR 0087 — Copy/export local run report
- PR 0088 — Local run history in page
- PR 0089 — Local empty and error states
- PR 0090 — First-time user onboarding panel
- PR 0091 — Manual acceptance checklist
- PR 0092 — Local user confusion signals

**Evidence for endpoint:** Project-memory PR directories exist for PR 0079
through PR 0092. No PR 0093 or higher UX-track PRs exist in project memory.
`git log` is not available in the current shell environment to confirm commit
SHAs.

**Status: CLOSED.** The Local Interaction page is feature-complete for manual
local testing purposes. No further single-feature frontend-only PRs against
this page without explicit architect sign-off.

---

## Execution/Substrate Track (Resumed at PR 0094)

**Current substrate state (verified from filesystem):**

| Component | File | Status |
|---|---|---|
| No-op runner adapter | `services/runner/src/runner/noop_adapter.py` | Present — deterministic dry_run/preview only |
| Docker agent adapter | `services/runner/src/runner/docker_agent_adapter.py` | Present — opt-in boundary, returns blocked without allow_docker=True |
| Adapter registry | `services/runner/src/runner/adapter_registry.py` | Present — dispatches noop or docker |
| Execution envelope | `services/runner/src/runner/execution_envelope.py` | Present — deterministic artifact/evidence normalization |
| Human review boundary | `services/runner/src/runner/review_boundary.py` | Present — deterministic approval/review state interpretation |
| Local harness | `services/runner/src/runner/local_harness.py` | Present — composes dispatcher, envelope, review boundary |
| Content-addressed artifact store | `services/runner/src/runner/artifacts.py` | Present — stores by sha256; writes to filesystem |
| Task intake server | `services/task_intake/src/task_intake/server.py` | Present — serves HTML page + API endpoints |
| Execution handoff | `services/task_intake/src/task_intake/execution_handoff.py` | Present — mock execution handoff |

### Substrate gaps (to be closed PR 0094–0100)

1. **Real Docker-backed execution** — `docker_agent_adapter.py` requires
   `allow_docker=True` + an injected executor. No actual Docker daemon
   invocation exists.
2. **Run artifact collection** — the artifact store exists as a library but
   is not wired into the execution pipeline. Artifacts are not persisted from
   real runs.
3. **Human review boundary for real runs** — `review_boundary.py` is a pure
   deterministic function. It is not wired into a persistence or notification
   path for real multi-step runs.
4. **Stabilization/acceptance pass** — end-to-end flow must be verified with
   real execution conditions (not just mock/noop).

---

## PR Sequence: PR 0094 to PR 0100

Gap consolidation is prioritized to merge dependency-graph-adjacent work into
the fewest coherent PRs.

### PR 0094 — Docker Execution Wiring

- Wire `docker_agent_adapter.py` into a real subprocess/executor that invokes
  Docker via `subprocess.run` or equivalent.
- Inject real executor into `run_docker_agent_execution` from the harness or
  entrypoint.
- Add minimal smoke test that the new executor path is callable (no daemon
  required in CI).

**Backend contract change:** Yes — executor wiring.
**Runner behavior change:** Yes — Docker adapter no longer always blocked.
**Artifact contract change:** No.
**Schema change:** No.

### PR 0095 — Run Artifact Persistence

- Wire `ArtifactStore` into the execution pipeline so artifacts produced
  during a run are persisted to a configured store root.
- Expose stored artifact metadata in the execution envelope.
- Add test that artifacts survive across run boundaries in a local store.

**Backend contract change:** Yes — artifact store integration.
**Runner behavior change:** Yes — artifacts are persisted, not only in-memory.
**Artifact contract change:** No (existing schema).
**Schema change:** No.

### PR 0096 — Human Review Persistence Path

- Wire an approval/review record into the execution pipeline so that
  `review_boundary.py` decisions can be persisted and later retrieved.
- Add a lightweight in-memory review store (file-backed or ephemeral) that
  records review decisions and makes them available for downstream
  consumption.
- Add test that review decisions are storable and retrievable.

**Backend contract change:** Yes — review storage path.
**Runner behavior change:** No.
**Artifact contract change:** No.
**Schema change:** No.

### PR 0097 — Local Docker End-to-End Smoke

- Combine PR 0094 + PR 0095 + PR 0096 into a local end-to-end smoke test that
  exercises the full substrate path: task intake → execution request → Docker
  executor (if Docker available) or noop fallback → artifact persistence →
  review boundary.
- Document the local end-to-end flow in a README or quickstart.
- Add a smoke CLI command that runs the full loop.

**Backend contract change:** No — integration of existing pieces.
**Runner behavior change:** No.
**Artifact contract change:** No.
**Schema change:** No.

### PR 0098 — Stabilization: Error Handling & Edge Cases

- Audit error propagation from adapter failures through harness, envelope,
  review boundary, and API response.
- Add missing error handling paths (Docker daemon unavailable, store disk
  full, malformed execution request at runtime).
- Add edge-case tests for each error path.

**Backend contract change:** No — hardening.
**Runner behavior change:** Minimal — better error messages.
**Artifact contract change:** No.
**Schema change:** No.

### PR 0099 — Stabilization: Acceptance Pass

- Run the full acceptance checklist (defined in PR 0091) against the actual
  local substrate, not just the noop mock.
- Fix any gaps found during acceptance.
- Ensure the local interaction page works correctly with the real execution
  pipeline (not just mock `/runs/execute`).

**Backend contract change:** No — hardening.
**Runner behavior change:** No.
**Artifact contract change:** No.
**Schema change:** No.

### PR 0100 — Freeze / Release Gate

- Tag the repository as `v0.1.0` (or equivalent release marker).
- Update version metadata.
- Write release notes summarizing the execution substrate capabilities.
- Lock all post-0100 capability streams.

**Backend contract change:** No — release.
**Runner behavior change:** No.
**Artifact contract change:** No.
**Schema change:** No.

---

## Post-0100 Capability Streams (LOCKED until PR 0100 lands)

No work on the following capability streams may begin before PR 0100 lands:

- **Proof-First Runtime** — formal verification, invariant enforcement
- **Decision Core** — conductor, planner orchestration, multi-agent decision
  loop
- **Context Layer** — context compilation beyond current mock/preview
- **Model Health Monitor** — model routing, capability profiling, cost
  tracking
- **External Capability Integration** — non-coding domain adapters, external
  service integration

These streams correspond to the original Phase 1–10 decomposition. They
remain locked. The roadmap above replaces the phase-based decomposition with
an explicit PR sequence that ends at PR 0100.

---

## Product Iteration Substrate Stream (COMPLETED)

| PR | Title | Status |
|----|-------|--------|
| 0117 | Product Iteration Signal Contract / Local Screen-Time Record | completed |
| 0119 | Product Iteration Session Capture Surface | completed |
| 0120 | Product Iteration Evidence Summary | completed |
| 0121 | Product Iteration Recommendation Candidate | completed |
| 0122 | Product Iteration Human Review Packet | completed |

Stream status: closed. Not a reopened Local Interaction UX Track.
Architect sign-off reference: "экран тайм, product, итерации."

---

## Production Line Stream (COMPLETED)

### Stage 1 — Orchestrator (0123-0127)

```
0123 — production line roadmap realignment (bridge)
0124 — Agent Runner Bridge: run a docker agent from Ariadne code via
       docker_agent_adapter with a real agents/*.yml config;
       input agent_name + task_prompt, output captured artifact
0125 — Prompt Composer: generate planner/plan-review/coder/precommit
       task prompts from templates + PR context
0126 — Verdict Parser: parse review artifacts, extract verdict/blockers,
       decide continue/stop/retry
0127 — Pipeline Runner: planner → plan-review → gate → coder →
       precommit → gate; one call, full cycle, stop on block
```

### Stage 2 — Closed loop (0128-0131)

```
0128 — Git Boundary: commit/push/PR creation only after explicit
       human approve; the single git-mutation surface in the substrate
0129 — ariadne task CLI: `ariadne task "description"` → full cycle → PR link
0130 — Run Persistence: run state/artifacts/proofs in .ariadne/runs/
0131 — DOGFOOD MILESTONE: PR 0131 is created by Ariadne itself
       via ariadne task
```

### Stage 3 — Production hardening (0132-0136)

```
0132 — Failure Recovery: retry with refined prompt on block, max 2,
       then human escalation
0133 — Model Health live: block/violation counters per model,
       automatic fallback model switch
0134 — Run Report: single markdown per cycle (actions, evidence,
       cost, time)
0135 — Parallel-safe runs: branch lock, task queue
0136 — Acceptance: 10 consecutive real tasks via ariadne task with
       recorded metrics (success rate, cost, human interventions)
```

**Status: COMPLETED.** PR 0131-0136 closed the Production Line hardening
stream. The runner now has dogfood proof (0131), execution result persistence
(0132), test residue isolation (0133), commit payload cleanliness gate (0134),
local run report (0135), and production-line readiness gate (0136).

## Product Architecture Stream (ACTIVE)

### PR 0137 — Product Architecture Roadmap Unlock

PR 0137 is the architecture transition PR that commits the product master
prompt as a durable source artifact, records the post-0136 roadmap, and opens
**Artifact Workspace Read-Only UI** as the next active stream. No runtime or
UI implementation happens in this PR.

### PR 0142 — Run Evidence Serialization Contract (COMPLETED)

PR 0142 completes the Artifact Workspace Read Model stream (0138-0142) by
freezing the JSON response shapes for GET /runs and GET /runs/<run_id> into
a versioned, backward-compatible serialization contract.

### PR 0142A — Ariadne Three-Response Orchestrator Happy Path Standard (GOVERNANCE INSERTION)

This PR is a non-product governance insertion authorized by the human architect
between product PR 0142 (Run Evidence Serialization Contract) and product PR 0143
(Artifact Workspace 4-Zone Shell Skeleton).

PR 0142A codifies the current optimal orchestrator workflow as a durable
repository artifact. It does not consume or renumber product roadmap slot PR 0143.
No product capability is implemented. No frozen stream is opened.

PR 0143 remains the next product PR: Artifact Workspace 4-Zone Shell Skeleton.

### PR 0147A — Local Operator Launch and End-to-End Smoke (GOVERNANCE INSERTION)

PR 0147A is a non-product governance insertion authorized by the human architect
between product PR 0147 (Proof and Manifest Viewer) and product PR 0148 (Mermaid
Artifact Type Read Model). It does not consume or renumber product roadmap slot
PR 0148.

PR 0147A adds a safe, deterministic local operator launch command
(`make local-operator`), an ASGI runtime wrapper with server-owned runs-root
configuration, loopback-only defaults, startup diagnostics, configuration check
mode, explicit uvicorn packaging, a committed operator runbook, and one canonical
end-to-end HTTP smoke that proves the full read-only Artifact Workspace through
the official entrypoint.

No agent launch, orchestration, mutation, git authority, Docker, or external
services are added. PR 0147B (Human-Gated Manual Orchestration Mode), PR 0147C
(Domain-Neutral Run and Artifact Profile Contract), PR 0147D (Construction
Estimate Read-Only Dogfood Adapter), and PR 0148+ remain unchanged.

### PR 0147B — Human-Gated Manual Orchestration Mode (GOVERNANCE INSERTION)

PR 0147B is a non-product governance insertion authorized by the human architect
between PR 0147A (Local Operator Launch and End-to-End Smoke) and product PR 0148
(Mermaid Artifact Type Read Model). It does not consume or renumber product
roadmap slot PR 0148.

PR 0147B formalizes the human-directed four-agent workflow into a deterministic
manual orchestration session store at `.ariadne/orchestration/<session_id>.json`.
It implements OPTION B (Dedicated Manual Orchestration Store with Run Bridge):
a versioned packet contract with exactly four inert prompt artifacts, exactly
four ordered stages (planner, plan-review, coder, precommit-review), stage-order
gates with planning-lock and review-verdict enforcement, deterministic session
identity and state hashing, stale-state protection via expected hashes,
inert dangerous-action proposals bound to session state, intent-only human
checkpoints (do not execute), separately recorded external action results,
a human-run CLI with nine subcommands, a GET-only read route
(`GET /orchestration/<session_id>`), and read-only Artifact Workspace
presentation. No agent launch, provider calls, command execution, git, gh,
Docker, HTTP mutation, or later-roadmap capability is added.

PR 0147C (Domain-Neutral Run and Artifact Profile Contract), PR 0147D
(Construction Estimate Read-Only Dogfood Adapter), and PR 0148+ remain unchanged.

### Next active stream: Artifact Workspace Read-Only UI (0138+)

The next active stream is read-only Artifact Workspace UI. Detailed roadmap
lives in `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`.

### Frozen boundaries

The following remain frozen until explicitly unlocked by a future roadmap PR:

- **UI mutation** — frozen until read-only Artifact Workspace is complete
- **Agent launch from UI** — frozen until UI can display state, gates, proofs,
  and run reports
- **Commit from UI** — frozen until explicitly unlocked
- **PR creation from UI** — frozen until explicitly unlocked
- **Context Core** — staged after Artifact Workspace foundations
- **Decision Core** — staged after Artifact Workspace and core evidence views
- **Rubrics runtime** — staged after artifact and evidence views exist
- **Model Router** — staged until observable role/evidence data exists
- **ETL/ERP demo** — staged until Artifact Workspace, Artifact Registry, and
  Visual Gate foundations exist

### Core principle

Agent output is not evidence. Runtime-captured proof is evidence.
The substrate exists to run the loop — the human must stop being the
orchestrator.

---

## Legacy Phase Reference (Superseded)

The phase-based roadmap from PR 0041/0042 is preserved below for historical
reference but is superseded by the execution/substrate PR sequence defined
above. No new PRs shall be planned against these phases without explicit
permission from the architect.

---

## Phase 1: Runtime Substrate

**Deliverables:** Orchestrator skeleton, run state, checkpoints, recovery.

- Orchestrator stub
- `run_state` dataclass with status FSM
- `checkpoint_store` with immutable checkpoints
- Recovery logic from checkpoints
- `audit_log` for step-level events
- `step_contracts` dataclass

**Acceptance criteria:**
- Orchestrator can start/pause/resume/cancel a run
- Checkpoint captured after every step
- Recovery replays from checkpoint without model context
- Audit log records step entries

**Dependencies:** Phase 0 (schemas exist).
**Estimated PR count:** 3–5.
**Risks:** Low — well-defined state machine.

---

## Phase 2: Context Core

**Deliverables:** Repository understanding as cached platform asset.

- `repo_indexer` — scans repo structure and annotations
- `graph_builder` — dependency graph, import graph
- `symbol_index` — symbols, types, function signatures
- `invariant_extractor` — reads `@ariadne-invariant` anchors
- `context_compiler` — assembles Context Packs
- `context_cache` — caches by content_hash + graph_version + policy_hash
- `invalidation_engine` — invalidates on diff

**Acceptance criteria:**
- Context Compiler produces valid Context Packs
- Context Cache returns cached pack for same content_hash
- Invalidated on relevant file changes
- No raw repo dumps in output

**Dependencies:** Phase 0 (schemas), Phase 1 (run state).
**Estimated PR count:** 5–8.
**Risks:** Medium — data structure investment required before visible output.

---

## Phase 3: State Core

**Deliverables:** State model extraction, transition graph, verification.

- `state_model_extractor` — reads `@ariadne-state` anchors
- `transition_graph_builder` — reads `@ariadne-transition` anchors
- `invariant_registry` — collects `@ariadne-invariant`
- `state_trace_builder` — builds traces from transitions
- `event_to_state_folder` — projects events to state
- `state_verifier` — verifies invariants after transitions

**Acceptance criteria:**
- State model extracted from anchor-annotated code
- Transition graph built from anchors
- State trace produced after transition
- State verifier detects invariant violations

**Dependencies:** Phase 0 (state-first schema), Phase 2 (context compiler).
**Estimated PR count:** 4–6.
**Risks:** Low — anchor-based extraction is well-scoped.

---

## Phase 4: PCAM/PBS

**Deliverables:** Purpose decomposition, purpose breakdown structure.

- `purpose_extractor` — extracts purpose from task intake
- `pbs_builder` — decomposes purpose into PBS tree
- `purpose.json` — machine-readable purpose record
- `pbs.json` — machine-readable PBS record
- `purpose_memory` — stores purpose history
- Human approval rules for root purpose changes

**Acceptance criteria:**
- Purpose extractor produces valid `purpose.json`
- PBS builder produces valid `pbs.json`
- Every agent task references a `purpose_id`
- Root purpose changes blocked without human approval

**Dependencies:** Phase 0 (schemas), Phase 2 (context packs reference purpose).
**Estimated PR count:** 3–5.
**Risks:** Low — purpose extraction is a classification task.

---

## Phase 5: Rubrics as Rewards Runtime

**Deliverables:** Rubric generator, rubric judge, verdict pipeline.

- `rubric_generator` — generates rubric packs per PBS node
- `rubric_pack` — machine-readable rubric
- `rubric_judge` — evaluates agent output against rubric
- `rubric_judge_report` — structured verdict
- Critical pitfall stop logic
- Insufficient evidence = needs_human_review

**Acceptance criteria:**
- Rubric generated for each PBS node
- Rubric judge produces structured verdict
- Essential fail = task incomplete
- Critical pitfall = pipeline stops

**Dependencies:** Phase 4 (PBS), Phase 0 (rubric schema).
**Estimated PR count:** 4–6.
**Risks:** Medium — rubric quality must match or exceed human review.

---

## Phase 6: Model Router

**Deliverables:** Model routing runtime, cost tracking, eval history.

- `model_capability_profile` — runtime data model
- `context_stress_profiler` — profiles task context stress
- `routing_policy` — selects model by role/context/risk/cost
- `cost_tracker` — tracks per-model cost
- `model_eval_history` — stores execution history
- Fallback model support

**Acceptance criteria:**
- Router selects model based on profile + stress + risk
- Cost tracker records per-step model usage
- Fallback activates when primary model fails
- No vendor names hardcoded in routing logic

**Dependencies:** Phase 0 (model-routing schema, ADR 0002).
**Estimated PR count:** 4–6.
**Risks:** Low — dry-run already exists in model_gateway.

---

## Phase 7: Agent Runtime

**Deliverables:** Docker-based agent runtime with sandbox isolation.

- `architect_agent`
- `planner_agent`
- `lead_coder_agent`
- `worker_coder_agent`
- `tester_agent`
- `reviewer_agent`
- `security_agent`
- `docs_agent`
- `support_agent`
- Docker sandbox policies per agent role

**Acceptance criteria:**
- Agent receives execution contract
- Agent executes within Docker sandbox
- Agent output conforms to agent_execution_contract
- Review agents have read-only repo access
- Coder agents have write access only in sandbox

**Dependencies:** Phase 1–6.
**Estimated PR count:** 8–12.
**Risks:** High — multi-agent coordination, Docker sandboxing, cost per run.

---

## Phase 8: Domain Adapters

**Deliverables:** Formalized domain-specific execution environments.

- Coding Adapter formalization (existing runner refactored)
- Document Adapter (structured edits, citations)
- Data Adapter (transforms, profiling)
- Research Adapter stub (search, synthesis)
- Custom Adapter registration

**Acceptance criteria:**
- Coding Adapter operates through domain adapter contract
- Document Adapter executes simple document transforms
- Data Adapter profiles datasets
- All adapters supply policy to Conductor

**Dependencies:** Phase 0 (domain-adapter schema, ADR 0004).
**Estimated PR count:** 5–8.
**Risks:** Medium — non-coding adapters require new execution contracts.

---

## Phase 9: Verification and Reports

**Deliverables:** Integrated verification layer, automated reports.

- Test runner integration
- Static analysis integration
- Security scanning integration
- State invariant checker
- Final report generation
- Verification report

**Acceptance criteria:**
- Verification runs after every step
- All verification results in final report
- Report explains why changes satisfy root purpose
- High-risk changes flagged for human review

**Dependencies:** Phase 1–8.
**Estimated PR count:** 4–6.
**Risks:** Low — integration work, not new algorithms.

---

## Phase 10: Dataset/Eval Export

**Deliverables:** Export capability for training data, evaluation packs.

- Rubric dataset export
- Execution trace export
- Failure case export
- Model routing performance logs
- Eval pack generation

**Acceptance criteria:**
- Datasets exportable in standard format
- Execution traces linked to rubric judge results
- Model routing logs available for performance analysis

**Dependencies:** Phase 5 (rubrics), Phase 6 (model routing).
**Estimated PR count:** 3–5.
**Risks:** Low — export pipelines only.
