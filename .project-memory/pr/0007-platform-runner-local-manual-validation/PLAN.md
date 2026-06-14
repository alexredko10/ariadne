# PR 0007: Platform Runner Local Manual Validation Runbook

## Goal

Document a safe, human-run local validation procedure for the `platform-runner` Docker image.

## Non-goals

- no CI Docker execution
- no GitHub Actions changes
- no GHCR workflow changes
- no registry publishing
- no Docker Hub
- no Artifactory
- no multi-arch publishing
- no docker-compose
- no Dockerfile changes
- no service code changes
- no packaging changes
- no docker.sock mount
- no host mounts
- no host secret mounts
- no credentials
- no PATs
- no privileged mode
- no real service entrypoint changes
- no exposed ports
- no image signing/attestation implementation

## Future implementation scope

Future implementation file:

```text
docs/runbooks/platform-runner-local-validation.md
```

Allowed future implementation files:

```text
.project-memory/pr/0007-platform-runner-local-manual-validation/PLAN.md
docs/runbooks/platform-runner-local-validation.md
```

## Runbook requirements

The runbook must document:

- prerequisites
- safe local environment checklist
- exact manual commands
- expected outputs
- failure handling
- incident handling
- sanitized evidence for PR comments
- reviewer checklist
- confirmation that no secrets, host mounts, docker.sock, privileged mode, or registry credentials are used

## Manual commands

The runbook should include these commands as manual-only:

```bash
docker build -t platform-runner:local docker/platform-runner
docker run --rm platform-runner:local python -c "import runner; print('runner import ok')"
docker run --rm platform-runner:local sh -lc "id && pwd && test \"$(id -u)\" != \"0\" && test \"$PWD\" = \"/app\""
```

Optional manual inspection command:

```bash
docker run --rm platform-runner:local sh -lc "python - <<'PY'
import runner
print(runner.__file__)
PY"
```

The runbook must clearly state:

- these commands are not CI
- these commands are not run by agents
- these commands are run only by a human maintainer in an approved local environment
- these commands must not mount host directories
- these commands must not mount docker.sock
- these commands must not pass secrets
- these commands must not use privileged mode
- these commands must not login to any registry
- these commands must not push images

## Expected checks

Runbook must verify:

- image builds
- `import runner` succeeds
- `runner.__file__` points under `/app/runner` if the optional inspection command is used
- container runs as non-root
- UID is not `0`
- working directory is `/app`
- no host mounts are required
- no registry credentials are required
- no network service is started
- no ports are exposed or required

## Sanitized evidence for PR comments

**Allowed evidence:**

- pass/fail summary
- local architecture, e.g. `linux/amd64` or `linux/arm64`
- `import runner` success
- sanitized `runner.__file__` path, e.g. `/app/runner/__init__.py`
- UID/GID result showing non-root
- working directory `/app`
- confirmation no host mounts, docker.sock, secrets, registry login, privileged mode, or image push were used

**Forbidden evidence:**

- full environment dumps
- tokens
- secrets
- `.env` values
- SSH key paths or contents
- cloud credential paths or contents
- full logs containing host paths
- registry credentials
- Docker config contents

## Failure handling

Runbook must say:

- if build/import fails, do not change workflow automatically
- do not run with `--privileged`
- do not mount docker.sock
- do not mount host directories
- do not mount host secrets
- do not pass PATs or registry credentials
- do not publish a broken image
- do not modify Dockerfile in this docs PR
- open a follow-up PR for fixes

## Accident / incident handling

If a maintainer accidentally used a secret, host secret mount, registry credential, or improper privileged setup:

- stop validation
- do not paste logs
- revoke exposed credentials if any
- clean up local artifacts if needed
- report the incident according to repository/project process
- open a follow-up issue/PR only with sanitized details

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
- publishing platform-runner image
- adding multi-arch publishing
- adding docker.sock access
- adding host mounts
- adding credentials or secrets
- adding PATs
- changing Dockerfile
- changing service code
- changing package/install strategy
- exposing ports
- changing entrypoint

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
