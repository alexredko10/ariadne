## Implementation note

PR 0039 implemented:
- Created `.project-memory/domain-adapter.schema.yml` with DomainAdapter, DomainCapability, DomainPolicy, DomainValidation, DomainArtifact, DomainApplyMechanism, DomainRollbackMechanism, DomainRisk, DomainStopCondition, DomainOutputFormat, DomainAdapterRegistry definitions, allowed domains, domain responsibilities, policies, Conductor Prompt Contract relationship, safety rules, and minimal valid Coding Adapter example
- Created `docs/adr/0004-ariadne-is-domain-agnostic.md` — decision that Ariadne Core is domain-agnostic and Coding is a Domain Adapter, not Core
- Created `docs/DOMAIN_ADAPTER_CONTRACT.md` documenting architecture, adapter responsibilities, examples for all 5 domains, and relationship to Conductor/Apply Gate/Run Record/Review Artifacts/State-First
- Added 19 `domain-adapter.*` contract entries to `.project-memory/project_contract.yml`
- Added 12 domain-adapter anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.15 with schema/ADR/docs in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.17 with new `domain-adapter` label

No runtime Domain Adapter implementation. No Coding Adapter execution. No apply/rollback implementation. No changes to agents, services, or existing schemas.# PR 0039: Domain Adapter Contract

## Goal

Define the Domain Adapter Contract for Ariadne.

This PR must establish that Ariadne Core is domain-agnostic.
The Conductor must not depend directly on:

```text
Git
patches
pytest
specific programming languages
specific file transforms
specific research tools
specific data validators
```

Those belong to Domain Adapters.

The Domain Adapter Contract must define how domain-specific policies provide:

```text
allowed_write_paths
forbidden_write_paths
validation_commands
execution_environment
artifact_types
apply_mechanism
rollback_mechanism
final_output_format
domain_specific_risks
domain_specific_stop_conditions
```

---

## Architectural thesis

```text
Conductor
  ↓
Domain Adapter
  ├── coding
  ├── document
  ├── data
  ├── research
  └── custom
```

Ariadne Core owns:
- purpose
- context
- contracts
- prompt artifacts
- checkpoints
- review artifacts
- verification contracts
- auditability

Domain Adapters own:
- execution environment
- allowed/forbidden paths
- validation commands
- artifact types
- apply/rollback mechanism
- domain risks
- domain stop conditions

The model is replaceable.
The domain adapter is pluggable.
The substrate is Ariadne.

---

## Context snapshot

```yaml
context_snapshot:
  base_sha: "76efc7cdfe8a1f65501d832a0fd02ff5a10d4583"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.16"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "76efc7cdfe8a1f65501d832a0fd02ff5a10d4583"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

---

## Snapshot policy

PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review must report snapshot deltas but must not block solely because current HEAD differs from PLAN.md base_sha, unless scope evidence shows unrelated or forbidden changes.
Review artifacts must include snapshot_delta fields according to `.project-memory/review-artifact.schema.yml`.

---

## Non-goals

```text
- no agents/** changes
- no services/** changes
- no runner changes
- no task_intake changes
- no model_gateway changes
- no .ariadne/** writes
- no runtime Domain Adapter implementation
- no Coding Adapter implementation
- no Document Adapter implementation
- no Data Adapter implementation
- no Research Adapter implementation
- no apply/rollback implementation
- no runtime Conductor changes
- no automatic prompt generation changes
- no PCAM/PBS/Rubric runtime implementation
- no apply-gate semantic changes
- no run-record semantic changes
- no Workspace Feature Record changes
- no Review Artifact schema changes
- no Conductor Prompt schema changes
- no Prompt Artifact schema changes
- no State-First schema changes
- no Model Routing schema changes
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

---

## Future allowed write paths for implementation

Implementation may modify/create only:

```text
.project-memory/domain-adapter.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0039-domain-adapter-contract/PLAN.md
.project-memory/pr/0039-domain-adapter-contract/reviews/plan-review.yml
.project-memory/pr/0039-domain-adapter-contract/reviews/precommit-review.yml
docs/DOMAIN_ADAPTER_CONTRACT.md
docs/adr/0004-ariadne-is-domain-agnostic.md
```

Notes:
- Prefer `.project-memory/domain-adapter.schema.yml` — consistent with existing contract schema location policy.
- Do not create `.ariadne/**` in this PR.
- Do not create `schemas/**` in this PR.
- `.project-memory/` remains current/legacy-compatible project memory.
- `.ariadne/` remains canonical long-term namespace but is not created in this PR.
- `docs/adr/0004-ariadne-is-domain-agnostic.md` is confirmed available: `0004` does not exist in the repository at PLAN creation time.

---

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
.project-memory/context-bundles/agent-config.yml
docs/** except:
  - docs/DOMAIN_ADAPTER_CONTRACT.md
  - docs/adr/0004-ariadne-is-domain-agnostic.md
```

---

## Required schema: Domain Adapter Contract

Future implementation must create:

```text
.project-memory/domain-adapter.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

The schema must define:

```text
DomainAdapter
DomainCapability
DomainPolicy
DomainValidation
DomainArtifact
DomainApplyMechanism
DomainRollbackMechanism
DomainRisk
DomainStopCondition
DomainOutputFormat
DomainAdapterRegistry
```

### Required DomainAdapter fields

```text
schema_version
domain
adapter_id
description
capabilities
allowed_write_paths
forbidden_write_paths
validation_commands
execution_environment
artifact_types
apply_mechanism
rollback_mechanism
final_output_format
risks
stop_conditions
human_approval_policy
```

### Allowed initial `domain` values

```text
coding
document
data
research
custom
```

### Required Coding Adapter responsibilities

- create worktree
- apply patch
- normalize diff
- run tests
- detect generated artifacts
- map source files to tests
- preserve protected paths
- report validation evidence

### Required Document Adapter responsibilities

- structured document edits
- document diff/apply
- citation preservation
- export validation
- formatting validation

### Required Data Adapter responsibilities

- dataset transforms
- profiling
- schema validation
- quality reports
- reversible transforms where possible

### Required Research Adapter responsibilities

- search
- synthesis
- citation graph
- claim verification
- source attribution
- uncertainty reporting

### Required Custom Adapter responsibilities

- user-defined execution environment
- explicit allowed/forbidden actions
- explicit validation policy
- explicit artifact policy
- explicit human approval boundary

### Required policies

- Ariadne Core must not depend directly on domain-specific tools.
- Git/patch/pytest are Coding Adapter concerns, not universal Core concerns.
- Domain Adapter provides policy inputs to Conductor Prompt Contract.
- Domain Adapter must provide `allowed_write_paths` and `forbidden_write_paths`.
- Domain Adapter must provide `validation_commands` or explicitly mark validation as not supported.
- Domain Adapter must define artifact types.
- Domain Adapter must define apply and rollback semantics, even if manual.
- Domain Adapter must define domain-specific risks and stop conditions.
- Domain Adapter must not bypass apply-gate.
- Domain Adapter must not bypass run-record.
- Domain Adapter must not contain secrets.
- If domain requires protected path changes, human approval is required.

### Required relation to Conductor Prompt Contract

Domain Adapter supplies these Prompt Contract sections:

```text
allowed_write_paths
forbidden_write_paths
validation_commands
final_output_format
domain_specific_stop_conditions
domain_specific_risks
```

---

## Required documentation

Future implementation must create:

```text
docs/DOMAIN_ADAPTER_CONTRACT.md
```

Documentation must explain:

- Ariadne Core is domain-agnostic
- Conductor is universal
- Domain Adapters are domain-specific
- coding is only one adapter
- why Core must not depend directly on Git/patch/pytest/language tools
- how Domain Adapter feeds Conductor Prompt Contract
- how Domain Adapter feeds Context Compiler
- how Domain Adapter feeds Review/Rubric Judge
- allowed/forbidden path policy
- validation command policy
- artifact policy
- apply/rollback policy
- human approval policy
- coding adapter example
- document adapter example
- data adapter example
- research adapter example
- custom adapter example
- relationship to Apply Gate
- relationship to Run Record
- relationship to Review Artifacts
- relationship to Conductor Prompt Contract
- relationship to State-First
- `.project-memory/` as current/legacy-compatible memory
- `.ariadne/` as long-term canonical namespace, not created in this PR

---

## Required ADR

Future implementation must create:

```text
docs/adr/0004-ariadne-is-domain-agnostic.md
```

ADR must include:

- title: `ADR 0004: Ariadne is domain-agnostic`
- status: `Accepted`
- date
- context
- decision
- consequences
- domain_adapter_boundary
- coding_adapter_boundary
- non_coding_domains
- relationship_to_conductor
- relationship_to_apply_gate
- relationship_to_run_record
- future_work

ADR decision must state:

- Ariadne Core is domain-agnostic.
- Coding is a Domain Adapter, not Core.
- Domain-specific execution belongs to adapters.
- Universal Core must not hardcode Git, patches, pytest, programming languages, document transforms, data validators, or research tools.
- Domain Adapters supply policies to Conductor Prompt Contract.
- Apply Gate and Run Record remain separate boundaries.

---

## Future contract IDs

The following contract IDs must be registered in `project_contract.yml`:

| Contract ID | Meaning | Severity |
|---|---|---|
| `domain-adapter.schema-path` | Schema: `.project-memory/domain-adapter.schema.yml` | medium |
| `domain-adapter.adr-path` | ADR: `docs/adr/0004-ariadne-is-domain-agnostic.md` | medium |
| `domain-adapter.core-domain-agnostic` | Ariadne Core must remain domain-agnostic. | high |
| `domain-adapter.coding-not-core` | Coding is a Domain Adapter, not universal Core. | high |
| `domain-adapter.policy-supplies-prompt-contract` | Domain Adapter supplies prompt policy sections to Conductor Prompt Contract. | high |
| `domain-adapter.allowed-write-paths.required` | Domain Adapter must define allowed_write_paths. | high |
| `domain-adapter.forbidden-write-paths.required` | Domain Adapter must define forbidden_write_paths. | high |
| `domain-adapter.validation-policy.required` | Domain Adapter must define validation_commands or explicitly mark validation as not supported. | high |
| `domain-adapter.artifact-types.required` | Domain Adapter must define artifact types. | high |
| `domain-adapter.apply-mechanism.required` | Domain Adapter must define apply mechanism. | high |
| `domain-adapter.rollback-mechanism.required` | Domain Adapter must define rollback mechanism. | high |
| `domain-adapter.stop-conditions.required` | Domain Adapter must define domain-specific stop conditions. | high |
| `domain-adapter.human-approval-policy.required` | Domain Adapter must define human approval policy. | high |
| `domain-adapter.no-core-git-dependency` | Ariadne Core must not depend directly on Git; Git belongs to Coding Adapter. | high |
| `domain-adapter.no-core-pytest-dependency` | Ariadne Core must not depend directly on pytest; test tools belong to Coding Adapter. | high |
| `domain-adapter.no-secret-material` | Domain Adapter contracts must not contain secrets/tokens/credentials. | critical |
| `domain-adapter.no-apply-gate-bypass` | Domain Adapter must not bypass Apply Gate. | critical |
| `domain-adapter.no-run-record-bypass` | Domain Adapter must not bypass or replace Run Record. | critical |

---

## Future anchors

The following anchors must be added to `.project-memory/anchors.yml` by implementation:

```text
domain-adapter.schema-path
domain-adapter.adr-path
domain-adapter.core-domain-agnostic
domain-adapter.coding-not-core
domain-adapter.policy-supplies-prompt-contract
domain-adapter.allowed-write-paths.required
domain-adapter.validation-policy.required
domain-adapter.no-core-git-dependency
domain-adapter.no-core-pytest-dependency
domain-adapter.no-secret-material
domain-adapter.no-apply-gate-bypass
domain-adapter.no-run-record-bypass
```

---

## Future contracts bundle update

Future implementation must update:

```text
.project-memory/context-bundles/contracts.yml
```

Required:
- bump bundle version according to existing style (current: `"0.14"` → `"0.15"`)
- add `.project-memory/domain-adapter.schema.yml` to `read_first`
- add `docs/DOMAIN_ADAPTER_CONTRACT.md` to `read_first` (consistent with ADR docs included in bundle style)
- add `docs/adr/0004-ariadne-is-domain-agnostic.md` to `read_first` (consistent with ADR docs included in bundle style)
- add all domain-adapter anchors
- add notes:
  - Ariadne Core is domain-agnostic
  - Coding is a Domain Adapter, not Core
  - Domain Adapter supplies allowed/forbidden paths and validation commands to Conductor Prompt Contract
  - Git/patch/pytest belong to Coding Adapter, not Core
  - Domain Adapter does not bypass Apply Gate
  - Domain Adapter does not replace Run Record

---

## Future memory index update

Future implementation must update:

```text
.project-memory/memory_index.yml
```

Required:
- bump version according to existing style (current: `"0.16"` → `"0.17"`)
- add label: `domain-adapter`
- description: `Domain Adapter Contract for separating Ariadne Core from domain-specific execution environments.`
- additional_files:
  - `.project-memory/domain-adapter.schema.yml`
  - `docs/DOMAIN_ADAPTER_CONTRACT.md`
  - `docs/adr/0004-ariadne-is-domain-agnostic.md`
- preferred_agent: `architect`

---

## PR 0039 own review artifacts

- PR 0039 should create its own `reviews/plan-review.yml` after plan-review.
- PR 0039 should create its own `reviews/precommit-review.yml` after precommit-review.
- These artifacts must conform to `.project-memory/review-artifact.schema.yml`.
- These artifacts must be committed as part of PR 0039.
- No old PR review artifacts are created.

---

## Relationship to existing contracts

- Conductor Prompt Contract remains unchanged.
- Prompt Artifact schema remains unchanged.
- Review Artifact schema remains unchanged.
- Review Artifact workflow remains unchanged.
- Run Record remains execution evidence and is not replaced.
- Apply Gate remains write authorization and is not bypassed.
- Workspace Feature Records are not created.
- State-First contract remains unchanged.
- Model-routing contract remains unchanged.
- Runner remains unchanged.
- Agent configs remain unchanged.
- Domain Adapter is referenced by Conductor Prompt Contract (PR 0038) but implemented only as contract/schema/docs in PR 0039.

---

## Stop conditions

Stop if future implementation:

- modifies agents
- modifies services
- creates `.ariadne/**`
- creates `schemas/**`
- changes apply-gate semantics
- changes run-record semantics
- changes conductor prompt schema
- changes prompt artifact schema
- changes review-artifact schema
- changes state-first schema
- changes model-routing schema
- implements runtime Domain Adapter
- implements Coding Adapter execution
- hardcodes Git/pytest into Core
- creates old PR review artifacts
- stores secrets in contracts
- adds Docker/CI/root dependency changes

---

## Validation for future implementation

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "domain-adapter\|DOMAIN_ADAPTER_CONTRACT\|ariadne-is-domain-agnostic\|coding-not-core\|no-core-git" .project-memory docs
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

Expected:
- pytest passes
- compileall passes
- runner doctor passes
- grep shows expected domain adapter references
- import regression grep has no matches
- git status only contains expected PR 0039 files
- no generated artifacts
- no services/agents/runtime changes

---

## Expected changed files for planning task

```text
.project-memory/pr/0039-domain-adapter-contract/PLAN.md
```

## Expected changed files for full PR

```text
.project-memory/domain-adapter.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0039-domain-adapter-contract/PLAN.md
.project-memory/pr/0039-domain-adapter-contract/reviews/plan-review.yml
.project-memory/pr/0039-domain-adapter-contract/reviews/precommit-review.yml
docs/DOMAIN_ADAPTER_CONTRACT.md
docs/adr/0004-ariadne-is-domain-agnostic.md
```
