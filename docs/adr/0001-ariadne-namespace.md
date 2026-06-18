# ADR 0001: `.ariadne/` namespace

**Status:** Accepted

**Date:** 2026-06-18

## Context

The platform defines Workspace Feature Record schemas and contracts in
`.project-memory/`.  PR 0024 introduced the schema and contract but
intentionally did not define the physical storage namespace for future
workspace/feature state.

Without a namespace decision, there is no defined physical location for
feature records when the Context Steward archival workflow is implemented
(future PR 0026).  The `.project-memory/` directory is reserved for durable
contracts, schemas, historical plans, anchors, and shared project memory —
not for runtime/workspace state that evolves per PR lifecycle.

This ADR decides the `.ariadne/` namespace for repository-local
runtime/workspace state.

## Decision

```text
.ariadne/ is reserved for repository-local runtime/workspace state.
.project-memory/ remains the durable home for contracts, schemas, historical plans, anchors, and durable project memory.
.ariadne/features/{id}.yml is the future physical storage path for Workspace Feature Records.
PR 0025 defines the namespace only and does not create feature records.
```

### Namespace roles

**.project-memory/** — durable contracts, schemas, and project memory:

- contracts
- schemas
- anchors
- historical PR plans
- durable project memory
- validation and governance evidence

**.ariadne/** — repository-local runtime/workspace state:

- workspace state
- feature records
- archival outputs produced by future Context Steward workflow
- runtime/workspace metadata that should not be mixed into contract schemas

## Safety rules

- `.ariadne/**` may be introduced only by this ADR/contract.
- No agents may write `.ariadne/**` unless a future contract explicitly permits it.
- `.ariadne/features/{id}.yml` records must conform to `.project-memory/workspace-feature-record.schema.yml`.
- Feature record ids must be stable, repo-unique, lowercase kebab-case, and must not contain path separators.
- Context Steward archival may write `.ariadne/features/{id}.yml` only after a future archival workflow contract exists.
- Artifact references remain evidence-only and do not authorize canonical mutation.
- ApplyPatch HITL gate remains the only path toward future canonical mutation.

## Consequences

- Storage decision is made now.
- Actual writer workflow is future PR 0026.
- Actual records are not created in PR 0025.
- `.project-memory/workspace-feature-record.schema.yml` remains the schema source of truth.
- Run Record continues to capture execution evidence in `.project-memory/pr/<PR-ID>/run_record.yml`.
- Workspace Feature Record captures durable feature/workspace state at `.ariadne/features/{id}.yml`.
- `run_id → feature_workspace_id` linkage remains required for traceability.

## Non-goals

- No actual `.ariadne/` directory or files are created in PR 0025.
- No Context Steward archival workflow implementation.
- No runner Python dataclass or runtime implementation.
- No ApplyPatch, Artifact Store, WorktreeManager, or MockCoder changes.
- No Run Record or Apply Gate schema changes.
- No modifications to services, packages, apps, or agent configs.
- No secrets or credentials.

## Relationship to `.project-memory/`

`.project-memory/` remains the durable contracts and project memory layer.
Future workspace feature record instances stored at `.ariadne/features/{id}.yml`
must conform to the schema defined in `.project-memory/workspace-feature-record.schema.yml`.

## Relationship to Workspace Feature Record

Workspace Feature Record schemas and contracts live in `.project-memory/`.
Future physical feature records may live at `.ariadne/features/{id}.yml`.

## Relationship to Context Steward archival

Context Steward archival after merge is required by contract
(`workspace-feature.record.context-steward-archival-required`).
The archival writer workflow that produces `.ariadne/features/{id}.yml`
records is future PR 0026 and is not implemented in PR 0025.

## Forbidden current behavior

- Agents must not write `.ariadne/**` without explicit future contract approval.
- `.ariadne/` must not be used for secrets, credentials, tokens, or environment dumps.
- `.ariadne/` must not contain executable or applied-patch state.

## Future work

- PR 0026: Context Steward archival workflow implementation.
- PR 0027: Task Intake API skeleton / Phase 2 (independent).
- Future PR: Runner dataclass for Workspace Feature Record runtime support.
