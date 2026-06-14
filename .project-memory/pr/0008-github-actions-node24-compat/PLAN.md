# PR 0008: GitHub Actions Node 24 Compatibility

## Goal

Update the existing `agent-runtime-python` GHCR workflow to use Node.js 24-compatible action versions.

This PR is maintenance-only and must not change image behavior, registry behavior, tag policy, permissions, or publishing rules.

## Context

The current workflow successfully builds and pushes:

```text
ghcr.io/<org>/ariadne/agent-runtime-python:sha-<shortsha>
```

But GitHub Actions emitted a Node.js 20 deprecation warning for the action versions currently used.

## Non-goals

- no new workflow
- no platform-runner workflow
- no Dockerfile changes
- no image tag policy changes
- no registry target changes
- no permission expansion
- no Docker Hub
- no Artifactory
- no PATs
- no new secrets
- no docker.sock
- no host mounts
- no multi-arch
- no `latest` tag
- no publishing behavior change
- no service code changes
- no changes to any other workflow file

## Future implementation scope

Future implementation may modify only:

```text
.github/workflows/agent-runtime-python-image.yml
.project-memory/pr/0008-github-actions-node24-compat/PLAN.md
```

## Required action updates

Implementation PR must update:

```text
actions/checkout@v4              -> actions/checkout@v5
docker/setup-buildx-action@v3    -> docker/setup-buildx-action@v4
docker/login-action@v3           -> docker/login-action@v4
docker/metadata-action@v5        -> docker/metadata-action@v6
docker/build-push-action@v6      -> docker/build-push-action@v7
```

## Invariants that must not change

The workflow must keep:

- workflow-level `permissions: contents: read`
- `packages: write` only in publish job
- PR job has no secrets
- PR job has no registry login
- PR job uses `push: false`
- publish job uses `environment: ghcr-publish`
- publish job logs in only to `ghcr.io`
- publish job uses only `${{ secrets.GITHUB_TOKEN }}`
- no PATs
- no external secrets
- no Docker Hub
- no Artifactory
- no `latest`
- no floating `main` tag
- image name unchanged:
  - `ghcr.io/${{ github.repository_owner }}/ariadne/agent-runtime-python`
- single-platform `linux/amd64` unchanged
- no changes to any other file outside the workflow

## Validation

This PLAN-only PR should pass:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Future implementation PR should be validated by:

- static workflow review
- successful PR workflow run
- no Node.js 20 warning if GitHub runner/action ecosystem supports the updated versions
- no permissions or behavior drift

## Human approval triggers

Require human approval before:

- changing registry
- changing image name
- changing publish refs
- changing permissions
- adding secrets
- adding PATs
- adding Docker Hub
- adding Artifactory
- adding `latest`
- adding multi-arch
- changing Dockerfile
- adding platform-runner workflow

## Implementation compatibility notes

Updated action pins:

- `actions/checkout@v5`
- `docker/setup-buildx-action@v4`
- `docker/login-action@v4`
- `docker/metadata-action@v6`
- `docker/build-push-action@v7`

Workflow behavior, permissions, tags, image name, registry, and platform are intentionally unchanged.

PR validation must confirm:

- PR job uses `push: false`
- PR job has no registry login
- PR job has no secrets
- publish job is skipped for PRs
- no `latest` tag is produced
- no floating `main` tag is produced

Publish validation on main/tag remains gated by `ghcr-publish` environment.

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
