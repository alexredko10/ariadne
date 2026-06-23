# Cache Contracts

## Cache contracts vs cache backend

Ariadne separates cache **contracts** from cache **backends**.

Cache contracts define:
- How cache keys are constructed (deterministic, backend-agnostic)
- What cache entries look like (payload digest, provenance, invalidation inputs)
- What cache policies apply (namespaces, artifact kinds, TTL, invalidation)

A cache backend implements the contract. The backend may be in-memory, file-based,
Redis, SQLite, or any other storage. The contract remains unchanged.

Cache contracts are substrate contracts. A cache backend is replaceable.

## Deterministic cache key normalization

Cache keys must be **deterministic across machines, agents, and time**.

### Stable JSON serialization

When computing the `input_digest` of a cache key:

1. Serialize the key input map as JSON.
2. Use `json.dumps(data, sort_keys=True)`.
3. Use `ensure_ascii=True`.
4. Use `separators=(",", ":")` (compact — no extra whitespace).
5. Encode as UTF-8 bytes.
6. Compute SHA-256 hex digest.

### Sorted keys

All map keys must be sorted lexicographically. This is the default behaviour
of `json.dumps(sort_keys=True)`.

### Relative path normalization

Path inputs in cache key computation must be:
- Repo-relative POSIX paths (e.g. `services/core/src/core/runtime_substrate.py`).
- Normalized to remove `./` prefixes.
- Sorted lexicographically if multiple paths are present.
- Absolute paths must not appear in cache keys.

### List ordering rules

Lists used in cache key computation must be sorted lexicographically,
applied recursively for nested lists.  This ensures that `["b", "a"]` and
`["a", "b"]` produce the same cache key.

### Null / empty handling

- Absent optional fields: omitted from the input map.
- Empty strings: omitted.
- Empty lists: omitted.
- `null` values: omitted.

## Digest algorithm policy

All digests use **SHA-256** as the default algorithm.

- `input_digest`: SHA-256 of canonical JSON input.
- `payload_digest`: SHA-256 of the cache entry payload.
- Source reference digests: SHA-256 of the referenced artifact.

Hex-encoded lowercase.

## Namespace policy

Namespaces define the top-level scope for cache keys.
Each artifact belongs to exactly one namespace.

| Namespace | Description |
|---|---|
| `core.runtime` | Core runtime artifacts (run state, checkpoints, evidence) |
| `conductor` | Conductor orchestration artifacts (phase plans, event logs) |
| `runner` | Runner execution artifacts (validation results, patch summaries) |
| `domain_adapter.coding` | Coding domain adapter artifacts (previews, capability profiles) |
| `context` | Context compilation artifacts (context packs, source traces) |
| `repository_understanding` | Repository analysis artifacts (symbol indexes, graph snapshots) |
| `rubric` | Rubric artifacts (packs, judge results) |
| `model_capability` | Model capability artifacts (profiles, stress profiles) |

## Artifact kind policy

Artifact kinds describe what type of artifact is cached.

| Kind | Namespace | Description |
|---|---|---|
| `context_pack` | context | Compiled context pack for a task |
| `repository_snapshot_summary` | repository_understanding | Summary of repository structure at a point |
| `repository_understanding` | repository_understanding | Full compiled repository understanding |
| `adapter_preview` | domain_adapter.coding | Domain adapter dry-run preview output |
| `rubric_pack` | rubric | Compiled rubric pack |
| `rubric_judge_result` | rubric | Rubric judge evaluation result |
| `verification_summary` | core.runtime | Verification evidence summary |
| `final_report_inputs` | core.runtime | Inputs used to build a final report |
| `model_capability_profile` | model_capability | Model capability profile data |
| `long_context_stress_profile` | model_capability | Long-context stress profile data |

## Invalidation inputs

Invalidation inputs are captured per cache entry. If any invalidation input
changes, the cached entry should be invalidated.

| Artifact Kind | Invalidation Inputs |
|---|---|
| `context_pack` | base_sha, index_version, repo_id, purpose_id |
| `repository_snapshot_summary` | content_hash, policy_hash |
| `repository_understanding` | content_hash, graph_version, policy_hash |
| `adapter_preview` | task_id, intent, sorted target_paths digest |
| `rubric_pack` | schema_version, rubric pack digest |
| `verification_summary` | run_id, evidence digests |
| `final_report_inputs` | run_id, report generation inputs |
| `model_capability_profile` | profile_id, model version |

## Provenance requirements

Cache entries should include provenance information:

- `producer`: The adapter or service that produced the artifact.
- `contract_versions`: The versions of contracts used to produce the artifact.
- Source references: Digests of source artifacts used to produce this artifact.

## Safety / privacy rules

Cache keys and entries must not contain:

- secrets, credentials, tokens, API keys
- raw private file contents
- absolute local paths or machine-specific paths
- environment-specific values
- raw repository dumps beyond what the artifact kind requires
- old project examples/names (water_meter, Broken Clock, etc.)

Cache entries should prefer digests and stable relative references over
raw content.

## Relationship to future PR 0053 (distributed cache backend)

PR 0053 may implement a cache backend based on these contracts.
The backend (in-memory, file-based, Redis, or other) implements the
cache-key, cache-entry, and cache-policy contracts without changing them.

## Relationship to future PR 0054 (cached repository understanding)

PR 0054 may add cached repository understanding based on these contracts.
The `repository_understanding` namespace and `content_hash`, `graph_version`,
`policy_hash` invalidation inputs align with ADR 0007.

## Relationship to existing ADRs

- **ADR 0007**: Decided that repository understanding is a platform-owned asset,
  built once, cached, invalidated on diff. ADR 0007 established the architectural
  need. ADR 0008 (this PR) extends this by defining the cache key contract
  that makes cached repository understanding possible.

- **ADR 0008**: Decides that cache keys themselves are a durable substrate
  contract, not an implementation detail of any backend. This document
  describes the normalization rules, namespaces, artifact kinds, and safety
  policies that implementers must follow.
