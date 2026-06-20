# ADR 0006: Model Replaceability

**Status:** Accepted

**Date:** 2026-06-20

## Context

The Bitter Lesson teaches that general methods (search, learning) outperform
hand-crafted heuristics over time.  ATLAS shows that long-context benchmarks
reveal significant capability variation across models.

Hardcoding a model vendor into the platform creates lock-in, hides
degradation, and prevents cost optimisation.  Model routing should be
a platform concern — determined by role, context stress profile, failure
mode, cost, latency, and historical evidence.

## Decision

**The model is replaceable.  No vendor lock-in.**

### Capability profiles over rankings

Instead of ranking models by aggregate score, Ariadne profiles models
by role scores (architect, worker_coder, reviewer, etc.) and context
capability scores (retrieval, aggregation, graph_reasoning, etc.).

### Routing criteria

Model selection uses:
- Role fit
- Context stress profile
- Risk level
- Cost per token
- Latency
- Historical success
- Availability

### No vendor hardcoding

- No model vendor names in contract ids.
- Model capability profiles are runtime data.
- Profiles updated from execution history.
- Fallback models supported.

### Reviewer independence

High-risk tasks require reviewer model different from coder model
to avoid same-model blind spots (see ADR 0002).

## Consequences

- Model routing is a platform concern, not an ad-hoc decision.
- Cost optimisation by role is possible.
- Model degradation is detected and routed around.
- New models can be added without platform changes.
- Capability profile data must be maintained and updated.
