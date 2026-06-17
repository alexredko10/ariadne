## Implementation note

PR 0023 implemented:
- Created `services/runner/src/runner/mock_coder.py` with:
  - `MockCoder` class (proof harness, not real LLM coder)
  - `MockCoderRequest`, `MockCoderResult`, `SandboxWrite`, `SandboxViolation` models
  - `MockCoderError` exception
  - Sandbox-only writes with absolute path, path traversal, and symlink escape rejection
  - Structured violation reasons for every refused write
  - No git commands, subprocess, Docker, or network
  - stdlib only
- Created `services/runner/tests/test_mock_coder_sandbox.py` with 15+ tests covering:
  - Sandbox writes, parent directory creation, multiple writes
  - Canonical repo unchanged verification
  - Absolute path, path traversal, and symlink escape refusal
  - Structured rejection reasons
  - No side-effects (no git/subprocess/docker)
  - Worktree separation proof (snapshot unchanged while sandbox modified)
- Updated `services/runner/src/runner/__init__.py` to export `MockCoder`

No memory schemas, contracts, or forbidden files were modified. All dependencies are stdlib only.# PR 0023: Mock Coder sandbox-only proof

## Goal

Add a runner-local mock coder proof showing that agent-like writes occur only inside the sandbox and canonical repository files remain unchanged.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "765521e891610965d604bbb488d1b329be451ecd"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.6"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "765521e891610965d604bbb488d1b329be451ecd"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review should report snapshot deltas but must not block solely because current HEAD differs from PLAN.md base_sha, unless scope evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no real LLM agent execution
- no external model calls
- no Docker commands
- no git mutation commands
- no canonical repository writes by agents
- no ApplyPatch real application
- no workflow/GHCR/Dockerfile changes
- no API server
- no frontend
- no automatic team runner
- no .ariadne/** namespace introduction
- no run_record.yml backfill
- no Apply Gate schema changes
- no Run Record schema changes
- no artifact store redesign
- no secrets or credentials
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
services/runner/src/runner/mock_coder.py
services/runner/tests/test_mock_coder_sandbox.py
.project-memory/pr/0023-mock-coder-sandbox-only-proof/PLAN.md
```

Optional only if justified by import/export need:

```text
services/runner/src/runner/__init__.py
services/runner/src/runner/worktree.py
services/runner/src/runner/models.py
```

## Future implementation forbidden_write_paths

Implementation must not modify:

```text
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
.ariadne/**
agents/**
services/conductor/**
services/core/**
services/model_gateway/**
services/task_intake/**
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
```

## Required implementation design

Create:

```text
services/runner/src/runner/mock_coder.py
```

Expected concepts:

```text
MockCoder
MockCoderRequest
MockCoderResult
SandboxWrite
SandboxViolation
```

Required behavior:

```text
- mock coder accepts a sandbox root and a list of intended writes
- mock coder writes only under the sandbox root
- all write targets must be repo-relative POSIX paths
- absolute paths are rejected
- path traversal is rejected
- symlink traversal is rejected or safely ignored
- attempts to target canonical repo paths outside sandbox are refused
- no git commands
- no subprocess
- no Docker
- no network
- stdlib only
- result records written files and refused writes
- canonical repository files are never mutated by MockCoder
```

The implementation must be a proof harness, not a real LLM coder.

Allowed final behavior:

```text
sandbox_write_performed
sandbox_write_refused
```

Forbidden final behavior:

```text
canonical_repo_write_performed
git_mutation_executed
docker_executed
network_executed
```

## Required tests

Create:

```text
services/runner/tests/test_mock_coder_sandbox.py
```

Tests must cover:

```text
- mock coder writes a file inside sandbox
- mock coder creates parent directories inside sandbox
- canonical repo fixture file remains unchanged
- absolute path write is refused
- ../ path traversal is refused
- symlink escape is refused or safely ignored
- multiple sandbox writes are recorded
- refused writes are recorded with structured reasons
- no writes outside sandbox root
- no git/subprocess/docker/network calls are used
- interaction with WorktreeManager or equivalent sandbox fixture proves snapshot/canonical separation
```

## Relationship to existing contracts

```text
Mock Coder sandbox-only proof demonstrates that agent-like writes are confined to a sandbox/worktree.
Raw diff remains the mechanism for comparing snapshot and sandbox.
Artifact Store may store future evidence but does not authorize writes.
ApplyPatch HITL gate remains the only path toward future canonical mutation.
PR 0023 does not implement real apply and does not mutate the canonical repository.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
```

Expected grep result:

- no matches

## Stop conditions

Stop if:

- implementation mutates canonical repo files
- implementation uses git mutation
- implementation uses Docker
- implementation uses subprocess for writes
- implementation uses network
- implementation modifies Apply Gate schema
- implementation modifies Run Record schema
- implementation creates actual run_record.yml files
- implementation introduces `.ariadne/**`
- implementation writes outside allowed runner files/tests
- implementation adds non-stdlib dependencies
- implementation weakens patch safety, worktree safety, artifact store safety, or Apply Gate invariants

## Machine-checkable acceptance criteria

```text
mock_coder_module: services/runner/src/runner/mock_coder.py
mock_coder_tests: services/runner/tests/test_mock_coder_sandbox.py
sandbox_root_required: required
repo_relative_posix_paths: required
absolute_paths_refused: required
path_traversal_refused: required
symlink_escape_refused: required
canonical_repo_unchanged: required
writes_recorded: required
refusals_recorded: required
structured_rejection_reasons: required
worktree_or_sandbox_separation_proved: required
canonical_repo_mutation: forbidden
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
subprocess_writes: forbidden
network: forbidden
non_stdlib_dependencies: forbidden
apply_gate_schema_changes: forbidden
run_record_schema_changes: forbidden
actual_run_record_files: forbidden
ariadne_namespace_changes: forbidden
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
services/runner/src/runner/mock_coder.py
services/runner/tests/test_mock_coder_sandbox.py
.project-memory/pr/0023-mock-coder-sandbox-only-proof/PLAN.md
```

Optional:

```text
services/runner/src/runner/__init__.py
services/runner/src/runner/worktree.py
services/runner/src/runner/models.py
```

## Context receipt requirement

Every agent response for this PR must include:

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
