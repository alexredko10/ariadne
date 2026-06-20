# PR 0041: Ariadne Architecture Blueprint

## Goal

Produce the first complete architecture blueprint for Ariadne as a substrate-first agentic software production platform.

This is not a coding task.

The implementation agent must produce:

* `ARIADNE_ARCHITECTURE.md`
* `ROADMAP.md`
* platform schemas under `schemas/**`
* ADRs under `docs/adr/**`

The output must allow:

1. a second planner agent to decompose the roadmap into concrete PRs/issues/commits
2. a third coder/architect agent to implement Phase 0 without ambiguity

## Architectural thesis

```text
Ariadne is not a chatbot wrapper.
Ariadne is not a model-centered agent framework.
Ariadne is an execution substrate for agentic software production.

The model is replaceable.
The substrate is the product.
```

Durable substrate includes:

```text
run state
step boundaries
checkpoints
recovery
audit logs
cached repository understanding
context packs
state models
transition graphs
purpose decomposition
rubrics
verification contracts
model routing
human approval boundaries
domain adapters
```

## Context snapshot

```yaml
context_snapshot:
  base_sha: "dd0de461e88517f8a91b78df2dffd908451bc05d"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.18"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "dd0de461e88517f8a91b78df2dffd908451bc05d"
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
- no implementation code
- no services/** changes
- no agents/** changes
- no packages/** changes
- no apps/** changes
- no .project-memory/** changes during blueprint implementation
- no .ariadne/** writes
- no runtime orchestrator implementation
- no runtime Context Core implementation
- no runtime State Core implementation
- no runtime PCAM/PBS implementation
- no runtime Rubric Judge implementation
- no runtime Model Router implementation
- no Docker/CI/workflow changes
- no root dependency changes
- no production secrets
- no automatic deployment
- no automatic merge
- no GRPO/PPO/RL implementation
```

## Future allowed write paths for implementation

Implementation may create/update only:

```text
ARIADNE_ARCHITECTURE.md
ROADMAP.md
schemas/purpose.schema.yml
schemas/pbs.schema.yml
schemas/context-pack.schema.yml
schemas/state-model.schema.yml
schemas/transition-graph.schema.yml
schemas/rubric-pack.schema.yml
schemas/rubric-judge-result.schema.yml
schemas/model-capability-profile.schema.yml
schemas/agent-execution-contract.schema.yml
schemas/run-state.schema.yml
schemas/checkpoint.schema.yml
schemas/long-context-stress-profile.schema.yml
schemas/final-report.schema.yml
docs/adr/0005-rubrics-as-runtime-contracts.md
docs/adr/0006-model-replaceability.md
docs/adr/0007-cached-repository-understanding.md
```

ADR 0004 policy:

* The repository already contains `docs/adr/0004-ariadne-is-domain-agnostic.md`.
* Implementation must NOT overwrite it and must NOT create a competing `0004-*` file.
* `ARIADNE_ARCHITECTURE.md` must reference the existing ADR 0004.
* No `docs/adr/0004-ariadne-domain-agnostic.md` is created.

Operational review artifacts:

* PR 0041 plan-review may write:
  `.project-memory/pr/0041-architecture-blueprint/reviews/plan-review.yml`
* PR 0041 precommit-review may write:
  `.project-memory/pr/0041-architecture-blueprint/reviews/precommit-review.yml`
* The blueprint implementation agent itself must not modify `.project-memory/**`.

## Future forbidden write paths for implementation

Implementation must not modify/create:

```text
.project-memory/**
agents/**
services/**
packages/**
apps/**
.ariadne/**
.github/**
docker/**
Dockerfile*
pyproject.toml
package.json
Makefile
.env
.env.*
```

Implementation must not modify existing operational schemas in `.project-memory/**`.

## Required output: ARIADNE_ARCHITECTURE.md

Future implementation must create:

```text
ARIADNE_ARCHITECTURE.md
```

It must contain these sections in order:

```text
1. Project Identity and Core Principles
2. Architectural Thesis
3. Existing Implementation Status
4. Full Subsystem Map
5. Data Artifact Schemas
6. Ariadne Anchors
7. Conductor and Prompt Contract
8. Context Core Design
9. State-First Design
10. PCAM/PBS Design
11. Rubrics as Runtime Contracts
12. Model Routing Design
13. Domain Adapter Architecture
14. Agent Execution Contract
15. Security Model
16. Verification Layer
17. Final Report Format
18. Risks and Open Questions
19. Research References
```

Required content:

* Use name `Ariadne`.
* State Sprint 0–1 evidence from existing implementation:

  * `services/runner`
  * `services/task_intake`
  * `services/model_gateway`
  * `.project-memory/**` contracts
  * existing ADRs
* Include gap analysis from current repository to full substrate.
* Include full subsystem map:

```text
ariadne/
  runtime/
  context_core/
  state_core/
  pcam/
  model_router/
  agent_runtime/
  domain_adapters/
  verifier/
  artifacts/
```

* Reference existing `.project-memory/**` contracts where they already exist.
* Reference new `schemas/**` files written in this PR.
* Explain how artifacts flow:

```text
purpose.json
→ pbs.json
→ context_pack.json
→ state_model.json + transition_graph.json
→ rubric_pack.json
→ agent_execution_contract
→ run_state + checkpoints
→ review_artifact
→ rubric_judge_result
→ final_report
```

## Required output: ROADMAP.md

Future implementation must create:

```text
ROADMAP.md
```

It must include phased commit plan:

```text
Phase 0: Architecture Contracts
Phase 1: Runtime Substrate
Phase 2: Ariadne Context Core
Phase 3: State Core
Phase 4: PCAM/PBS
Phase 5: Rubrics as Rewards Runtime
Phase 6: Model Router
Phase 7: Agent Runtime
Phase 8: Domain Adapters
Phase 9: Verification and Reports
Phase 10: Dataset/Eval Export
```

For each phase include:

* deliverables
* acceptance criteria
* dependencies
* estimated PR count
* risks
* implementation boundary

## Required output: schemas/

Future implementation must create platform schemas under `schemas/**`.

Each schema document must:

* use YAML
* include `schema_version: "0.1"`
* include field descriptions as YAML comments
* include type annotations as YAML comments
* document enum values
* document relationships to other schemas
* document storage path convention
* document safety rules
* document invalid cases
* include minimal valid example as commented YAML

Schemas to create:

```text
schemas/purpose.schema.yml
schemas/pbs.schema.yml
schemas/context-pack.schema.yml
schemas/state-model.schema.yml
schemas/transition-graph.schema.yml
schemas/rubric-pack.schema.yml
schemas/rubric-judge-result.schema.yml
schemas/model-capability-profile.schema.yml
schemas/agent-execution-contract.schema.yml
schemas/run-state.schema.yml
schemas/checkpoint.schema.yml
schemas/long-context-stress-profile.schema.yml
schemas/final-report.schema.yml
```

Required schema themes:

purpose:

* root purpose
* task type
* goals
* non-goals
* constraints
* risk
* human owner
* success definition

pbs:

* purpose breakdown structure
* tree of purpose nodes
* each agent task references purpose_id
* root purpose changes require human approval

context-pack:

* task context
* relevant files/symbols/tests/configs
* invariants
* risks
* stable prompt blocks
* anchors
* state-first context
* base_sha
* index_version
* no secrets

state-model:

* durable state entities
* derived views
* storage enum
* invariants

transition-graph:

* transitions
* preconditions/postconditions
* invariants
* side effects
* emitted events
* transaction boundary
* idempotency
* rollback behavior

rubric-pack:

* local rubrics per PBS node
* essential/important/optional/pitfalls/evidence/stop conditions
* human approval triggers
* size guideline

rubric-judge-result:

* verdict
* score
* essential_passed
* pitfalls_triggered
* required fixes
* human approval
* insufficient evidence rule

model-capability-profile:

* role scores
* context capability scores
* operational profile
* evidence
* no vendor hardcoding as contract value

long-context-stress-profile:

* retrieval
* aggregation
* graph_reasoning
* QA
* ICL
* long_code
* memory_use
* mitigations

agent-execution-contract:

* role
* purpose
* pbs_node
* context_pack
* state_model
* transition_graph
* rubric
* domain_adapter
* allowed/forbidden actions
* stop conditions
* output contract
* evidence for claims

run-state:

* run status
* step records
* model used
* cost
* artifacts
* checkpoint
* failure mode
* resumability
* no secrets

checkpoint:

* immutable checkpoint
* run_state_hash
* artifact ids
* memory_snapshot_hash
* resume instructions
* no secrets

final-report:

* root purpose
* PBS summary
* model routing
* context used
* state model
* transition graph
* rubrics
* changes
* verification
* rubric judge results
* risks
* human approval
* cost
* next steps
* why changes satisfy purpose

## Required output: ADRs

Future implementation must create or reference ADRs.

Existing ADR 0004 policy:

* `docs/adr/0004-ariadne-is-domain-agnostic.md` already exists.
* Reference it in ARIADNE_ARCHITECTURE.md. Do not duplicate 0004.
* Do not create `docs/adr/0004-ariadne-domain-agnostic.md`.

Future implementation must create:

```text
docs/adr/0005-rubrics-as-runtime-contracts.md
docs/adr/0006-model-replaceability.md
docs/adr/0007-cached-repository-understanding.md
```

ADR 0005:

* Status: Accepted
* Rubrics are runtime contracts, not docs.
* MVP: no RL training.
* Future: rubric packs and judge reports may become eval/training data.

ADR 0006:

* Status: Accepted
* Model is replaceable.
* No vendor lock-in.
* Use capability profiles over rankings.
* Route by role/context/risk/cost/latency/history.

ADR 0007:

* Status: Accepted
* Repository understanding is a platform-owned asset.
* Built once, cached, invalidated on diff, reused across runs.
* Context Core is first-class subsystem.
* Models receive context packs, not raw repo dumps.

## Research references to include

PLAN must require architecture document to reference and apply:

```text
Rubrics as Rewards
Transformers represent belief state geometry
ATLAS Long-Context Benchmark
The Bitter Lesson
React / UI = F(State)
Chu Spaces / State-Event Duality
```

Use research as conceptual grounding, not as proof of implementation.

## Security and safety constraints

PLAN must require architecture document to include:

* no privileged containers
* no Docker socket mount
* no production secrets in agent context
* read-only repo access for review agents
* write access only in sandbox for coder/tester agents
* all shell commands logged
* all file changes diffed
* network access policy-controlled
* agent identities not equal human identities
* protected file changes require approval
* high-risk changes require independent reviewer + security scan + rubric judge + human approval

## Stop conditions for future implementation

Stop if future implementation:

* modifies `.project-memory/**`
* modifies `agents/**`
* modifies `services/**`
* modifies packages/apps
* writes implementation code
* hardcodes a model vendor as a contract value
* creates `.ariadne/**`
* changes root dependencies/build/CI
* introduces production secrets
* overwrites existing ADR numbering
* duplicates ADR 0004 if it already exists
* uses GRACE as project identity
* calls Ariadne a chatbot wrapper
* calls Ariadne model-centered

## Validation for future implementation

PLAN must require:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
python - <<'PY'
from pathlib import Path
import yaml

paths = [
    "schemas/purpose.schema.yml",
    "schemas/pbs.schema.yml",
    "schemas/context-pack.schema.yml",
    "schemas/state-model.schema.yml",
    "schemas/transition-graph.schema.yml",
    "schemas/rubric-pack.schema.yml",
    "schemas/rubric-judge-result.schema.yml",
    "schemas/model-capability-profile.schema.yml",
    "schemas/agent-execution-contract.schema.yml",
    "schemas/run-state.schema.yml",
    "schemas/checkpoint.schema.yml",
    "schemas/long-context-stress-profile.schema.yml",
    "schemas/final-report.schema.yml",
]
for p in paths:
    data = yaml.safe_load(Path(p).read_text())
    assert data["schema_version"] == "0.1", p
print("schemas ok")
PY
grep -R -n "GRACE\|Grace" ARIADNE_ARCHITECTURE.md ROADMAP.md schemas docs/adr || true
grep -R -n "Ariadne\|substrate\|replaceable\|checkpoint\|rubric\|context pack" ARIADNE_ARCHITECTURE.md ROADMAP.md schemas docs/adr
git status --short
git diff --name-only
```

Expected:

* pytest passes
* compileall passes
* runner doctor passes
* schemas parse as YAML
* schema_version is `0.1`
* no GRACE identity usage
* expected Ariadne/substrate references found
* git status only contains expected PR 0041 files
* no `.project-memory/**` modifications except PLAN/review artifacts
* no agents/services changes
* no generated artifacts

## Expected changed files for planning task

```text
.project-memory/pr/0041-architecture-blueprint/PLAN.md
```

## Expected changed files for full PR

```text
ARIADNE_ARCHITECTURE.md
ROADMAP.md
schemas/purpose.schema.yml
schemas/pbs.schema.yml
schemas/context-pack.schema.yml
schemas/state-model.schema.yml
schemas/transition-graph.schema.yml
schemas/rubric-pack.schema.yml
schemas/rubric-judge-result.schema.yml
schemas/model-capability-profile.schema.yml
schemas/agent-execution-contract.schema.yml
schemas/run-state.schema.yml
schemas/checkpoint.schema.yml
schemas/long-context-stress-profile.schema.yml
schemas/final-report.schema.yml
docs/adr/0005-rubrics-as-runtime-contracts.md
docs/adr/0006-model-replaceability.md
docs/adr/0007-cached-repository-understanding.md
.project-memory/pr/0041-architecture-blueprint/PLAN.md
.project-memory/pr/0041-architecture-blueprint/reviews/plan-review.yml
.project-memory/pr/0041-architecture-blueprint/reviews/precommit-review.yml
```

Conditional expected file:

* `docs/adr/0004-ariadne-domain-agnostic.md` — NOT created. Existing `docs/adr/0004-ariadne-is-domain-agnostic.md` is referenced instead.

## PR 0041 own review artifacts

PLAN must state:

* PR 0041 should create its own `reviews/plan-review.yml` after plan-review.
* PR 0041 should create its own `reviews/precommit-review.yml` after precommit-review.
* These artifacts must conform to `.project-memory/review-artifact.schema.yml`.
* These artifacts must be committed as part of PR 0041.
* No old PR review artifacts are created.

## Relationship to existing contracts

PLAN must state:

* Existing `.project-memory/**` contracts are read-only inputs for PR 0041 implementation.
* This PR creates platform-level blueprint schemas under `schemas/**`.
* This PR does not replace existing operational `.project-memory/**` schemas.
* Future planner PR will decide which platform schemas should be integrated into `.project-memory/**`.
* Existing Conductor Prompt, Prompt Artifact, Domain Adapter, Context Pack, Ariadne Anchor, Review Artifact, State-First, Model Routing, Apply Gate, Run Record contracts remain unchanged.

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
- ADRs inspected:
- implementation files inspected:
- files modified:
- files intentionally ignored:
```
