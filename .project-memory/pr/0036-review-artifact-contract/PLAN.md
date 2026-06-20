# PR 0036: Review Artifact Contract

## Goal

Define a durable review artifact contract for Ariadne PR workflows.

Future review artifacts must be stored as:

```text
.project-memory/pr/<pr-id>/reviews/plan-review.yml
.project-memory/pr/<pr-id>/reviews/precommit-review.yml
```

The goal is to stop saving review evidence chaotically and define one stable machine-readable format for future agent reviews.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "65b57564d7581942bf4aa285779c8de3e75032e2"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.13"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "65b57564d7581942bf4aa285779c8de3e75032e2"
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
Review artifacts must include snapshot_delta fields.
```

## Non-goals

```text
- no retroactive migration of old PR reviews
- no saving this PR's plan-review as a review artifact before the contract exists
- no changes to agents/ configs
- no services/ changes
- no runner changes
- no task_intake changes
- no model_gateway changes
- no .ariadne/** writes
- no run_record.yml creation
- no Workspace Feature Record creation
- no apply-gate changes
- no model-routing changes
- no state-first contract changes except references if needed
- no Docker / CI / workflow changes
- no root dependency changes
- no secrets or credentials
```

## Review artifact adoption policy

```text
PR 0036 defines the contract.
Review artifacts become required for future PR workflows after PR 0036 is merged.
PR 0036 itself does not need to persist its own plan-review/precommit-review under
the new format because the contract is not yet merged at review time.
Future PRs should persist:
- .project-memory/pr/<pr-id>/reviews/plan-review.yml after plan-review
- .project-memory/pr/<pr-id>/reviews/precommit-review.yml after precommit-review
```

## Future allowed write paths for implementation

Implementation commit may modify/create only:

```text
.project-memory/review-artifact.schema.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml
.project-memory/pr/0036-review-artifact-contract/PLAN.md
```

Optional only if strongly justified:

```text
docs/adr/0004-review-artifacts.md
```

But prefer no ADR unless project style requires it.

**Plan-review resolution:** PR 0036 does not create `docs/adr/0004-review-artifacts.md`.
`docs/**` remains forbidden for implementation. Review artifact contract is kept in
`.project-memory/**` only.

## Implementation note

PR 0036 implemented:
- Created `.project-memory/review-artifact.schema.yml` with ReviewArtifact, SnapshotDelta, ScopeCheck, ValidationCommand, ReviewBlocker, ReviewWarning, ReviewDecision, ReviewContextUsed definitions, verdict rules, snapshot policy, safety rules, invalid cases, and minimal valid plan-review/precommit-review examples
- Added 15 `review-artifact.*` contract entries to `.project-memory/project_contract.yml`
- Added 10 review-artifact anchors to `.project-memory/anchors.yml`
- Updated `.project-memory/context-bundles/contracts.yml` to version 0.12 with review-artifact schema in read_first, anchors, and notes
- Bumped `.project-memory/memory_index.yml` to version 0.14 with new `review-artifacts` label

Plan-review warning resolved: No ADR 0004 created. docs/** remains forbidden.

No actual review artifact files created. No retroactive migration. No services/agents/runner changes.

## Future forbidden write paths for implementation

Implementation must not modify/create:

```text
.ariadne/**
.project-memory/features/**
.project-memory/pr/*/feature*.yml
.project-memory/pr/*/run_record.yml
.project-memory/pr/*/reviews/*.yml
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/workspace-feature-record.schema.yml
.project-memory/context-steward-archival.schema.yml
.project-memory/task-intake-request.schema.yml
.project-memory/task-intake-runner-handoff.schema.yml
.project-memory/model-routing.schema.yml
.project-memory/state-first.schema.yml
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

Note:

- `.project-memory/pr/*/reviews/*.yml` is forbidden in this PR because PR 0036 defines the contract only.
- Actual review artifacts start in future PRs after this contract is merged.

## Required schema

Create:

```text
.project-memory/review-artifact.schema.yml
```

Schema version:

```text
schema_version: "0.1"
```

Schema must define:

```text
ReviewArtifact
SnapshotDelta
ScopeCheck
ValidationCommand
ReviewBlocker
ReviewWarning
ReviewDecision
ReviewContextUsed
```

ReviewArtifact required fields:

```text
schema_version
pr_id
review_type
verdict
reviewer
timestamp
snapshot_delta
scope
files_checked
validation
blockers
warnings
decisions_made
context_used
```

ReviewArtifact optional fields:

```text
summary
recommendations
related_plan
related_commit
```

Allowed `review_type` values:

```text
plan-review
precommit-review
security-review
ci-review
manual-review
```

Required initial review types:

- `plan-review`
- `precommit-review`

Allowed `verdict` values:

```text
approve
pass
warning
block
```

Verdict rules:

- `plan-review` may use `approve`, `warning`, `block`.
- `precommit-review` may use `pass`, `warning`, `block`.
- `block` requires at least one blocker.
- `warning` requires at least one warning or explicit rationale.
- `approve` and `pass` require blockers to be empty.
- Validation failures must not be hidden.

SnapshotDelta required fields:

```text
plan_base_sha
current_head
action
stale_snapshot
```

Snapshot policy in schema comments:

- Report delta.
- Do not block solely on PLAN base_sha mismatch.
- Block only if scope evidence shows unrelated or forbidden changes.

ScopeCheck required fields:

```text
expected_files
actual_files
forbidden_paths_checked
forbidden_paths_found
generated_artifacts_found
scope_status
```

Allowed `scope_status` values:

```text
in_scope
warning
blocked
```

ValidationCommand required fields:

```text
command
result
exit_code
evidence
```

Allowed validation result values:

```text
passed
failed
skipped
not_run
```

ReviewBlocker required fields:

```text
id
description
severity
evidence
required_fix
```

ReviewWarning required fields:

```text
id
description
evidence
recommendation
```

ReviewDecision required fields:

```text
decision
reason
```

ReviewContextUsed required fields:

```text
labels
memory_files_read
anchors_used
files_inspected
files_modified
files_intentionally_ignored
```

Required safety rules:

- ReviewArtifact is evidence only.
- ReviewArtifact does not authorize canonical writes.
- ReviewArtifact does not replace `apply-gate.schema.yml`.
- ReviewArtifact does not replace `run-record.schema.yml`.
- ReviewArtifact does not create runtime state.
- ReviewArtifact must not contain secrets.
- ReviewArtifact must not invent validation evidence.
- ReviewArtifact must distinguish not-run/skipped validation from passed validation.
- ReviewArtifact must include files_modified, even when empty.

Required artifact path rules:

- `plan-review` artifact path: `.project-memory/pr/<pr-id>/reviews/plan-review.yml`
- `precommit-review` artifact path: `.project-memory/pr/<pr-id>/reviews/precommit-review.yml`
- exactly one canonical artifact per review type per PR unless future contract defines attempts
- path must remain under the same PR directory
- review artifact must not be stored in `.ariadne/**`

Include minimal valid example for `plan-review`.
Include minimal valid example for `precommit-review`.
Include invalid cases:

- `block` verdict with empty blockers
- `pass` verdict with blockers
- validation failure marked as passed
- missing snapshot_delta
- missing files_checked
- review artifact outside `.project-memory/pr/<pr-id>/reviews/`
- review artifact used as write authorization
- secret/API key included in review evidence

## Future required contract ids

```text
review-artifact.schema-path
review-artifact.plan-review.required
review-artifact.precommit-review.required
review-artifact.path.required
review-artifact.verdict-rules.required
review-artifact.snapshot-delta.required
review-artifact.scope-check.required
review-artifact.validation-evidence.required
review-artifact.no-fake-validation
review-artifact.blockers-required-for-block
review-artifact.evidence-only
review-artifact.no-apply-gate-bypass
review-artifact.no-run-record-bypass
review-artifact.no-secrets
review-artifact.no-retroactive-migration-this-pr
```

Required meanings:

- `review-artifact.schema-path`: Schema path `.project-memory/review-artifact.schema.yml`. severity: medium
- `review-artifact.plan-review.required`: Future PR workflows must persist plan-review artifacts. severity: high
- `review-artifact.precommit-review.required`: Future PR workflows must persist precommit-review artifacts. severity: high
- `review-artifact.path.required`: Review artifacts must live under `.project-memory/pr/<pr-id>/reviews/`. severity: high
- `review-artifact.verdict-rules.required`: Review artifacts must follow verdict rules by review type. severity: high
- `review-artifact.snapshot-delta.required`: Review artifacts must include snapshot_delta. severity: high
- `review-artifact.scope-check.required`: Review artifacts must include scope check. severity: high
- `review-artifact.validation-evidence.required`: Review artifacts must record validation results. severity: high
- `review-artifact.no-fake-validation`: Validation marked passed only when evidence exists. severity: critical
- `review-artifact.blockers-required-for-block`: Block verdict requires at least one blocker. severity: high
- `review-artifact.evidence-only`: Review artifacts are evidence only. severity: high
- `review-artifact.no-apply-gate-bypass`: Must not bypass apply-gate. severity: critical
- `review-artifact.no-run-record-bypass`: Must not replace run records. severity: critical
- `review-artifact.no-secrets`: Must not contain secrets. severity: critical
- `review-artifact.no-retroactive-migration-this-pr`: PR 0036 does not migrate historical reviews. severity: medium

## Future required anchors

```text
review-artifact.schema-path
review-artifact.plan-review.required
review-artifact.precommit-review.required
review-artifact.path.required
review-artifact.snapshot-delta.required
review-artifact.validation-evidence.required
review-artifact.no-fake-validation
review-artifact.evidence-only
review-artifact.no-apply-gate-bypass
review-artifact.no-secrets
```

## Future contracts bundle update

Future implementation will update `.project-memory/context-bundles/contracts.yml`:

- bump bundle version
- add `.project-memory/review-artifact.schema.yml` to read_first
- add review-artifact anchors
- add notes:
  - review artifacts are evidence only
  - review artifacts do not bypass apply-gate
  - review artifacts do not replace run records
  - future PRs should save `plan-review.yml` and `precommit-review.yml`
  - PR 0036 does not retroactively migrate old reviews

## Future memory index update

Future implementation will update `.project-memory/memory_index.yml`:

- bump version
- add label: `review-artifacts`
- description: Durable review artifact contract for plan-review and precommit-review evidence.
- additional_files:
  - `.project-memory/review-artifact.schema.yml`
- preferred_agent: `plan-review`

## Relationship to existing contracts

- Review artifacts complement Run Record but do not replace it.
- Review artifacts complement Apply Gate but do not authorize writes.
- Review artifacts complement Workspace Feature Records but do not create feature records.
- Snapshot policy follows existing Ariadne policy: report delta, do not block on stale base_sha alone.
- State-First contract remains unchanged.
- Model-routing contract remains unchanged.
- Runner remains unchanged.
- Agents configs remain unchanged in this PR.

## Stop conditions

Stop if future implementation:

- modifies services
- modifies agents
- creates `.ariadne/**`
- creates `run_record.yml`
- creates actual review artifacts under `.project-memory/pr/*/reviews/*.yml` in this PR
- retroactively migrates old reviews
- modifies forbidden schemas
- changes apply-gate semantics
- changes run-record semantics
- adds dependencies
- adds secrets or credentials
- saves fake validation as passed
- weakens snapshot delta policy

## Validation for future implementation

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "review-artifact\|plan-review.yml\|precommit-review.yml" .project-memory
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

Expected:

- pytest passes
- compileall passes
- runner doctor passes
- review-artifact grep shows expected references
- import regression grep has no matches
- git status only contains expected contract files
- no actual review artifacts are created in PR 0036
- no generated artifacts

## Expected changed files for planning task

```text
.project-memory/pr/0036-review-artifact-contract/PLAN.md
```
