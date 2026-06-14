# Agent Runtime Python Local Manual Validation

## Purpose

This runbook documents **human-run local smoke validation** for the
`docker/agent-runtime-python` image.

- It is **not** CI.
- It is **not** registry publishing.
- It is **not** a platform service validation.
- It must **not** modify any workflow, Dockerfile, or image publishing behavior.

## Scope

### Allowed

- Local/manual `docker build` and smoke tests of the
  `docker/agent-runtime-python` image on a trusted machine.

### Forbidden

- CI Docker execution
- GitHub Actions workflow changes
- Registry publishing (GHCR, Docker Hub, Artifactory)
- Registry login
- Docker socket mounts
- Host directory mounts
- Secrets or credentials passed to containers
- Personal access tokens (PATs)
- Privileged containers
- Changing the Dockerfile or base image

## Safe local environment checklist

Before running these commands, the maintainer **must** confirm:

1. Using a trusted local machine or ephemeral VM.
2. Docker is installed and available (`docker --version`).
3. No host directories will be mounted.
4. `docker.sock` will not be mounted into the container.
5. No secrets will be passed as environment variables.
6. No registry login is required.
7. Shell environment does not intentionally expose tokens to the container.
8. No `--privileged` mode will be used.
9. Commands are not running on shared CI runners.
10. No credentials, SSH keys, `.env`, cloud SDK directories, or host secret
    paths are mounted.

## Manual commands

These commands are **manual-only**. They must be run only by a human
maintainer in an approved local environment. Agents must not run them
automatically. CI must not run them in this PR.

```bash
# Build the image
docker build -t agent-runtime-python:local docker/agent-runtime-python

# Verify Python is available
docker run --rm agent-runtime-python:local python --version

# Verify pip is available
docker run --rm agent-runtime-python:local pip --version

# Verify git is available
docker run --rm agent-runtime-python:local git --version

# Verify non-root user, working directory, and non-zero UID
docker run --rm agent-runtime-python:local sh -lc "id && pwd && test \"$(id -u)\" != \"0\""
```

These commands:

- do **not** require host mounts.
- do **not** require secrets.
- do **not** require registry credentials.
- do **not** require privileged mode.
- do **not** mount `docker.sock`.
- do **not** call `docker login`.

## Expected checks

| Check | Expected result |
|-------|----------------|
| Image builds | Exit code 0, output: `agent-runtime-python base image built successfully` |
| `python --version` | Python version printed (e.g. `Python 3.12.x`) |
| `pip --version` | pip version printed |
| `git --version` | git version printed |
| `id` | UID is **not** `0` (output shows `uid=10001(agent) gid=10001(agent)`) |
| `pwd` | Prints `/workspace` |
| Final combined check | Exits successfully (`test "$(id -u)" != "0"` passes) |

Exact version numbers are not required and must not be treated as a
validation gate.

## Sanitized evidence for PR comments

Maintainers may record the following in a PR comment after manual
validation.

### Allowed evidence

- Pass/fail summary
- Local architecture (e.g. `linux/amd64` or `linux/arm64`)
- Sanitized Python version
- Sanitized pip version
- Sanitized git version
- UID/GID result showing non-root
- Working directory `/workspace`
- Confirmation that no secrets, host mounts, `docker.sock`, registry login,
  or privileged mode were used

### Forbidden evidence

- Full environment dumps
- Tokens, secrets, or `.env` values
- SSH key paths or contents
- Cloud credential paths or contents
- Full logs containing host paths
- Registry credentials
- Docker config contents

## Example PR comment

```markdown
Manual local image validation completed.

- Image: `agent-runtime-python:local`
- Host architecture: `<linux/amd64 or linux/arm64>`
- Python: `<sanitized version>`
- pip: `<sanitized version>`
- git: `<sanitized version>`
- Container user: non-root UID/GID observed
- Working directory: `/workspace`
- Safety confirmation: no host mounts, no docker.sock mount, no secrets,
  no registry login, no privileged mode
```

## Failure handling

If validation fails:

- **Do not** run with `--privileged`.
- **Do not** mount `docker.sock`.
- **Do not** mount host secrets.
- **Do not** pass PATs or registry credentials.
- **Do not** publish a broken image.
- **Do not** modify any workflow automatically.
- **Do not** change the Dockerfile in this docs PR.
- Open a **follow-up PR** for fixes.
- Investigate the failure in a safe local environment only.

## Accident / incident handling

If a maintainer accidentally used a secret, host secret mount, registry
credential, or improper privileged setup:

1. **Stop** validation immediately.
2. **Do not** paste logs into GitHub or other permanent records.
3. **Revoke** exposed credentials if any (rotate tokens, invalidate keys).
4. **Clean up** local artifacts if needed (`docker system prune` or manual
   removal).
5. **Report** the incident according to repository / project process with
   sanitized details only.
6. **Open** a follow-up issue or PR only with sanitized information —
   never raw secrets or host paths.

## Reviewer checklist

Before approving this PR, reviewer must confirm:

- [ ] Only `docs/runbooks/agent-runtime-python-local-validation.md` and
      `.project-memory/pr/0005-local-manual-image-validation/PLAN.md` changed
- [ ] No workflow changes
- [ ] No Dockerfile changes
- [ ] No CI Docker execution
- [ ] Commands are explicitly documented as manual-only
- [ ] No secrets or mounts in commands
- [ ] Evidence guidance is sanitized (no tokens, no host paths)
- [ ] Failure handling forbids unsafe shortcuts (`--privileged`,
      `docker.sock`, host secrets, PATs)
- [ ] Accident/incident handling section is present

## Related files

- `.project-memory/pr/0005-local-manual-image-validation/PLAN.md`
- `docker/agent-runtime-python/README.md`
- `docker/agent-runtime-python/Dockerfile`
- `.github/workflows/agent-runtime-python-image.yml`
- `docs/adr/0002-container-build-strategy.md`
