## Implementation note

PR 0022 implemented:
- Added validation shell permissions (`shell:cmd=python -m pytest*`, `shell:cmd=python -m compileall*`, `shell:cmd=PYTHONPATH=* python*`) to `agents/plan-review.yml` permissions.allow
- Added validation commands instruction block to plan-review.yml
- precommit-review.yml was NOT modified (already has permissions)
- Added `agents.review.validation-shell-access` contract entry to `.project-memory/project_contract.yml`
- Added `agents.review.validation-shell-access` anchor to `.project-memory/anchors.yml`
- Bumped `.project-memory/memory_index.yml` from version 0.5 to 0.6

No agent config changes to coder.yml, architect.yml, or precommit-review.yml. No service code, schema, or Docker permissions modified.# PR 0022: Reviewer Validation Shell Access

## Goal

Add read-only validation shell commands to plan-review and precommit-review agent configs so reviewers can self-execute required validation commands instead of blocking PRs due to missing author-supplied evidence.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "3ae2cdc1c6b550ea9e967b396dd0985d9a4ed6ad"
  base_sha_source: "git introspection"
  index_version: "0.5"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "3ae2cdc1c6b550ea9e967b396dd0985d9a4ed6ad"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: git introspection
```

## Problem

PR 0021 review produced `VERDICT: PASS` only after the author manually ran and attached validation outputs. The reviewer could not run `python -m pytest`, `python -m compileall`, or `python -m runner doctor` itself because shell permissions did not include these commands. This creates unnecessary round-trips on every implementation PR.

Validation commands are READ-ONLY with respect to the repository. They do not mutate files, git state, or the canonical repository. They are safe to add to reviewer agent shell permissions.

Note: `precommit-review.yml` already includes `python -m pytest*`, `python -m compileall*`, `make test*`, `make lint*`, and `grep*`. Only `plan-review.yml` needs addition of validation commands. However, to ensure consistency and future-proofing, both configs should have matching read-only validation shell access entries.

## Allowed write paths

```text
agents/plan-review.yml
agents/precommit-review.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/memory_index.yml
.project-memory/pr/0022-reviewer-validation-shell-access/PLAN.md
```

## Forbidden write paths

```text
agents/architect.yml
agents/coder.yml
agents/archive/**
services/**
packages/**
apps/**
docs/**
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
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
```

## Read-only context (inspect only, do not modify)

```text
agents/architect.yml
agents/coder.yml
```

## Required modifications

### 1. agents/plan-review.yml

Add to `permissions.allow`:

```yaml
    - "shell:cmd=python -m pytest*"
    - "shell:cmd=python -m pytest -q*"
    - "shell:cmd=python -m compileall*"
    - "shell:cmd=PYTHONPATH=services/runner/src python -m runner*"
```

The `grep*` and `find*` entries already exist in plan-review.yml — no change needed for those.

Preserve existing:
- all existing allow/ask/deny entries unchanged
- stale snapshot stop behavior unchanged
- git read-only allowlist unchanged (`git status`, `git rev-parse`, `git diff --name-only`)
- all forbidden git mutation commands unchanged

### 2. agents/precommit-review.yml

Add to `permissions.allow`:

```yaml
    - "shell:cmd=PYTHONPATH=services/runner/src python -m runner*"
```

The `python -m pytest*`, `python -m compileall*`, `grep*`, and `find*` entries already exist in precommit-review.yml — no change needed for those.

Preserve existing:
- all existing entries unchanged
- write_file/edit_file deny unchanged
- all forbidden git mutation commands unchanged
- all forbidden Docker commands unchanged

### 3. .project-memory/project_contract.yml

Add:

```yaml
  - id: "agents.review.validation-shell-access"
    text: >
      plan-review and precommit-review agents may execute
      read-only validation commands (pytest, compileall,
      runner doctor, grep) to self-verify implementation PRs
      without requiring author-supplied evidence.
    severity: "medium"
```

### 4. .project-memory/anchors.yml

Add:

```yaml
  - id: "agents.review.validation-shell-access"
    type: "agent-config"
    labels: ["agent-config", "contracts"]
    description: >
      Reviewers may run read-only validation commands.
      This does not grant write access to the repository
      or the ability to run git mutation or Docker commands.
```

### 5. .project-memory/memory_index.yml

Bump version from `"0.5"` to `"0.6"`. No label or bundle changes required.

## Invariants preserved

- git mutation commands remain forbidden for all agents
- Docker commands remain forbidden for all agents
- canonical repo write access remains forbidden for all agents
- coder agent shell permissions unchanged
- architect agent shell permissions unchanged
- all existing deny entries in both reviewer configs unchanged

## Validation commands

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

## Post-change checks

```bash
grep -n "shell:cmd=python\|shell:cmd=PYTHONPATH\|shell:cmd=grep" agents/plan-review.yml
grep -n "shell:cmd=python\|shell:cmd=PYTHONPATH\|shell:cmd=grep" agents/precommit-review.yml
grep -n "agents.review.validation-shell-access" .project-memory/project_contract.yml
git status --short
```

## Expected changed files

```text
agents/plan-review.yml
agents/precommit-review.yml
.project-memory/project_contract.yml
.project-memory/anchors.yml
.project-memory/memory_index.yml
.project-memory/pr/0022-reviewer-validation-shell-access/PLAN.md
```

## Decisions required

- **grep patterns**: Use separate explicit entries `shell:cmd=grep -R*` and `shell:cmd=grep -n*` rather than a single broad `shell:cmd=grep*`. Both configs already have `shell:cmd=grep*` from prior PRs, so this PR preserves existing patterns and does not change them.
- **PYTHONPATH pattern**: Use the exact prefix `shell:cmd=PYTHONPATH=services/runner/src python -m runner*` for the runner doctor command. This is more restrictive and preferred over a wildcard.
