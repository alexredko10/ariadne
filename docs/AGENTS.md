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
