## Implementation note

PR 0022 implemented:
- Created `services/runner/src/runner/apply.py` with:
  - `ApplyRequest` dataclass with all gate-required fields
  - `ApplyPatch.evaluate()` gate/stub that validates ApplyRequests
  - `ApplyDecision`, `ApplyStatus`, `HumanApproval`, `ValidationEntry` models
  - `ApplyGateError` exception
  - `ApprovalStatus`, `ValidationResult`, `SnapshotVerifiedBy` enums
  - `validate_sha256()` and `validate_repo_relative()` helpers
  - Default refuse behaviour; only returns `ready_for_apply` when all gate checks pass
  - Structured rejection reasons for every failure
  - No canonical repo writes, git commands, subprocess, Docker, or network
- Created `services/runner/tests/test_apply_gate.py` with 20+ tests covering all gate checks, valid request, structured reasons, and no-side-effect guarantees
- Updated `services/runner/src/runner/__init__.py` to export `ApplyPatch`

No memory schemas, contracts, or forbidden files were modified. All dependencies are stdlib only.# PR 0022: ApplyPatch stub + HITL gate

## Goal

Add a runner-local ApplyPatch stub that refuses to apply normalized patches unless an explicit human-approved ApplyRequest passes gate checks.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "f608a5413d55dcd7e8a1320bf9292edeac0749c9"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.6"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "f608a5413d55dcd7e8a1320bf9292edeac0749c9"
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
- no real canonical repository mutation
- no git apply
- no git mutation commands by agents
- no Docker commands by agents
- no automatic apply
- no API server
- no frontend
- no automatic team runner
- no .ariadne/** namespace introduction
- no run_record.yml backfill
- no Apply Gate schema changes unless PLAN identifies a concrete mismatch
- no Run Record schema changes
- no artifact store redesign
- no secrets or credentials
- no workflow/GHCR/Dockerfile changes
```

## Future implementation allowed_write_paths

Implementation may modify/create only:

```text
services/runner/src/runner/apply.py
services/runner/tests/test_apply_gate.py
.project-memory/pr/0022-applypatch-stub-hitl-gate/PLAN.md
```

Optional only if justified by import/export need:

```text
services/runner/src/runner/__init__.py
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
services/runner/src/runner/apply.py
```

Expected concepts:

```text
ApplyPatch
ApplyRequest
ApplyDecision
ApplyGateResult
ApplyGateError
```

Required behavior:

```text
- default behavior is refuse
- no canonical repository writes
- no git commands
- no subprocess
- no Docker
- no network
- stdlib only
- ApplyPatch must validate an ApplyRequest-like object before any apply action
- ApplyRequest must require explicit human approval
- ApplyRequest must require normalized_patch_id or patch artifact sha
- ApplyRequest must require run_record_path and run_id reference
- ApplyRequest must require base_sha/current_head match or explicit stale waiver
- ApplyRequest must require scope_approved true
- ApplyRequest must require patch_normalized true
- ApplyRequest must require snapshot_verified true
- ApplyRequest must require no forbidden paths
- ApplyRequest must require validation passed or explicit human waiver
- ApplyRequest must record allowed_paths and forbidden_paths
- rejected requests must return structured reasons
- approved requests may only return "ready_for_apply" or equivalent stub result
- actual patch application remains unimplemented
```

The implementation must be a **gate/stub**, not a real patch applier.

Allowed final approved result:

```text
ready_for_apply
```

Forbidden final behavior:

```text
mutated_repo
applied_patch
git_apply_executed
canonical_write_performed
```

## Required tests

Create:

```text
services/runner/tests/test_apply_gate.py
```

Tests must cover:

```text
- default request is refused
- missing human approval refused
- missing normalized patch artifact refused
- missing run_record_path refused
- missing run_id refused
- missing snapshot verification refused
- missing scope approval refused
- missing patch normalization refused
- forbidden paths refused
- failed validation refused unless human waiver is present
- base_sha/current_head mismatch refused unless explicit stale waiver is present
- valid approved request returns ready_for_apply stub result
- no repository files are mutated
- no git/subprocess/docker/network calls are used
- structured rejection reasons are returned
```

## Relationship to existing contracts

```text
Apply Gate remains the only authorization contract for turning normalized patches into canonical writes.
PR 0022 implements only runner-local gate checks and a refusal-first ApplyPatch stub.
Artifact Store provides evidence references but does not authorize apply.
Run Record references are required for auditability but this PR does not create run_record.yml files.
Actual canonical patch application remains a future PR.
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

- implementation performs canonical repo writes
- implementation runs git apply
- implementation runs git mutation
- implementation uses Docker
- implementation uses subprocess for apply
- implementation modifies Apply Gate schema
- implementation modifies Run Record schema
- implementation creates actual run_record.yml files
- implementation introduces `.ariadne/**`
- implementation writes outside allowed runner files/tests
- implementation adds non-stdlib dependencies
- implementation weakens patch safety, worktree safety, artifact store safety, or Apply Gate invariants

## Machine-checkable acceptance criteria

```text
apply_module: services/runner/src/runner/apply.py
apply_tests: services/runner/tests/test_apply_gate.py
default_refuse: required
human_approval_required: required
normalized_patch_reference_required: required
run_record_path_required: required
run_id_required: required
snapshot_verified_required: required
scope_approved_required: required
patch_normalized_required: required
forbidden_paths_refused: required
validation_required_or_human_waiver: required
base_sha_current_head_match_or_waiver: required
structured_rejection_reasons: required
ready_for_apply_stub_only: required
canonical_repo_mutation: forbidden
git_apply: forbidden
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
subprocess_apply: forbidden
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
services/runner/src/runner/apply.py
services/runner/tests/test_apply_gate.py
.project-memory/pr/0022-applypatch-stub-hitl-gate/PLAN.md
```

Optional:

```text
services/runner/src/runner/__init__.py
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
