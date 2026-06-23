# PR 0052 — Cache Contracts and Keys Plan

## Goal

Add backend-agnostic cache contracts and deterministic cache key schemas for Ariadne.

The contracts should describe stable cacheable artifacts such as:

- context packs
- compiled repository understanding
- adapter dry-run previews
- rubric packs
- verification summaries
- model capability profiles
- long-context stress profiles
- final report inputs, if appropriate

The contracts must be usable later by distributed cache and repository-understanding work without changing Core runtime APIs.

## Architectural Thesis

Ariadne needs stable cache contracts before it needs a cache backend.

Cache keys are part of the substrate contract.

A cache backend is replaceable.
The cache key contract is durable.

The model remains replaceable.
The substrate owns artifact identity, provenance, and invalidation boundaries.

## Context Snapshot

- **current HEAD sha**: `5f011729386a87fe379c8add2faacaad8969b8df`
- **current branch**: `0052-cache-contracts-and-keys`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `5f01172` (main after PR 0051 merge — no delta since this is the first commit on this branch)
- **index_version**: `"0.18"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0051, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/review-artifact.schema.yml`
- `.project-memory/domain-adapter.schema.yml`
- `.project-memory/context-pack.schema.yml`
- `.project-memory/ariadne-anchor.schema.yml`
- `.project-memory/conductor-prompt-contract.schema.yml` — not present
- `.project-memory/prompt-artifact.schema.yml` — not present
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `docs/CONTEXT_COMPILER.md`
- `docs/ARIADNE_ANCHORS.md`
- `docs/DOMAIN_ADAPTER_CONTRACT.md`
- `docs/CONDUCTOR_PROMPT_CONTRACT.md` — not present
- `docs/adr/0004-ariadne-is-domain-agnostic.md`
- `docs/adr/0005-rubrics-as-runtime-contracts.md`
- `docs/adr/0006-model-replaceability.md`
- `docs/adr/0007-cached-repository-understanding.md`
- `.project-memory/pr/0040-context-pack-anchors/PLAN.md`
- `.project-memory/pr/0041-architecture-blueprint/PLAN.md` — not inspected
- `.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md`
- `.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md` — presumed
- `.project-memory/pr/0046-runtime-state-transitions/PLAN.md`
- `.project-memory/pr/0047-runtime-verification-evidence/PLAN.md`
- `.project-memory/pr/0048-runtime-in-memory-store/PLAN.md`
- `.project-memory/pr/0049-runner-runtime-smoke-demo/PLAN.md`
- `.project-memory/pr/0050-conductor-dry-run-pipeline/PLAN.md`
- `.project-memory/pr/0051-coding-domain-adapter-minimal/PLAN.md`
- `schemas/context-pack.schema.yml`
- `schemas/run-state.schema.yml`
- `schemas/checkpoint.schema.yml`
- `schemas/final-report.schema.yml`
- `schemas/agent-execution-contract.schema.yml`
- `schemas/purpose.schema.yml`
- `schemas/pbs.schema.yml`
- `schemas/state-model.schema.yml`
- `schemas/transition-graph.schema.yml`
- `schemas/rubric-pack.schema.yml`
- `schemas/rubric-judge-result.schema.yml`
- `schemas/model-capability-profile.schema.yml`
- `schemas/long-context-stress-profile.schema.yml`
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/store.py`
- `services/core/src/core/runtime/verification.py`
- `services/conductor/src/conductor/dry_run.py`
- `services/runner/src/runner/runtime_smoke.py`
- `services/domain_adapters/src/domain_adapters/coding.py`

## Existing Contract Snapshot

### Cache-relevant existing schemas

| Schema | Cache-relevant fields |
|---|---|
| `schemas/context-pack.schema.yml` | context_pack_id, base_sha, index_version, repo_id, source traces |
| `schemas/run-state.schema.yml` | run_id, status, checkpoint references |
| `schemas/checkpoint.schema.yml` | checkpoint_id, run_state_hash, resumable |
| `schemas/final-report.schema.yml` | report_id, run_id, verification references |
| `schemas/rubric-pack.schema.yml` | rubric_id, schema_version |
| `schemas/rubric-judge-result.schema.yml` | judge_result_id, rubric references |
| `schemas/model-capability-profile.schema.yml` | profile_id, model references |
| `schemas/long-context-stress-profile.schema.yml` | profile_id, context stress factors |
| `schemas/agent-execution-contract.schema.yml` | contract_id, step_id references |
| `schemas/purpose.schema.yml` | purpose_id, root purpose |
| `schemas/pbs.schema.yml` | pbs_node_id, decomposition path |
| `schemas/state-model.schema.yml` | state entities, transitions |
| `schemas/transition-graph.schema.yml` | transition definitions |

### ADR 0007 (cached repository understanding)

- Repository understanding is a platform-owned asset.
- Built once, cached, invalidated on diff.
- Cache keys include `content_hash`, `graph_version`, `policy_hash`.
- Context Core owns cache (indexer, graph builder, symbol index, invariant extractor, context compiler, context cache, invalidation engine).
- No cache backend selected; no cache contracts defined.

### Existing `schemas/` directory pattern

All schemas are YAML files under `schemas/`. This PR follows the same pattern for new cache schema files.

## Implementation Location Decision

**Decision: Create cache schemas in `schemas/` and cache docs in `docs/`.**

### Files to create

1. **`schemas/cache-key.schema.yml`** — cache key contract
2. **`schemas/cache-entry.schema.yml`** — cache entry/record contract
3. **`schemas/cache-policy.schema.yml`** — cache policy contract
4. **`docs/CACHE_CONTRACTS.md`** — cache contracts documentation

### Files optionally created, justified below

5. **`docs/adr/0008-cache-keys-are-substrate-contracts.md`** — ADR establishing cache key as stable substrate contract. **Justification:** ADR 0007 established the architectural decision for cached repository understanding. ADR 0008 extends this by establishing that cache keys themselves are a durable substrate contract, not an implementation detail of any backend. This follows the pattern of ADR 0004 (domain-agnostic), ADR 0005 (rubrics as contracts), ADR 0006 (model replaceability), and ADR 0007 (cached repository understanding).

### Project-memory registry updates

6. **`.project-memory/context-bundles/contracts.yml`** — add cache schemas and docs to `read_first`, add anchors, bump version.
7. **`.project-memory/memory_index.yml`** — add `cache-contracts` label with cache schema/docs files.
8. **`.project-memory/project_contract.yml`** — add cache contract IDs.
9. **`.project-memory/anchors.yml`** — add cache contract anchors.

**Justification for project-memory updates:** These are contract/schema-only registry changes following the pattern established by PR 0039 (domain adapter), PR 0040 (context pack/anchors), and all subsequent contract PRs. They update registry metadata without modifying runtime code.

### No other files

No changes to `services/`, `packages/`, `agents/`, `apps/`, `pyproject.toml`, or any existing schema/docs files (except the registry files listed above).

## Cache Key Contract

### Schema: `schemas/cache-key.schema.yml`

```yaml
schema_version: "0.1"

# CacheKey — deterministic identifier for a cacheable artifact.
#
# The cache key is a substrate contract, not a backend-specific key format.
# It must be serializable, deterministic across machines, agents, and time.

# Required fields:
#   schema_version: string
#   namespace: string
#   artifact_kind: string
#   input_digest: string (sha256 hex)
#   contract_versions: map of string keys to string versions
#   producer: string (adapter/service identifier)

# Optional fields:
#   source_refs: list of strings (digests of source artifacts)
#   environment_class: string (optional, e.g. "production", "test")
#   created_from: map (references to source artifacts/contracts)

# Deterministic normalization requirements:
#   1. All map keys must be sorted lexicographically.
#   2. input_digest must be hex-encoded SHA-256.
#   3. Lists must be sorted iteratively (recursive for nested structures).
#   4. Empty strings and null values are serialized consistently:
#      - absent optional fields: omitted
#      - empty strings: omitted
#      - empty lists: omitted
#      - null values: omitted
#   5. Timestamps must not be part of cache key (provided by entry, not key).
#   6. Random ids must not be part of cache key.

# Safety rules:
#   Cache keys must not contain:
#   - absolute local paths
#   - current timestamp
#   - random ids
#   - machine-specific values
#   - secrets, tokens, credentials
#   - raw repository dumps
#   - old project names/examples
```

**Input digest computation rules** (documented in `docs/CACHE_CONTRACTS.md`):

- The `input_digest` is a hex-encoded SHA-256 hash of the canonical JSON representation of key inputs.
- Inputs are serialized with sorted keys and JSON-serializable values only.
- Examples of input compositions:
  - Context pack: `{"base_sha": "...", "index_version": "...", "repo_id": "...", "purpose_id": "..."}`
  - Adapter preview: `{"task_id": "...", "intent": "...", "target_paths": [...], "constraints": [...]}`
  - Repository understanding: `{"content_hash": "...", "graph_version": "...", "policy_hash": "..."}` (aligns with ADR 0007)

## Cache Entry Contract

### Schema: `schemas/cache-entry.schema.yml`

```yaml
schema_version: "0.1"

# CacheEntry — stored artifact record for a cache key.
#
# The entry references the payload without requiring a specific backend.
# Cache entries are backend-agnostic; payload storage is backend-specific.

# Required fields:
#   schema_version: string
#   cache_key: CacheKey-compatible structure (inline or ref)
#   artifact_kind: string
#   payload_digest: string (sha256 hex of payload)
#   payload_summary: string (human-readable summary, no secrets)

# Optional fields:
#   payload_ref: string (backend-specific reference)
#   provenance: map (producer, contract versions, sources)
#   invalidation_inputs: map (inputs that would invalidate this entry)
#   created_at: string (caller-provided ISO 8601 timestamp, not generated by cache layer)

# Determinism rules:
#   - created_at must be caller-supplied, not generated by cache layer.
#   - payload_digest must be deterministic for same payload.
#   - Provenance must be deterministic for same cache key and build.

# Safety rules:
#   Cache entries must not contain secrets, credentials, raw file content
#   beyond what the artifact kind explicitly requires.
```

## Cache Policy Contract

### Schema: `schemas/cache-policy.schema.yml`

```yaml
schema_version: "0.1"

# CachePolicy — backend-agnostic cache behavior policy.
#
# Defines which namespaces, artifact kinds, and invalidation policies
# are allowed for a cache backend.

# Required fields:
#   schema_version: string
#   allowed_namespaces: list of strings
#   allowed_artifact_kinds: list of strings

# Optional fields:
#   ttl_policy: map (default_ttl_seconds, kind_specific_ttls)
#   invalidation_policy: map (strategy, allowed_triggers)
#   replayable: boolean (default false)
#   deterministic_requirement: string (e.g. "strict", "relaxed")
#   cacheability_decisions: list of maps (kind, cacheable, rationale)
#   privacy_class: string (e.g. "public", "internal", "restricted")

# Backend-agnostic:
#   Policy does not name Redis, SQLite, filesystem, or any specific backend.
#   Backend implementation is a separate concern.
```

## Namespace and Artifact Kinds

### Initial namespaces

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

### Initial artifact kinds

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

## Invalidation Inputs

Invalidation inputs are captured per cache entry as part of the `invalidation_inputs` map. These are the inputs that, if changed, would invalidate the cached artifact:

| Artifact Kind | Invalidation Inputs |
|---|---|
| `context_pack` | base_sha, index_version, repo_id, purpose_id |
| `repository_snapshot_summary` | content_hash, policy_hash |
| `repository_understanding` | content_hash, graph_version, policy_hash |
| `adapter_preview` | task_id, intent, target_paths digest |
| `rubric_pack` | schema_version, rubric pack digest |
| `verification_summary` | run_id, evidence digests |
| `final_report_inputs` | run_id, report generation inputs |
| `model_capability_profile` | profile_id, model version |

These are documented in `docs/CACHE_CONTRACTS.md` for implementers. No runtime invalidation engine is implemented in this PR.

## Safety and Privacy Rules

The cache contracts (schemas and docs) must state that keys and entries must not contain:

- secrets, credentials, tokens
- raw private file contents
- absolute local paths
- machine-specific paths
- environment-specific values
- raw repository dumps
- old project examples/names (`water_meter`, `Broken Clock`, `daily-consumption`, `.grace`, `@grace-*`, old Flask examples)

The contracts should prefer digests and stable relative references.

## Relationship to Future PRs

- **PR 0052**: Defines cache contracts and key schemas only. No backend, no integration, no runtime changes.
- **PR 0053 (future)**: Can add a cache backend implementation based on these contracts (e.g., in-memory cache, file-based cache, or Redis-based cache).
- **PR 0054 (future)**: Can add cached repository understanding based on these contracts.
- Core runtime remains unchanged.
- Conductor remains unchanged.
- Domain adapters remain unchanged.
- Runner remains unchanged.
- The cache contracts are designed to be backend-agnostic — any future backend implements the contract, not the reverse.

## Future Allowed Write Paths

- `schemas/cache-key.schema.yml`
- `schemas/cache-entry.schema.yml`
- `schemas/cache-policy.schema.yml`
- `docs/CACHE_CONTRACTS.md`
- `docs/adr/0008-cache-keys-are-substrate-contracts.md` (new ADR)
- `.project-memory/context-bundles/contracts.yml` (registry update)
- `.project-memory/memory_index.yml` (registry update)
- `.project-memory/project_contract.yml` (contract IDs)
- `.project-memory/anchors.yml` (anchors)

Precommit review may later write only:
- `.project-memory/pr/0052-cache-contracts-and-keys/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0052-cache-contracts-and-keys/PLAN.md` (planner only)
- `.project-memory/pr/0052-cache-contracts-and-keys/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except exact allowed registry files listed above
- `agents/**`
- `services/**`
- `packages/**`
- `apps/**`
- `schemas/**` except exact allowed cache schema files listed above
- `docs/**` except exact allowed cache docs/ADR files listed above
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `PHASE_0_DECOMPOSITION.md`
- `ROADMAP_PHASE_0_PR_PLAN.md`

## Required Tests / Validation

This PR is schema/documentation/registry only. No runtime code. Validation checks file presence and schema content.

### Schema presence

```bash
python - <<'PY'
from pathlib import Path
required = [
    "schemas/cache-key.schema.yml",
    "schemas/cache-entry.schema.yml",
    "schemas/cache-policy.schema.yml",
    "docs/CACHE_CONTRACTS.md",
    "docs/adr/0008-cache-keys-are-substrate-contracts.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, f"Missing files: {missing}"
print("cache contract files present")
PY
```

### Schema content checks

- cache-key schema includes namespace, artifact_kind, input_digest, contract_versions, producer
- cache-entry schema references cache key shape
- cache-policy schema is backend-agnostic
- schemas do not require Redis/SQLite/backend-specific fields
- schemas do not require current-time generation
- schemas include deterministic normalization requirements

### Doc content checks

- docs define deterministic cache key normalization rules
- docs define invalidation inputs per artifact kind
- docs define safety/privacy constraints
- docs distinguish cache contracts from cache backend
- docs define future relationship to distributed cache and repository understanding

### Registry checks

- `context-bundles/contracts.yml` cache schemas in read_first
- `memory_index.yml` has cache-contracts label
- `project_contract.yml` has cache contract IDs
- `anchors.yml` has cache contract anchors

### Safety checks

- no cache backend implementation added
- no Redis/SQLite references in cache schemas
- no runtime integration added
- no changes to services/ or packages/

### Validation commands

```bash
python - <<'PY'
from pathlib import Path
required = [
    "schemas/cache-key.schema.yml",
    "schemas/cache-entry.schema.yml",
    "schemas/cache-policy.schema.yml",
    "docs/CACHE_CONTRACTS.md",
    "docs/adr/0008-cache-keys-are-substrate-contracts.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print("cache contract files present")
PY

grep -R -n "redis\|sqlite\|backend implementation\|open(\|Path(.*write\|subprocess\|requests\|httpx\|docker\|git \|water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" schemas/cache-*.schema.yml docs/CACHE_CONTRACTS.md docs/adr/0008-cache-keys-are-substrate-contracts.md || true

python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -R -n "cache-key\|cache-entry\|cache-policy\|CACHE_CONTRACTS\|cache-keys-are-substrate" schemas/cache-*.schema.yml docs/CACHE_CONTRACTS.md docs/adr/0008-cache-keys-are-substrate-contracts.md .project-memory/project_contract.yml .project-memory/anchors.yml
```

## Expected Changed Files

1. `schemas/cache-key.schema.yml` — new cache key schema
2. `schemas/cache-entry.schema.yml` — new cache entry schema
3. `schemas/cache-policy.schema.yml` — new cache policy schema
4. `docs/CACHE_CONTRACTS.md` — cache contracts documentation
5. `docs/adr/0008-cache-keys-are-substrate-contracts.md` — new ADR
6. `.project-memory/context-bundles/contracts.yml` — registry update
7. `.project-memory/memory_index.yml` — registry update
8. `.project-memory/project_contract.yml` — contract IDs
9. `.project-memory/anchors.yml` — cache anchors

Expected future review artifact:
- `.project-memory/pr/0052-cache-contracts-and-keys/reviews/precommit-review.yml`

## Non-goals

- no cache backend
- no Redis
- no SQLite
- no database
- no distributed cache implementation
- no filesystem cache implementation
- no runtime cache integration
- no conductor integration
- no runner integration
- no domain adapter integration
- no repository scanning
- no repository tree digest implementation
- no LLM integration
- no model-provider integration
- no network
- no subprocess
- no Git operations
- no Docker
- no changes to `services/**`
- no changes to `packages/**`
- no changes to `agents/**`
- no changes to `apps/**`
- no `.ariadne/**` namespace creation
- no root dependency/build changes
- no old `.grace` namespace
- no water_meter / broken_clock / old Flask examples

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no services/ changes, no packages/ changes, no runtime code.
- Reviewers must verify: cache schemas are backend-agnostic (no Redis/SQLite/database).
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: docs define deterministic normalization rules.
- Reviewers must verify: safety rules documented.
- Reviewers must verify: registry updates follow existing patterns.

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `services/**` → stop
- about to write to `packages/**` → stop
- about to write to `apps/**` → stop
- about to modify Core runtime internals → stop
- about to modify conductor/runner/adapter implementation → stop
- about to modify existing schema or doc files beyond allowed paths → stop
- about to write `.project-memory/**` beyond exact allowed registry paths → stop
- implementation requires Redis/SQLite/database → stop
- implementation requires a cache backend → stop
- implementation requires filesystem cache writes → stop
- implementation requires network/subprocess → stop
- implementation requires Git/Docker → stop
- implementation requires dependency/build config changes → stop
- implementation requires raw repository content caching → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should cache key include a `version` field separate from `contract_versions`?** **Decision:** No. `schema_version` covers the cache-key schema version. `contract_versions` covers the versions of contracts used to produce the artifact (e.g., context-pack schema version, domain adapter version). A separate `key_version` is unnecessary for the initial contract.

2. **Should cache key include `environment_class` as required or optional?** **Decision:** Optional. Most cacheable artifacts are environment-independent. Environment-specific artifacts (e.g., model capability profiles for a specific deployment) can set this field. Default is absent.

3. **Should ADR 0008 extend ADR 0007 or be independent?** **Decision:** Independent but complementary. ADR 0007 decided that repository understanding is cached. ADR 0008 decides that cache keys themselves are a durable substrate contract. They reference each other.

4. **Should `cache-policy.schema.yml` include a `caching_required` flag?** **Decision:** No. Cache policies describe what is cacheable, not what must be cached. The decision to cache is made by the runtime layer, not the policy.

## Decisions Made

### schema_files

```
schemas/cache-key.schema.yml
schemas/cache-entry.schema.yml
schemas/cache-policy.schema.yml
```

### docs_files

```
docs/CACHE_CONTRACTS.md
docs/adr/0008-cache-keys-are-substrate-contracts.md
```

### project_memory_registry_updates

```
.project-memory/context-bundles/contracts.yml   — add schemas/docs to read_first, add anchors, bump version
.project-memory/memory_index.yml                 — add cache-contracts label
.project-memory/project_contract.yml             — add cache contract IDs
.project-memory/anchors.yml                      — add cache contract anchors
```

### cache_key_shape

```
schema_version, namespace, artifact_kind, input_digest (SHA-256'),
contract_versions (map), producer.
Optional: source_refs (list), environment_class (string), created_from (map).
Normalization: sorted keys, sorted lists, no empty/null, no timestamps, no random ids.
Safety: no secrets, absolute paths, timestamps, random ids, repo dumps, old names.
```

### cache_entry_shape

```
schema_version, cache_key (inline map), artifact_kind, payload_digest, payload_summary.
Optional: payload_ref, provenance, invalidation_inputs, created_at.
created_at must be caller-supplied, not cache-layer-generated.
Safety: no secrets, no raw file content beyond artifact kind requirements.
```

### cache_policy_shape

```
schema_version, allowed_namespaces, allowed_artifact_kinds.
Optional: ttl_policy, invalidation_policy, replayable, deterministic_requirement, cacheability_decisions, privacy_class.
Backend-agnostic. No Redis/SQLite/backend-specific fields.
```

### namespace_set

```
core.runtime, conductor, runner, domain_adapter.coding, context, repository_understanding, rubric, model_capability
```

### artifact_kind_set

```
context_pack, repository_snapshot_summary, repository_understanding, adapter_preview, rubric_pack, rubric_judge_result, verification_summary, final_report_inputs, model_capability_profile, long_context_stress_profile
```

### validation_strategy

```
Schema/document presence checks via Python script.
Content checks via grep and manual review.
Safety checks via grep for forbidden patterns.
No runtime tests (no runtime code).
```

---

PLAN written: yes
