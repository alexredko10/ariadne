## Implementation note

PR 0038 implemented:
- Created `.project-memory/conductor-prompt-contract.schema.yml` with ConductorPromptContract, PromptSection, PromptSectionSource, PromptGenerationPolicy, PromptValidationPolicy, PromptHashPolicy, required sections, section sources, source registry, policies, safety rules, and minimal valid example
- Created `.project-memory/prompt-artifact.schema.yml` with PromptArtifact, PromptMemorySnapshot, PromptSections, PromptAudit, PromptSourceTrace definitions, hash policies, safety rules, and minimal valid example
- Created `docs/CONDUCTOR_PROMPT_CONTRACT.md` documenting architectural thesis, prompt lifecycle, source mapping, replay/audit behavior, and model-agnostic substrate principle
- Added 13 `conductor-prompt.*` contract entries to `.project-memory/project_contract.yml`
- Added 9 conductor-prompt anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.14 with schemas and doc in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.16 with new `conductor-prompt` label

No runtime Conductor implementation. No automatic prompt generator. No Domain Adapter. No PCAM/PBS/Rubric runtime. No changes to agents, services, or existing schemas.# PR 0038: Conductor Prompt Contract

## Goal

Define the Conductor Prompt Contract and Prompt Artifact Contract.

This PR must establish that prompts are not hand-written ephemeral strings.
Prompts must be machine-readable, reproducible, hashable, auditable, and generated from known Ariadne substrate sources:

```text
task intake
project contract
anchors
memory index
context bundles
repository graph
semantic index
domain adapter
PCAM purpose
PBS node
rubric package
nt contract
```

The Conductor must not invent context.
The Conductor must assemble prompts from known sources and preserve a prompt artifact that can be replayed and audited.

---

## Architectural thesis

Most agent frameworks put the model at the center.
Ariadne must not.

In Ariadne, the model is replaceable. The durable layer is the execution substrate:

- run state
- step boundaries
- checkpoints
- recovery
- auditability
- prompt contracts
- domain contracts
- cached repository understanding
- semantic anchors
- context packs
- purpose decomposition
- rubrics
- review artifacts
- verification contracts

The substrate is the product.
The model is a configuration decision.

---

## Context snapshot

```yaml
context_snapshot:
  base_sha: "80c2bdc7ac0f3768341852a14385a991d148f0da"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.15"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "80c2bdc7ac0f3768341852a14385a991d148f0da"
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
- no runtime conductor implementation
- no automatic prompt generator implementation
- no domain adapter implementation
- no PCAM/PBS implementation
- no rubric judge implementation
- no cached repository understanding implementation
- no production model routing changes
- no apply-gate semantic changes
- no run-record semantic changes
- no Workspace Feature Record changes
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

---

## Future allowed write paths for implementation

Implementation may modify/create only:

```text
.project-memory/conductor-prompt-contract.schema.yml
.project-memory/prompt-artifact.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0038-conductor-prompt-contract/PLAN.md
.project-memory/pr/0038-conductor-prompt-contract/reviews/plan-review.yml
.project-memory/pr/0038-conductor-prompt-contract/reviews/precommit-review.yml
docs/CONDUCTOR_PROMPT_CONTRACT.md
```

Notes:
- Prefer `.project-memory/*.schema.yml` because current repository contracts live in project memory.
- Do not create `.ariadne/**` in this PR.
- Do not create `schemas/**` unless the repository already has an established `schemas/` convention and PLAN explicitly justifies it.
- `.project-memory/` remains current/legacy-compatible project memory.
- `.ariadne/` remains canonical long-term namespace but is not created in this PR.

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
.project-memory/context-bundles/agent-config.yml
docs/** except:
  - docs/CONDUCTOR_PROMPT_CONTRACT.md
schemas/**
```

---

## Required schema: Conductor Prompt Contract

Future implementation must create:

```text
.project-memory/conductor-prompt-contract.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

The schema must define:

```text
ConductorPromptContract
PromptSection
PromptSectionSource
PromptGenerationPolicy
PromptValidationPolicy
PromptHashPolicy
```

### Required prompt sections

```text
task_description
agent_role
mode
cold_read_protocol
context_snapshot
purpose
pbs_node
rubric
allowed_write_paths
forbidden_write_paths
required_behavior
stop_conditions
validation_commands
final_output_format
```

### Required artifact fields exposed by prompt contract

```text
task_id
prompt_id
agent_id
domain
model_profile
context_bundle_ids
memory_snapshot_hash
generated_prompt_hash
created_at
prompt_contract_version
```

### Required section sources

```text
task_description:       task_intake
context_snapshot:       context_compiler
purpose:                pcam.purpose_extractor
pbs_node:               pcam.pbs_builder
rubric:                 pcam.rubric_generator
allowed_write_paths:    domain_adapter.policy
forbidden_write_paths:  domain_adapter.policy
validation_commands:    domain_adapter.validation
final_output_format:    agent_contract
```

### Required source registry

The Conductor may assemble context only from known sources:

```text
task_intake
project_contract
anchors
memory_index
context_bundles
repository_graph
semantic_index
domain_adapter
pcam_purpose
pbs_node
rubric_pack
nt_contract
state_first_context
review_artifact_contract
```

### Required policies

- Conductor must not invent context.
- Generated prompt must be reproducible from Prompt Artifact.
- If Prompt Artifact changes, `generated_prompt_hash` must change.
- Prompt Contract version must be explicit.
- Prompt sections must be traceable to `section_sources`.
- Missing required source must be represented as `missing/blocked`, not silently invented.
- Prompt generation is evidence-producing, not write authorization.
- Prompt artifact does not bypass apply-gate.
- Prompt artifact does not replace run-record.

---

## Required schema: Prompt Artifact

Future implementation must create:

```text
.project-memory/prompt-artifact.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

The schema must define:

```text
PromptArtifact
PromptMemorySnapshot
PromptSections
PromptAudit
PromptSourceTrace
```

### Required PromptArtifact fields

```text
prompt_id
task_id
agent_id
agent_role
domain
mode
model_profile
prompt_contract_version
memory_snapshot
sections
audit
```

### Required memory_snapshot fields

```text
memory_snapshot_hash
context_bundle_ids
anchors_hash
project_contract_hash
memory_index_hash
domain_adapter_hash
rubric_pack_hash
state_first_context_hash
```

### Required sections fields

```text
task_description
agent_role
mode
cold_read_protocol
context_snapshot
purpose
pbs_node
rubric
allowed_write_paths
forbidden_write_paths
required_behavior
stop_conditions
validation_commands
final_output_format
```

### Required audit fields

```text
created_at
generated_by
generated_prompt_hash
source_trace
```

### Required PromptSourceTrace fields

```text
section
source
source_id
source_hash
required
present
```

### Required rules

- Generated prompt must be reproducible from artifact.
- Hash must change when any section changes.
- Hash must change when any memory snapshot component changes.
- Source trace must identify missing required sources.
- Prompt artifact must not contain secrets.
- Prompt artifact must not contain unbounded repository dumps.
- Prompt artifact must reference context packs rather than embedding excessive raw context.

---

## Documentation requirement

Future implementation must create:

```text
docs/CONDUCTOR_PROMPT_CONTRACT.md
```

Documentation must explain:

- why prompts are artifacts, not ephemeral strings
- Conductor responsibility
- section source mapping
- prompt contract lifecycle
- prompt artifact lifecycle
- hash/replay/audit behavior
- relationship to Domain Adapter
- relationship to PCAM/PBS
- relationship to Rubric Rewards
- relationship to Context Compiler
- relationship to State-First
- relationship to review artifacts
- `.project-memory/` as current/legacy-compatible project memory
- `.ariadne/` as long-term canonical namespace, not created in this PR
- model-agnostic principle: model is configuration; substrate is product

---

## Future contract IDs

PLAN lists the following future contract IDs to be registered in `project_contract.yml` and `anchors.yml`:

| Contract ID | Meaning | Severity |
|---|---|---|
| `conductor-prompt.contract.schema-path` | Schema: `.project-memory/conductor-prompt-contract.schema.yml` | medium |
| `conductor-prompt.artifact.schema-path` | Schema: `.project-memory/prompt-artifact.schema.yml` | medium |
| `conductor-prompt.required-sections` | Generated prompts must include all required prompt sections. | high |
| `conductor-prompt.section-sources.required` | Every prompt section must trace to a known source. | high |
| `conductor-prompt.no-invented-context` | Conductor must not invent context or silently fill missing required sources. | critical |
| `conductor-prompt.prompt-hash.required` | Generated prompt hash is required for replay/audit. | high |
| `conductor-prompt.memory-snapshot-hash.required` | Prompt artifact must include memory_snapshot_hash. | high |
| `conductor-prompt.replayable-artifact.required` | Generated prompt must be reproducible from Prompt Artifact. | high |
| `conductor-prompt.no-secret-material` | Prompt artifacts must not include secrets/tokens/credentials. | critical |
| `conductor-prompt.no-raw-repository-dump` | Prompt artifacts must use structured context packs, not unbounded repository dumps. | high |
| `conductor-prompt.no-apply-gate-bypass` | Prompt artifacts do not authorize writes or bypass apply-gate. | critical |
| `conductor-prompt.no-run-record-bypass` | Prompt artifacts do not replace run-record. | critical |
| `conductor-prompt.model-agnostic-substrate` | Prompt contracts are model-agnostic substrate artifacts. | high |

---

## Future anchors

The following anchors must be added to `.project-memory/anchors.yml` by implementation:

```text
conductor-prompt.contract.schema-path
conductor-prompt.artifact.schema-path
conductor-prompt.required-sections
conductor-prompt.section-sources.required
conductor-prompt.no-invented-context
conductor-prompt.replayable-artifact.required
conductor-prompt.no-secret-material
conductor-prompt.no-apply-gate-bypass
conductor-prompt.model-agnostic-substrate
```

---

## Future contracts bundle update

Future implementation must update:

```text
.project-memory/context-bundles/contracts.yml
```

Required:
- bump bundle version according to existing style (current: `"0.13"` → `"0.14"`)
- add `.project-memory/conductor-prompt-contract.schema.yml` to `read_first`
- add `.project-memory/prompt-artifact.schema.yml` to `read_first`
- add `docs/CONDUCTOR_PROMPT_CONTRACT.md` to `read_first` (consistent with ADR files already included in bundle)
- add all conductor-prompt anchors to `anchors:`
- add notes:
  - prompts are replayable artifacts, not ephemeral strings
  - Conductor must not invent context
  - Prompt Artifact must include `generated_prompt_hash` and `memory_snapshot_hash`
  - model is replaceable; substrate is Ariadne
  - no apply-gate/run-record bypass

---

## Future memory index update

Future implementation must update:

```text
.project-memory/memory_index.yml
```

Required:
- bump version according to existing style (current: `"0.15"` → `"0.16"`)
- add label: `conductor-prompt`
- description: `Conductor Prompt Contract and Prompt Artifact schema for reproducible model-agnostic prompt generation.`
- additional_files:
  - `.project-memory/conductor-prompt-contract.schema.yml`
  - `.project-memory/prompt-artifact.schema.yml`
  - `docs/CONDUCTOR_PROMPT_CONTRACT.md`
- preferred_agent: `architect`

---

## PR 0038 own review artifacts

- PR 0038 should create its own `reviews/plan-review.yml` after plan-review.
- PR 0038 should create its own `reviews/precommit-review.yml` after precommit-review.
- These artifacts must conform to `.project-memory/review-artifact.schema.yml`.
- These artifacts must be committed as part of PR 0038.
- No old PR review artifacts are created.

---

## Relationship to existing contracts

- Review Artifact schema remains unchanged.
- Review Artifact workflow remains unchanged.
- Run Record remains execution evidence and is not replaced.
- Apply Gate remains write authorization and is not bypassed.
- Workspace Feature Records are not created.
- State-First contract remains unchanged.
- Model-routing contract remains unchanged.
- Runner remains unchanged.
- Agent configs remain unchanged.
- Domain Adapter is referenced but not implemented in PR 0038.
- PCAM/PBS/Rubrics are referenced but not implemented in PR 0038.

---

## Stop conditions

Stop if future implementation:

- modifies agents
- modifies services
- creates `.ariadne/**`
- changes apply-gate semantics
- changes run-record semantics
- changes review-artifact schema
- changes review-artifact workflow
- changes state-first schema
- changes model-routing schema
- implements runtime Conductor
- implements automatic prompt generation
- implements Domain Adapter
- implements PCAM/PBS/Rubric runtime
- creates old PR review artifacts
- stores secrets in prompt artifacts
- introduces raw repository dump as prompt artifact content
- adds Docker/CI/root dependency changes

---

## Validation for future implementation

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "conductor-prompt\|prompt-artifact\|CONDUCTOR_PROMPT_CONTRACT\|generated_prompt_hash\|memory_snapshot_hash" .project-memory docs
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

Expected:
- pytest passes
- compileall passes
- runner doctor passes
- grep shows expected conductor prompt references
- import regression grep has no matches
- git status only contains expected PR 0038 files
- no generated artifacts
- no services/agents/runtime changes

---

## Expected changed files for planning task

```text
.project-memory/pr/0038-conductor-prompt-contract/PLAN.md
```

## Expected changed files for full PR

```text
.project-memory/conductor-prompt-contract.schema.yml
.project-memory/prompt-artifact.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0038-conductor-prompt-contract/PLAN.md
.project-memory/pr/0038-conductor-prompt-contract/reviews/plan-review.yml
.project-memory/pr/0038-conductor-prompt-contract/reviews/precommit-review.yml
docs/CONDUCTOR_PROMPT_CONTRACT.md
```
