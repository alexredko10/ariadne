# Ariadne Roadmap

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
