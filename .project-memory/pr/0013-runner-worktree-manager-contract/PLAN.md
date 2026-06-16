# PR 0013: Runner WorktreeManager Contract

## Goal

Add a minimal `WorktreeManager` contract for safe filesystem isolation before agent execution.

The goal is not task execution yet. The goal is to establish the runner-controlled file substrate that future agents will use.

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
- no canonical repository writes
- no applying patches to the canonical repo
- no raw diff normalization yet
- no `git diff --no-index` yet unless explicitly planned in a later PR

## Future implementation scope

Future implementation may modify/create only:

```text
services/runner/src/runner/worktree.py
services/runner/tests/test_worktree_manager.py
.project-memory/pr/0013-runner-worktree-manager-contract/PLAN.md
```

## Required contract

Define a minimal `WorktreeManager` in:

```text
services/runner/src/runner/worktree.py
```

Required public methods:

```text
create_context_snapshot(source_root: Path, include_paths: Sequence[str]) -> Path
create_sandbox(snapshot_path: Path) -> Path
destroy(path: Path) -> None
```

Optional dataclass if useful:

```text
WorktreePaths
- root: Path
- context_snapshot: Path
- sandbox: Path
```

## Required behavior

`create_context_snapshot` must:

- accept a canonical `source_root`
- accept explicit relative `include_paths`
- copy only requested files/directories
- reject absolute paths
- reject `..` path traversal
- reject `.git` paths
- reject missing include paths unless tests define clear behavior
- create the snapshot under a temporary runner-owned directory
- never modify `source_root`

`create_sandbox` must:

- copy from a context snapshot into a writable sandbox directory
- create a separate path from the snapshot
- not include `.git`
- never modify the snapshot
- never modify the canonical repo

`destroy` must:

- remove only paths created by the manager
- reject unsafe paths outside the manager-owned temp root
- be deterministic
- reject paths not created by this manager instance
- reject paths under manager-owned temp root but absent from the manager-created registry
- reject `/`, `source_root`, repository root, and parent directories of manager-owned temp root
- be idempotent or clearly documented as safe to call once
- never remove canonical repository paths
- not call `shutil.rmtree` on untrusted caller-provided paths before ownership validation

## Safety invariants

- agents never write directly to canonical repo
- canonical repo is read-only input for this PR
- `.git` is never copied into snapshot or sandbox
- no credentials are copied
- no network required
- no Docker required
- no git commands required
- future patch application remains a separate trusted step

## Manager-owned temp root

```text
WorktreeManager MUST create and use one manager-owned temporary root for all snapshots and sandboxes.
The manager-owned temp root must be created with tempfile.mkdtemp or equivalent.
create_context_snapshot and create_sandbox MUST place all created artifacts under this manager-owned temp root.
WorktreeManager MUST track created snapshot and sandbox paths in an internal registry.
destroy MUST only remove paths that are both:
- under the manager-owned temp root
- present in the manager-created path registry
destroy MUST reject canonical repository paths, arbitrary absolute paths, and paths outside the manager-owned temp root.
destroy MUST NOT call shutil.rmtree on untrusted caller-provided paths before ownership validation.
```

## Symlink policy

```text
Symlink handling must be explicit and safe.
The implementation MUST NOT follow symlinks that resolve outside source_root.
Symlink escapes must be rejected.
A symlink inside include_paths that points outside source_root must not copy external contents into snapshot or sandbox.
A symlink inside include_paths that points to .git, .env, credentials, or another forbidden path must be rejected.
Tests must cover symlink escape behavior.
```

## Hidden and secret file policy

```text
Known secret-like files must not be copied into snapshots or sandboxes even if explicitly requested.
At minimum, reject:
- .env
- .env.*
- id_rsa
- id_dsa
- id_ecdsa
- id_ed25519
- files under .ssh/
- files under .aws/
- files under .config/gh/
Behavior for these paths must be deterministic and tested.
```

## Git metadata policy

The manager must reject:
- `.git` directories
- nested `.git` directories
- `.git` file pointers used by submodules/worktrees
- include paths that resolve into any `.git` component

No git metadata may be copied into snapshots or sandboxes.

## Machine-readable scope

```text
allowed_write_paths:
- services/runner/src/runner/worktree.py
- services/runner/tests/test_worktree_manager.py
- .project-memory/pr/0013-runner-worktree-manager-contract/PLAN.md

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
  - services/runner/src/runner/worktree.py
- tests/**
- .project-memory/** except:
  - .project-memory/pr/0013-runner-worktree-manager-contract/PLAN.md
```

## Tests

Require tests in:

```text
services/runner/tests/test_worktree_manager.py
```

Tests must cover:

- snapshot copies only explicitly included files
- snapshot rejects absolute include paths
- snapshot rejects `..` traversal
- snapshot rejects `.git`
- sandbox is separate from snapshot
- sandbox can be modified without changing snapshot
- source_root/canonical repo is not modified
- `.git` is not copied
- destroy removes manager-owned temp paths
- destroy rejects unsafe paths outside manager-owned temp root
- no Docker, network, credentials, or git commands are required
- manager creates a dedicated temp root
- snapshot and sandbox are created under manager-owned temp root
- created paths are tracked
- destroy removes registered paths
- destroy rejects paths outside manager-owned temp root
- destroy rejects source_root/repository root
- destroy rejects paths under temp root if they were not created by manager
- symlink to file outside source_root is rejected
- symlink to forbidden path is rejected
- `.env` and `.env.*` are rejected
- private key-like filenames are rejected
- `.git` directory is rejected
- `.git` file pointer is rejected
- nested `.git` path is rejected
- relative paths and file contents are preserved for allowed files
- sandbox mutation does not modify snapshot or source_root

## Machine-checkable acceptance criteria

```text
worktree_module: services/runner/src/runner/worktree.py
test_file: services/runner/tests/test_worktree_manager.py
docker_required: false
network_required: false
credentials_required: false
git_commands_required: false
canonical_repo_writes: forbidden
copies_git_directory: forbidden
copies_gitfile_pointer: forbidden
raw_diff_generation: forbidden
patch_application: forbidden
manager_owned_temp_root: required
created_path_registry: required
destroy_outside_temp_root: forbidden
destroy_unregistered_path: forbidden
symlink_escape: forbidden
copy_secret_files: forbidden
copy_git_metadata: forbidden
implicit_include_paths: forbidden
include_paths_allowlist_only: required
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
- `.git` can be copied into snapshot or sandbox
- absolute paths are accepted
- `..` traversal is accepted
- canonical repository files are modified
- destroy can remove paths outside manager-owned temp root
- WorktreeManager can follow symlinks outside source_root
- WorktreeManager can copy `.env`, `.env.*`, SSH keys, AWS config, GH config, or other known secret-like files
- WorktreeManager can copy `.git` directories, nested `.git` paths, or `.git` file pointers
- destroy can remove unregistered paths
- snapshot or sandbox paths are not under manager-owned temp root
- Dockerfile/workflow/GHCR/runbook files are modified
- services outside `services/runner/src/runner/worktree.py` are modified
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is violated
- `agents.no-git-mutation` is violated
- `agents.no-secrets` is violated

## Context receipt requirement

## Implementation note

The WorktreeManager was implemented in ``services/runner/src/runner/worktree.py``.

Key implementation choices:

- All symlinks are rejected for safety (simpler than selective symlink following).
- `create_context_snapshot` rejects `.git` directories, nested `.git`, `.git` file pointers, 
  and any path with a `.git` component.
- Secret-like files (`.env`, `.env.*`, SSH keys, `.aws/`, `.ssh/`, `.config/gh/`) are 
  rejected even if explicitly requested.
- `destroy` validates ownership via path registry before any removal.
- All paths use `source_root.resolve()` to avoid symlink-based path confusion.
- Tests cover all safety requirements including symlink rejection, secret rejection,
  git metadata rejection, and destroy ownership validation.

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
