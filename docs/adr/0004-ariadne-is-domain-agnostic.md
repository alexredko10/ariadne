# ADR 0004: Ariadne is domain-agnostic

**Status:** Accepted

**Date:** 2026-06-20

## Context

Ariadne currently implements coding-related runner capabilities (worktree,
diff, patch, apply gate) as core architecture.  As Ariadne evolves beyond
software engineering into documents, data, research, and custom domains,
it must separate the universal execution substrate from domain-specific
tools and environments.

If Git, patches, pytest, and programming language support are hardcoded
into Ariadne Core, the system becomes impossible to extend to non-coding
domains without breaking core abstractions.

## Decision

**Ariadne Core is domain-agnostic.  Coding is a Domain Adapter, not Core.**

### Domain Adapter boundary

- Conductor is universal.
- Domain Adapters are domain-specific.
- Coding is one Domain Adapter, not the identity of Ariadne.

### Coding Adapter boundary

- Git, patches, pytest, source file mapping, and test execution belong
  to the Coding Adapter.
- Ariadne Core must not import or depend on these directly.

### Non-coding domains

| Domain     | Execution focus                                       |
|------------|-------------------------------------------------------|
| document   | Structured edits, diff/apply, citations, export        |
| data       | Transforms, profiling, schema validation, quality     |
| research   | Search, synthesis, citation graph, claim verification |
| custom     | User-defined environment and policy                   |

### Universal Core ownership

Ariadne Core owns:
- purpose decomposition
- context compilation
- contracts
- prompt artifacts
- checkpoints
- review artifacts
- verification contracts
- auditability

### Domain Adapter ownership

Each Domain Adapter owns:
- execution environment
- allowed/forbidden write paths
- validation commands
- artifact types
- apply/rollback mechanism
- domain-specific risks
- domain-specific stop conditions
- human approval policy

## Consequences

### Positive

- Ariadne can extend to non-coding domains without Core changes.
- Coding tools are not forced on document/data/research users.
- Core abstractions remain stable across domains.
- Domain Adapter policies are pluggable and testable independently.
- Model-routing and prompt contracts are domain-agnostic.

### Negative

- Domain Adapter development is required before a new domain can execute.
- Coding Adapter must be explicitly registered, not implicit.
- Initial overhead of separating existing runner code into adapter boundary.

## Relationship to Conductor

Domain Adapters supply policy inputs to the Conductor Prompt Contract:
`allowed_write_paths`, `forbidden_write_paths`, `validation_commands`,
`final_output_format`, `domain_specific_stop_conditions`, and
`domain_specific_risks`.

The Conductor remains universal; it does not know whether it is building
a coding prompt, a document prompt, or a data analysis prompt.

## Relationship to Apply Gate

Apply Gate remains the universal write authorization boundary.
Domain Adapters define apply/rollback mechanisms but must not bypass
Apply Gate requirements.

## Relationship to Run Record

Run Record remains the universal execution evidence boundary.
Domain Adapters produce evidence in run record-compatible format but
must not bypass or replace run-record contracts.

## Future work

- Coding Adapter implementation (refactor existing runner code into adapter)
- Document Adapter implementation
- Data Adapter implementation
- Research Adapter implementation
- Custom Adapter registration mechanism
- Domain Adapter registry and discovery
- Domain Adapter versioning and compatibility contract
