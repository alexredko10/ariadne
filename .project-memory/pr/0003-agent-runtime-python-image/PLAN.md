# PR 0003: Agent Runtime Python Image

## Goal

Define a minimal Docker image used as runtime for controlled Docker Agents.

The image is not a platform service image.
The image does not run conductor/core/runner.
The image does not publish to a registry in this PR.

## Non-goals

- no GHCR publishing workflow
- no Docker Hub publishing
- no Artifactory
- no docker-compose
- no platform service image
- no Docker socket mount
- no host secret mount
- no repository packaging changes
- no pyproject changes
- no GitHub Actions changes unless explicitly approved later
- no image signing/attestation implementation yet

## Proposed implementation scope

Future implementation files:

```text
docker/agent-runtime-python/Dockerfile
docker/agent-runtime-python/README.md
docker/agent-runtime-python/.dockerignore
```

## Base image decision

The implementation PR must choose a conservative Python base image and document rationale.

Preferred starting point:

- `python:3.12-slim`

The plan must require rationale covering:

- security
- size
- glibc compatibility
- amd64/arm64 support
- avoiding Alpine/musl surprises for Python packages
- local development parity

## Runtime contents

The image should include only minimal tools:

- Python 3.12
- pip
- git
- bash or sh
- ca-certificates
- non-root user
- `/workspace` working directory

Avoid adding broad packages unless justified.

### Git in image rationale

If git is included in the image, the implementation PR must justify why it is needed. The default allowed rationale is read-only repository inspection or ephemeral clone operations inside isolated workspaces. The image must not include Git credentials, SSH keys, credential helpers, or default remote credentials.

## Cross-architecture strategy

The implementation PR must document:

- intended support for amd64 and arm64
- whether future builds will use Docker buildx, QEMU emulation, separate native runners, or another explicitly approved strategy
- local development parity expectations
- which architecture is manually smoke-tested in this PR
- how multi-arch validation will be handled later in the GHCR workflow PR

## Security constraints

- run as non-root by default
- no docker.sock access
- no host secret mounts
- no registry credentials
- no personal access tokens
- no long-lived credentials
- no SSH keys
- no automatic git mutation
- no apply-patch behavior
- no platform secrets baked into image
- no `.env` copied into image

## Dockerfile requirements

The implementation Dockerfile must:

- use `python:3.12-slim` unless the plan is revised
- create a non-root group and user with explicit non-zero UID/GID
  - default recommendation: UID 10001, GID 10001, username `agent`
- create `/workspace`
- `chown /workspace` to the non-root user
- set `WORKDIR /workspace`
- run as `USER agent` by default
- document username and UID/GID in README
- avoid copying the repository into the image — see explicit rule below
- include OCI labels (see Labels section)
- avoid installing project dependencies
- avoid registry auth
- avoid Docker CLI unless explicitly approved later
- avoid mounting anything; mounts are runtime concerns, not image build concerns

### No repository copy rule

The Dockerfile must not `COPY` or `ADD` the repository root, service code, project memory, agent configs, prompts, artifacts, or any application source into the image. The image is a generic runtime base, not a baked project image.

Review checklist: review Dockerfile for any `COPY` or `ADD` instructions. Only minimal files required for image metadata are allowed, and copying the repository root is forbidden.

## Labels and provenance placeholders

Dockerfile must include these OCI labels:

```text
org.opencontainers.image.title
org.opencontainers.image.description
org.opencontainers.image.source
org.opencontainers.image.version
org.opencontainers.image.revision
org.opencontainers.image.licenses
```

Labels may contain placeholders in this PR. Concrete revision/tag values are deferred to the future build workflow PR.

## .dockerignore requirements

Must exclude:

- `.git`
- `.venv`
- `node_modules`
- `.pytest_cache`
- `__pycache__`
- `.DS_Store`
- `.env`
- `.env.*`
- `artifacts`
- `*.pem`
- `*.key`
- `.aws/`
- `.gcloud/`
- `.secrets/`
- `credentials`
- `id_rsa`
- `id_ed25519`
- `.idea/`
- `.vscode/`

`.dockerignore` must be reviewed as part of the PR because it is a secret-protection boundary.

## README requirements

README must explain:

- purpose of image
- what it includes
- what it intentionally excludes
- local build command
- local smoke test command
- security notes
- non-root user (username `agent`, UID 10001, GID 10001)
- no docker.sock
- no secrets

## Validation

Mandatory validation for this PR:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Local/manual Docker validation:

The following commands may be run manually by a human developer after reviewing the Dockerfile. They must not be added to CI in this PR. They must not be run automatically by agents. Any automated Docker build or Docker run requires a separate PR and explicit human approval.

```bash
docker build -t agent-runtime-python:local docker/agent-runtime-python
docker run --rm agent-runtime-python:local python --version
docker run --rm agent-runtime-python:local git --version
docker run --rm agent-runtime-python:local sh -lc "id && pwd"
```

This PR must not add GitHub Actions workflows, Docker build automation, registry publishing, or automated Docker execution.

## CI / automation prohibition

No GitHub Actions workflow may be added or modified in this PR. Any future build workflow must follow ADR 0002:

- no publishing from pull requests
- no production credentials in pull request builds
- no personal access tokens
- no long-lived developer credentials
- publishing only from approved main/tag workflows

## Human approval triggers

Require human approval before:

- any automated Docker build or Docker run
- adding GitHub Actions build/publish workflows
- registry publishing
- using PATs or long-lived credentials
- enabling docker.sock access
- adding host mounts
- adding host secret mounts
- adding SSH keys or registry credentials
- installing broad additional OS packages
- changing base image away from documented choice
- adding project dependency installation

## Recommended future security note

Future publishing workflow PR should include image scanning and signing/provenance attestation before production release.

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
