# PR 0005: Local Manual Image Validation Runbook

## Goal

Document a safe, human-run local validation procedure for the `agent-runtime-python` image.

## Non-goals

- no CI Docker execution
- no GitHub Actions changes
- no registry publishing
- no GHCR changes
- no Docker Hub
- no Artifactory
- no multi-arch publishing
- no docker-compose
- no platform service images
- no docker.sock mount
- no host secret mounts
- no credentials
- no PATs
- no image signing/attestation implementation
- no Dockerfile changes unless separately approved

## Future implementation scope

Future implementation file:

```text
docs/runbooks/agent-runtime-python-local-validation.md
```

Allowed future implementation files:

```text
.project-memory/pr/0005-local-manual-image-validation/PLAN.md
docs/runbooks/agent-runtime-python-local-validation.md
```

## Runbook requirements

The runbook must document:

- prerequisites
- safety warnings
- exact manual commands
- expected outputs
- failure handling
- what must not be done
- what evidence a maintainer may record in a PR comment
- confirmation that no secrets, host mounts, docker.sock, or registry credentials are used

## Manual commands

The runbook should include these commands as manual-only:

```bash
docker build -t agent-runtime-python:local docker/agent-runtime-python
docker run --rm agent-runtime-python:local python --version
docker run --rm agent-runtime-python:local pip --version
docker run --rm agent-runtime-python:local git --version
docker run --rm agent-runtime-python:local sh -lc "id && pwd && test \"$(id -u)\" != \"0\""
```

The runbook must clearly state:

- these commands are not CI
- these commands are not run by agents
- these commands are run only by a human maintainer in an approved local environment
- these commands must not mount host directories
- these commands must not pass secrets
- these commands must not login to any registry

## Expected checks

Runbook must verify:

- image builds
- Python is available
- pip is available
- git is available
- container runs as non-root
- UID is not 0
- working directory is `/workspace`
- no host mounts are required
- no registry credentials are required

## Failure handling

Runbook must say:

- if build fails, do not change workflow automatically
- open a follow-up PR
- do not add privileged mode
- do not mount docker.sock
- do not add secrets
- do not add PATs
- do not publish broken image

## Validation for this docs-only PR

Mandatory validation:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Docker commands are not mandatory validation for this PR and must remain manual-only.

## Human approval triggers

Require human approval before:

- adding Docker execution to CI
- changing GHCR workflow
- publishing images
- adding multi-arch publishing
- adding docker.sock access
- adding host mounts
- adding credentials or secrets
- adding PATs
- changing Dockerfile
- changing base image

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
