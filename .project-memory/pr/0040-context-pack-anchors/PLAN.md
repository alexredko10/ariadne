# PR 0040: Context Pack + Ariadne Anchors + Semantic Context Decomposition

## Goal

Define machine-readable contracts for Ariadne Context Packs and Ariadne Anchors.

The goal is to make Ariadne capable of giving agents structured, evidence-backed context instead of raw repository dumps.

This PR must define how future Context Compiler output answers:

```text
What is the task?
What is the root purpose?
Which PBS node is being executed?
Which domain adapter applies?
Which files are relevant?
Which symbols are relevant?
Which tests are related?
Which configs are related?
Which invariants must not be violated?
Which state entities are involved?
Which transitions are involved?
Which risks are attached?
Which stop conditions apply?
Which validation commands must be run?
```

## Architectural thesis

```text
Ariadne must not feed raw repository dumps into agents.

Good context is not more tokens.

Good context is:
- more structure
- more labels
- more explicit relationships
- more evidence
- less noise
```

Context Compiler should assemble Context Packs from known sources:

```text
project contract
anchors
memory index
context bundles
AST / symbols
imports
call graph where available
tests
configs
git history
semantic search
state model
transition graph
invariants
rubrics
domain adapter policy
```

This PR defines contracts only.
It does not implement runtime extraction, indexing, semantic search, AST parsing, or graph building.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "452a383b92330e9482ae6b58cca7506f59b7f594"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.17"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "452a383b92330e9482ae6b58cca7506f59b7f594"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review must report snapshot deltas but must not block solely because current HEAD differs from PLAN.md base_sha, unless scope evidence shows unrelated or forbidden changes.
Review artifacts must include snapshot_delta fields according to .project-memory/review-artifact.schema.yml.
```

## Non-goals

```text
- no agents/** changes
- no services/** changes
- no runner changes
- no task_intake changes
- no model_gateway changes
- no .ariadne/** writes
- no schemas/** writes
- no runtime Context Compiler implementation
- no AST parser implementation
- no semantic search implementation
- no repository graph implementation
- no anchor scanner implementation
- no state model extraction implementation
- no transition graph extraction implementation
- no rubric generation implementation
- no Domain Adapter implementation
- no Conductor runtime changes
- no automatic prompt generation changes
- no apply-gate semantic changes
- no run-record semantic changes
- no Workspace Feature Record changes
- no Review Artifact schema/workflow changes
- no Conductor Prompt schema changes
- no Prompt Artifact schema changes
- no Domain Adapter schema changes
- no State-First schema changes
- no Model Routing schema changes
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

## Future allowed write paths for implementation

Implementation may modify/create only:

```text
.project-memory/context-pack.schema.yml
.project-memory/ariadne-anchor.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0040-context-pack-anchors/PLAN.md
.project-memory/pr/0040-context-pack-anchors/reviews/plan-review.yml
.project-memory/pr/0040-context-pack-anchors/reviews/precommit-review.yml
docs/CONTEXT_COMPILER.md
docs/ARIADNE_ANCHORS.md
```

Note:

* Prefer `.project-memory/*.schema.yml` because current repository contract schemas live in `.project-memory`.
* Do not create `.ariadne/**` in this PR.
* Do not create `schemas/**` in this PR.
* `.project-memory/` remains current/legacy-compatible project memory.
* `.ariadne/` remains canonical long-term namespace but is not created in this PR.

## Future forbidden write paths for implementation

Implementation must not modify/create:

```text
.ariadne/**
agents/**
services/**
packages/**
apps/**
.github/**
docker/**
Dockerfile*
prompts/**
schemas/**
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/model-routing.schema.yml
.project-memory/state-first.schema.yml
.project-memory/review-artifact.schema.yml
.project-memory/review-artifact-workflow.yml
.project-memory/conductor-prompt-contract.schema.yml
.project-memory/prompt-artifact.schema.yml
.project-memory/domain-adapter.schema.yml
.project-memory/context-bundles/agent-config.yml
docs/** except:
  - docs/CONTEXT_COMPILER.md
  - docs/ARIADNE_ANCHORS.md
```

## Required schema: Context Pack

Future implementation must create:

```text
.project-memory/context-pack.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

The schema must define:

```text
ContextPack
PurposeContext
PBSNodeContext
RepositoryContext
SemanticContext
StateFirstContext
RubricContext
DomainAdapterContext
ValidationContext
ContextEvidence
ContextPackSourceTrace
```

Required `ContextPack` fields:

```text
schema_version
context_pack_id
task_id
domain
purpose
pbs_node
repository_context
semantic_context
state_first_context
rubric_context
domain_adapter_context
validation_context
source_trace
created_at
```

Required `PurposeContext` fields:

```text
root_purpose
business_goal
technical_goal
non_goals
constraints
risk_level
```

Required `PBSNodeContext` fields:

```text
id
title
parent_id
local_goal
```

Required `RepositoryContext` fields:

```text
relevant_files
relevant_symbols
related_tests
configs
recent_changes
suggested_entry_points
```

Required `SemanticContext` fields:

```text
anchors
invariants
risks
known_bad_patterns
architectural_notes
```

Required `StateFirstContext` fields:

```text
state_entities
transitions
derived_views
transaction_boundaries
state_traces
```

Required `RubricContext` fields:

```text
rubric_id
essential
important
optional
pitfalls
evidence
stop_conditions
```

Required `DomainAdapterContext` fields:

```text
domain
adapter_id
allowed_write_paths
forbidden_write_paths
validation_commands
artifact_types
risks
stop_conditions
```

Required `ValidationContext` fields:

```text
commands
expected_evidence
not_run_policy
```

Required `ContextPackSourceTrace` fields:

```text
source
source_id
source_hash
section
required
present
```

Required policies:

* Context Pack must not contain raw unbounded repository dumps.
* Context Pack must identify source traces.
* Missing required sources must be represented as missing/blocked, not invented.
* Context Pack must include anchors when relevant.
* Context Pack must include invariants when relevant.
* Context Pack must include domain adapter policy when relevant.
* Context Pack must include state-first context when relevant.
* Context Pack must include rubric context when relevant.
* Context Pack must preserve validation commands from Domain Adapter.
* Context Pack must not contain secrets.

## Required schema: Ariadne Anchor

Future implementation must create:

```text
.project-memory/ariadne-anchor.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

The schema must define:

```text
AriadneAnchor
AnchorKind
AnchorLocation
AnchorScope
AnchorRisk
AnchorIndexRecord
AnchorAliasPolicy
```

Canonical prefix policy:

* Canonical project prefix: `@ariadne-*`
* Accept legacy/source-doc alias: `@ariadna-*` only as compatibility input if already present in source materials.
* Do not replace existing `@ariadne-*` semantics.
* Do not weaken existing `@ariadne-invariant` semantics.
* Normalized anchor records should use canonical kind names without prefix.

Required anchor kinds:

```text
domain
risk
invariant
owner
state
transition
register
derived-view
purpose
non-goal
stop-condition
```

Required supported annotation spellings:

```text
@ariadne-domain
@ariadne-risk
@ariadne-invariant
@ariadne-owner
@ariadne-state
@ariadne-transition
@ariadne-register
@ariadne-derived-view
@pcam-purpose
@pcam-non-goal
@pcam-stop-condition
```

Compatibility aliases, if explicitly needed:

* `@ariadna-domain`
* `@ariadna-risk`
* `@ariadna-invariant`
* `@ariadna-owner`
* `@ariadna-state`
* `@ariadna-transition`
* `@ariadna-register`
* `@ariadna-derived-view`

Required `AriadneAnchor` fields:

```text
schema_version
anchor_id
raw_text
prefix
kind
value
normalized_kind
normalized_value
location
scope
source_hash
risk_level
indexed
```

Required `AnchorLocation` fields:

```text
path
line_start
line_end
symbol
```

Required `AnchorIndexRecord` fields:

```text
anchor_id
kind
value
path
symbol
source_hash
context_pack_ids
```

Required policies:

* Anchors must be indexable.
* Anchors must be included in Context Packs when relevant.
* Anchors must be visible to Conductor.
* Anchors must be available to future Rubric Generator and Rubric Judge.
* Anchors must not contain secrets.
* Anchors must not be treated as execution authorization.
* Anchors are semantic landmarks, not runtime mutation permission.

## Required documentation: Context Compiler

Future implementation must create:

```text
docs/CONTEXT_COMPILER.md
```

Documentation must explain:

* Context Compiler purpose
* why raw repository dumps are forbidden/unsafe
* how Context Pack is assembled
* source inputs:

  * project contract
  * anchors
  * memory index
  * context bundles
  * AST/symbols
  * imports
  * call graph where available
  * tests
  * configs
  * git history
  * semantic search
  * state model
  * transition graph
  * invariants
  * rubrics
  * domain adapter policy
* how Context Pack feeds Conductor Prompt Contract
* how Context Pack feeds Prompt Artifact
* how Context Pack feeds Review/Rubric Judge
* how Context Pack relates to Domain Adapter
* how Context Pack relates to State-First
* how Context Pack handles missing sources
* no-invented-context policy
* no raw unbounded repo dump policy
* no secrets policy
* `.project-memory/` as current/legacy-compatible memory
* `.ariadne/` as long-term canonical namespace, not created in this PR

## Required documentation: Ariadne Anchors

Future implementation must create:

```text
docs/ARIADNE_ANCHORS.md
```

Documentation must explain:

* anchors as machine-readable semantic landmarks
* anchors are for Context Compiler, Conductor, Rubric Generator, Rubric Judge, and agents
* canonical `@ariadne-*` prefix
* compatibility alias policy for `@ariadna-*` if needed
* supported anchor kinds
* examples in code/docs
* indexing behavior
* inclusion in Context Packs
* relationship to State-First annotations
* relationship to PCAM annotations
* relationship to risks/invariants
* anchors are evidence/context, not execution authorization
* anchors must not contain secrets

Must include examples for:

```text
@ariadne-domain auth
@ariadne-risk security
@ariadne-invariant auth.refresh_token.rotation.atomic
@ariadne-owner auth-session
@ariadne-state Invoice
@ariadne-transition invoice.post
@ariadne-register stock
@ariadne-derived-view invoice.total
@pcam-purpose preserve-session-security
@pcam-non-goal do-not-weaken-token-validation
@pcam-stop-condition protected-file-change-requires-approval
```

## Future contract IDs

PLAN must list future contract IDs:

```text
context-pack.schema-path
context-pack.required-structure
context-pack.no-raw-repository-dump
context-pack.no-invented-context
context-pack.source-trace.required
context-pack.domain-adapter-context.required
context-pack.state-first-context.supported
context-pack.rubric-context.supported
context-pack.validation-context.required
context-pack.no-secret-material
ariadne-anchor.schema-path
ariadne-anchor.indexable
ariadne-anchor.context-pack-visible
ariadne-anchor.conductor-visible
ariadne-anchor.rubric-visible
ariadne-anchor.canonical-prefix
ariadne-anchor.legacy-prefix-compatibility
ariadne-anchor.no-secret-material
ariadne-anchor.not-authorization
```

Required meanings and severities:

```text
context-pack.schema-path:
  Schema: .project-memory/context-pack.schema.yml
  severity: medium

context-pack.required-structure:
  Context Pack must include purpose, PBS node, repository context, semantic context, state-first context, rubric context, domain adapter context, validation context, and source trace.
  severity: high

context-pack.no-raw-repository-dump:
  Context Pack must not be an unbounded raw repository dump.
  severity: high

context-pack.no-invented-context:
  Context Compiler must not invent missing context.
  severity: critical

context-pack.source-trace.required:
  Context Pack must include source trace for context sections.
  severity: high

context-pack.domain-adapter-context.required:
  Context Pack must include Domain Adapter policy when relevant.
  severity: high

context-pack.state-first-context.supported:
  Context Pack must support State-First context.
  severity: high

context-pack.rubric-context.supported:
  Context Pack must support rubric context.
  severity: high

context-pack.validation-context.required:
  Context Pack must include validation context.
  severity: high

context-pack.no-secret-material:
  Context Pack must not contain secrets/tokens/credentials.
  severity: critical

ariadne-anchor.schema-path:
  Schema: .project-memory/ariadne-anchor.schema.yml
  severity: medium

ariadne-anchor.indexable:
  Anchors must be indexable.
  severity: high

ariadne-anchor.context-pack-visible:
  Relevant anchors must be included in Context Packs.
  severity: high

ariadne-anchor.conductor-visible:
  Anchors must be visible to Conductor.
  severity: high

ariadne-anchor.rubric-visible:
  Anchors must be available to future Rubric Generator/Judge.
  severity: high

ariadne-anchor.canonical-prefix:
  Canonical prefix is @ariadne-*.
  severity: medium

ariadne-anchor.legacy-prefix-compatibility:
  @ariadna-* may be accepted as compatibility input if present in source materials.
  severity: medium

ariadne-anchor.no-secret-material:
  Anchors must not contain secrets/tokens/credentials.
  severity: critical

ariadne-anchor.not-authorization:
  Anchors are context/evidence, not execution authorization.
  severity: high
```

## Future anchors

PLAN must list future anchors:

```text
context-pack.schema-path
context-pack.required-structure
context-pack.no-raw-repository-dump
context-pack.no-invented-context
context-pack.source-trace.required
context-pack.domain-adapter-context.required
context-pack.validation-context.required
context-pack.no-secret-material
ariadne-anchor.schema-path
ariadne-anchor.indexable
ariadne-anchor.context-pack-visible
ariadne-anchor.conductor-visible
ariadne-anchor.rubric-visible
ariadne-anchor.canonical-prefix
ariadne-anchor.not-authorization
```

## Future contracts bundle update

Future implementation must update:

```text
.project-memory/context-bundles/contracts.yml
```

Required:

* bump bundle version according to existing style
* add `.project-memory/context-pack.schema.yml` to read_first
* add `.project-memory/ariadne-anchor.schema.yml` to read_first
* add `docs/CONTEXT_COMPILER.md` to read_first if docs files are included in bundle style
* add `docs/ARIADNE_ANCHORS.md` to read_first if docs files are included in bundle style
* add context-pack and ariadne-anchor anchors
* add notes:

  * context packs are structured context, not raw repository dumps
  * context compiler must not invent context
  * anchors are machine-readable semantic landmarks
  * anchors are included in context packs when relevant
  * anchors are not execution authorization
  * canonical anchor prefix is @ariadne-*
  * @ariadna-* is compatibility alias only if needed

## Future memory index update

Future implementation must update:

```text
.project-memory/memory_index.yml
```

Required:

* bump version according to existing style
* add label: `context-pack`
* description: `Context Pack schema and Semantic Context Decomposition contract for structured agent context.`
* additional_files:

  * `.project-memory/context-pack.schema.yml`
  * `docs/CONTEXT_COMPILER.md`
* preferred_agent: `architect`
* add or update label: `ariadne-anchors`
* description: `Ariadne Anchor schema and documentation for machine-readable semantic landmarks.`
* additional_files:

  * `.project-memory/ariadne-anchor.schema.yml`
  * `docs/ARIADNE_ANCHORS.md`
* preferred_agent: `architect`

## PR 0040 own review artifacts

PLAN must state:

* PR 0040 should create its own `reviews/plan-review.yml` after plan-review.
* PR 0040 should create its own `reviews/precommit-review.yml` after precommit-review.
* These artifacts must conform to `.project-memory/review-artifact.schema.yml`.
* These artifacts must be committed as part of PR 0040.
* No old PR review artifacts are created.

## Relationship to existing contracts

PLAN must state:

* Conductor Prompt Contract remains unchanged.
* Prompt Artifact schema remains unchanged.
* Domain Adapter schema remains unchanged.
* Review Artifact schema/workflow remains unchanged.
* Run Record remains execution evidence and is not replaced.
* Apply Gate remains write authorization and is not bypassed.
* Workspace Feature Records are not created.
* State-First contract remains unchanged.
* Model-routing contract remains unchanged.
* Runner remains unchanged.
* Agents configs remain unchanged.
* Context Pack will feed Conductor Prompt Contract in future runtime work, but runtime assembly is not implemented in PR 0040.
* Ariadne Anchors extend semantic context; they do not replace State-First annotations or existing invariants.

## Stop conditions

Stop if future implementation:

* modifies agents
* modifies services
* creates `.ariadne/**`
* creates `schemas/**`
* changes apply-gate semantics
* changes run-record semantics
* changes conductor prompt schema
* changes prompt artifact schema
* changes domain-adapter schema
* changes review-artifact schema/workflow
* changes state-first schema
* changes model-routing schema
* implements runtime Context Compiler
* implements anchor scanner
* implements AST/symbol extraction
* implements semantic search
* stores secrets in context or anchors
* creates raw repository dump context artifacts
* creates old PR review artifacts
* adds Docker/CI/root dependency changes

## Validation for future implementation

PLAN must require:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "context-pack\|CONTEXT_COMPILER\|ariadne-anchor\|ARIADNE_ANCHORS\|no-raw-repository-dump\|no-invented-context" .project-memory docs
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

Expected:

* pytest passes
* compileall passes
* runner doctor passes
* grep shows expected context-pack and anchor references
* import regression grep has no matches
* git status only contains expected PR 0040 files
* no generated artifacts
* no services/agents/runtime changes

## Expected changed files for planning task

```text
.project-memory/pr/0040-context-pack-anchors/PLAN.md
```

## Expected changed files for full PR

```text
.project-memory/context-pack.schema.yml
.project-memory/ariadne-anchor.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0040-context-pack-anchors/PLAN.md
.project-memory/pr/0040-context-pack-anchors/reviews/plan-review.yml
.project-memory/pr/0040-context-pack-anchors/reviews/precommit-review.yml
docs/CONTEXT_COMPILER.md
docs/ARIADNE_ANCHORS.md
```

## Context receipt requirement

Every agent response must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- base_sha_source:
- index_version:
- index_version_source:
- current_head:
- stale_snapshot:
- snapshot_verified:
- snapshot_verified_by:

DECISIONS MADE:
- None — followed PLAN.md exactly
- or <decision> — <reason>

CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files modified:
- files intentionally ignored:
```
