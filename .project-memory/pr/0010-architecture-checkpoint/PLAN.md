# PR 0010: Architecture Checkpoint and Documentation Alignment

## Goal

Create a checkpoint document that:

- describes what is actually implemented now
- draws the current project shape
- compares current implementation to existing project docs
- separates implemented, partially implemented, planned, and out-of-scope items
- identifies next sensible tracks without starting implementation

## Non-goals

- no workflow changes
- no Dockerfile changes
- no service code changes
- no package changes
- no agent YAML changes
- no new Docker images
- no GHCR publish changes
- no runtime behavior changes
- no new architecture decisions
- no migration or refactor
- no product feature implementation

## Future implementation scope

Future implementation may create or edit only:

```text
docs/architecture/current-project-map.md
.project-memory/pr/0010-architecture-checkpoint/PLAN.md
```

## Required document structure

The future `docs/architecture/current-project-map.md` must include:

- purpose of the checkpoint
- current implemented artifacts
- current repository map
- current agent/control model
- current project-memory model
- current runner/patch contract state
- current Docker/GHCR state
- Mermaid architecture diagram
- PR timeline from 0001 through 0009
- documentation alignment table
- implemented vs planned table
- risks / drift found
- recommended next tracks
- explicit non-decisions

## Required diagram

The document must include a Mermaid diagram showing:

- project documentation
- project memory
- controlled agents
- PR plan files
- runner service source
- agent-runtime-python image
- platform-runner image
- GHCR workflows
- GHCR packages
- manual validation runbooks

## Documentation alignment

The document must compare current implementation against existing docs and classify each item as:

```text
implemented
partially implemented
planned
unclear
out of scope
```

## Current known implemented baseline

The document must include at least:

- controlled agent model exists
- `.project-memory` exists
- PR plan discipline exists
- runner patch contracts exist
- `agent-runtime-python` image exists
- `agent-runtime-python` GHCR workflow exists
- `agent-runtime-python` manual validation runbook exists
- `platform-runner` image exists
- `platform-runner` manual validation runbook exists
- `platform-runner` GHCR workflow exists
- GHCR publishing uses `GITHUB_TOKEN`
- PR builds are non-publishing
- publish jobs are gated by `ghcr-publish`
- no Docker Hub / Artifactory / PATs
- no `latest` / floating `main` tags

## Required questions to answer

The future document must answer:

- How many container artifacts exist now?
- What are they for?
- What is still only documentation or aspiration?
- Does the current implementation still match the project docs?
- Where has the implementation drifted from the original docs?
- What should be done next: runner functionality, more images, or documentation cleanup?

## Machine-readable scope

```text
allowed_write_paths:
- docs/architecture/current-project-map.md
- .project-memory/pr/0010-architecture-checkpoint/PLAN.md
```

```text
forbidden_paths:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/**
- services/**
- packages/**
- apps/**
- agents/**
- prompts/**
- pyproject.toml
- package.json
- Makefile
- docker-compose.yml
- .env
- .env.*
- docs/** except docs/architecture/current-project-map.md
- .project-memory/** except .project-memory/pr/0010-architecture-checkpoint/PLAN.md
```

Any change outside allowed_write_paths is out of scope and must be reverted.

## Acceptance criteria

Machine-checkable:

```text
document_path: docs/architecture/current-project-map.md
plan_path: .project-memory/pr/0010-architecture-checkpoint/PLAN.md
docs_only: required
runtime_code_changes: forbidden
workflow_changes: forbidden
dockerfile_changes: forbidden
agent_yaml_changes: forbidden
new_architecture_decisions: forbidden
new_adr: forbidden
```

Required content checks:

```text
contains_title: "# Current Project Map"
contains_mermaid_block: required
mermaid_fence: "```mermaid"
contains_current_container_artifacts_count: "Current container artifacts: 2"
contains_pr_timeline_0001_0009: required
contains_documentation_alignment_table: required
contains_implemented_vs_planned_table: required
contains_drift_risk_notes: required
contains_recommended_next_tracks: required
contains_non_decisions: required
```

Mermaid acceptance:

```text
mermaid_diagram_required: fenced mermaid code block
mermaid_render_guidance: diagram should use standard Mermaid flowchart syntax
rendered_svg: optional, not required in this PR
```

PR timeline acceptance:

```text
pr_timeline_required_entries:
- 0001
- 0002
- 0003
- 0004
- 0005
- 0006
- 0007
- 0008
- 0009
```

Classification acceptance:

```text
allowed_status_values:
- implemented
- partially implemented
- planned
- unclear
- out of scope
```

Baseline acceptance:

```text
implemented_baseline_must_cover:
- controlled agent model
- .project-memory
- PR plan discipline
- runner patch contracts
- agent-runtime-python image
- agent-runtime-python GHCR workflow
- agent-runtime-python manual validation runbook
- platform-runner image
- platform-runner manual validation runbook
- platform-runner GHCR workflow
- GHCR publishing with GITHUB_TOKEN
- non-publishing PR builds
- ghcr-publish gated publish jobs
- no Docker Hub / Artifactory / PATs
- no latest / floating main tags
```

## Stop / merge gates

```text
Do not merge if any pytest test fails.
Do not merge if compileall returns non-zero.
Do not merge if any file outside allowed_write_paths is modified.
Do not merge if the document introduces new ADRs.
Do not merge if the document introduces new architecture decisions.
If new architecture decisions are discovered, move them to a separate ADR PR.
Do not merge if the document starts implementation work.
Do not merge if the document claims planned items are implemented without filesystem evidence.
```

## Validation constraints

```text
Validation commands must not install dependencies.
Validation commands must not publish artifacts.
Validation commands must not require credentials.
Validation commands must not modify workflows, Dockerfiles, service code, package files, or docs outside allowed_write_paths.
Validation commands are limited to:
- python -m pytest -q
- python -m compileall -f services packages
```

## Reviewer / approver requirement

```text
Requires approval from at least one maintainer.
Architecture-sensitive claims should be reviewed by an architecture reviewer or project maintainer.
Reviewers must use cold-read protocol and quote filesystem evidence for key claims.
```

## Validation

PLAN-only PR should pass:

```bash
python -m pytest -q
python -m compileall -f services packages
```

## Context receipt requirement

Every agent response for this PR must include:

```text
CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files modified:
- files intentionally ignored:
```
