# PR 0053 — Context Steward Contract Plan

## Goal

Add contract/schema/documentation for Context Steward.

Context Steward is the Ariadne role responsible for maintaining context memory and evidence artifacts across the planning, implementation, review, QA, and post-merge workflow.

This PR must define contracts only.

No service implementation.
No runtime integration.
No cache backend.
No repository scanning.
No `.ariadne/**` namespace creation.

## Architectural Thesis

Ariadne is not just a set of agents.

Ariadne is the substrate that preserves:

* project memory
* PR workspace memory
* context-pack inputs
* evidence
* decisions
* invalidation boundaries
* handoff records

Context Steward is the role that keeps this substrate coherent.

The model is replaceable.
The memory stewarding contract is durable.

Context Steward does not own code changes.
Context Steward owns context integrity.

## Context Snapshot

- **current HEAD sha**: `c9183d0134854aebb7c2ac2d1dbc585954614cf2`
- **current branch**: `0053-context-steward-contract`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `c9183d0` (main after PR 0052 merge — no delta since first commit on this branch)
- **index_version**: `"0.19"` (from `.project-memory/context-bundles/contracts.yml` — PR 0052 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0052, no pending changes
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
- `.project-memory/context-pack.schema.yml`
- `.project-memory/ariadne-anchor.schema.yml`
- `.project-memory/domain-adapter.schema.yml`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `docs/CONTEXT_COMPILER.md`
- `docs/ARIADNE_ANCHORS.md`
- `docs/DOMAIN_ADAPTER_CONTRACT.md`
- `docs/CACHE_CONTRACTS.md`
- `docs/adr/0004-ariadne-is-domain-agnostic.md`
- `docs/adr/0005-rubrics-as-runtime-contracts.md`
- `docs/adr/0006-model-replaceability.md`
- `docs/adr/0007-cached-repository-understanding.md`
- `docs/adr/0008-cache-keys-are-substrate-contracts.md`
- `schemas/cache-key.schema.yml`
- `schemas/cache-entry.schema.yml`
- `schemas/cache-policy.schema.yml`
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
- `.project-memory/pr/0040-context-pack-anchors/PLAN.md`
- `.project-memory/pr/0050-conductor-dry-run-pipeline/PLAN.md`
- `.project-memory/pr/0051-coding-domain-adapter-minimal/PLAN.md`
- `.project-memory/pr/0052-cache-contracts-and-keys/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/store.py`
- `services/core/src/core/runtime/verification.py`
- `services/conductor/src/conductor/dry_run.py`
- `services/runner/src/runner/runtime_smoke.py`
- `services/domain_adapters/src/domain_adapters/coding.py`

## Existing Contract Snapshot

### Context Pack (`schemas/context-pack.schema.yml`)
- Defines structured context with source traces.
- Explicitly forbids raw repository dumps.
- Requires base_sha, index_version, domain adapter context.

### Cache Contracts (`schemas/cache-key.schema.yml`, `schemas/cache-entry.schema.yml`, `schemas/cache-policy.schema.yml`)
- Backend-agnostic cache key with namespace, artifact_kind, input_digest (SHA-256), contract_versions, producer.
- Deterministic normalization rules (sorted keys, sorted lists, no empty/null, no timestamps, no random ids).
- Cache entry with payload_digest and caller-supplied created_at.
- Cache policy with allowed_namespaces, allowed_artifact_kinds, backend-agnostic.

### QA Review Artifact (`.project-memory/review-artifact.schema.yml`)
- Existing schema for plan-review/precommit-review artifacts.
- Used by agents to report review verdicts.
- QA Evidence Record (planned in this PR) aligns with but does not replace this schema.

### ADR 0007 (Cached Repository Understanding)
- Repository understanding is platform-owned, cached, invalidated on diff.
- Cache keys by content_hash, graph_version, policy_hash.

### ADR 0008 (Cache Keys Are Substrate Contracts)
- Cache keys are durable substrate contracts.
- Deterministic, backend-agnostic.
- Established by PR 0052.

### ADR 0004 (Domain-Agnostic)
- Ariadne Core is domain-agnostic.
- Coding is a domain adapter, not Core.

### PR Workspace Memory (existing pattern)
- `.project-memory/pr/<pr-id>/PLAN.md` — planning artifacts exist.
- `.project-memory/pr/<pr-id>/reviews/` — review artifacts exist.
- No formal workspace memory schema exists yet.

## Implementation Location Decision

**Decision: Six files to create in `schemas/`, `docs/`, and `docs/adr/`.**

### Schema files

1. `schemas/context-steward.schema.yml` — Context Steward role contract.
2. `schemas/feature-workspace-memory.schema.yml` — PR/feature workspace memory contract.
3. `schemas/qa-evidence-record.schema.yml` — QA evidence record contract.

### Documentation files

4. `docs/CONTEXT_STEWARD.md` — Context Steward documentation.
5. `docs/adr/0009-context-steward-owns-context-memory.md` — ADR establishing Context Steward role.

### Project-memory registry updates

6. `.project-memory/context-bundles/contracts.yml` — add new schemas/docs to `read_first`, add Context Steward notes, bump version.
7. `.project-memory/memory_index.yml` — add `context-steward` label with new schema/docs files.

**Justification for registry updates:** These follow the pattern established by PR 0039 (domain adapter), PR 0040 (context pack/anchors), and PR 0052 (cache contracts). They update registry metadata without modifying runtime code.

**Not included in this PR:**
- `.project-memory/anchors.yml` — anchor updates deferred to a future PR that establishes Context Steward as a recurring agent role.
- `.project-memory/project_contract.yml` — contract ID registration deferred to a future PR when Context Steward has runtime responsibilities.
- `.ariadne/**` — not created in this PR per the Ariadne namespace policy.

## Context Steward Contract

### Schema: `schemas/context-steward.schema.yml`

```yaml
schema_version: "0.1"

# ContextSteward — Ariadne role contract for context memory stewardship.
#
# Context Steward is the role responsible for:
# - Preserving project memory integrity
# - Maintaining PR/feature workspace memory
# - Recording QA evidence
# - Preparing context-pack inputs
# - Recording invalidation decisions
# - Facilitating handoffs between agents
#
# Context Steward does NOT:
# - Write application code
# - Modify runtime/conductor/runner/adapter behavior
# - Perform cache backend operations
# - Perform repository scanning
# - Write .ariadne/** (deferred)
```

**Required fields:**
- `schema_version: string`
- `role_id: string` — e.g. `"context-steward-v1"`
- `role_name: string` — `"Context Steward"`
- `purpose: string` — role purpose description
- `lifecycle_hooks: list[string]` — lifecycle points where steward acts
- `read_boundaries: list[string]` — what the steward may read
- `write_boundaries: list[string]` — what the steward may write
- `forbidden_boundaries: list[string]` — what the steward must never write
- `owned_artifacts: list[ArtifactKind]` — artifacts the steward owns
- `handoff_inputs: list[HandoffInput]` — inputs received from other agents
- `handoff_outputs: list[HandoffOutput]` — outputs delivered to other agents
- `invalidation_responsibilities: list[string]` — invalidation types
- `evidence_responsibilities: list[string]` — QA evidence responsibilities
- `context_pack_responsibilities: list[string]` — context pack input responsibilities
- `cache_contract_relationship: string` — how steward references cache contracts
- `review_requirements: list[string]` — review requirements for steward actions
- `stop_conditions: list[string]` — conditions that must stop steward action

**Lifecycle_hooks values:**
- `"before_plan"` — steward prepares workspace memory and context for planner
- `"after_plan_review"` — steward records plan decision in workspace memory
- `"after_implementation"` — steward records implementation summary in workspace memory
- `"after_precommit_review"` — steward records precommit review evidence
- `"after_qa"` — steward records QA evidence
- `"after_merge"` — steward archives workspace memory, prepares memory for next PR

**Operational namespace:** `.project-memory/**` (current).
**Long-term canonical namespace:** `.ariadne/**` (not yet created — deferred).

## Feature / PR Workspace Memory Contract

### Schema: `schemas/feature-workspace-memory.schema.yml`

```yaml
schema_version: "0.1"

# FeatureWorkspaceMemory — short-term workspace memory for one PR or feature.
#
# Created and maintained by Context Steward.
# Stored at: .project-memory/pr/<pr-id>/workspace.yml
```

**Required fields:**
- `schema_version: string`
- `pr_id: string`
- `feature_id: string` — optional, for non-PR features
- `title: string`
- `status: string` — one of the planned status values
- `goal: string` — PR goal
- `scope: list[string]` — scope boundaries
- `allowed_write_paths: list[string]` — from domain adapter
- `forbidden_paths: list[string]` — from domain adapter
- `source_contracts: list[ContractRef]` — contracts used
- `relevant_anchors: list[string]` — anchor references
- `context_pack_refs: list[string]` — context pack references
- `cache_key_refs: list[CacheKeyRef]` — cache key references
- `decisions: list[Decision]` — design decisions made
- `implementation_summary: string` — summary of changes
- `validation_summary: string` — validation results
- `qa_summary: string` — QA evidence summary
- `risks: list[Risk]` — identified risks
- `open_questions: list[Question]` — open questions
- `handoff_notes: string` — notes for next agent
- `created_from: SourceRef` — who/what created this record
- `updated_by: list[UpdateRecord]` — update history

**Status values:**
- `proposed`
- `planned`
- `plan_approved`
- `implementing`
- `implemented`
- `precommit_passed`
- `qa_passed`
- `merged`
- `archived`
- `blocked`

**Determinism rules:**
- Timestamps must be caller-supplied or evidence-supplied.
- No current-time generation by the steward.
- Decision records are append-only.

## QA Evidence Record Contract

### Schema: `schemas/qa-evidence-record.schema.yml`

```yaml
schema_version: "0.1"

# QAEvidenceRecord — QA evidence for a PR or feature.
#
# Created by Context Steward after review/QA steps.
# Aligned with but does not replace .project-memory/review-artifact.schema.yml.
#
# Stored at: .project-memory/pr/<pr-id>/qa-evidence.yml
```

**Required fields:**
- `schema_version: string`
- `pr_id: string`
- `review_type: string` — e.g. "plan-review", "precommit-review"
- `verdict: string` — from review artifact
- `reviewer: string` — reviewer agent id
- `snapshot: string` — snapshot description or SHA reference
- `commands_run: list[CommandResult]` — validation commands and their results
- `commands_not_run: list[CommandNotRun]` — commands explicitly not run, with reason
- `manual_checks: list[ManualCheck]` — manual checks performed
- `risks: list[Risk]` — identified risks
- `blockers: list[Blocker]` — blocking issues
- `warnings: list[Warning]` — non-blocking warnings
- `accepted_risks: list[AcceptedRisk]` — risks accepted
- `files_checked: list[string]` — files inspected
- `files_changed: list[string]` — files changed
- `context_used: ContextUsed` — context references
- `evidence_refs: list[string]` — evidence artifact references
- `created_from: SourceRef` — who/what created this record

**CommandNotRun structure:**
```yaml
command: string
reason: string
mark: "not_run"  # explicit, cannot be silent
```

**Key policy:** Every validation command that was expected must appear in either `commands_run` or `commands_not_run`. It must be impossible to silently claim validation without running a command.

## Context Pack Input Relationship

Context Steward prepares inputs for Context Compiler but does not compile context packs in this PR.

**Operational path pattern:** `.project-memory/pr/<pr-id>/context-pack-inputs.yml` (future use — not implemented in PR 0053; contract defines the intent but the schema file is not created yet).

Context Steward may record:

- task goal (from planner)
- source contracts used
- relevant anchors
- allowed/forbidden paths (from domain adapter)
- cache key refs (from PR 0052)
- prior PR refs
- QA evidence refs
- known risks
- manual checks required
- context freshness status

Context Steward must not dump raw repository contents.
Context Steward must not compile context packs in this PR.
Context Steward must not invoke Context Compiler in this PR.

## Cache Contract Relationship

PR 0053 builds on PR 0052 cache contracts:

- Context Steward references cache keys (`cache_key_refs` in workspace memory).
- Context Steward references cache entries (`evidence_refs` in QA evidence).
- Context Steward records invalidation inputs without implementing cache backend.
- Context Steward uses the namespace and artifact_kind taxonomy from PR 0052.
- Context Steward may mark workspace memory entries as stale based on invalidation inputs.

Context Steward does NOT:

- Look up a cache
- Store to a cache
- Implement a cache backend
- Use Redis, SQLite, or any specific backend
- Compute repository tree digests
- Scan the repository

## Memory Layers

### Layer 1: Global Project Memory (existing)

| File | Purpose |
|---|---|
| `.project-memory/memory_index.yml` | Registry of all memory labels |
| `.project-memory/project_contract.yml` | Contract IDs and severities |
| `.project-memory/context-bundles/contracts.yml` | Context bundles for agents |
| `.project-memory/anchors.yml` | Anchor references |

### Layer 2: PR Workspace Memory (this PR defines schema)

| File | Purpose |
|---|---|
| `.project-memory/pr/<pr-id>/workspace.yml` | PR workspace memory |
| `.project-memory/pr/<pr-id>/qa-evidence.yml` | QA evidence records |
| `.project-memory/pr/<pr-id>/context-pack-inputs.yml` | Context pack inputs (schema deferred) |
| `.project-memory/pr/<pr-id>/PLAN.md` | Existing planning artifact |
| `.project-memory/pr/<pr-id>/reviews/` | Existing review artifacts |

PR 0053 defines schemas for workspace memory and QA evidence. It does not create per-PR workspace artifacts except the PR 0053 precommit-review artifact.

## Invalidation Responsibilities

Context Steward may record invalidation decisions as machine-readable records within workspace memory:

- `changed_paths: list[string]` — paths that changed
- `affected_context_packs: list[string]` — context packs that may need refresh
- `affected_workspace_memories: list[string]` — workspace memories that may be stale
- `affected_cache_key_refs: list[string]` — cache keys that may be invalid
- `stale_context_markers: list[StaleMarker]` — manual stale markers
- `manual_refresh_required: bool` — whether manual refresh is needed

Context Steward does NOT:

- Compute repository graph
- Scan the repository
- Implement cache invalidation backend behavior
- Automatically refresh cache entries

## Safety and Privacy Rules

The Context Steward contract must state:

- No secrets, credentials, or tokens.
- No raw private file dumps.
- No raw repository dumps.
- No absolute local paths in portable artifacts.
- No machine-specific paths.
- No environment-specific values unless explicitly classified.
- No silent validation claims (every expected command is in `commands_run` or `commands_not_run` with a reason).
- No invented command results.
- No broad memory writes (writes are scoped to exact allowed paths).
- No `.ariadne/**` writes in this PR.
- No old project names/examples (`water_meter`, `Broken Clock`, `daily-consumption`, `.grace`, `@grace-*`, old Flask).

## Relationship to Future PRs

- **PR 0053**: Defines Context Steward contract only. No runtime, no agent, no cache, no scanning.
- **Future PR**: Add Context Steward prompt templates (agent-config-like artifact).
- **Future PR**: Add context-pack input generation from workspace memory.
- **Future PR**: Add Context Compiler integration (read context-pack inputs, produce context packs).
- **Future PR**: Add repository-understanding cache integration with cache contracts.
- **Future PR**: Add post-merge memory archival.
- This PR does not change runtime/conductor/runner/adapter behavior.

## Future Allowed Write Paths

- `schemas/context-steward.schema.yml`
- `schemas/feature-workspace-memory.schema.yml`
- `schemas/qa-evidence-record.schema.yml`
- `docs/CONTEXT_STEWARD.md`
- `docs/adr/0009-context-steward-owns-context-memory.md`
- `.project-memory/context-bundles/contracts.yml` (registry update)
- `.project-memory/memory_index.yml` (registry update)

Precommit review may later write only:
- `.project-memory/pr/0053-context-steward-contract/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0053-context-steward-contract/PLAN.md` (planner only)
- `.project-memory/pr/0053-context-steward-contract/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except exact allowed registry files listed above
- `.project-memory/anchors.yml` — deferred to future PR
- `.project-memory/project_contract.yml` — deferred to future PR
- `services/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `schemas/**` except exact allowed schema files listed above
- `docs/**` except exact allowed docs/ADR files listed above
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

This PR is schema/documentation/registry only. No runtime code.

### Schema presence

```bash
python - <<'PY'
from pathlib import Path
required = [
    "schemas/context-steward.schema.yml",
    "schemas/feature-workspace-memory.schema.yml",
    "schemas/qa-evidence-record.schema.yml",
    "docs/CONTEXT_STEWARD.md",
    "docs/adr/0009-context-steward-owns-context-memory.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, f"Missing files: {missing}"
print("context steward contract files present")
PY
```

### Schema content checks

- context-steward schema defines lifecycle_hooks (includes `before_plan`, `after_qa`, `after_merge`)
- context-steward schema defines read/write/forbidden boundaries
- context-steward schema states Context Steward does not write code
- workspace memory schema defines PR workspace fields (pr_id, status, goal, decisions, risks)
- workspace memory schema defines scope boundaries (allowed_write_paths, forbidden_paths)
- workspace memory schema has status values including `proposed`, `plan_approved`, `qa_passed`, `merged`, `archived`
- QA evidence schema defines commands_run and commands_not_run
- QA evidence schema requires not_run reasons
- schemas do not require cache backend implementation
- schemas do not require current-time generation
- schemas use `.project-memory/**`, not `.grace/**`
- schemas do not introduce `.ariadne/**` writes yet

### Docs content checks

- CONTEXT_STEWARD.md defines Context Steward role
- CONTEXT_STEWARD.md defines what it is NOT (not a coder, not a cache backend)
- CONTEXT_STEWARD.md defines lifecycle hooks
- CONTEXT_STEWARD.md defines memory layers (global + PR workspace)
- CONTEXT_STEWARD.md defines QA evidence handling
- CONTEXT_STEWARD.md defines relationship to cache contracts (PR 0052)
- CONTEXT_STEWARD.md defines invalidation responsibilities without implementation
- CONTEXT_STEWARD.md defines safety/privacy rules
- CONTEXT_STEWARD.md uses `.project-memory/**`, not `.grace/**`
- CONTEXT_STEWARD.md does not introduce `.ariadne/**` writes yet
- ADR 0009 establishes Context Steward as owner of context memory

### Boundary checks

- no services/** files changed
- no packages/** files changed
- no agents/** files changed
- no apps/** files changed
- no `.ariadne/**` files created
- no `.grace/**` files created
- no `.project-memory/anchors.yml` or `.project-memory/project_contract.yml` changed
- no old names/examples introduced

### Suggested validation commands

```bash
python - <<'PY'
from pathlib import Path
required = [
    "schemas/context-steward.schema.yml",
    "schemas/feature-workspace-memory.schema.yml",
    "schemas/qa-evidence-record.schema.yml",
    "docs/CONTEXT_STEWARD.md",
    "docs/adr/0009-context-steward-owns-context-memory.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print("context steward contract files present")
PY

grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|backend implementation\|open(\|Path(.*write\|subprocess\|requests\|httpx\|docker\|git " schemas/context-steward.schema.yml schemas/feature-workspace-memory.schema.yml schemas/qa-evidence-record.schema.yml docs/CONTEXT_STEWARD.md docs/adr/0009-context-steward-owns-context-memory.md || true

python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

## Post-change Checks

```bash
grep -R -n "context-steward\|CONTEXT_STEWARD\|context-steward-owns-context-memory\|feature-workspace-memory\|qa-evidence-record" schemas/context-steward.schema.yml schemas/feature-workspace-memory.schema.yml schemas/qa-evidence-record.schema.yml docs/CONTEXT_STEWARD.md docs/adr/0009-context-steward-owns-context-memory.md .project-memory/context-bundles/contracts.yml .project-memory/memory_index.yml
```

## Expected Changed Files

1. `schemas/context-steward.schema.yml`
2. `schemas/feature-workspace-memory.schema.yml`
3. `schemas/qa-evidence-record.schema.yml`
4. `docs/CONTEXT_STEWARD.md`
5. `docs/adr/0009-context-steward-owns-context-memory.md`
6. `.project-memory/context-bundles/contracts.yml` (registry update)
7. `.project-memory/memory_index.yml` (registry update)

Expected future review artifact:
- `.project-memory/pr/0053-context-steward-contract/reviews/precommit-review.yml`

## Non-goals

- no application code
- no services changes
- no packages changes
- no agents changes
- no apps changes
- no runtime integration
- no conductor integration
- no runner integration
- no domain adapter integration
- no cache backend
- no Redis
- no SQLite
- no database
- no distributed cache
- no filesystem cache
- no repository scanning
- no repository graph computation
- no context compiler implementation
- no prompt template implementation
- no QA runner implementation
- no LLM integration
- no model-provider integration
- no network
- no subprocess
- no Git/Docker behavior
- no dependency/build config changes
- no `.ariadne/**`
- no `.grace/**`
- no `.project-memory/anchors.yml` changes
- no `.project-memory/project_contract.yml` changes
- no old examples/names

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no services/packages/agents/apps changes.
- Reviewers must verify: no cache backend or repository scanning.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: schemas define lifecycle hooks, boundaries, and ownership.
- Reviewers must verify: QA evidence schema makes silent validation impossible.
- Reviewers must verify: workspace memory schema has scope and decision tracking.
- Reviewers must verify: docs define memory layers and cache contract relationship.
- Reviewers must verify: no `.ariadne/**` or `.grace/**` created.
- Reviewers must verify: registry updates follow existing patterns.

## Stop Conditions

- about to write to `services/**` → stop
- about to write to `packages/**` → stop
- about to write to `agents/**` → stop
- about to write to `apps/**` → stop
- about to modify Core runtime internals → stop
- about to modify conductor/runner/adapter implementation → stop
- about to implement cache backend → stop
- about to implement repository scanning → stop
- about to implement context compiler → stop
- about to create prompt templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `.project-memory/anchors.yml` → stop (deferred)
- about to modify `.project-memory/project_contract.yml` → stop (deferred)
- about to write PR workspace artifacts beyond allowed paths → stop
- implementation requires network/subprocess → stop
- implementation requires Git/Docker → stop
- implementation requires dependency/build config changes → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should `context-pack-inputs.yml` schema be included in PR 0053?** **Decision:** No. The plan defers this to a future PR. PR 0053 defines the Context Steward role and the two most immediate artifacts: workspace memory and QA evidence. Context pack input schema is conceptually related but not yet exercised — no Context Compiler exists yet to consume it.

2. **Should `context-steward.schema.yml` define the `before_plan` hook behavior or just list hook names?** **Decision:** The schema lists lifecycle hook names. Detailed behavior for each hook is documented in `docs/CONTEXT_STEWARD.md`. The schema defines the structure, not the behavior.

3. **Should QA evidence record replace or augment the existing review artifact schema?** **Decision:** Augment, not replace. The existing `.project-memory/review-artifact.schema.yml` is used by agents during reviews. The new QA evidence record is used by Context Steward to record evidence after reviews. They are complementary.

## Decisions Made

### schema_files

```
schemas/context-steward.schema.yml
schemas/feature-workspace-memory.schema.yml
schemas/qa-evidence-record.schema.yml
```

### docs_files

```
docs/CONTEXT_STEWARD.md
docs/adr/0009-context-steward-owns-context-memory.md
```

### project_memory_registry_updates

```
.project-memory/context-bundles/contracts.yml  — add schemas/docs to read_first, add notes, bump version
.project-memory/memory_index.yml               — add context-steward label
```

Not updated in this PR: `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`.

### context_steward_role_shape

```
Role contract with:
- role_id, role_name, purpose
- lifecycle_hooks (before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge)
- read_boundaries, write_boundaries, forbidden_boundaries
- owned_artifacts, handoff_inputs, handoff_outputs
- invalidation_responsibilities, evidence_responsibilities, context_pack_responsibilities
- cache_contract_relationship, review_requirements, stop_conditions
```

### workspace_memory_shape

```
Schema with: pr_id, feature_id, title, status (10 values: proposed to archived), goal, scope,
allowed_write_paths, forbidden_paths, source_contracts, relevant_anchors, context_pack_refs,
cache_key_refs, decisions, implementation_summary, validation_summary, qa_summary, risks,
open_questions, handoff_notes, created_from, updated_by.
Timestamps caller-supplied. Decision records append-only.
```

### qa_evidence_shape

```
Schema with: pr_id, review_type, verdict, reviewer, snapshot, commands_run (list with results),
commands_not_run (list with command + reason + mark="not_run"), manual_checks, risks,
blockers, warnings, accepted_risks, files_checked, files_changed, context_used, evidence_refs,
created_from.
Every expected command in either commands_run or commands_not_run.
Silent validation claims impossible.
```

### lifecycle_hooks

```
before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge
```

### operational_namespace

```
Current: .project-memory/**
Long-term: .ariadne/** (deferred — not created in this PR)
```

### cache_contract_relationship

```
Context Steward references cache keys (cache_key_refs in workspace memory) and cache entries
(evidence_refs in QA evidence). Records invalidation inputs without implementing cache backend.
Uses PR 0052 namespace/artifact_kind taxonomy. Does not perform cache lookups or stores.
```

### validation_strategy

```
Schema/doc presence checks via Python script.
Content checks via grep and manual review.
Safety checks via grep for forbidden patterns.
No runtime tests (no runtime code).
```

---

PLAN written: yes
