# ADR 0002: Model Selection Methodology

**Status:** Accepted

**Date:** 2026-06-19

## Context

Model selection in agentic systems is often treated as an ad-hoc decision:
use the strongest available model for all phases, or switch models based
on loose heuristics without evidence.  This creates platform lock-in,
unnecessary cost, and opaque degradation when a model underperforms in a
specific role.

Ariadne must treat model selection as a platform concern, not an ad-hoc
decision.  The model is replaceable.  The substrate (context packs,
invariants, rubrics, evidence, audit logs) is the product.

This ADR establishes the methodology for selecting models by role, context
stress profile, failure mode, cost, and verification requirements.

## Decision

**Model is selected by role + context stress profile + failure mode + cost
+ verification requirements, not by brand or leaderboard score.**

### Model roles

| Role               | Purpose                                                      |
|--------------------|--------------------------------------------------------------|
| architect          | Purpose analysis, architecture, risk, system boundaries      |
| worker_coder       | Implementation, patches, tests, refactors, tool calls        |
| ui_frontend        | React, forms, dashboards, SVG, UX, visual composition        |
| backend_optimizer  | Performance, DB, concurrency, debugging, API contracts       |
| reviewer           | Independent review, rubric checking, diff critique           |
| dataset_synth      | Synthetic data, test case generation, rubric expansion       |

### Selection rules

**Rule 1 — Do not use the strongest model by default.**
Use strong model when: root purpose unclear, risk high, human-facing
quality matters, novel reasoning required.
Use cheap/fast model when: task well-specified, tests available,
context pack good, rubric clear, output verifiable.

**Rule 2 — Strong model for purpose, cheap model for execution.**

**Rule 3 — UI is not backend.  Separate routing logic required.**

**Rule 4 — Long context is not one capability.**
Profile by subtask: retrieval, aggregation, graph reasoning.

**Rule 5 — The context substrate beats model loyalty.**
If Ariadne owns: cached repo understanding, symbol graph, invariants,
task subgraphs, context packs, rubrics, test evidence, audit logs — then
model choice is a configuration decision.
If the model owns the reasoning state and project understanding, that is
platform lock-in.

**Rule 6 — Reviewer model must differ from coder model when risk is high.**
Independent review requires independent model capability.

**Rule 7 — No hardcoded model vendor assignments.**
Model-to-role mappings must be runtime configuration, not contract
values or agent config commitments.

**Rule 8 — Model profiles must be updated from execution history.**
Static model scores are insufficient.  Historical success, failure
penalty, and availability must feed into the scoring function.

### Pipeline

```
User Request
→ Purpose Extractor
→ Context Stress Profiler      ← new component (contract only in this PR)
→ Ariadne Core
→ Model Router                 ← new component (contract only in this PR)
→ Agent Execution
→ Rubric Judge
→ Model Performance Update
```

## Consequences

### Positive

- Model choice stays a configuration decision if the substrate is owned
- Prevents platform lock-in to any single model provider
- Enables cost optimisation by routing cheap models to low-risk phases
- Reviewer independence improves when model diversity is enforced

### Negative

- Requires maintaining model capability profile data (runtime data, not contracts)
- Requires Context Stress Profiler component implementation (future)
- Requires Model Router component implementation (future)
- Initial profiling data must be gathered or estimated

## Relationship to Model Gateway

`_route_with_policy()` in the Model Gateway must be extended in a future
PR to accept `context_stress_profile` as an input parameter.  This ADR
defines the methodology; the implementation is future work.

## Future work

- ModelRouter implementation
- ContextStressProfiler implementation
- Model performance feedback loop
- model_capability_profile.json schema and runtime population
