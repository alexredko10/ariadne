# Platform Runner Local Manual Validation

## Purpose

This runbook documents **human-run local smoke validation** for the
`docker/platform-runner` image.

- It is **not** CI.
- It is **not** registry publishing.
- It is **not** `agent-runtime-python` validation.
- It must **not** modify any workflow, Dockerfile, service code, package/install
  strategy, or publishing behavior.

## Safe local environment checklist

Before running these commands, the maintainer **must** confirm:

1. Using a trusted local machine or ephemeral VM.
2. Docker is installed and available (`docker --version`).
3. Not running on shared CI runners.
4. No host directories will be mounted.
5. `docker.sock` will not be mounted into the container.
6. No secrets will be passed as environment variables.
7. No registry login is required.
8. No image push will be performed.
9. Shell environment does not intentionally expose tokens to the container.
10. No `--privileged` mode will be used.
11. No credentials, SSH keys, `.env`, cloud SDK directories, or host secret
    paths are mounted.

## Scope

### Allowed

- Local/manual `docker build` and smoke tests of the
  `docker/platform-runner` image on a trusted machine.

### Forbidden

- CI Docker execution
- GitHub Actions workflow changes
- Dockerfile changes
- Service code changes
- Packaging changes
- Registry publishing (GHCR, Docker Hub, Artifactory)
- Registry login
- Image push
- Docker socket mounts
- Host directory mounts
- Host secret mounts
- Secrets or credentials passed to containers
- Personal access tokens (PATs)
- Privileged containers
- Exposed ports
- Entrypoint changes

## Manual commands

These commands are **manual-only**. They must be run only by a human
maintainer in an approved local environment. Agents must not run them
automatically. CI must not run them in this PR.

```bash
# Build the image
docker build -t platform-runner:local docker/platform-runner

# Verify runner package is importable
docker run --rm platform-runner:local python -c "import runner; print('runner import ok')"

# Verify non-root user, working directory, and non-zero UID
docker run --rm platform-runner:local sh -lc "id && pwd && test \"$(id -u)\" != \"0\" && test \"$PWD\" = \"/app\""
```

Optional manual inspection command (verify module location):

```bash
docker run --rm platform-runner:local sh -lc "python - <<'PY'
import runner
print(runner.__file__)
PY"
```

These commands:

- do **not** require host mounts
- must **not** mount `docker.sock`
- must **not** pass secrets
- must **not** use `--privileged` mode
- must **not** login to any registry
- must **not** push images

## Expected checks

| Check | Expected result |
|-------|----------------|
| Image builds | Exit code 0 |
| `import runner` succeeds | Prints `runner import ok` |
| `runner.__file__` (optional) | Points under `/app/runner`, e.g. `/app/runner/__init__.py` |
| `id` | UID is **not** `0` (output shows `uid=10002(runner) gid=10002(runner)`) |
| `pwd` | Prints `/app` |
| Final combined check | Exits successfully (all conditions pass) |

Exact version numbers are not required and must not be treated as a
validation gate.

No network service is started. No ports are exposed or required by the
container.

## Sanitized evidence for PR comments

Maintainers may record the following in a PR comment after manual
validation.

### Allowed evidence

- Pass/fail summary
- Local architecture (e.g. `linux/amd64` or `linux/arm64`)
- `import runner` success
- Sanitized `runner.__file__` path, e.g. `/app/runner/__init__.py`
- UID/GID result showing non-root
- Working directory `/app`
- Confirmation that no host mounts, `docker.sock`, secrets, registry login,
  privileged mode, or image push were used

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
Manual local validation completed for `platform-runner`.

- Image: `platform-runner:local`
- Host architecture: `<linux/amd64 or linux/arm64>`
- Import check: `import runner` succeeded
- Runner module path: `/app/runner/__init__.py`
- Container user: non-root UID/GID observed
- Working directory: `/app`
- Safety confirmation: no host mounts, no docker.sock mount, no secrets,
  no registry login, no image push, no privileged mode
```

## Failure handling

If validation fails:

- **Do not** run with `--privileged`.
- **Do not** mount `docker.sock`.
- **Do not** mount host directories.
- **Do not** mount host secrets.
- **Do not** pass PATs or registry credentials.
- **Do not** publish a broken image.
- **Do not** modify any workflow automatically.
- **Do not** change the Dockerfile in this docs PR.
- **Do not** change service code or packaging in this docs PR.
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

- [ ] Only `docs/runbooks/platform-runner-local-validation.md` and
      `.project-memory/pr/0007-platform-runner-local-manual-validation/PLAN.md`
      changed
- [ ] No workflow changes
- [ ] No Dockerfile changes
- [ ] No service code changes
- [ ] No packaging changes
- [ ] No CI Docker execution
- [ ] Commands are explicitly documented as manual-only
- [ ] No secrets or mounts in commands
- [ ] Sanitized evidence guidance is present
- [ ] Failure handling forbids unsafe shortcuts

## Related files

- `.project-memory/pr/0007-platform-runner-local-manual-validation/PLAN.md`
- `docker/platform-runner/README.md`
- `docker/platform-runner/Dockerfile`
- `docker/platform-runner/.dockerignore`
- `docs/runbooks/agent-runtime-python-local-validation.md`
- `docs/adr/0002-container-build-strategy.md`
