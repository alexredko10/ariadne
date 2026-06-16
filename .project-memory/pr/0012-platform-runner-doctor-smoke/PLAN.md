# PR 0012: Platform Runner Doctor Smoke

## Goal

Update the platform-runner image and its local/manual validation docs so the image uses:

```bash
python -m runner doctor
```

as the default runtime smoke command.

## Non-goals

- no GHCR workflow changes
- no GitHub Actions changes
- no new Docker images
- no registry changes
- no publishing changes
- no service orchestration
- no task execution engine
- no API server
- no frontend
- no deployment model change
- no network calls
- no credentials
- no Docker commands executed by agents

## Future implementation scope

Future implementation may modify/create only:

```text
docker/platform-runner/Dockerfile
docker/platform-runner/README.md
docs/runbooks/platform-runner-local-validation.md
.project-memory/pr/0012-platform-runner-doctor-smoke/PLAN.md
```

## Required behavior

The Dockerfile CMD should change from the old import-only smoke command to:

```Dockerfile
CMD ["python", "-m", "runner", "doctor"]
```

The image should still:

- use `python:3.12-slim`
- run as non-root `runner` user
- keep `PYTHONPATH=/app`
- copy only runner source needed for the image
- avoid git and development tools
- avoid network/runtime credentials
- avoid ENTRYPOINT
- avoid EXPOSE unless a real server exists

## Documentation updates

Update:

- `docker/platform-runner/README.md`
- `docs/runbooks/platform-runner-local-validation.md`

Docs must explain:

- the default container command now runs doctor
- expected output is:

```text
platform-runner doctor
runner import: ok
patch models: ok
patch safety: ok
```

- Docker validation commands are manual-only
- agents must not run Docker commands
- no secrets or credentials are required
- failures should be reported with sanitized output only

## Machine-readable scope

```text
allowed_write_paths:
- docker/platform-runner/Dockerfile
- docker/platform-runner/README.md
- docs/runbooks/platform-runner-local-validation.md
- .project-memory/pr/0012-platform-runner-doctor-smoke/PLAN.md
```

```text
forbidden_files:
- .github/**
- Dockerfile
- Dockerfile.*
- docker/** except:
  - docker/platform-runner/Dockerfile
  - docker/platform-runner/README.md
- services/**
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
- docs/** except:
  - docs/runbooks/platform-runner-local-validation.md
- .project-memory/** except:
  - .project-memory/pr/0012-platform-runner-doctor-smoke/PLAN.md
```

## Validation

Implementation PR must pass non-Docker validation:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Docker validation is manual-only and must not be run by agents unless separately human-approved.

## Manual Docker validation guidance

Document but do not execute:

```bash
docker build -f docker/platform-runner/Dockerfile -t platform-runner:local .
docker run --rm platform-runner:local
```

Expected container output:

```text
platform-runner doctor
runner import: ok
patch models: ok
patch safety: ok
```

## Stop / merge gates

Do not merge if:

- tests fail
- compileall fails
- source-tree doctor command fails
- Dockerfile CMD does not use `python -m runner doctor`
- Dockerfile user/root safety changes unexpectedly
- workflow/GHCR files are modified
- services/packages/agents are modified
- docs imply agents may run Docker automatically
- any repository protection invariant in `.project-memory/project_contract.yml` is violated
- `agents.no-git-mutation` is violated
- `agents.no-secrets` is violated

## Context receipt requirement

## Implementation note

The Dockerfile CMD was changed from the import-only placeholder to the doctor
CLI. The README and runbook were updated to reflect the new doctor output and
the correct repository-root build context.

- `docker/platform-runner/Dockerfile.dockerignore` was intentionally unchanged
- `.github/workflows/platform-runner-image.yml` was intentionally unchanged
- No services, packages, or agents were modified
- Docker commands documented in README/runbook remain manual-only

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
