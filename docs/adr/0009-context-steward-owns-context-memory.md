# ADR 0009: Context Steward Owns Context Memory

**Status:** Accepted

**Date:** 2026-06-22

## Context

Ariadne has accumulated multiple contract layers across PRs 0017–0052:
run records, apply gate, state-first, domain adapters, model routing,
context packs, anchors, review artifacts, conductor prompt contracts,
runtime substrate, and cache contracts.  However, there is no defined
role responsible for preserving, updating, or handing off context memory.

Without Context Steward, the following gaps exist:

- PR workspace memory has no formal schema — each PR accumulates
  unstructured artifacts.
- QA evidence is reported by review agents but not formally stewarded
  as a cross-PR evidence trace.
- Cache contracts from PR 0052 define how to key and store cacheable
  artifacts, but no role records which cache keys are relevant to
  which PR or feature.
- Invalidation decisions are not recorded — when an agent determines
  that cached context is stale, there is no machine-readable record
  of the invalidation.
- Handoff between agents is unstructured — agents rely on the PR
  description and review artifacts rather than a structured handoff
  record.
- Post-merge archival is undefined — there is no defined process for
  archiving PR workspace memory after merge.

## Decision

**Context Steward owns context integrity, not code changes.**

Context Steward may maintain:

- PR workspace memory (`.project-memory/pr/<pr-id>/workspace.yml`)
- QA evidence records (`.project-memory/pr/<pr-id>/qa-evidence.yml`)
- Context-pack inputs (future, schema deferred)
- Invalidation records (within workspace memory)
- Handoff summaries (within workspace memory)
- Approved project-memory registry updates

Context Steward must NOT own:

- Application code
- Runtime implementation
- Conductor implementation
- Runner implementation
- Domain adapter implementation
- Cache backend implementation
- Repository scanner implementation
- `.ariadne/**` writes (deferred)

### Lifecycle hooks

Context Steward acts at six lifecycle points:

1. **before_plan** — prepare workspace memory and context for planner
2. **after_plan_review** — record plan decision in workspace memory
3. **after_implementation** — record implementation summary
4. **after_precommit_review** — record precommit review evidence
5. **after_qa** — record QA evidence
6. **after_merge** — archive workspace memory, prepare for next PR

### Operational namespace

Current: `.project-memory/**`
Long-term canonical: `.ariadne/**` (deferred)

### QA evidence policy

Every validation command that was expected must be recorded in either
`commands_run` or `commands_not_run`.  Silent validation claims are
structurally impossible.

## Consequences

### Positive

- PR workspace memory has a defined schema and lifecycle.
- QA evidence is stewarded as a cross-PR evidence trace.
- Cache key references from PR 0052 are storable in workspace memory.
- Invalidation decisions are machine-readable.
- Handoff between agents is structured through workspace memory.
- Post-merge archival has a defined functional owner.

### Negative

- Context Steward as an agent role requires prompt templates (future PR).
- QA evidence stewardship requires integrating with review artifact output (future PR).
- Post-merge archival implementation is deferred (future PR).
- `.ariadne/**` remains deferred.
- The contract is schema/documentation only — no runtime implementation yet.

## Relationship to existing contracts

- **Review Artifacts**: QA evidence records complement but do not replace
  `.project-memory/review-artifact.schema.yml`.
- **Cache Contracts (PR 0052)**: Context Steward references cache keys
  (`cache_key_refs`) and cache entries (`evidence_refs`) without
  implementing or depending on a cache backend.
- **Context Pack Schema**: Context Steward prepares inputs for Context
  Compiler but does not compile context packs in this PR.
- **Domain Adapter**: Context Steward records `allowed_write_paths` and
  `forbidden_paths` from the domain adapter in workspace memory.
- **State-First**: Workspace memory follows state-first principles:
  explicit state transitions (status FSM), append-only decisions, no
  silent mutations.
- **Run Record**: QA evidence records reference run evidence but do not
  replace run records.
- **Apply Gate**: Context Steward does not bypass, replace, or inform
  apply gate decisions.
