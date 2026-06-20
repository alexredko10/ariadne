# Context Compiler

## Purpose

The Context Compiler assembles structured Context Packs from known Ariadne
sources.  Its output is used by the Conductor to build prompt artifacts.

## Why raw repository dumps are forbidden

Raw repository dumps:
- waste context window on irrelevant files
- hide important signals in noise
- make it hard to identify what the agent actually needs
- cannot be traced to specific sources
- are not reproducible

Good context is:
- more structure
- more labels
- more explicit relationships
- more evidence
- less noise

## Source inputs

The Context Compiler may assemble context from:

- project contract (`.project-memory/project_contract.yml`)
- anchors (`.project-memory/ariadne-anchor.schema.yml`)
- memory index (`.project-memory/memory_index.yml`)
- context bundles (`.project-memory/context-bundles/*.yml`)
- AST / symbols (future)
- imports (future)
- call graph where available (future)
- tests
- configs
- git history
- semantic search (future)
- state model (`.project-memory/state-first.schema.yml`)
- transition graph (future)
- invariants
- rubrics
- domain adapter policy (`.project-memory/domain-adapter.schema.yml`)

## How Context Pack feeds Conductor Prompt Contract

The Context Pack provides structured input for these prompt contract sections:

- `task_description` → from PurposeContext
- `context_snapshot` → from RepositoryContext + SemanticContext
- `purpose` → from PurposeContext.root_purpose
- `pbs_node` → from PBSNodeContext
- `rubric` → from RubricContext
- `allowed_write_paths` → from DomainAdapterContext
- `forbidden_write_paths` → from DomainAdapterContext
- `validation_commands` → from ValidationContext
- `stop_conditions` → from DomainAdapterContext + RubricContext

## How Context Pack feeds Prompt Artifact

The Context Pack populates PromptMemorySnapshot with hashes of sources
that were used to build the pack.  This enables replay and audit.

## How Context Pack feeds Review/Rubric Judge

The Context Pack provides:
- rubric references for review comparison
- domain adapter policy for scope validation
- validation commands for evidence checking
- source traces for auditability

## Missing source handling

If a required source is missing, the Context Pack must represent it as
`missing/blocked` rather than silently skipping it.

## Policies

- No invented context.
- No raw unbounded repo dumps.
- No secrets.
- Source traces required.
- Evidence only — no execution authorization.

## Current and future storage

- `.project-memory/` — current/legacy-compatible memory.
- `.ariadne/` — long-term canonical namespace, not created in this PR.
