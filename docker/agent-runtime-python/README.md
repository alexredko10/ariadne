# Agent Runtime Python

Minimal Python base image for controlled Docker Agents.

This image provides a safe, non-root Python runtime environment for executing
agent tool calls in isolated workspaces. It is **not** a platform service image
— it does not run the runner, conductor, core, model gateway, or task intake.

## What's included

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12 | From `python:3.12-slim` |
| pip | latest | Bundled with Python |
| git | latest | Read-only repo inspection only — see below |
| bash | latest | Default shell |
| ca-certificates | latest | TLS certificate bundle |
| `agent` user | UID/GID 10001 | Non-root runtime user |

### Why git is included

Git is included for **read-only repository inspection** and **ephemeral workspace
operations** (e.g. cloning a snapshot or inspecting file history inside an
isolated sandbox). The image does **not** include:

- Git credentials or credential helpers
- SSH keys or SSH agents
- Default remote credentials or `.gitconfig`

All git operations run as the non-root `agent` user inside `/workspace`.

## What's intentionally excluded

- Platform service code (runner, conductor, core, model gateway, task intake)
- Repository source code (the monorepo is **not** copied into the image)
- Docker CLI
- Docker socket
- Registry credentials or authentication
- Personal access tokens (PATs)
- SSH keys or agents
- Secrets of any kind (`.env`, `.pem`, `.key`, etc.)
- `.project-memory`, agent configs, prompts, or documentation

## Base image rationale

**`python:3.12-slim`** was chosen because:

- **Security**: smaller attack surface than full Debian or `python:3.12`
- **Size**: significantly smaller than the full variant, faster pulls
- **glibc compatibility**: avoids the musl compatibility issues common with
  Alpine-based Python images (many Python wheels expect glibc)
- **amd64/arm64 support**: official multi-arch manifest; good availability
  on both architectures
- **Local parity**: matches typical local development Python versions for
  consistent behavior

`python:3.12-alpine` is avoided because musl-linked Python can break
platform-specific wheels and C extensions without explicit build-time handling.

## Cross-architecture considerations

- Target future support for **amd64** and **arm64**
- Build method (buildx + QEMU, separate native runners, etc.) will be decided
  in the future GHCR build workflow PR
- This PR does **not** implement multi-arch publishing
- Local development smoke tests in this PR target the developer's native
  architecture

## Security constraints

- Runs as **non-root** user `agent` (UID 10001, GID 10001)
- `/workspace` is owned by `agent:agent`
- **No docker.sock** — agent containers cannot control the host Docker daemon
- **No host secrets** — no `.env`, credentials, PATs, or SSH keys baked in
- **No registry credentials** — authentication is a runtime concern
- **No project secrets** — nothing from `.project-memory`, `.env.*`, or
  similar files is copied into the image
- **No repository source** — the monorepo is not copied; this is a generic
  runtime base, not a baked project image

## Local build and smoke test (manual only)

These commands are **manual-only** and must not be added to CI in this PR.
Automated Docker execution requires a separate PR and explicit human approval.

```bash
# Build the image
docker build -t agent-runtime-python:local docker/agent-runtime-python

# Verify Python is available
docker run --rm agent-runtime-python:local python --version

# Verify git is available
docker run --rm agent-runtime-python:local git --version

# Verify non-root user and working directory
docker run --rm agent-runtime-python:local sh -lc "id && pwd"
```

Expected output:

```
Python 3.12.x
git version 2.x.x
uid=10001(agent) gid=10001(agent) groups=10001(agent)
/workspace
```

## Future work

- **PR 0004**: GHCR build and publish workflow
- **PR 0004+**: Image scanning and vulnerability reporting
- **PR 0004+**: Image signing and/or provenance attestation
- **PR 0004+**: Multi-architecture build workflow (amd64 + arm64)

## License

MIT — see repository root LICENSE file.
