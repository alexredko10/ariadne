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
