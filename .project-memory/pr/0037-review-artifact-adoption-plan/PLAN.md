## Implementation note

PR 0037 implemented:
- Created `.project-memory/review-artifact-workflow.yml` with workflow stages, artifact paths, writer policy, validation policy, snapshot policy, safety policy, and adoption boundary
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.13 with review-artifact-workflow in read_first and adoption notes
- Bumped `.project-memory/memory_index.yml` to version 0.15 with review-artifact-workflow added to review-artifacts label additional_files

Review artifacts:
- `reviews/plan-review.yml` was already created by plan-review (approved)
- `reviews/precommit-review.yml` will be created by precommit-review after this implementation
- No review artifacts from old PRs were created
- No agents config changes in this PR# PR 0037: Review Artifact Adoption Plan

## Goal

Adopt the Review Artifact Contract from PR 0036 into the manual Ariadne PR workflow without changing agent configs yet.

Define a durable workflow guide:

```text
.project-memory/review-artifact-workflow.yml
```

The guide must tell future agents/humans:

- when `plan-review.yml` is created
- when `precommit-review.yml` is created
- what fields must be present
- how to distinguish passed/skipped/not_run validation
- how to preserve snapshot delta policy
- how to keep review artifacts evidence-only
- how to avoid apply-gate/run-record bypass
- how to avoid secrets in review evidence

## Context snapshot

```yaml
context_snapshot:
  base_sha: "01c0158525aceb472dc8fa927e254e2aaccfee06"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.14"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "01c0158525aceb472dc8fa927e254e2aaccfee06"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review must report snapshot deltas but must not block
solely because current HEAD differs from PLAN.md base_sha, unless scope
evidence shows unrelated or forbidden changes.
Review artifacts must include snapshot_delta fields according to
.project-memory/review-artifact.schema.yml.
```

## Non-goals

```text
- no agents/** changes
- no agent config changes
- no services/** changes
- no runner changes
- no task_intake changes
- no model_gateway changes
- no apply-gate semantic changes
- no run-record semantic changes
- no workspace feature record changes
- no .ariadne/** writes
- no runtime execution
- no Docker / CI / workflow changes
- no root dependency changes
- no retroactive migration of old reviews
- no review artifact attempts/history model
- no secrets or credentials
```

## Adoption policy

```text
PR 0037 applies the PR 0036 review artifact contract to the manual workflow.

For PR 0037 and future PRs:
- plan-review output should be persisted as .project-memory/pr/<pr-id>/reviews/plan-review.yml
- precommit-review output should be persisted as .project-memory/pr/<pr-id>/reviews/precommit-review.yml

PR 0037 itself should save its plan-review artifact after plan-review approval.
PR 0037 itself should save its precommit-review artifact after precommit-review pass/warning/block.

Old PRs are not migrated.
```

## Future allowed write paths for implementation

Implementation may modify/create only:

```text
.project-memory/review-artifact-workflow.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0037-review-artifact-adoption-plan/PLAN.md
.project-memory/pr/0037-review-artifact-adoption-plan/reviews/plan-review.yml
.project-memory/pr/0037-review-artifact-adoption-plan/reviews/precommit-review.yml
```

Important:

- `reviews/plan-review.yml` is created after plan-review.
- `reviews/precommit-review.yml` is created after precommit-review.
- Review artifacts must conform to `.project-memory/review-artifact.schema.yml`.

## Future forbidden write paths for implementation

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/model-routing.schema.yml
.project-memory/state-first.schema.yml
.project-memory/review-artifact.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/agent-config.yml
docs/**
agents/**
services/**
packages/**
apps/**
.github/**
docker/**
Dockerfile*
prompts/**
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
```

## Required workflow file

Future implementation must create:

```text
.project-memory/review-artifact-workflow.yml
```

Required content:

- `schema_version: "0.1"`
- relationship to `.project-memory/review-artifact.schema.yml`
- manual workflow stages:
  - `plan_created`
  - `plan_review_completed`
  - `implementation_completed`
  - `precommit_review_completed`
  - `pr_opened`
- artifact paths:
  - `.project-memory/pr/<pr-id>/reviews/plan-review.yml`
  - `.project-memory/pr/<pr-id>/reviews/precommit-review.yml`
- writer policy:
  - review agent may write only its own review artifact path
  - human may save artifact from agent output if agent has no write access
  - artifact must be committed with the PR
- validation policy:
  - passed/skipped/not_run must be distinct
  - fake validation is forbidden
- snapshot policy:
  - report delta
  - do not block solely on stale base_sha
  - block only on unrelated/forbidden scope evidence
- safety policy:
  - evidence only
  - no apply-gate bypass
  - no run-record bypass
  - no secrets
  - no runtime authorization
- adoption boundary:
  - no old PR migration
  - no agents config change in PR 0037
  - future PR may update agents after this manual workflow is established

## Contracts bundle update

Future implementation must update:

```text
.project-memory/context-bundles/contracts.yml
```

Required:

- bump bundle version according to existing style
- add `.project-memory/review-artifact-workflow.yml` to read_first
- add note: review artifact workflow adopted manually in PR 0037
- add note: future PRs should persist plan-review/precommit-review artifacts
- add note: agents configs are not changed in PR 0037

## Memory index update

Future implementation must update:

```text
.project-memory/memory_index.yml
```

Required:

- bump version according to existing style
- add or update label `review-artifacts`
- additional_files must include:
  - `.project-memory/review-artifact.schema.yml`
  - `.project-memory/review-artifact-workflow.yml`
- preferred_agent: `plan-review`

## PR 0037 own review artifacts

- PR 0037 should create its own `reviews/plan-review.yml` after plan-review.
- PR 0037 should create its own `reviews/precommit-review.yml` after precommit-review.
- These are not retroactive migration; they are first adoption of the new contract.
- These artifacts must be committed as part of PR 0037.
- No review artifacts from old PRs are created.

## Relationship to existing contracts

- Review Artifact schema from PR 0036 is authoritative.
- Run Record remains execution evidence and is not replaced.
- Apply Gate remains write authorization and is not bypassed.
- Workspace Feature Records are not created by review artifacts.
- State-First contract remains unchanged.
- Model-routing contract remains unchanged.
- Runner remains unchanged.
- Agents configs remain unchanged in this PR.

## Stop conditions

Stop if future implementation:

- modifies agents
- modifies services
- creates `.ariadne/**`
- creates run_record.yml
- changes apply-gate semantics
- changes run-record semantics
- changes review-artifact schema
- changes project_contract or anchors
- creates review artifacts for old PRs
- stores secrets in review evidence
- marks skipped/not_run validation as passed
- adds Docker/CI/root dependency changes

## Validation for future implementation

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "review-artifact-workflow\|plan-review.yml\|precommit-review.yml" .project-memory
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- grep shows expected review workflow references
- import regression grep has no matches
- git status only contains expected PR 0037 files
- no generated artifacts

## Expected changed files for planning task

```text
.project-memory/pr/0037-review-artifact-adoption-plan/PLAN.md
```

## Expected changed files for full PR

```text
.project-memory/review-artifact-workflow.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0037-review-artifact-adoption-plan/PLAN.md
.project-memory/pr/0037-review-artifact-adoption-plan/reviews/plan-review.yml
.project-memory/pr/0037-review-artifact-adoption-plan/reviews/precommit-review.yml
```

## Context receipt requirement

Every agent response must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- base_sha_source:
- index_version:
- index_version_source:
- current_head:
- stale_snapshot:
- snapshot_verified:
- snapshot_verified_by:

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
