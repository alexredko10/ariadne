# Developer Pack v1.0

## Purpose

This Developer Pack is the neutral starting package for building a universal agentic development platform.

It defines:

- repository structure
- implementation order
- first build agents
- MVP services
- initial API contracts
- safety invariants
- first sprint scope
- Git bootstrap plan

## Components

```text
Task Intake
  Converts raw input into a confirmed task draft.

Core
  Indexes repositories, builds a symbol graph, retrieves relevant context,
  and compiles task subgraphs.

Repository Memory
  Stores project contracts, anchors, decisions, accepted risks, and feature workspaces.

Cache
  Reuses stable repository context to avoid rebuilding the same context repeatedly.

Conductor
  Validates and schedules workflows, tracks runs, and opens approval gates.

Runner
  Creates clean snapshots and sandboxes; extracts normalized patch artifacts.

Model Gateway
  Routes model calls according to policy and records claims, usage, and cost.

Frontend
  Provides task intake, live run monitoring, context inspection, diff review,
  approval, and observability.
```

## First development decision

Start with the repository skeleton in Git.

Reason: before building agents, core services, or UI, the team needs a stable repository shape, ownership boundaries, module names, shared contracts, CI placeholders, and documentation conventions.

## Initial repository shape

```text
.
├── README.md
├── docs/
├── agents/
├── services/
│   ├── task_intake/
│   ├── core/
│   ├── conductor/
│   ├── runner/
│   └── model_gateway/
├── apps/
│   └── web/
├── packages/
│   ├── common/
│   ├── policy/
│   └── contracts/
├── infra/
├── evals/
├── artifacts/
└── .project-memory/
```

## First four build agents

These are not the final runtime product agents. These are the first development agents used to build this platform.

1. Platform Architect
2. Repository Scaffolder
3. Runner and Patch Engineer
4. QA and Contracts Reviewer

Each agent has a dedicated brief in `agents/`.

## First sprint sequence

```text
Sprint 0: Repository skeleton
Sprint 1: Runner + patch pipeline proof
Sprint 2: Task Intake mock loop
Sprint 3: Core indexing MVP
Sprint 4: Conductor state machine
Sprint 5: Frontend workspace MVP
```

## Definition of the first successful milestone

The first milestone is complete when:

```text
- the repository is initialized in Git
- service folders exist
- docs and agent briefs exist
- CI placeholder runs
- Task Intake mock endpoint returns a task draft
- context preview mock returns a preview object
- Runner can create a sandbox from a repository snapshot
- Runner can produce a normalized patch artifact
- no agent writes to the canonical repository
```
