# PR 0015: Runner Raw Diff Normalization Contract

## Goal

Add a minimal runner integration layer that takes a snapshot and sandbox, generates raw diff using `runner.diff.raw_diff`, and normalizes that diff using the existing `runner.patch` contract.

This PR must connect already-existing pieces without introducing patch application.

## Non-goals

- no Dockerfile changes
- no workflow changes
- no GHCR changes
- no runbook changes
- no API server
- no frontend
- no task execution engine
- no real agent execution
- no LLM calls
- no network calls
- no credentials
- no git mutation
- no git command dependency
- no canonical repository writes
- no patch application to canonical repo
- no ApplyPatch step
- no modification to `WorktreeManager`
- no modification to `raw_diff` behavior unless tests prove an integration bug
- no new patch format beyond existing `runner.patch` contract
- no broad refactor of `runner.patch`

## Future implementation scope

Future implementation may modify/create only:

```text
services/runner/src/runner/normalize.py
services/runner/tests/test_raw_diff_normalization.py
.project-memory/pr/0015-runner-raw-diff-normalization-contract/PLAN.md
```

No existing module has a natural home for this integration. A new `normalize.py` module avoids coupling either `diff.py` or `patch.py` with new import dependencies.

## Required contract

Create a minimal public function in:

```text
services/runner/src/runner/normalize.py
```

```python
def normalize_sandbox_diff(snapshot_path: Path, sandbox_path: Path) -> NormalizedPatch
```

Behavior:

- call `runner.diff.raw_diff(snapshot_path, sandbox_path)`
- pass the raw diff string into `runner.patch.normalize_patch_text(diff_text)`
- return the resulting `NormalizedPatch`
- do not invent a parallel patch model — reuse `NormalizedPatch` from `runner.models`

### Existing types used

| Module | Function / type | Role |
|--------|-----------------|------|
| `runner.diff` | `raw_diff(snapshot_path, sandbox_path) -> str` | Generates raw unified diff |
| `runner.patch` | `normalize_patch_text(diff_text: str) -> NormalizedPatch` | Validates paths, extracts touched paths |
| `runner.models` | `NormalizedPatch` | Return type |

## Required behavior

`normalize_sandbox_diff` must:

- accept snapshot path
- accept sandbox path
- call `raw_diff`
- normalize the raw diff through existing `patch.normalize_patch_text`
- preserve all raw diff safety behavior
- preserve all PatchNormalizer safety behavior
- reject unsafe paths through existing patch validation
- return deterministic output
- not mutate snapshot
- not mutate sandbox
- not modify canonical repo
- not apply patches
- not call git
- not use Docker
- not use network
- not use credentials

## Empty diff behavior

When `raw_diff` returns an empty string (no differences between snapshot and sandbox), `normalize_patch_text("")` returns:

```python
NormalizedPatch(text="", touched_paths=())
```

This is the existing no-op representation already used by the patch contract for empty/whitespace-only diffs. No new type or exception is needed.

## Safety invariants

- raw diff remains read-only
- normalization remains read-only
- patch application is forbidden
- canonical repo writes are forbidden
- no git commands
- no Docker
- no network
- no credentials
- no secrets
- no `.git` metadata
- no symlink following
- no binary files
- existing `runner.patch` safety rules remain source of truth for normalized patch validation

## Machine-readable scope

```text
allowed_write_paths:
- services/runner/src/runner/normalize.py
- services/runner/tests/test_raw_diff_normalization.py
- .project-memory/pr/0015-runner-raw-diff-normalization-contract/PLAN.md

forbidden_files:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/**
- docs/**
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
- services/** except:
  - services/runner/src/runner/normalize.py
- tests/**
- .project-memory/** except:
  - .project-memory/pr/0015-runner-raw-diff-normalization-contract/PLAN.md
```

## Tests

Require tests in:

```text
services/runner/tests/test_raw_diff_normalization.py
```

Tests must cover:

- no changes / empty diff returns `NormalizedPatch(text="", touched_paths=())`
- modified file diff normalizes successfully and returns `NormalizedPatch` with non-empty `touched_paths`
- added file diff normalizes successfully
- deleted file diff normalizes successfully
- nested relative path normalizes successfully
- unsafe path from patch contract is rejected (e.g. `.git` paths, secret-like files, symlinks, binaries)
- `.git` metadata rejection is preserved through the integration
- secret-like file rejection is preserved
- symlink rejection is preserved
- binary rejection is preserved
- snapshot is not mutated
- sandbox is not mutated
- canonical repo is not touched
- no patch application occurs
- no git command is required
- no Docker, network, or credentials are required

## Machine-checkable acceptance criteria

```text
normalize_module: services/runner/src/runner/normalize.py
test_file: services/runner/tests/test_raw_diff_normalization.py
public_function: normalize_sandbox_diff
uses_raw_diff: required
uses_existing_patch_contract: required
new_patch_model: forbidden
patch_application: forbidden
canonical_repo_writes: forbidden
git_commands_required: false
docker_required: false
network_required: false
credentials_required: false
filesystem_mutation: forbidden
raw_diff_safety_preserved: required
patch_safety_preserved: required
empty_diff_behavior: NormalizedPatch(text="", touched_paths=())
```

## Validation

Implementation PR must pass:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Do not run Docker commands.

## Stop / merge gates

Do not merge if:

- tests fail
- compileall fails
- doctor command fails
- implementation does not use `runner.diff.raw_diff`
- implementation bypasses existing `runner.patch.normalize_patch_text`
- implementation invents a duplicate patch model
- implementation applies patches
- implementation writes to canonical repo
- implementation mutates snapshot
- implementation mutates sandbox
- implementation calls git
- implementation uses Docker
- implementation uses network
- implementation reads credentials
- unsafe paths can pass normalization
- `.git` metadata can pass normalization
- secret-like files can pass normalization
- Dockerfile/workflow/GHCR/runbook files are modified
- services outside `services/runner/src/runner/normalize.py` are modified
- `runner.patch`, `runner.diff`, or `runner.models` are modified
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is violated
- `agents.no-git-mutation` is violated
- `agents.no-secrets` is violated

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

## Implementation note

The ``normalize_sandbox_diff`` function was implemented in
``services/runner/src/runner/normalize.py``.

The module is intentionally small (26 lines of code body). It delegates all
safety and validation to the two existing modules:

- ``runner.diff.raw_diff`` — deterministic unified diff with safety checks
- ``runner.patch.normalize_patch_text`` — path validation and normalization

No new safety logic, patch model, or patch application was added.
No existing modules (``patch.py``, ``diff.py``, ``models.py``, ``worktree.py``)
were modified. Tests verify end-to-end integration, safety preservation,
determinism, and no-mutation guarantees.

## Final output requirements

Every implementation PR response for this PR must include:

- files changed
- validation results
- confirm no Docker commands were run
- confirm no git mutation commands were run
- CONTEXT SNAPSHOT:
  - base_sha:
  - index_version:
- DECISIONS MADE:
  - none, if no deviation from PLAN.md
  - otherwise list each deviation and reason
- CONTEXT USED:
  - labels:
  - memory files read:
  - anchors used:
  - files inspected:
  - files modified:
  - files intentionally ignored:
