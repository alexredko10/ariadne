# Docker Agents Memory Setup

This repository uses four manually controlled Docker Agent configurations:

```text
agents/
├── architect.yml
├── coder.yml
├── plan-review.yml
└── precommit-review.yml
```

They are intentionally separate. There is no automatic team runner at this stage.

## Shared memory entrypoint

Every agent must read this file first:

```text
.project-memory/memory_index.yml
```

The memory index maps task labels to small context bundles. This avoids repeatedly scanning the entire repository.

## Context bundles

```text
.project-memory/context-bundles/
├── architecture.yml
├── sprint-0.yml
├── sprint-1-runner.yml
├── task-intake.yml
├── contracts.yml
└── agent-config.yml
```

A task should specify labels such as:

```yaml
labels: ["sprint-0"]
assigned_agent: "coder"
```

The agent then reads only the matching bundle and the files listed there.

## Minimal task manifest

Create `.project-memory/current_task.yml` when you want repeatable agent runs:

```yaml
task_id: "fix-pytest-import-mismatch"
description: "Fix pytest import mismatch caused by duplicate test_smoke.py module names."
labels: ["sprint-0"]
assigned_agent: "coder"
mode: "bugfix"
risk_level: "low"

scope:
  allowed_write_paths:
    - "services/*/tests/"
  runtime_read_paths:
    - "pyproject.toml"
    - "Makefile"
  out_of_scope:
    - "services/*/src/"
    - "docs/"
    - "agents/"

context:
  required_bundles:
    - ".project-memory/context-bundles/sprint-0.yml"
  required_anchors:
    - "repo.structure.root"
  max_context_files: 8

acceptance:
  automated:
    - "python -m pytest -q"
    - "python -m compileall services packages"

stop_conditions:
  - "fix requires changing application/service code"
  - "dependency installation is required"
```

## Recommended manual flow

```text
1. Write or update .project-memory/current_task.yml
2. Run plan-review if the change is larger than a tiny fix
3. Run coder with explicit allowed paths
4. Run precommit-review
5. Human commits if verdict is pass
```

## Token control rules

- Do not attach the full Developer Pack to every agent run.
- Do not ask agents to inspect the whole repo unless necessary.
- Prefer labels, anchors, and context bundles.
- Keep one task per run.
- Keep allowed_write_paths narrow.
