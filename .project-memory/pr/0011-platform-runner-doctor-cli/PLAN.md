# PR 0011: Platform Runner Doctor CLI

## Goal

Add a minimal runtime command:

```bash
python -m runner doctor
```

The command should confirm that the runner module loads and basic patch-contract components are importable.

## Non-goals

- no Dockerfile changes
- no workflow changes
- no GHCR changes
- no runbook changes
- no new Docker images
- no agent YAML changes
- no service orchestration
- no task execution engine
- no network server
- no frontend
- no deployment
- no external API calls

## Future implementation scope

Future implementation may modify/create only:

```text
services/runner/src/runner/__main__.py
services/runner/src/runner/doctor.py
services/runner/tests/test_doctor_cli.py
.project-memory/pr/0011-platform-runner-doctor-cli/PLAN.md
```

Implementation note:
The test file lives under ``services/runner/tests/test_doctor_cli.py`` so it is discovered
by the repository's existing pytest configuration when running ``python -m pytest -q``.

## Machine-readable scope

```text
allowed_write_paths:
- services/runner/src/runner/__main__.py
- services/runner/src/runner/doctor.py
- services/runner/tests/test_doctor_cli.py
- .project-memory/pr/0011-platform-runner-doctor-cli/PLAN.md

forbidden_files:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/**
- docs/runbooks/**
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
  - services/runner/src/runner/__main__.py
  - services/runner/src/runner/doctor.py
  - services/runner/tests/test_doctor_cli.py
- tests/** except:
  - services/runner/tests/test_doctor_cli.py
- .project-memory/** except:
  - .project-memory/pr/0011-platform-runner-doctor-cli/PLAN.md

Any change outside allowed_write_paths is out of scope and must be reverted.
```

## Stable CLI output contract

```text
expected_output_lines:
- platform-runner doctor
- runner import: ok
- patch models: ok
- patch safety: ok

Tests must assert these exact strings are present in stdout.
Output order must be stable in the order listed above.
The command exits 0 only when all checks pass.
The command exits non-zero if any check fails.
Unknown commands must exit non-zero.
The command must not print secrets or environment dumps.
```

## PYTHONPATH and working-directory contract

```text
For local source-tree execution, validation and tests must set PYTHONPATH explicitly:

PYTHONPATH=services/runner/src python -m runner doctor

The implementation must not rely implicitly on the current working directory.
No hidden environment variables are allowed except PYTHONPATH for source-tree import resolution.
If the package is installed/importable normally, plain `python -m runner doctor` may also work, but this PR must validate the explicit PYTHONPATH form.
```

## Machine-checkable validation commands

```text
validation_commands:
- python -m pytest -q
- python -m compileall -f services packages
- PYTHONPATH=services/runner/src python -m runner doctor
```

## CLI behavior

```bash
python -m runner doctor
```

Expected behavior:

- prints a short human-readable diagnostic report
- verifies runner package import
- verifies patch models import
- verifies patch safety module import
- exits with code `0` on success
- exits non-zero on failed check
- does not require Docker
- does not require network
- does not require credentials
- does not modify files

## Suggested output

Example acceptable output:

```text
platform-runner doctor
runner import: ok
patch models: ok
patch safety: ok
```

## Tests

Require tests for:

- `python -m runner doctor` exits `0`
- output contains `platform-runner doctor`
- output contains `runner import: ok`
- output contains `patch models: ok`
- output contains `patch safety: ok`
- unknown command exits non-zero or prints usage/help

## Machine-checkable acceptance criteria

```text
cli_entrypoint: services/runner/src/runner/__main__.py
doctor_module: services/runner/src/runner/doctor.py
test_file: services/runner/tests/test_doctor_cli.py
command: python -m runner doctor
expected_exit_code: 0
docker_required: false
network_required: false
credentials_required: false
filesystem_mutation: forbidden
workflow_changes: forbidden
dockerfile_changes: forbidden
```

## Validation

Implementation PR must pass:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

The explicit `PYTHONPATH` form is the required local source-tree validation command. If the package is installed or importable through other means, plain `python -m runner doctor` may also work, but the explicit form must pass first.

## Stop / merge gates

Do not merge if:

- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `repo.canonical-write.single-gate` is violated
- `agents.no-git-mutation` is violated
- `agents.no-secrets` is violated
- any Dockerfile, workflow, GHCR, runbook, package, or agent YAML file is modified
- the doctor command requires network, credentials, Docker, or filesystem mutation
- tests rely implicitly on current working directory instead of explicit PYTHONPATH for source-tree execution

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
