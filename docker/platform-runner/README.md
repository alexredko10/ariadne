# Platform Runner

Minimal platform service image for the runner service.

This image packages the runner service Python code (`services/runner/src/runner`)
for use within the platform. It is **not** an agent runtime image — it does not
contain agent configs, execute agents, or manage agent containers.

## Relationship to agent-runtime-python

| Aspect | `agent-runtime-python` | `platform-runner` |
|--------|------------------------|-------------------|
| Purpose | Generic agent runtime base | Platform runner service |
| Audience | Controlled Docker Agents | Platform infrastructure |
| Python | 3.12 | 3.12 |
| User | `agent` (UID 10001) | `runner` (UID 10002) |
| Working dir | `/workspace` | `/app` |
| Git | Yes (read-only inspection) | No |
| Service code | No | Yes — runner models + patch |
| Network ports | None | None (not exposed) |

## What's included

| Component | Location |
|-----------|----------|
| Python 3.12 | From `python:3.12-slim` |
| `services/runner/src/runner` | `/app/runner` |
| `runner` user | UID 10002, GID 10002 |
| ca-certificates | TLS bundle |

### Import strategy

The runner package is copied to `/app/runner`. The environment variable
`PYTHONPATH=/app` allows `import runner` to resolve because
`/app/runner/__init__.py` exists. Copied files are owned by non-root
UID/GID `10002:10002`. No repository root is copied.

## What's intentionally excluded

- `.project-memory`, `.github`, agents, prompts, docs, artifacts
- `packages/` and `apps/` (other platform components)
- All other service directories (`core`, `conductor`, `task_intake`,
  `model_gateway`)
- Runner test files
- Git, Docker CLI, SSH keys, credentials, secrets
- `docker.sock`, `--privileged` mode, host mounts
- Registry credentials, PATs, `.env` files

## Base image rationale

**`python:3.12-slim`** was chosen:

- **Consistency** with `agent-runtime-python` — same base, same tooling
- **glibc compatibility** — avoids musl issues common with Alpine Python
- **Size** — significantly smaller than the full Debian variant
- **Security** — reduced attack surface compared to full image
- **amd64/arm64** — official multi-arch support (arm64 deferred)

## Runtime user

- Username: `runner`
- UID / GID: `10002`
- Working directory: `/app`
- Writable runtime directory: `/tmp/platform-runner`
- Default execution is **non-root**

## Command / entrypoint

The default command is an **import-only placeholder**:

```bash
python -c "import runner; print('runner image ready')"
```

This validates that the runner package is importable. No real network service
is started. No ports are exposed. A real entrypoint will be added in a future
PR once a stable service interface exists.

## Security constraints

- **No docker.sock** — this container cannot control the host Docker daemon
- **No host mounts** — no host directories required
- **No host secrets** — no `.env`, credentials, PATs, or SSH keys baked in
- **No registry credentials** — authentication is a runtime concern
- **No Git credentials or SSH agents**
- **No privileged mode**
- **No automatic apply-patch** to the canonical repository
- **No broad package installation** — only `ca-certificates` OS package added

## Local build and smoke test (manual only)

These commands are **manual-only** and must not be added to CI in this PR.
Automated Docker execution requires a separate PR and explicit human approval.

```bash
# Build the image
docker build -t platform-runner:local docker/platform-runner

# Verify runner package is importable
docker run --rm platform-runner:local python -c "import runner; print('runner import ok')"

# Verify non-root user and working directory
docker run --rm platform-runner:local sh -lc "id && pwd && test \"$(id -u)\" != \"0\""
```

Expected output:

```
runner import ok
uid=10002(runner) gid=10002(runner) groups=10002(runner)
/app
```

These commands:

- do **not** require host mounts
- do **not** require secrets
- do **not** require registry credentials
- do **not** require privileged mode
- do **not** mount `docker.sock`
- do **not** call `docker login`

## Future work

- Real runner service entrypoint when a stable service contract exists
- GHCR publishing workflow for `platform-runner` (separate PR)
- Image scanning and signing / provenance attestation
- Multi-architecture build support (amd64 + arm64)

## License

MIT — see repository root LICENSE file.
