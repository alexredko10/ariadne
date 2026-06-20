# Domain Adapter Contract

## Architectural thesis

```
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
- purpose decomposition
- context compilation
- contracts
- prompt artifacts
- checkpoints
- review artifacts
- verification contracts
- auditability

Domain Adapters own:
- execution environment
- allowed/forbidden write paths
- validation commands
- artifact types
- apply/rollback mechanism
- domain-specific risks
- domain-specific stop conditions
- human approval policy

The model is replaceable.
The domain adapter is pluggable.
The substrate is Ariadne.

## Why Core must be domain-agnostic

If Ariadne Core depends directly on Git, patches, pytest, and programming
language tools, it cannot extend to:

- document editing (structured document Diffs, citation validation)
- data analysis (dataset transforms, profiling, schema validation)
- research (search, citation graph, claim verification)
- custom domains (user-defined tools and environments)

## How Domain Adapter feeds Conductor Prompt Contract

The Domain Adapter supplies these sections to the Conductor Prompt
Contract (see `.project-memory/conductor-prompt-contract.schema.yml`):

| Prompt section               | Domain Adapter source               |
|------------------------------|-------------------------------------|
| allowed_write_paths          | DomainPolicy                        |
| forbidden_write_paths        | DomainPolicy                        |
| validation_commands          | DomainValidation                    |
| final_output_format          | DomainOutputFormat                  |
| domain_specific_stop_conditions | DomainStopCondition list         |
| domain_specific_risks        | DomainRisk list                     |

## How Domain Adapter feeds Context Compiler

The Domain Adapter defines:

- allowed write paths → used by context compiler to scope context
- forbidden write paths → used by context compiler to filter forbidden files
- validation commands → used by context compiler to include test commands
- domain-specific risks → included in task context

## How Domain Adapter feeds Review/Rubric Judge

The Domain Adapter defines:

- artifact types → reviewed by Rubric Judge
- final output format → checked by review workflow
- domain-specific risks → checked by domain-aware review

## Allowed/forbidden path policy

Every Domain Adapter must define:

- `allowed_write_paths`: paths the agent may write to
- `forbidden_write_paths`: paths the agent must not write to

If a domain requires protected path changes (e.g., configuration outside
allowed paths), human approval is required.

## Validation command policy

Every Domain Adapter must either:

- define `validation_commands`: list of commands to validate the output, or
- explicitly set `validation_not_supported_explicit: true` if the domain
  has no automated validation.

Validation commands are executed by the runner after apply.

## Artifact policy

Every Domain Adapter must define `artifact_types`:

- `type`: artifact type identifier
- `description`: human-readable description
- `path_pattern`: optional path pattern for artifact location

## Apply/rollback policy

Every Domain Adapter must define:

- `apply_mechanism`: how changes are applied to the target environment
- `rollback_mechanism`: how changes are rolled back

Coding Adapter:
- Apply: `git apply` after human approval (via Apply Gate)
- Rollback: reset worktree to snapshot

Document Adapter:
- Apply: structured document merge
- Rollback: restore previous document version

Data Adapter:
- Apply: dataset transform execution
- Rollback: revert to pre-transform profile

Research Adapter:
- Apply: citation/attribution integration
- Rollback: detach sources

## Human approval policy

- Apply Gate remains the universal write authorization boundary.
- Domain Adapter defines its own human approval policy for domain-specific
  decisions (e.g., protected paths, irreversible changes).
- Domain Adapter must not bypass Apply Gate requirements.

## Coding Adapter example

```yaml
schema_version: "0.1"
domain: "coding"
adapter_id: "coding-v1"
allowed_write_paths:
  - "services/**"
  - "packages/**"
  - "tests/**"
forbidden_write_paths:
  - ".git/**"
  - ".env"
validation_commands:
  - "python -m pytest -q"
execution_environment: "worktree"
apply_mechanism:
  mechanism: "git_apply"
  requires_human_apply: true
rollback_mechanism:
  mechanism: "git_reset"
```

## Document Adapter example

```yaml
schema_version: "0.1"
domain: "document"
adapter_id: "document-v1"
allowed_write_paths:
  - "docs/**"
forbidden_write_paths:
  - ".git/**"
validation_commands:
  - "python -m pytest -q docs"  # placeholder
execution_environment: "local"
apply_mechanism:
  mechanism: "structured_merge"
rollback_mechanism:
  mechanism: "restore_backup"
```

## Data Adapter example

```yaml
schema_version: "0.1"
domain: "data"
adapter_id: "data-v1"
allowed_write_paths:
  - "data/**"
forbidden_write_paths:
  - "secrets/**"
validation_commands: null
execution_environment: "notebook"
```

## Research Adapter example

```yaml
schema_version: "0.1"
domain: "research"
adapter_id: "research-v1"
allowed_write_paths:
  - "docs/research/**"
forbidden_write_paths:
  - "data/**"
  - "secrets/**"
validation_commands: null
```

## Custom Adapter example

```yaml
schema_version: "0.1"
domain: "custom"
adapter_id: "custom-v1"
allow_write_paths: []
forbidden_write_paths: []
execution_environment: "user_defined"
human_approval_policy: "All actions require explicit human approval."
```

## Relationship to existing contracts

- **Conductor Prompt Contract**: Domain Adapter supplies prompt policy sections.
- **Apply Gate**: Domain Adapter defines apply/rollback but does not bypass Apply Gate.
- **Run Record**: Domain Adapter produces evidence in run record-compatible format.
- **Review Artifacts**: Review artifacts may reference domain adapter ID.
- **State-First**: Domain Adapter execution is a state transformation.
- **Model Routing**: Domain Adapter is independent of model selection.

## Current and future storage

- `.project-memory/` — current/legacy-compatible project memory for contracts/schemas.
- `.ariadne/` — long-term canonical namespace for runtime artifacts. Not created in this PR.
