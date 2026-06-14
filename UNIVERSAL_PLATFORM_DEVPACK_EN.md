# Universal Agentic Development Platform — English Developer Pack v1.0

---

<!-- docs/START_HERE.md -->

# Start Here

## Product goal

Build a universal agentic development platform for controlled AI-assisted software engineering.

The platform must work with arbitrary repositories. It must not be tied to a specific application, route structure, storage backend, UI feature, or legacy project name.

## Core outcome

A user can submit a task, inspect what the system believes is in scope, approve the run, observe execution, review the patch, and apply it only after validation.

## Core pipeline

```text
Input
  -> Task Intake
  -> Repository Context Preview
  -> Task Subgraph
  -> Workflow Planning
  -> Sandboxed Execution
  -> Patch Normalization
  -> Verification
  -> Human Approval
  -> Apply Patch
  -> Graph and Memory Update
```

## Non-negotiable principles

```text
Agents never write directly to the canonical repository.
ApplyPatch is the only component allowed to modify the canonical repository.
The Runner owns sandbox execution.
The Conductor never mounts the container runtime socket.
The model gateway does not trust agent-provided request bodies for policy decisions.
Context previews do not start agents.
Voice input never starts agents directly.
Every patch is scope-checked before it can be applied.
Every run is observable and auditable.
```

## What to build first

Start with the Git repository skeleton. Then implement two parallel tracks:

```text
Track A: Task Intake mock loop
  manual text -> normalize -> preview mock -> mock run

Track B: Runner proof
  repository snapshot -> sandbox -> mock edit -> raw diff -> normalized patch artifact
```

This gives the project both a visible product loop and a safety-critical execution proof.

---

<!-- docs/DEVELOPER_PACK.md -->

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

---

<!-- docs/REPOSITORY_STRUCTURE.md -->

# Repository Structure

## Goal

Create a repository layout that makes service ownership, contracts, tests, and documentation obvious from day one.

## Proposed structure

```text
.
├── README.md
├── pyproject.toml
├── package.json
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── docs/
│   ├── START_HERE.md
│   ├── DEVELOPER_PACK.md
│   ├── DEVELOPMENT_ORDER.md
│   ├── REPOSITORY_STRUCTURE.md
│   ├── AGENTS.md
│   ├── api/
│   ├── architecture/
│   ├── sprints/
│   └── adr/
│
├── agents/
│   ├── 01_platform_architect.md
│   ├── 02_repository_scaffolder.md
│   ├── 03_runner_patch_engineer.md
│   └── 04_qa_contracts_reviewer.md
│
├── services/
│   ├── task_intake/
│   ├── core/
│   ├── conductor/
│   ├── runner/
│   └── model_gateway/
│
├── apps/
│   └── web/
│
├── packages/
│   ├── common/
│   ├── policy/
│   └── contracts/
│
├── infra/
│   ├── docker/
│   └── scripts/
│
├── evals/
│   └── fixtures/
│
├── artifacts/
└── .project-memory/
    ├── project_contract.yml
    ├── anchors.yml
    ├── accepted_risks.yml
    ├── current_task.example.yml
    ├── features/
    ├── qa/
    └── context_packs/
```

## Service responsibilities

### `services/task_intake`

Normalizes raw text, voice transcript, or issue text into a task draft. It never starts agents directly.

### `services/core`

Indexes repositories and builds task subgraphs.

### `services/conductor`

Owns run state, workflow validation, step scheduling, repair loops, and approval gates.

### `services/runner`

Owns snapshots, sandboxes, raw diffs, patch normalization, and artifact creation.

### `services/model_gateway`

Routes model calls through policy and records usage.

## Shared packages

### `packages/common`

Common IDs, timestamps, error envelopes, pagination, and typed response helpers.

### `packages/policy`

Policy objects, scope rules, protected paths, approval requirements, and provider routing rules.

### `packages/contracts`

Shared API schemas and event schemas.

---

<!-- docs/DEVELOPMENT_ORDER.md -->

# Development Order

## Start with Git and structure

The first real development action should be repository initialization, not service implementation.

```bash
git init
git add .
git commit -m "chore: initialize platform repository skeleton"
```

After the skeleton is committed, build in this order.

## Phase 0: Repository skeleton

Deliver:

```text
- folder structure
- README
- Developer Pack
- agent briefs
- placeholder services
- placeholder tests
- docker-compose placeholder
- CI placeholder
```

## Phase 1: Runner proof

Deliver:

```text
- create repository snapshot without VCS metadata
- create sandbox from snapshot
- run mock agent edit inside sandbox
- compute raw diff
- normalize diff to repository-relative patch
- store patch as content-addressed artifact
```

This phase proves the most important safety property: agent code execution cannot modify the canonical repository.

## Phase 2: Task Intake mock loop

Deliver:

```text
- POST /task-intake/normalize
- POST /context/preview mock
- POST /runs mock
- simple run status object
```

This gives the frontend a visible product loop.

## Phase 3: Core MVP

Deliver:

```text
- repository scanner
- file and symbol nodes
- basic import/test links
- lexical search
- task subgraph output
```

## Phase 4: Conductor MVP

Deliver:

```text
- Run and Step models
- workflow state machine
- DAG validator stub
- Runner client
- approval gate state
```

## Phase 5: Frontend MVP

Deliver:

```text
- New Task screen
- context preview panel
- run progress page
- diff/artifacts page
- approval controls
```

---

<!-- docs/AGENTS.md -->

# First Four Build Agents

## Purpose

These four agents are the first team used to build the platform itself. They are development agents, not yet the final runtime agents that the product will later orchestrate for user repositories.

## Agent 1: Platform Architect

Owns architecture, boundaries, invariants, and documentation quality.

Outputs:

```text
- architecture decisions
- service boundaries
- risk register
- review comments on design changes
```

## Agent 2: Repository Scaffolder

Owns the initial repository structure, tool configuration, placeholder services, and CI baseline.

Outputs:

```text
- folders and placeholder modules
- pyproject/package metadata
- docker-compose skeleton
- CI skeleton
- initial smoke tests
```

## Agent 3: Runner and Patch Engineer

Owns the first safety-critical proof: snapshot, sandbox, raw diff, normalized patch, artifact store.

Outputs:

```text
- WorktreeManager
- sandbox creation
- raw diff generation
- PatchNormalizer
- content-addressed artifact store
```

## Agent 4: QA and Contracts Reviewer

Owns checks, contracts, invariants, test gates, and acceptance evidence.

Outputs:

```text
- scope checks
- contract checks
- test plan
- review reports
- acceptance criteria
```

## Operating rules

```text
- No agent directly edits the canonical repository without a patch artifact.
- Agents must write concise implementation reports.
- Every implementation change must include tests or a documented reason why tests are deferred.
- The QA and Contracts Reviewer can block a change.
- The Platform Architect can request a design revision before implementation continues.
```

---

<!-- docs/sprints/SPRINT_0_REPOSITORY_SKELETON.md -->

# Sprint 0 — Repository Skeleton

## Goal

Create the Git repository starting point for the platform.

## Scope

```text
- initialize repository
- add documentation set
- add agent briefs
- add service directories
- add placeholder modules
- add test placeholders
- add CI placeholder
- add docker-compose placeholder
- add project memory templates
```

## Tasks

```text
[ ] Create repository root files
[ ] Create docs structure
[ ] Create services structure
[ ] Create apps/web placeholder
[ ] Create packages structure
[ ] Create .project-memory templates
[ ] Create first four agent briefs
[ ] Add pyproject.toml
[ ] Add package.json
[ ] Add docker-compose.yml
[ ] Add .github/workflows/ci.yml
[ ] Add smoke tests
[ ] Commit skeleton
```

## Definition of done

```text
- `git status` is clean after initial commit
- folder structure matches docs/REPOSITORY_STRUCTURE.md
- placeholder tests run locally
- CI workflow exists
- no project-specific legacy examples exist in docs
```

---

<!-- docs/sprints/SPRINT_1_RUNNER_PATCH_PIPELINE.md -->

# Sprint 1 — Runner and Patch Pipeline

## Goal

Prove the core safety model: agents operate in an isolated sandbox and produce patch artifacts, not direct repository mutations.

## Scope

```text
[ ] Runner service skeleton
[ ] WorktreeManager.create_context_snapshot
[ ] WorktreeManager.create_sandbox
[ ] Mock Coder writes only inside sandbox
[ ] Raw diff generation
[ ] PatchNormalizer
[ ] Content-addressed artifact store
[ ] Patch validation: no absolute paths, no path traversal
[ ] ApplyPatch stub requiring approval
```

## Proof checklist

```text
[ ] sandbox has no VCS metadata
[ ] mock Coder cannot write to canonical repository
[ ] normalized patch uses repository-relative paths
[ ] new files are represented correctly
[ ] deleted files are represented correctly
[ ] ApplyPatch refuses to run without approval
```

---

<!-- docs/api/TASK_INTAKE_API.md -->

# Task Intake API MVP

## POST /task-intake/normalize

Request:

```json
{
  "raw_input": "Fix the failing task flow after recent changes.",
  "input_type": "text",
  "repo_id": "example-repo",
  "branch": "main",
  "hint_labels": [],
  "language": "en"
}
```

Response:

```json
{
  "draft_id": "draft_example",
  "description": "Fix the failing task flow after recent changes.",
  "original_input": "Fix the failing task flow after recent changes.",
  "input_type": "text",
  "inferred_mode": "bugfix",
  "inferred_domains": ["example-domain"],
  "inferred_risk_hints": [],
  "suggested_repo_id": "example-repo",
  "mode_confidence": 0.75,
  "description_quality": "clear",
  "warnings": []
}
```

## POST /context/preview

MVP returns a mock preview until Core is implemented.

## POST /runs

MVP creates a mock run object until Conductor is implemented.

---

<!-- docs/architecture/CONTROL_PLANES.md -->

# Control Planes

## Trusted control plane

```text
Core
Conductor
Model Gateway
Repository Memory
Cache
Ledger
Policy Engine
```

## Semi-trusted execution plane

```text
Runner
```

The Runner may access the container runtime or sandbox backend, but it must not hold model provider credentials or repository push credentials.

## Untrusted execution plane

```text
Agent containers
```

Agent containers receive only scoped context and a sandbox filesystem. They do not receive canonical repository write access.
