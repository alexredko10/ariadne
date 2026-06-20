# Ariadne Architecture Blueprint

## 1. Project Identity and Core Principles

**Ariadne is an execution substrate for agentic software production.**

Ariadne is not GRACE.
Ariadne is not a chatbot wrapper.
Ariadne is not a model-centered agent framework.

The model is replaceable.
The substrate is the product.

## 2. Architectural Thesis

### Why substrate > model

Models improve every year. Substrate components — run state, checkpoints,
recovery, audit logs, repository understanding, state models, rubrics,
verification — accumulate over the lifetime of the platform.  Investing
in substrate produces compounding returns.  Model selection is a
recurring configuration decision.

### Why cached context > rediscovery

Rediscovering repository structure, symbols, invariants, and ownership
on every run is expensive, inconsistent, and wasteful.  Cached repository
understanding built once, invalidated on diff, and reused across runs is
faster and more reliable.

### Why state > events for agent reasoning

Events hide behavior inside callbacks, queue timing, and async cascades.
State provides explicit checkpoints, replayable traces, and verifiable
invariants.  Agents reason naturally over state snapshots.

### Why purpose > task for agent coordination

Tasks describe what to do.  Purpose describes why it matters.
When multiple agents collaborate, purpose alignment prevents contradictory
changes, rubric gaming, and scope drift.  Purpose decomposition (PBS)
ensures every agent action traces to a root purpose.

### Why rubrics > prose for agent evaluation

Prose instructions are ambiguous and inconsistent across review cycles.
Rubrics as runtime contracts define essential criteria, important criteria,
edge cases, required evidence, and stop conditions in machine-readable
form.  Rubric judge results are reproducible and auditable.

### Why model routing uses profiles, not ideology

No single model is best for all roles.  Routing by role, context stress,
risk, cost, latency, and historical success is empirically grounded.
Hardcoded vendor preferences are platform debt.

### Why human owns the root purpose

Ariadne orchestrates agents, proposes changes, and produces evidence.
But the root purpose — why are we doing this work — belongs to a human.
No agent may silently change the root purpose.

## 3. Existing Implementation Status

### What exists now

| Component | Status |
|-----------|--------|
| Runner (worktree, diff, patch) | Implemented in `services/runner/` |
| Task Intake API | Implemented in `services/task_intake/` |
| Model Gateway dry-run | Implemented in `services/model_gateway/` |
| Run Record schema | Contract in `.project-memory/` |
| Apply Gate schema | Contract in `.project-memory/` |
| Workspace Feature Record schema | Contract in `.project-memory/` |
| Context Steward archival schema | Contract in `.project-memory/` |
| Task Intake Request schema | Contract in `.project-memory/` |
| Task Intake → Runner Handoff schema | Contract in `.project-memory/` |
| Model Routing schema | Contract in `.project-memory/` |
| State-First schema | Contract in `.project-memory/` |
| Review Artifact schema | Contract in `.project-memory/` |
| Review Artifact Workflow | Workflow guide in `.project-memory/` |
| Conductor Prompt Contract schema | Contract in `.project-memory/` |
| Prompt Artifact schema | Contract in `.project-memory/` |
| Domain Adapter schema | Contract in `.project-memory/` |
| Context Pack schema | Contract in `.project-memory/` |
| Ariadne Anchor schema | Contract in `.project-memory/` |
| ADR 0001 (Namespace) | Accepted |
| ADR 0002 (Model Selection) | Accepted |
| ADR 0003 (State-First) | Accepted |
| ADR 0004 (Domain-Agnostic) | Accepted |
| Mock Coder sandbox proof | Proof in `services/runner/` |

### Gap analysis

| Area | Status | Next action |
|------|--------|-------------|
| Orchestrator | Not implemented | Phase 1 |
| Run State / Checkpoints | Not implemented | Phase 1 |
| Context Core | Not implemented | Phase 2 |
| State Core | Not implemented | Phase 3 |
| PCAM / PBS | Not implemented | Phase 4 |
| Rubric Generator / Judge | Not implemented | Phase 5 |
| Model Router runtime | Not implemented | Phase 6 |
| Agent Runtime | Not implemented | Phase 7 |
| Domain Adapters (non-coding) | Not implemented | Phase 8 |
| Verification layer | Not implemented | Phase 9 |
| Dataset/Eval export | Not implemented | Phase 10 |

## 4. Full Subsystem Map

```
ariadne/
  runtime/
    orchestrator/
    run_state/
    checkpoint_store/
    recovery/
    audit_log/
    step_contracts/
  context_core/
    repo_indexer/
    graph_builder/
    symbol_index/
    invariant_extractor/
    context_compiler/
    context_cache/
    invalidation_engine/
  state_core/
    state_model_extractor/
    transition_graph_builder/
    invariant_registry/
    state_trace_builder/
    event_to_state_folder/
    state_verifier/
  pcam/
    purpose_extractor/
    pbs_builder/
    rubric_generator/
    rubric_registry/
    rubric_judge/
    purpose_memory/
  model_router/
    capability_profiles/
    context_stress_profiler/
    routing_policy/
    cost_tracker/
    model_eval_history/
  agent_runtime/
    architect_agent/
    planner_agent/
    lead_coder_agent/
    worker_coder_agent/
    tester_agent/
    reviewer_agent/
    security_agent/
    docs_agent/
    support_agent/
  domain_adapters/
    coding/
    document/
    data/
    research/
    custom/
  verifier/
    test_runner/
    static_analysis/
    security_scanner/
    invariant_checker/
    diff_analyzer/
    final_report_builder/
  artifacts/
```

## 5. Data Artifact Schemas

This blueprint defines platform schemas under `schemas/`.  Artifact flow:

```
purpose.json
→ pbs.json
→ context_pack.json
→ state_model.json + transition_graph.json
→ rubric_pack.json
→ agent_execution_contract
→ run_state + checkpoints
→ review_artifact
→ rubric_judge_result
→ final_report
```

| Schema | Path |
|--------|------|
| Purpose | `schemas/purpose.schema.yml` |
| PBS | `schemas/pbs.schema.yml` |
| Context Pack | `schemas/context-pack.schema.yml` |
| State Model | `schemas/state-model.schema.yml` |
| Transition Graph | `schemas/transition-graph.schema.yml` |
| Rubric Pack | `schemas/rubric-pack.schema.yml` |
| Rubric Judge Result | `schemas/rubric-judge-result.schema.yml` |
| Model Capability Profile | `schemas/model-capability-profile.schema.yml` |
| Long-Context Stress Profile | `schemas/long-context-stress-profile.schema.yml` |
| Agent Execution Contract | `schemas/agent-execution-contract.schema.yml` |
| Run State | `schemas/run-state.schema.yml` |
| Checkpoint | `schemas/checkpoint.schema.yml` |
| Final Report | `schemas/final-report.schema.yml` |

## 6. Ariadne Anchors

Anchors are machine-readable semantic landmarks embedded in source code.

| Annotation | Kind | Example |
|------------|------|---------|
| `@ariadne-domain` | domain | `@ariadne-domain auth` |
| `@ariadne-risk` | risk | `@ariadne-risk security` |
| `@ariadne-invariant` | invariant | `@ariadne-invariant auth.refresh_token.rotation.atomic` |
| `@ariadne-owner` | owner | `@ariadne-owner auth-session` |
| `@ariadne-state` | state | `@ariadne-state Invoice` |
| `@ariadne-transition` | transition | `@ariadne-transition invoice.post` |
| `@ariadne-register` | register | `@ariadne-register stock` |
| `@ariadne-derived-view` | derived-view | `@ariadne-derived-view invoice.total` |
| `@pcam-purpose` | purpose | `@pcam-purpose preserve-session-security` |
| `@pcam-non-goal` | non-goal | `@pcam-non-goal do-not-weaken-token-validation` |
| `@pcam-stop-condition` | stop-condition | `@pcam-stop-condition protected-file-change-requires-approval` |

Canonical prefix: `@ariadne-*`.  Compatibility alias `@ariadna-*` accepted only if present in source materials.

Anchors are indexable, included in Context Packs when relevant, and visible to Conductor, Rubric Generator, and Rubric Judge.  Anchors are context/evidence, not execution authorization.

## 7. Conductor and Prompt Contract

The Conductor assembles prompts from known Ariadne substrate sources.

Defined in `.project-memory/conductor-prompt-contract.schema.yml` and `.project-memory/prompt-artifact.schema.yml`.

### Section source registry

| Section | Source |
|---------|--------|
| task_description | task_intake |
| context_snapshot | context_compiler |
| purpose | pcam.purpose_extractor |
| pbs_node | pcam.pbs_builder |
| rubric | pcam.rubric_generator |
| allowed_write_paths | domain_adapter.policy |
| forbidden_write_paths | domain_adapter.policy |
| validation_commands | domain_adapter.validation |
| final_output_format | agent_contract |

### Prompt artifact lifecycle

```
create → hash → run → review → archive
```

### Policies

- No invented context.
- Missing required sources = missing/blocked.
- Prompt artifact is evidence only.
- Prompt artifact does not bypass Apply Gate.
- Prompt artifact does not replace Run Record.

## 8. Context Core Design

The Context Core makes repository understanding a cached platform asset.

### Components

- **Repo indexer**: Scans repository structure, file types, annotations.
- **Graph builder**: Builds dependency graph, call graph, import graph.
- **Symbol index**: Extracts symbols, types, function signatures.
- **Invariant extractor**: Reads `@ariadne-invariant` annotations.
- **Context compiler**: Assembles Context Packs from all sources.
- **Context cache**: Caches compiled context by content_hash.
- **Invalidation engine**: Invalidates cached context on diff/changes.

### Cache keys

- `content_hash`: Hash of relevant file contents.
- `graph_version`: Version of dependency graph.
- `policy_hash`: Hash of domain adapter policy.

### Stable prompt blocks

The context compiler produces stable, hashable prompt sections that change only when the underlying source changes.  This enables prompt artifact replay without re-compiling.

## 9. State-First Design

Defined in `docs/adr/0003-state-first-agent-architecture.md` and `.project-memory/state-first.schema.yml`.

```
State(t) → Transition(Command/Event) → State(t+1) → Verification
```

### Events at boundary, state at core

Events are not banned.  Events must produce a state projection before
agents reason about behavior.  Event-driven subsystems without state
projection are HIGH RISK for AI modification.

### State trace as verification unit

Every transition produces a StateTrace showing before snapshot, after
snapshot, invariants checked, passed, and failed.  State traces enable
audit, recovery, and replanning.

## 10. PCAM/PBS Design

Purpose-Centred Agent Methodology decomposes work through Purpose
Breakdown Structure (PBS).

### Purpose Extractor

Accepts a task prompt and extracts: root purpose, business goal,
technical goal, non-goals, constraints, risk level.

### PBS Builder

Decomposes root purpose into a tree of purpose nodes.  Every agent
task references a purpose_id.  Root purpose changes require human
approval.

### Purpose memory

Agents may propose purpose changes but must not silently change purpose.

## 11. Rubrics as Runtime Contracts

Rubrics are runtime contracts — not documentation.  See
`docs/adr/0005-rubrics-as-runtime-contracts.md`.

### Per PBS node

Each PBS node may have a rubric pack containing:

- Essential criteria (must pass)
- Important criteria (should pass)
- Optional criteria (nice to have)
- Pitfalls (must not trigger)
- Evidence requirements
- Stop conditions

### Rubric judge verdicts

- `pass`: All essential passed, no critical pitfalls.
- `warning`: Important criteria failed or non-critical pitfalls.
- `fail`: Essential criteria failed.
- `needs_human_review`: Insufficient evidence.

### Rules

- Essential fail = task not complete.
- Critical pitfall = pipeline stops.
- Insufficient evidence = needs_human_review.

## 12. Model Routing Design

Defined in `docs/adr/0002-model-selection-methodology.md` and `.project-memory/model-routing.schema.yml`.

### Routing criteria

- Role fit
- Context stress profile
- Cost
- Latency
- Historical success
- Risk level

### No hardcoded vendor assignments

Model capability profiles are runtime data, not contract values.  Profiles
updated from execution history.  No model vendor names in contract ids.

### Reviewer independence

High-risk tasks require reviewer model different from coder model.

## 13. Domain Adapter Architecture

Defined in `docs/adr/0004-ariadne-is-domain-agnostic.md` and `.project-memory/domain-adapter.schema.yml`.

### Core principle

Ariadne Core is domain-agnostic.  Coding is a Domain Adapter, not Core.
Git, patches, pytest, source file mapping, and test execution belong to
the Coding Adapter.

### Adapter types

| Domain | Execution focus |
|--------|-----------------|
| coding | Worktree, patches, tests |
| document | Structured edits, citations |
| data | Transforms, profiling, validation |
| research | Search, synthesis, verification |
| custom | User-defined environment and policy |

### Adapter responsibilities

Each adapter supplies: allowed/forbidden write paths, validation commands,
artifact types, apply/rollback mechanism, risks, stop conditions,
human approval policy.

## 14. Agent Execution Contract

Every agent receives:

- Purpose context
- PBS node
- Context pack
- State model / transition graph
- Rubric pack
- Domain adapter policy
- Allowed/forbidden actions
- Stop conditions
- Human approval policy

Every agent must return:

- Actions taken
- Files changed
- Claims with evidence
- Uncertainties
- Stop condition triggered
- Next recommended step

### Rules

- No silent purpose mutation.
- No stop bypass.
- No rubric gaming.
- No domain adapter bypass.
- Evidence required for all claims.

## 15. Security Model

- No privileged containers.
- No Docker socket mount.
- No production secrets in agent context.
- Read-only repo access for review agents.
- Write access only in sandbox for coder/tester agents.
- All shell commands logged.
- All file changes diffed.
- Network access policy-controlled.
- Agent identities not equal human identities.
- Protected file changes require approval.
- High-risk changes require: independent reviewer + security scan + rubric judge + human approval.

## 16. Verification Layer

### Deterministic verification

- Tests
- Static analysis
- Type checking
- Linting
- Security scanning
- Dependency audit
- Invariant checks

### Model-based verification

- Independent reviewer agent
- Rubric judge

### Human approval

- High-risk gate
- Protected path changes

### Verification output

All verification sources feed into the final report.

## 17. Final Report Format

Defined in `schemas/final-report.schema.yml`.

Required sections:

- Root purpose and PBS summary
- Model routing decisions
- Context used
- Changes made
- Verification results
- Rubric judge results
- Security summary
- Risks
- Human approval status
- Cost summary
- Next steps

The report must explain why changes satisfy the root purpose — not only
what changed.

## 18. Risks and Open Questions

### Risks

- Phase 2 (Context Core) requires significant data structure investment
  before producing visible results.
- Phase 5 (Rubrics as Rewards) requires rubric quality that matches or
  exceeds human review.
- Agent runtime (Phase 7) cost per run will be higher than single-model
  approaches until model routing optimization matures.
- Domain adapters (Phase 8) require new execution environment contracts
  for each non-coding domain.

### Open questions

- Should `schemas/` become part of `.project-memory/` after validation?
- Should agent runtime agents be Docker containers or host processes?
- Should rubrics be generated per-PBS-node or globally?
- Should model capability profiles be published as files or managed
  through a data service?
- What is the granularity of context cache invalidation?

## 19. Research References

| Reference | Key idea applied to Ariadne |
|-----------|----------------------------|
| **Rubrics as Rewards** | Rubrics are runtime contracts, not docs.  Rubric judge replaces ambiguous prose review. |
| **Transformers represent belief state geometry** | Model state can be profiled by context stress type.  Context stress profiling before routing. |
| **ATLAS Long-Context Benchmark** | Long context is not one capability.  Profile by retrieval, aggregation, graph reasoning. |
| **The Bitter Lesson** | Search and learning generalise.  Hand-coded heuristics do not.  Model routing profiles update from history. |
| **React / UI = F(State)** | UI/API/Report = F(State).  State-First architecture. |
| **Chu Spaces / State-Event Duality** | Events at boundary, state at core.  State projection required before agent reasoning. |
