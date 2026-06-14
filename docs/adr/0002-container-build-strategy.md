# ADR 0002: Container Build Strategy

Date: 2026-06-14
Status: Proposed

## Context

The platform is currently a monorepo skeleton with multiple services, shared packages, and controlled Docker Agents. The repository is not yet a single installable Python package. Containerization is needed to support controlled execution of agent runtimes and platform services, but must be introduced gradually to preserve safety boundaries.

## Decision

The platform will be containerized gradually. The repository is not treated as one installable Python package yet. Container images will be built separately for each component rather than as a single monolithic image.

The first image to build will be `agent-runtime-python`, providing the base runtime for controlled Docker Agents. Platform services (`runner`, `core`, `conductor`, `task-intake`, `model-gateway`, `web`) will receive their own images in later PRs once each service has a stable API surface.

## Image strategy

- **Separate images per component.** No monolithic all-in-one image. Each platform service gets its own image.
- **First image: `agent-runtime-python`.** A minimal Python base image with the necessary standard-library dependencies for agent execution. No platform code is baked in.
- **Platform images follow later** in dependency order: `runner` (requires sandbox and patch logic), then `core`, `conductor`, `task-intake`, `model-gateway`, `web`.
- **Images are thin.** Each image contains only the runtime and its service code, not the full monorepo.

## Registry strategy

- **Default: GitHub Container Registry (ghcr.io).** Colocated with the GitHub repository, supports fine-grained permissions via GitHub-provided tokens. No additional credential management needed in early stages.
- **Docker Hub** may be added later for public distribution of agent runtime images.
- **Artifactory** may be added later for enterprise or air-gapped private deployments.
- Registry credentials must use GitHub-provided tokens or officially configured secrets only. No hardcoded credentials or personal access tokens.
- No personal access tokens (PATs), long-lived developer credentials, or committed registry credentials may be used in workflows. Future publishing workflows must use GitHub Actions-provided tokens, OIDC flows, repository/environment secrets managed by repository administrators, or another explicitly approved short-lived credential mechanism.

## CI/CD strategy

- **Test CI and image build CI are kept separate.** Tests run on every push and pull request without building images. Image builds run only on `main` branch pushes and version tags, or when explicitly triggered.
- **No automatic publishing from pull requests.** Images are published only from `main` / tags, unless explicitly approved later via a dedicated workflow trigger. If image builds are later enabled for pull request validation, PR builds must be non-publishing and non-credentialed: no registry push, no production credentials, no release tags.
- Publishing step requires explicit workflow permissions and a designated environment with registry write access.

## Security constraints

- **No docker.sock mount** by default. Agent containers must not control the host Docker daemon.
- **No host secret forwarding.** Agent containers receive only scoped context, not environment secrets or filesystem mounts from the host.
- **No canonical repository mutation** inside agent containers. The apply-patch step is external.
- **No automatic apply-patch** from containers. Patch application requires human or conductor approval.
- Image publishing workflows must not use unauthenticated or anonymous push.
- Container entrypoints must not run with elevated privileges unless explicitly required and approved.

## Deferred decisions

- Which base Python image (slim, alpine, distroless) — deferred to the `agent-runtime-python` image PR.
- Multi-stage build patterns — deferred to the first image build PR.
- Image signing and/or provenance attestation is required before production image release. The concrete tooling is deferred to the publishing workflow PR.
- Container orchestration (Compose, Kubernetes, Nomad) — deferred.
- Health checks, readiness probes, and startup ordering — deferred to per-service image PRs.
- Version tagging strategy (semver, commit SHA, date) — deferred to the publishing workflow PR.

## Consequences

Positive:

- Clear separation of concerns: test CI and image CI are independent.
- No premature packaging decisions. The monorepo does not need `pyproject.toml` changes or a setup script yet.
- Incremental approach allows each service image to be reviewed and validated independently.
- Safety boundaries from the architecture decision record (see `project_contract.yml`) are preserved: no docker.sock, no secrets forwarding, no in-container repo mutation.

Negative:

- Multiple Dockerfiles to maintain over time (one per service + agent runtime).
- No single `docker compose up` experience until PR 0006.
- CI complexity grows with each new image build workflow, but that is intentional and auditable.

## Future PRs

- `0003-agent-runtime-python-image` — First Dockerfile for the controlled agent runtime. Must document: chosen base image rationale, amd64 vs arm64 build considerations, local development parity, non-root user expectation, minimal package surface, no docker.sock mount, no host secret mounts.
- `0004-ghcr-build-workflow` — GitHub Actions workflow to build and publish images to GHCR
- `0005-platform-runner-image` — Dockerfile and image for the runner service
- `0006-local-dev-compose` — `docker-compose.yml` for full local development stack
