# PR 0002: Container Build Strategy

## Goal

Define how the platform will be containerized later without implementing container builds in this PR.

## Non-goals

- no Dockerfile in this PR
- no GitHub Actions image build in this PR
- no registry publishing in this PR
- no packaging changes
- no pyproject changes
- no Docker socket usage
- no secrets
- no deployment

## Proposed strategy

- Use GitHub Container Registry (ghcr.io) as default first registry.
- Docker Hub may be added later for public distribution.
- Artifactory may be added later for enterprise/private deployments.
- Do not build one monolithic all-in-one image.
- Prefer separate images:

  - `agent-runtime-python` first
  - `platform-runner` later
  - `platform-core` later
  - `platform-conductor` later
  - `platform-task-intake` later
  - `platform-model-gateway` later
  - `platform-web` later

- Keep tests CI separate from image build CI.
- Publish images only from `main` / tags, not from every PR, unless explicitly approved later.

## Future PR sequence

```text
0003-agent-runtime-python-image
0004-ghcr-build-workflow
0005-platform-runner-image
0006-local-dev-compose
```

PR `0003-agent-runtime-python-image` must document:
- chosen base image rationale
- amd64 vs arm64 build considerations
- local development parity
- non-root user expectation
- minimal package surface
- no docker.sock mount
- no host secret mounts

## Safety constraints

- no docker.sock mount by default
- no host secret forwarding
- no canonical repo mutation inside agent containers
- no automatic apply-patch from containers
- image publishing requires explicit workflow and permissions
- registry credentials must use GitHub-provided tokens or configured secrets only
- no personal access tokens (PATs), long-lived developer credentials, or committed registry credentials may be used in workflows
- future publishing workflows must use GitHub Actions-provided tokens, OIDC flows, repository/environment secrets managed by repository administrators, or another explicitly approved short-lived credential mechanism
- if image builds are later enabled for pull request validation, PR builds must be non-publishing and non-credentialed: no registry push, no production credentials, no release tags
- image signing and/or provenance attestation is required before production image release; concrete tooling is deferred to the publishing workflow PR

## Validation

This docs-only PR has no mandatory runtime validation beyond repository CI. Maintainers may run:

```bash
python -m pytest -q
python -m compileall -f services packages
```

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
