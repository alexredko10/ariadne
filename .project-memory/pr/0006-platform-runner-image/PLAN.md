# PR 0006: Platform Runner Service Image

## Goal

Plan a Docker image for the platform runner service.

The image is a platform service image, not an agent runtime image.

It must package only the runner service and required internal Python code needed to import/run it.

## Non-goals

- no GHCR publishing workflow
- no Docker Hub
- no Artifactory
- no docker-compose
- no multi-service image
- no conductor/core/task-intake/frontend images
- no agent runtime changes
- no docker.sock mount
- no host secret mount
- no privileged mode
- no registry credentials
- no PATs
- no runtime deployment
- no Kubernetes
- no image signing/attestation implementation
- no service behavior changes unless explicitly approved
- no changes to existing GHCR workflow unless separate plan-review approves it

## Future implementation scope

Future implementation files should be limited to:

```text
docker/platform-runner/Dockerfile
docker/platform-runner/README.md
docker/platform-runner/.dockerignore
```

Optional only if strictly needed and separately justified:

```text
services/runner/pyproject.toml
```

But prefer no packaging changes in the first implementation unless the existing service cannot be installed/imported cleanly.

## Image relationship

- `agent-runtime-python` is for controlled agents
- `platform-runner` is for the platform runner service
- the runner image must not contain agent configs
- the runner image must not execute Docker Agents directly
- the runner image must not mount docker.sock
- the runner image must not include credentials
- the runner image must not mutate canonical repository state by itself

## Base image decision

Preferred base:

```text
python:3.12-slim
```

Rationale:

- consistency with agent-runtime-python
- glibc compatibility
- avoids Alpine/musl surprises
- smaller than full Debian image
- acceptable for amd64 first
- arm64/multi-arch deferred

## Runtime user

- non-root user
- username `runner`
- UID/GID `10002`
- working directory `/app`
- writable runtime directory `/var/lib/platform-runner` or `/tmp/platform-runner`
- no root default execution

## Copy/install strategy

Implementation PR must propose a minimal copy strategy.

**Allowed:**

- copy only `services/runner`
- copy only required internal package paths if imports need them
- copy no `.project-memory`
- copy no `.github`
- copy no agents
- copy no prompts
- copy no docs
- copy no artifacts
- copy no `.env`
- copy no secrets

The Dockerfile must not `COPY` repository root blindly.

If package installation is needed, implementation must explain whether it uses:

- direct `PYTHONPATH`
- editable install of service-local package
- wheel build
- another minimal strategy

Do not use root monorepo editable install.

## Entrypoint / command

Because runner service may not yet expose a production server, PLAN must require one of:

**Option A:**

- image validates importability only
- command is safe placeholder such as `python -c "import runner; print('runner image ready')"`

**Option B:**

- if a real runner service entrypoint exists, document it and use it

Do not invent a fake network service.

Do not expose ports unless service already requires one.

## Security constraints

- no docker.sock
- no privileged mode
- no host mounts
- no host secrets
- no registry credentials
- no PATs
- no SSH keys
- no Git credentials
- no package deletion/admin operations
- no automatic apply-patch to canonical repository
- no broad package installation
- no curl-pipe-shell
- no secret files copied into image
- `.dockerignore` must block common secrets and repo-private areas

## .dockerignore requirements

Future `.dockerignore` must exclude:

```text
.git
.github/
.project-memory/
agents/
prompts/
docs/
artifacts/
.env
.env.*
*.pem
*.key
.aws/
.gcloud/
.secrets/
credentials
id_rsa
id_ed25519
.venv
node_modules
.pytest_cache
__pycache__
.DS_Store
.idea/
.vscode/
```

## README requirements

README must explain:

- purpose of runner service image
- difference from agent-runtime-python
- what is copied into image
- what is intentionally excluded
- user/UID/GID
- working directory
- command/entrypoint status
- local/manual build command
- local/manual import smoke command
- no docker.sock
- no host secrets
- no registry credentials
- no CI/publishing in this PR

## Validation

This PLAN-only PR should pass:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Future implementation PR should include non-Docker validation:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Docker build/run commands must be local/manual only unless separately approved:

```bash
docker build -t platform-runner:local docker/platform-runner
docker run --rm platform-runner:local python -c "import runner; print('runner import ok')"
```

These Docker commands are manual-only:

- not CI
- not run by agents automatically
- no host mounts
- no secrets
- no registry login

## Human approval triggers

Require human approval before:

- adding CI Docker build
- adding GHCR workflow for platform-runner
- publishing platform-runner image
- adding docker-compose
- adding docker.sock access
- adding host mounts
- adding secrets or credentials
- adding PATs
- changing base image
- adding broad OS packages
- changing runner service behavior
- exposing network ports
- adding real service entrypoint if not already present
- copying additional repository areas into image

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
