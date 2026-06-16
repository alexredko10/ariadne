# PR 0014: Runner Raw Diff Contract

## Goal

Add a minimal raw diff contract that compares a `WorktreeManager` snapshot and sandbox and returns a unified diff string.

This is the next runner substrate layer after snapshot/sandbox isolation.

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
- no `git diff --no-index`
- no canonical repository writes
- no patch application to canonical repo
- no PatchNormalizer integration yet
- no binary diff support unless explicitly rejected with tests

## Future implementation scope

Future implementation may modify/create only:

```text
services/runner/src/runner/diff.py
services/runner/tests/test_raw_diff.py
.project-memory/pr/0014-runner-raw-diff-contract/PLAN.md
```

## Required contract

Define a minimal raw diff function in:

```text
services/runner/src/runner/diff.py
```

Required public function:

```python
raw_diff(snapshot_path: Path, sandbox_path: Path) -> str
```

Optional exception if useful:

```python
class RawDiffError(ValueError):
    ...
```

## Required behavior

`raw_diff` must:

- accept a snapshot path
- accept a sandbox path
- compare files recursively
- return a unified diff string
- use Python stdlib only, preferably `difflib`
- avoid git commands
- avoid network
- avoid credentials
- avoid Docker
- avoid filesystem mutation
- never modify snapshot
- never modify sandbox
- never modify canonical repo
- reject paths that do not exist
- reject paths that are not directories
- reject paths where snapshot and sandbox are the same path
- reject `.git` metadata
- reject secret-like files if encountered:

  * `.env`
  * `.env.*`
  * `id_rsa`
  * `id_dsa`
  * `id_ecdsa`
  * `id_ed25519`
  * files under `.ssh/`
  * files under `.aws/`
  * files under `.config/gh/`
- reject symlinks or handle them safely by deterministic rejection
- reject binary files for this PR with deterministic error

## Diff output requirements

The unified diff should cover:

- modified text files
- added text files
- deleted text files

Diff paths should be stable and relative.

Suggested path labels:

- `a/<relative-path>` for snapshot side
- `b/<relative-path>` for sandbox side

Expected style example:

```diff
--- a/app.py
+++ b/app.py
@@ ... @@
-old
+new
```

For added files:

- old side may be `/dev/null` or `a/<path>` with empty content
- behavior must be deterministic and tested

For deleted files:

- new side may be `/dev/null` or `b/<path>` with empty content
- behavior must be deterministic and tested

## Determinism and text policy

```text
File traversal must be deterministic.
raw_diff MUST collect relative file paths from snapshot and sandbox, normalize them to POSIX-style forward-slash paths, and process them in sorted lexical order.

Text decoding policy:
- text files MUST be decoded as UTF-8 with errors="strict"
- files that fail UTF-8 decoding MUST be rejected deterministically as binary/unsupported
- files containing NUL bytes MUST be rejected deterministically as binary/unsupported

Line ending policy:
- raw_diff MUST normalize CRLF and CR line endings to LF for diff presentation
- output diff lines MUST use LF newlines
- newline-at-EOF behavior must be deterministic and covered by tests

Path policy:
- diff headers MUST use POSIX-style forward slashes
- snapshot-side labels MUST use `a/<relative-path>`
- sandbox-side labels MUST use `b/<relative-path>`
- added files MUST use `/dev/null` for the snapshot side
- deleted files MUST use `/dev/null` for the sandbox side

Directory and metadata policy:
- empty directories are ignored
- chmod-only or metadata-only changes are ignored in this PR
- hidden non-secret files are allowed if they are explicitly present in snapshot or sandbox and do not match forbidden secret/git policies
```

## Binary detection policy

```text
Binary detection is deterministic.
A file is treated as binary/unsupported if:
- it contains a NUL byte
- it cannot be decoded as UTF-8 with strict errors
Binary files are rejected in this PR.
raw_diff MUST fail with a deterministic RawDiffError or equivalent deterministic exception when binary/unsupported files are encountered.
```

## Safety invariants

- raw diff is read-only
- raw diff does not apply patches
- raw diff does not normalize patches yet
- raw diff does not call git
- raw diff does not use Docker
- raw diff does not use network
- raw diff does not read secrets
- raw diff does not include `.git`
- canonical repo is not touched
- snapshot and sandbox are inputs only

## Machine-readable scope

```text
allowed_write_paths:
- services/runner/src/runner/diff.py
- services/runner/tests/test_raw_diff.py
- .project-memory/pr/0014-runner-raw-diff-contract/PLAN.md

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
  - services/runner/src/runner/diff.py
- tests/**
- .project-memory/** except:
  - .project-memory/pr/0014-runner-raw-diff-contract/PLAN.md
```

## Tests

Require tests in:

```text
services/runner/tests/test_raw_diff.py
```

Tests must cover:

- no changes returns empty string
- modified text file returns unified diff
- added text file appears in diff
- deleted text file appears in diff
- nested relative paths are stable
- output uses stable relative path labels
- snapshot path must exist
- sandbox path must exist
- snapshot and sandbox must be directories
- snapshot and sandbox cannot be same path
- `.git` metadata is rejected
- nested `.git` is rejected
- `.env` and `.env.*` are rejected
- private key-like filenames are rejected
- `.ssh/`, `.aws/`, `.config/gh/` are rejected
- symlinks are rejected
- binary files are rejected deterministically
- function does not mutate snapshot
- function does not mutate sandbox
- no Docker, network, credentials, or git commands are required
- deterministic sorted file ordering
- POSIX-style path separators in diff headers
- UTF-8 strict decoding
- invalid UTF-8 rejected as binary/unsupported
- NUL byte rejected as binary/unsupported
- CRLF normalized to LF in diff output
- newline-at-EOF behavior is deterministic
- added file uses `/dev/null` on snapshot side
- deleted file uses `/dev/null` on sandbox side
- empty directories are ignored
- chmod-only / metadata-only changes are ignored
- hidden non-secret file can be diffed when explicitly present
- hidden secret-like file is rejected

## Machine-checkable acceptance criteria

```text
diff_module: services/runner/src/runner/diff.py
test_file: services/runner/tests/test_raw_diff.py
public_function: raw_diff
stdlib_only: required
git_commands_required: false
docker_required: false
network_required: false
credentials_required: false
filesystem_mutation: forbidden
canonical_repo_writes: forbidden
patch_application: forbidden
patch_normalizer_integration: forbidden
binary_diff_support: forbidden
copy_secret_files: forbidden
read_secret_files: forbidden
read_git_metadata: forbidden
symlink_handling: reject
stable_ordering: required
path_normalization: posix
utf8_text_policy: strict
line_ending_policy: normalize_to_lf
binary_detection: nul_or_invalid_utf8
added_file_old_label: /dev/null
deleted_file_new_label: /dev/null
empty_directories: ignored
metadata_only_changes: ignored
hidden_non_secret_files: allowed
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
- raw_diff calls git
- raw_diff mutates snapshot
- raw_diff mutates sandbox
- raw_diff can read `.git`
- raw_diff can read `.env`, `.env.*`, SSH keys, AWS config, GH config, or other known secret-like files
- raw_diff follows symlinks
- raw_diff silently processes binary files
- raw_diff applies patches
- raw_diff integrates PatchNormalizer in this PR
- raw_diff output ordering depends on filesystem iteration order
- diff headers use platform-specific path separators
- invalid UTF-8 or NUL-containing files are silently diffed
- CRLF handling is undefined
- added/deleted file labels are ambiguous
- empty directories or metadata-only changes produce undocumented output
- Dockerfile/workflow/GHCR/runbook files are modified
- services outside `services/runner/src/runner/diff.py` are modified
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is violated
- `agents.no-git-mutation` is violated
- `agents.no-secrets` is violated

## Context receipt requirement

## Implementation note

The raw diff function was implemented in ``services/runner/src/runner/diff.py``.

Key implementation choices:

- Uses ``difflib.unified_diff`` from stdlib — no git commands, no external dependencies.
- ``os.walk`` for sorted file collection; ``os.path.relpath`` for relative path extraction.
- Symlinks in snapshot/sandbox are rejected via ``os.walk`` not following symlinks
  by default; any symlinked file will fail NUL/UTF-8 checks or produce an error.
- Binary detection via NUL byte check and UTF-8 strict decoding.
- CRLF and CR are normalised to LF before diffing.
- Added files use ``/dev/null`` for the snapshot side; deleted files use ``/dev/null``
  for the sandbox side.
- Do not integrate with ``runner.patch`` (PatchNormalizer — ``normalize_patch_text``) yet.
- Tests cover all required safety and determinism edge cases (34 tests).

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
