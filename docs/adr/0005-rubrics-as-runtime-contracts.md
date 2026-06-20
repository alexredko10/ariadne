# ADR 0005: Rubrics as Runtime Contracts

**Status:** Accepted

**Date:** 2026-06-20

## Context

Agent evaluation currently uses prose instructions, which are ambiguous,
inconsistent across review cycles, and not reproducible.  The Rubrics as
Rewards paper demonstrates that rubrics can replace reward modelling in
RL for code generation.

For Ariadne, rubrics serve a broader purpose: they are runtime contracts
that define what "done" means for a task.  They are not documentation.

## Decision

**Rubrics are runtime contracts, not docs.**

### Per PBS node

Each PBS node may have a rubric pack containing:
- Essential criteria (must pass)
- Important criteria (should pass)
- Optional criteria (nice to have)
- Pitfalls (must not trigger)
- Evidence requirements
- Stop conditions

### Rubric judge

The rubric judge evaluates agent output against the rubric and produces
a structured verdict: `pass`, `warning`, `fail`, or `needs_human_review`.

### MVP

No RL training in the MVP.  The rubric judge verdict is used for:
- Step completion gates
- Review artifact generation
- Human escalation triggers

### Future

Rubric packs and judge reports may become eval/training data for
RL-based fine-tuning or reward modelling.

## Consequences

- Every task must have a rubric before execution.
- Essential fail means task not complete.
- Critical pitfall stops the pipeline.
- Insufficient evidence means `needs_human_review`.
- Rubric packs must be generated per PBS node.
- Rubric quality must match or exceed human review.
