# PR 0016: Agent Context Snapshot and Final Output Contract

## Context snapshot verified at plan time

```text
Context snapshot verified at plan time:
- base_sha: db6999309a2656f2768eb9c9b453b153f340e36d
- index_version: "0.1"
```

## Goal

Add a mandatory prompt/output contract for controlled agents so every task verifies the repository base state before work and reports machine-readable final context after work.

## Non-goals

- no runner code changes
- no Dockerfile changes
- no workflow changes
- no GHCR changes
- no API server
- no frontend
- no task execution engine
- no real agent execution
- no LLM runtime integration
- no automation of memory writes yet
- no automatic team runner
- no canonical repo writes outside normal human-controlled git workflow
- no git mutation commands by agents
- no Docker commands by agents
- no secrets or credentials
- no change to patch/diff/worktree behavior

## Future implementation scope

Future implementation may modify/create only:

```text
agents/architect.yml
agents/coder.yml
agents/plan-review.yml
agents/precommit-review.yml
.project-memory/project_contract.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/memory_index.yml
.project-memory/pr/0016-agent-context-snapshot-output-contract/PLAN.md
```

## Required prompt skeleton

Every implementation/review prompt must follow this order:

```text
Task + Agent + Mode
Cold-read protocol
Context snapshot
Context labels + Read first
Goal
Allowed write paths
Forbidden
Implement / Create / Modify
Required behavior
Must not
Stop conditions
Validation commands
Post-change checks
Expected changed files
Final output format
```

## Required context snapshot block

Every controlled agent prompt must include:

```text
Context snapshot:
- base_sha: <sha from PLAN.md>
- index_version: <version from PLAN.md>

Before starting:
- run `git rev-parse --verify HEAD` as read-only introspection if available
- compare current HEAD to base_sha
- if base_sha is not `unknown` and current HEAD differs from base_sha, stop and report stale snapshot
- do not proceed on a stale snapshot
- do not run git mutation commands
```

Clarify:

- `git rev-parse --verify HEAD` is allowed as read-only introspection
- git mutation commands remain forbidden for agents
- examples of forbidden git mutation commands:

  - `git add`
  - `git commit`
  - `git push`
  - `git reset`
  - `git checkout`
  - `git switch`
  - `git merge`
  - `git rebase`
  - `git clean`

## Required final output format

Every implementation agent final output must include:

```text
FINAL OUTPUT:
- files changed:
  - <list>
- validation results:
  - <command>: <result>
- decisions made:
  - None — followed PLAN.md exactly
  - or <decision> — <reason>
- deviations from PLAN.md:
  - None
  - or <deviation> — <reason and impact>
- confirm:
  - no Docker commands run
  - no git mutation commands run
- CONTEXT USED:
  - base_sha:
  - index_version:
  - snapshot_verified: true | false | skipped
  - snapshot_verified_by: git introspection | not available | filesystem
  - labels:
  - memory files read:
  - anchors used:
  - files inspected:
  - files modified:
  - files intentionally ignored:
```

Every review agent final output must include:

```text
VERDICT: approve | revise | block
EVIDENCE FROM FILESYSTEM:
- <exact snippets>

BLOCKERS:
- ...

WARNINGS:
- ...

REQUIRED CHANGES:
- ...

CONTEXT SNAPSHOT:
- base_sha:
- index_version:
- current_head:
- stale_snapshot:
- snapshot_verified:
- snapshot_verified_by:

DECISIONS MADE:
- None — review followed PLAN.md exactly
- or <decision> — <reason>

CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files intentionally ignored:
```

## Feature Workspace Memory intent

```text
This PR does not automate memory writes.
It standardizes final output so Feature Workspace Memory can be filled manually or by future automation after each PR.
The required output fields are:
- base_sha
- index_version
- files changed
- validation results
- decisions made
- deviations from PLAN.md
- context used
```

## Machine-readable scope

```text
allowed_write_paths:
- agents/architect.yml
- agents/coder.yml
- agents/plan-review.yml
- agents/precommit-review.yml
- .project-memory/project_contract.yml
- .project-memory/context-bundles/agent-config.yml
- .project-memory/memory_index.yml
- .project-memory/pr/0016-agent-context-snapshot-output-contract/PLAN.md

forbidden_files:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/**
- docs/** except:
  - docs/architecture/current-project-map.md
- packages/**
- apps/**
- services/**
- prompts/**
- pyproject.toml
- package.json
- Makefile
- docker-compose.yml
- .env
- .env.*
- .project-memory/** except:
  - .project-memory/project_contract.yml
  - .project-memory/context-bundles/agent-config.yml
  - .project-memory/memory_index.yml
  - .project-memory/pr/0016-agent-context-snapshot-output-contract/PLAN.md
```

(Note: `docs/architecture/current-project-map.md` is included as an allowed doc path but will only be modified if the document needs a snapshot update after this PR is implemented.)

## Required behavior

Implementation must:

- add `base_sha` guard requirement to controlled agent prompts/configs
- add `index_version` requirement to controlled agent prompts/configs
- add stale snapshot stop condition
- add decisions made output requirement
- add deviations from PLAN.md output requirement
- add machine-readable final output format
- preserve existing CONTEXT USED requirement
- preserve cold-read protocol
- preserve no Docker command policy
- preserve no git mutation command policy
- preserve scoped allowed/forbidden path discipline
- keep changes textual/config-only

## Tests / checks

No code tests are required beyond repository validation, but implementation must include grep-style checks proving:

- `Context snapshot`
- `base_sha`
- `index_version`
- `stale snapshot`
- `DECISIONS MADE`
- `deviations from PLAN.md`
- `no Docker commands run`
- `no git mutation commands run`
- `CONTEXT USED`
- `git rev-parse --verify HEAD`
- forbidden git mutation examples

## Machine-checkable acceptance criteria

```text
agent_prompt_skeleton: required
base_sha_guard: required
index_version_capture: required
stale_snapshot_stop: required
read_only_git_introspection: allowed
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
decisions_made_output: required
deviations_output: required
context_used_output: required
feature_workspace_memory_ready_output: required
code_changes: forbidden
runner_behavior_changes: forbidden
```

## Validation

Implementation PR must pass:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Do not run Docker commands.
Do not run git mutation commands.

Read-only git introspection allowed:

```bash
git rev-parse --verify HEAD
git status --short
```

## Stop / merge gates

Do not merge if:

- controlled agent prompts/configs do not include `base_sha` guard
- controlled agent prompts/configs do not include `index_version`
- stale snapshot stop condition is missing
- final output does not include decisions made
- final output does not include deviations from PLAN.md
- final output does not include CONTEXT USED
- implementation blurs read-only git introspection and git mutation
- implementation permits agents to run git mutation commands
- implementation permits agents to run Docker commands
- runner service code is modified
- Dockerfile/workflow/GHCR files are modified
- package/app/service code is modified
- secrets or credentials are introduced
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is weakened
- `agents.no-git-mutation` is weakened
- `agents.no-secrets` is weakened

## Snapshot verification fields

Standardized `snapshot_verified` and `snapshot_verified_by` fields added to
review-agent and implementation-agent output requirements:

- `snapshot_verified: true | false | skipped`
  - `true`: current HEAD checked and matched `base_sha`
  - `false`: current HEAD checked and did not match `base_sha`
  - `skipped`: verification could not run or `base_sha` was `unknown`
- `snapshot_verified_by: git introspection | not available | filesystem`
  - `git introspection`: `git rev-parse --verify HEAD` was used
  - `not available`: no verification mechanism was available
  - `filesystem`: reserved for future non-git verification

All three review agents (architect, plan-review, precommit-review) and the
implementation agent (coder) now include these fields in their output format.
The project contract was extended with
`agents.context-snapshot.snapshot-verification-fields`.

## Context receipt requirement

## Stale snapshot refresh

Plan-review detected a stale snapshot during review:
- Previous base_sha: `f265ecd94fa5304ab377dfd7ce8c7334c2dc9229`
- Current HEAD: `db6999309a2656f2768eb9c9b453b153f340e36d`
- Action: PLAN base_sha refreshed before implementation

## Implementation note

All four controlled agent configs (architect, coder, plan-review, precommit-review)
were updated to include:

- Context snapshot block with base_sha guard and index_version capture
- Stale snapshot stop condition with exact STALE SNAPSHOT message format
- Allowed read-only git commands (git rev-parse --verify HEAD, git status --short)
- Forbidden git mutation command examples (git add, commit, push, reset, checkout,
  switch, merge, rebase, clean)
- Agent-appropriate final output format (implementation-style vs review-style)
- `git rev-parse*` added to each agent's allowed shell commands

The project contract was extended with 8 new contract entries covering
context-snapshot and final-output requirements.

The agent-config context bundle was updated with new anchors and notes
referencing the new contract IDs.

The memory index version was bumped from "0.1" to "0.2".

No runner code, Dockerfiles, workflows, docs, packages, apps, or prompts
were modified. No existing contracts were weakened.

Every agent response for this PR must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- index_version:
- current_head:
- stale_snapshot:

DECISIONS MADE:
- None — followed PLAN.md exactly
- or <decision> — <reason>

CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files modified:
- files intentionally ignored:
```
