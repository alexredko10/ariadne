# PR 0004: GHCR Agent Runtime Python Build Workflow

## Goal

Define a GitHub Actions workflow that will later:

- build `docker/agent-runtime-python`
- run non-publishing validation on PRs
- publish to GitHub Container Registry only from approved refs
- avoid Docker Hub, Artifactory, PATs, long-lived credentials, and production credentials in PR builds

## Non-goals

- no Docker Hub
- no Artifactory
- no docker-compose
- no platform service images
- no runner/core/conductor/task-intake images
- no docker.sock mount
- no host secret mount
- no PATs
- no long-lived credentials
- no signing/attestation implementation in this PR unless plan is revised
- no deployment
- no changes to Dockerfile unless explicitly reviewed

## Future implementation scope

Future workflow file:

```text
.github/workflows/agent-runtime-python-image.yml
```

Future allowed files for implementation PR:

```text
.github/workflows/agent-runtime-python-image.yml
.project-memory/pr/0004-ghcr-agent-runtime-python-workflow/PLAN.md
```

Any deviation requires project lead approval.

## Workflow behavior

### PR mode

- trigger on `pull_request`
- build image locally for validation only
- `push: false`
- no registry login
- no registry credentials
- no publishing
- no production environment
- no release tags
- `pull_request` jobs must not reference secrets
- `pull_request` jobs must not call `docker/login-action`
- all login/push steps must be conditionally disabled unless the event is a trusted push to main/tag
- `pull_request` jobs from forks must not use registry credentials or environment secrets

### Main/tag mode

- trigger on push to `main` and semver-like tags
- build image
- login to GHCR using `GITHUB_TOKEN`
- publish to GHCR only after allowed branch/tag conditions
- use `permissions: contents: read, packages: write` (only in publish job)
- no PAT
- no long-lived credentials
- publish job must run only for:
  - push to `main`
  - push of semver-like tags
- publish job must not run for `pull_request`

## Explicit permissions model

The implementation workflow must use minimal permissions:

- workflow-level (default) permissions should be `contents: read` only
- PR validation job must have **no** `packages: write` permission
- publish job may request `packages: write` only for GHCR publishing
- no `contents: write`
- no admin/delete package permissions
- no repository write permissions

The implementation PR must document why `packages: write` is needed **only** in the publish job.

## Registry naming

Default image name:

```text
ghcr.io/${{ github.repository_owner }}/ariadne/agent-runtime-python
```

If GHCR rejects nested package path or repository policy prefers simpler naming, fallback:

```text
ghcr.io/${{ github.repository_owner }}/agent-runtime-python
```

Implementation PR must document the final chosen name.

## Tagging policy

### PR builds

- no tags pushed
- no `latest`
- no registry push

### Main builds

- publish immutable SHA tag only:
  - `sha-<shortsha>`
- optional floating `main` tag requires explicit approval in the implementation PR
- no `latest` on main

### Semver tag builds

- publish exact semver tag:
  - `vX.Y.Z`
- optionally publish `vX.Y`
- `latest` is allowed only for stable semver release tags and only if explicitly approved

Mutable tags must be treated as higher risk.

## GitHub Environment / publish gating

Publishing job must use `environment: ghcr-publish`:

- publishing must not run without environment gate where available
- environment should have required reviewers when available
- environment should restrict publishing to main/tags
- publishing permissions must be minimal
- if GitHub environment protection is unavailable on the repository plan, maintainers must rely on branch protection and manual PR approval before merge

## GITHUB_TOKEN capability and fallback

- implementation PR must confirm that `GITHUB_TOKEN` can publish to GHCR with `packages: write`
- if repository/org settings block this, workflow must **not** fall back to a PAT
- fallback may only be an environment-scoped repository secret approved by maintainers
- fallback requires explicit human approval and must not be used in PR builds

## Security constraints

- no PAT
- no committed credentials
- no docker.sock mount
- no privileged containers
- no host secret mounts
- no production credentials in PR builds
- use `GITHUB_TOKEN` only in main/tag mode, and only in publish job
- use minimal workflow permissions
- do not expose secrets to `pull_request` jobs
- do not publish from `pull_request`
- do not publish from forks
- no package deletion/admin operations

## Build tooling

Implementation must use these exact action versions:

```text
actions/checkout@v4
docker/setup-buildx-action@v3
docker/login-action@v3
docker/metadata-action@v5
docker/build-push-action@v6
```

Changing these versions requires human review.

buildx may be used for local build mechanics. Multi-arch publishing is not enabled by default in this workflow unless explicitly approved. If multi-arch publishing is added, it must be gated by the `ghcr-publish` environment and documented. Default implementation should build one platform unless this PLAN is revised.

## Reviewer checklist

Reviewer must verify all of the following before approving the implementation PR:

- no PATs
- no long-lived credentials
- no Docker Hub
- no Artifactory
- no docker.sock
- no privileged containers
- no host mounts
- no secrets in `pull_request` jobs
- PR build has `push: false`
- publish job has `environment: ghcr-publish`
- minimal permissions (no `contents: write`, no admin/delete)
- no `latest` from main
- no package delete/admin operations
- only expected workflow file changed
- `docker/login-action` is not called in PR mode
- workflow-level default permissions are `read` only
- publish job uses `packages: write` only, not broader scope
- `GITHUB_TOKEN` confirmed capable of GHCR publishing with `packages: write`

## Validation

### This PLAN-only PR

```bash
python -m pytest -q
python -m compileall -f services packages
```

### Future workflow implementation PR

- PR workflow must build with `push: false`
- no registry login in PR mode
- no secrets in PR mode
- publish behavior must be inspected by reviewer before merge
- main/tag publishing must depend on `ghcr-publish` environment
- no Docker Hub login
- no PAT references
- no `.env` or secret files

## Human approval triggers

Require human approval before:

- enabling publishing
- changing registry target
- adding Docker Hub
- adding Artifactory
- adding PATs
- adding external secrets
- adding signing/attestation
- adding multi-arch publish
- changing image name
- pushing `latest`
- using any action version outside the pinned set
- adding any fallback credential mechanism beyond `GITHUB_TOKEN`

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
