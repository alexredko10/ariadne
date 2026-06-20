# ADR 0007: Cached Repository Understanding

**Status:** Accepted

**Date:** 2026-06-20

## Context

Every agent run currently rediscovers repository structure, symbols,
invariants, and ownership from scratch.  This is expensive, inconsistent,
and wastes context window on re-discovery.

Without caching, every prompt artifact must include raw file contents
or summaries that are re-generated each time.  Stable prompt blocks
cannot be reused across runs.

## Decision

**Repository understanding is a platform-owned asset.**

### Built once, cached, invalidated on diff

- Context Core scans the repository after clone or significant diff.
- Results are stored in a cache keyed by content_hash, graph_version,
  and policy_hash.
- Subsequent runs reuse cached context without re-scanning.
- Cache is invalidated when relevant files change.

### Context Core is a first-class subsystem

The Context Core owns:
- Repo indexer (structure, annotations)
- Graph builder (dependencies, calls)
- Symbol index (symbols, types, signatures)
- Invariant extractor (@ariadne-invariant)
- Context compiler (assembles Context Packs)
- Context cache (caches compiled context)
- Invalidation engine (triggers re-index on diff)

### Models receive context packs, not raw repo dumps

Context Packs contain structured, traceable, hashable context sections.
Raw repository dumps are forbidden.

## Consequences

- Faster run startup (cached context reused).
- Consistent context across runs.
- Stable prompt blocks enable replay without re-compilation.
- Context Compiler investment pays off across all agent types.
- Cache invalidation policy must be carefully defined.
- Initial build of Context Core requires significant data structure work.
