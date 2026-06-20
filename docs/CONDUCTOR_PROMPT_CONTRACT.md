# Conductor Prompt Contract

## Architectural thesis: substrate over model

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

## Why prompts must be artifacts, not ephemeral strings

Manual prompt conventions do not scale when:

- multiple agents generate prompts from different sources
- prompt sources evolve independently
- a PR must be replayed after the model changes
- an audit must confirm the agent received the correct context
- a test must reproduce an exact prompt from a past run

A **Prompt Artifact** solves this by capturing all prompt sections,
source references, hashes, and audit metadata in a durable, machine-readable
structure.

## Conductor responsibility

The Conductor is responsible for:

1. Receiving a task from Task Intake (via future handoff contract).
2. Loading required context from known Ariadne substrate sources.
3. Assembling prompt sections from those sources.
4. Producing a `PromptArtifact` with all section content, source traces, and hashes.
5. Returning the assembled prompt together with its artifact.

The Conductor must not invent context.
Missing required sources must be represented as `missing/blocked`, not silently filled.

## Required prompt sections

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

## Section source mapping

| Section               | Source                        |
|-----------------------|-------------------------------|
| task_description      | task_intake                   |
| context_snapshot      | context_compiler              |
| purpose               | pcam.purpose_extractor        |
| pbs_node              | pcam.pbs_builder              |
| rubric                | pcam.rubric_generator         |
| allowed_write_paths   | domain_adapter.policy         |
| forbidden_write_paths | domain_adapter.policy         |
| validation_commands   | domain_adapter.validation     |
| final_output_format   | agent_contract                |

## Known source registry

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
agent_contract
state_first_context
review_artifact_contract
```

## Prompt contract lifecycle

1. **Task intake** — task is validated and accepted.
2. **Context loading** — Conductor reads known sources.
3. **Prompt assembly** — Conductor assembles sections from sources.
4. **Prompt validation** — sections validated against contract.
5. **Prompt artifact creation** — artifact with sections, traces, hashes.
6. **Agent execution** — agent receives prompt and artifact.
7. **Execution result** — run record captures evidence.
8. **Review** — review artifact may reference the prompt artifact.

## Prompt artifact lifecycle

1. **Create** — artifact is created with prompt content and audit metadata.
2. **Store** — artifact must be stored with the PR (e.g., as review artifact or run record attachment).
3. **Replay** — artifact can be replayed by reassembling sections without calling model.
4. **Audit** — artifact contains `generated_prompt_hash` and `memory_snapshot_hash` for integrity.
5. **Reference** — future review artifacts and run records may reference the prompt artifact.

## Hash/replay/audit behavior

- `generated_prompt_hash` is computed from assembled prompt sections.
- `memory_snapshot_hash` is computed from memory snapshot components.
- Both must change when any component changes.
- Replay means reassembling the prompt from the artifact without model calls.
- Audit means verifying that the prompt received by the agent matches the artifact.

## Relationship to existing contracts

- **Review Artifacts** — review artifacts may reference prompt artifact IDs to document what prompt was reviewed.
- **Apply Gate** — prompt artifacts do not bypass apply-gate; do not authorize writes.
- **Run Record** — prompt artifacts do not replace run records; run records capture execution evidence.
- **State-First** — prompt generation is a state transformation (context → prompt), not a side effect.
- **Domain Adapter** — domain adapter provides policy and validation sources for prompt sections.
- **PCAM/PBS** — PCAM purpose extractor, PBS builder, and rubric generator are future sources for prompt sections.
- **Context Compiler** — context compiler assembles context bundles from memory index and sources.
- **Model Gateway** — prompt artifacts pass through model gateway for routing.

## Model-agnostic principle

```text
The model is replaceable.
The substrate is Ariadne.
```

A prompt contract is a model-agnostic substrate artifact.
It does not reference a specific model vendor.
It does not contain model-specific formatting.
It contains the structured context that any compatible model can use.

## Current and future storage

- `.project-memory/` — current/legacy-compatible project memory for contracts and schemas.
- `.ariadne/` — long-term canonical namespace for runtime artifacts. Not created in this PR.
- Prompt artifacts should be stored with the PR they belong to, consistent with review artifact conventions.
