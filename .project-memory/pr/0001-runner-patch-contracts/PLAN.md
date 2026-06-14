# Sprint 1 PR 0001: Runner Patch Contracts

## Goal

Introduce the first safe Runner foundation:

- typed run models
- normalized patch representation
- repo-relative path validation
- forbidden path rejection
- run artifact schema

This PR also includes a CI workflow fix: GitHub Actions must not install the root monorepo as an editable Python package yet, so `pip install -e ".[dev]"` is replaced with `pip install pytest`.

CI may install test tooling directly, but must not install the repository root with `pip install -e` until packaging strategy is explicitly designed.

This PR explicitly does **not** include:

- no Docker execution yet
- no canonical repository mutation
- no automatic apply-patch
- no git commit/push/reset/checkout/stash
- no secrets forwarding

## Allowed write paths

Only these paths may be created or modified by the implementation PR:

```text
.project-memory/pr/0001-runner-patch-contracts/PLAN.md
services/runner/src/runner/models.py
services/runner/src/runner/patch.py
services/runner/tests/test_runner_models.py
services/runner/tests/test_patch_normalizer.py
services/runner/tests/test_sandbox_paths.py
.github/workflows/ci.yml
```

## Forbidden files

Do **not** change:

```text
services/*/src/** except services/runner/src/runner/models.py and services/runner/src/runner/patch.py
packages/**
.project-memory/** except .project-memory/pr/0001-runner-patch-contracts/PLAN.md
.git/**
docker-compose.yml
Dockerfile
Makefile
pyproject.toml
.env
.env.*
apps/**
docs/** except no docs changes in this PR
```

## Path validation algorithm

All repo-relative path validation in `patch.py` must apply these rules in order:

1. Strip leading/trailing whitespace. Reject if the stripped string differs from the original input (prevents hidden/spoofed paths).
2. Reject empty string.
3. Reject whitespace-only string.
4. Reject NUL byte (`\0`) and ASCII control characters (`< 0x20`).
5. Convert all backslashes to `/` (POSIX-style separators).
6. Reject Windows drive-letter absolute paths after separator conversion, using a check equivalent to `^[A-Za-z]:/`. Reject ambiguous drive-prefixed paths matching `^[A-Za-z]:($|/)`.
   
   Rejected examples:
   - `C:\etc\passwd`
   - `C:/etc/passwd`
   - `C:/project/file.py`
   - `C:relative/path`
7. Reject any path containing `..` (directory traversal).
8. Normalize with `posixpath.normpath` (collapses repeated slashes, resolves `.`).
9. Reject normalized path starting with `/`.
10. Reject normalized path equal to `.`.
11. Reject all paths under `.git/`.
12. Reject all paths under `.project-memory/` — except exactly `.project-memory/pr/0001-runner-patch-contracts/PLAN.md`. This exception must be implemented as an exact normalized-path equality check.
    
    Required test cases:
    - `.project-memory/pr/0001-runner-patch-contracts/PLAN.md` — **accepted**
    - `.project-memory/project_contract.yml` — **rejected**
    - `.project-memory/pr/other/PLAN.md` — **rejected**
    - `.project-memory/pr/0001-runner-patch-contracts/OTHER.md` — **rejected**
13. Reject secret-like file paths using these exact rules:
    - `.env` is rejected (exact basename match)
    - `.env.*` is rejected (basename starts with `.env.`), e.g. `.env.prod`, `.env.local`, `.env.production`
    - extensions `.pem` and `.key` are rejected **case-insensitively**
    - basenames `id_rsa` and `id_ed25519` are rejected (exact match)
    - basename substring checks for `secret`, `token`, and `credential` are **case-insensitive**
    - substring checks apply to the final basename **including extension**
    
    Required test cases:
    - `.env` — rejected
    - `.env.prod` — rejected
    - `.env.local` — rejected
    - `PRIVATE.KEY` — rejected (case-insensitive `.key`)
    - `cert.PEM` — rejected (case-insensitive `.pem`)
    - `mySecret.txt` — rejected (basename contains `secret`)
    - `api_TOKEN.json` — rejected (basename contains `token`)
    - `dbCredential.yml` — rejected (basename contains `credential`)

## Expected implementation files

### `services/runner/src/runner/models.py`

Must define minimal dataclasses or typed models:

- **RunSpec** — task id, command, allowed write paths, timeout.
- **CommandSpec** — command string list, environment variables (optional), working directory (optional).
- **RunResult** — run id, exit code, stdout, stderr, duration, touched paths, normalized patch.
- **RunArtifact** — run id, exit code, stdout, stderr, touched paths, normalized patch.
- **PatchFile** — repo-relative path, old content (optional), new content (optional), diff hunk (optional).
- **NormalizedPatch** — list of PatchFile entries, timestamp, source run id.

### `services/runner/src/runner/patch.py`

Must define:

- **`normalize_repo_path(path: str) -> str`** — normalizes a single repo-relative path, raises `ValueError` on invalid input.
- **`is_forbidden_patch_path(path: str) -> bool`** — returns `True` if the path matches any forbidden pattern.
- **`validate_patch_path(path: str) -> str`** — combines normalization and forbidden check; returns the normalized path or raises `ValueError`.
- **`normalize_patch_text(diff_text: str) -> NormalizedPatch`** — parses a unified-diff string and extracts touched paths into a `NormalizedPatch`.

## Tests required

### `services/runner/tests/test_runner_models.py`

- RunSpec stores task id, command, allowed write paths and timeout.
- RunArtifact contains run id, exit code, stdout, stderr, touched paths and normalized patch.

### `services/runner/tests/test_patch_normalizer.py`

- accepts normal repo-relative paths
- rejects absolute paths
- rejects `../` traversal
- rejects `.git/`
- rejects `.project-memory/`
- rejects `.env`
- rejects secret-like file names
- extracts touched paths from basic unified diff text
- Windows drive-letter absolute paths rejected (`C:\\etc\\passwd`, `C:/etc/passwd`, `C:/project/file.py`, `C:relative/path`)
- `.project-memory/` whitelist exact-match: `PLAN.md` accepted, sibling files rejected
- secret-like matching edge cases: `PRIVATE.KEY`, `cert.PEM`, `mySecret.txt`, `api_TOKEN.json`, `dbCredential.yml`
- empty string rejected
- whitespace-only string rejected
- leading/trailing whitespace rejected (input differs from stripped form)
- NUL byte rejected
- control characters rejected
- repeated slashes normalized (e.g. `src//module.py` → `src/module.py`)
- current-dir path `.` rejected
- paths that normalize to `.` rejected

### `services/runner/tests/test_sandbox_paths.py`

- documents that sandbox paths must be isolated from canonical repo
- asserts path validator rejects host-sensitive paths
- no Docker socket path is allowed:
  - `/var/run/docker.sock`

## Validation commands

**Primary required gate:**

```bash
python -m pytest -q services/runner/tests
python -m compileall services/runner
```

**Secondary full-repo confidence gate:**

```bash
python -m pytest -q
python -m compileall services packages
```

Note: `compileall` over `packages/` is read-only and must not require modifying or building packages.

## Dependency policy

This PR must introduce **no new runtime or test dependencies**.
If a new dependency appears necessary, stop and request human approval.

## Stop conditions

Stop and ask for human review if:

- implementation requires modifying files outside allowed_write_paths
- tests require Docker
- code needs to read real environment secrets
- code needs to run git mutation commands
- patch handling touches `.git`, `.project-memory`, `.env`, key files, or credential-like files
- implementation requires changing pyproject.toml, Makefile, CI, or root config

## Human approval triggers

Require human approval for:

- Docker execution
- mounting host paths
- mounting docker.sock
- applying patches to canonical repo
- changing project memory contracts
- changing CI or package config
- adding dependencies

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
