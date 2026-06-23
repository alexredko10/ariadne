# ADR 0008: Cache Keys Are Substrate Contracts

**Status:** Accepted

**Date:** 2026-06-22

## Context

ADR 0007 established that repository understanding is a platform-owned asset
built once, cached, and invalidated on diff.  However, ADR 0007 did not
define cache contracts — it only established the architectural need.

Cache keys are often treated as an implementation detail of whichever cache
backend is chosen.  In practice, if cache keys change due to a backend
switch, all cached artifacts become invalid and must be recomputed.
This is wasteful, unpredictable, and breaks auditability when execution
traces reference cached artifacts.

Ariadne must treat cache keys as a durable substrate contract, not a
backend implementation detail.

## Decision

**Cache keys are substrate contracts.**

### Cache contract architecture

```
Cache Contract (this ADR)
  → Cache Key (input digest, namespace, artifact kind)
  → Cache Entry (payload digest, provenance, invalidation)
  → Cache Policy (namespaces, TTL, invalidation rules)
    → Cache Backend (implementation-specific — future PR 0053)
```

### Key requirements

- Cache keys must be deterministic across machines, agents, and time.
- Cache keys must be serializable without runtime state.
- Cache keys must not contain secrets, absolute paths, timestamps, or
  random identifiers.
- Cache entries must capture invalidation inputs so the cache backend
  can make eviction decisions without understanding artifact semantics.
- Cache policies are backend-agnostic and do not name specific backends.

### Digest algorithm

All cache key digests use SHA-256 (hex-encoded lowercase).

### Addresses

- ADR 0007: Established the need for cached repository understanding.
  ADR 0008 defines the cache contract that makes it implementable.
- Phase 0 blueprints (PR 0041): The architecture document lists cache
  contracts as a deferred component.  ADR 0008 makes cache contracts
  a current architectural deliverable.

## Consequences

### Positive

- Cache keys are portable across backends.
- Cache entries carry invalidation inputs directly, enabling
  backend-agnostic invalidation.
- Cache policies are backend-agnostic, so switching from e.g. in-memory
  to Redis does not require policy schema changes.
- Cache contracts align with the existing `schemas/` pattern.
- Cache key normalization rules are explicit and testable.

### Negative

- Cache key computation must follow deterministic rules (sorted keys,
  sorted lists, omitted empty values), which adds a small burden to
  implementers.
- Input digests must be computed from canonical JSON, which requires
  JSON-serializable inputs.

## Relationship to ADR 0007

ADR 0007 decided that repository understanding is a platform-owned asset,
built once, cached, invalidated on diff.  ADR 0008 extends this by defining
the cache key and cache entry contracts that make cached repository
understanding possible.

ADR 0007 mentions cache keys: `content_hash`, `graph_version`, `policy_hash`.
ADR 0008 generalises this into a namespace-based cache key contract where
`repository_understanding` is one namespace among several.

## Relationship to existing contracts

- Backend-agnostic: no Redis, SQLite, filesystem, or database references.
- No runtime code: cache contracts are schema/documentation only.
- No changes to Core, conductor, runner, adapters, services, or packages.
- Cache contracts may be referenced by future PR 0053 (distributed cache
  backend) and PR 0054 (cached repository understanding).
