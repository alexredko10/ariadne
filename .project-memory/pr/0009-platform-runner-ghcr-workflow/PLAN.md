# PR 0009: Platform Runner GHCR Build Workflow

## Goal

Define a GitHub Actions workflow that will later:

- build `docker/platform-runner`
- run non-publishing validation on PRs
- publish to GitHub Container Registry only from approved refs
- avoid Docker Hub, Artifactory, PATs, long-lived credentials, and production credentials in PR builds

## Non-goals

- no Docker Hub
- no Artifactory
- no docker-compose
- no agent-runtime workflow changes
- no Dockerfile changes
- no service code changes
- no packaging changes
- no platform-core/conductor/task-intake/frontend images
- no docker.sock mount
- no host secret mount
- no PATs
- no long-lived credentials
- no signing/attestation implementation in this PR
- no deployment
- no Kubernetes
- no multi-arch publishing by default
- no `latest` tag by default

## Future implementation scope

Future workflow file:

```text
.github/workflows/platform-runner-image.yml
```

Future allowed files for implementation PR:

```text
.github/workflows/platform-runner-image.yml
.project-memory/pr/0009-platform-runner-ghcr-workflow/PLAN.md
```

No other files.

## Workflow behavior

### PR mode

- trigger on `pull_request`
- build image locally for validation only
- `push: false`
- no registry login
- no registry credentials
- no secrets
- no publishing
- no production environment
- no release tags
- no `latest`
- no floating `main` tag

### Main/tag mode

- trigger on push to `main` and semver-like tags
- build image
- login to GHCR using `GITHUB_TOKEN`
- publish to GHCR only after allowed branch/tag conditions
- use `permissions: contents: read, packages: write` only in publish job
- no PAT
- no long-lived credentials
- no external registry secrets

## Registry naming

Default image name:

```text
ghcr.io/${{ github.repository_owner }}/ariadne/platform-runner
```

If GHCR rejects nested package path or repository policy prefers simpler naming, fallback:

```text
ghcr.io/${{ github.repository_owner }}/platform-runner
```

Implementation PR must document the final chosen name.

## Tagging policy

### PR builds

- no tags pushed
- no registry push
- no `latest`
- no floating `main`

### Main builds

- publish immutable SHA tag only:
  - `sha-<shortsha>`
- no `main` tag by default
- no `latest`

### Semver tag builds

- publish exact semver tag:
  - `vX.Y.Z`
- optionally publish:
  - `vX.Y`
- `latest` is not enabled in this PR unless explicitly approved later

## GitHub Environment / human approval

Publishing job must use named environment:

```text
ghcr-publish
```

- environment should have required reviewers when available
- environment should restrict publishing to main/tags
- publishing permissions must be minimal
- if environment protection is unavailable on the repository plan, maintainers must rely on branch protection and manual PR approval before merge

## Security constraints

- no PAT
- no committed credentials
- no docker.sock mount
- no privileged containers
- no host secret mounts
- no production credentials in PR builds
- use `GITHUB_TOKEN` only
- use minimal workflow permissions
- do not expose secrets to `pull_request` jobs
- do not publish from `pull_request`
- do not publish from forks
- no package deletion/admin operations
- no Docker Hub
- no Artifactory
- no external registry login

## Build tooling

Implementation must use Node 24-compatible action pins:

```text
actions/checkout@v5
docker/setup-buildx-action@v4
docker/login-action@v4
docker/metadata-action@v6
docker/build-push-action@v7
```

Changing these versions requires human review.

## Permissions model

- workflow-level permissions:
  - `contents: read`
- PR job permissions:
  - `contents: read`
- publish job permissions:
  - `contents: read`
  - `packages: write`
- no global `packages: write`
- no `contents: write`
- no repository write permissions
- no admin/delete package permissions

## Workflow implementation requirements

Implementation must preserve these constraints:

- workflow name: `platform-runner image`
- image name: `ghcr.io/${{ github.repository_owner }}/ariadne/platform-runner`
- context: `docker/platform-runner`
- file: `docker/platform-runner/Dockerfile`
- platform: `linux/amd64`
- no multi-arch by default
- PR job must not call `docker/login-action`
- PR job must not reference `secrets`
- publish job must call `docker/login-action@v4` only inside publish job
- publish job must use `environment: ghcr-publish`
- publish job must be skipped for `pull_request`
- publish job must only run for main or semver tag pushes
- no `pull_request_target`

## Validation

This PLAN-only PR should pass:

```bash
python -m pytest -q
python -m compileall -f services packages
```

Future workflow implementation PR should be validated by:

- static workflow review
- successful PR workflow run
- PR run confirms:
  - no registry login
  - no secrets
  - `push: false`
  - publish job skipped
- main/tag publish remains gated by `ghcr-publish`

## Human approval triggers

Require human approval before:

- enabling publishing without `ghcr-publish`
- changing registry target
- changing image name
- changing publish refs
- changing permissions
- adding secrets
- adding PATs
- adding Docker Hub
- adding Artifactory
- adding `latest`
- adding floating `main`
- adding multi-arch
- changing Dockerfile
- changing service code or packaging
- adding docker.sock
- adding host mounts

## Reviewer checklist

Implementation PR checklist must verify:

- only workflow file and PLAN changed
- no Dockerfile changes
- no service code changes
- no packaging changes
- no PATs
- no long-lived credentials
- no Docker Hub
- no Artifactory
- no docker.sock
- no privileged containers
- no host mounts
- no secrets in `pull_request` jobs
- PR build has `push: false`
- `docker/login-action` is not called in PR mode
- publish job has `environment: ghcr-publish`
- `packages: write` appears only in publish job
- no `latest`
- no floating `main`
- no package delete/admin operations
- Node 24-compatible action pins are used

## Implementation blocker list

Reviewers must block the implementation PR if any of the following are present:

* `pull_request_target`
* workflow-level `packages: write`
* `contents: write`
* any secret other than `${{ secrets.GITHUB_TOKEN }}`
* PAT usage
* external registry secrets
* `docker/login-action` in the PR job
* `push: true` in the PR job
* publish job running for `pull_request`
* missing `environment: ghcr-publish` in the publish job
* registry other than `ghcr.io`
* Docker Hub
* Artifactory
* `latest`
* floating `main` tag
* `type=raw`
* `value=main`
* multi-arch platforms
* `privileged: true`
* `/var/run/docker.sock`
* host volume mounts
* host secret mounts
* package delete/admin permissions
* Dockerfile changes
* service code changes
* packaging changes
* workflow files other than `.github/workflows/platform-runner-image.yml`

## GHCR environment ownership note

- `ghcr-publish` environment must be configured by repository maintainers or administrators
- it should require reviewers where available
- if environment protection is unavailable, branch protection and manual PR approval are required before merge
- implementation PR must not weaken or bypass environment gating

## Implementation PR security review note

The implementation PR description must include a short security review note with these exact confirmations:

* Final `IMAGE_NAME` chosen:
  * default: `ghcr.io/${{ github.repository_owner }}/ariadne/platform-runner`
  * fallback only if documented: `ghcr.io/${{ github.repository_owner }}/platform-runner`
* Workflow-level permissions remain `contents: read`.
* PR job permissions remain `contents: read`.
* PR job has no `packages: write`.
* Publish job is the only job with `packages: write`.
* PR job has `push: false`.
* PR job has no `docker/login-action`.
* PR job has no `secrets.` references.
* Publish job uses `environment: ghcr-publish`.
* Publish job logs in only to `ghcr.io`.
* Publish job uses only `${{ secrets.GITHUB_TOKEN }}`.
* No PATs or external secrets are used.
* No Docker Hub or Artifactory references are present.
* No `latest` tag is produced.
* No floating `main` tag is produced.
* No `pull_request_target` trigger is used.
* No docker.sock mount is used.
* No privileged mode is used.
* No host mounts are used.
* Platform remains `linux/amd64`.

The implementation PR must include sanitized PR-run evidence or reviewer instructions confirming:

* PR run used `push: false`.
* PR run did not attempt registry login.
* PR run did not access secrets.
* Publish job was skipped on PR.
* No Node.js 20 deprecation warning remains if the GitHub runner/action ecosystem supports the updated action versions.

## Machine-checkable acceptance criteria

The implementation PR must satisfy all of the following grep-able checks.

### Workflow identity

- `workflow_path: .github/workflows/platform-runner-image.yml`
- `workflow_name: platform-runner image`
- `image_name_default: ghcr.io/${{ github.repository_owner }}/ariadne/platform-runner`
- `image_name_final: ghcr.io/${{ github.repository_owner }}/ariadne/platform-runner` (default, no fallback)
- `context: docker/platform-runner`
- `dockerfile: docker/platform-runner/Dockerfile`
- `platforms: linux/amd64`

### Triggers

The workflow must include only these intended trigger classes:

- `trigger_pull_request: true`
- `trigger_push_main: true`
- `trigger_push_semver_tags: true`

The workflow must not include:

- `pull_request_target: forbidden`

### Permissions

Workflow-level permissions must be exactly minimal:

```yaml
permissions:
  contents: read
```

PR job permissions must include:

```yaml
permissions:
  contents: read
```

Publish job permissions must include:

```yaml
permissions:
  contents: read
  packages: write
```

Acceptance checks:

* `workflow_level_packages_write: forbidden`
* `contents_write: forbidden`
* `packages_write_only_in_publish_job: required`
* `repository_write_permissions: forbidden`
* `package_delete_or_admin_permissions: forbidden`

### PR job safeguards

The PR job must satisfy:

* `pr_job_push: false`
* `pr_job_platforms: linux/amd64`
* `pr_job_permissions: contents: read`
* `pr_job_docker_login_action: forbidden`
* `pr_job_secrets_reference: forbidden`
* `pr_job_registry_login: forbidden`
* `pr_job_registry_push: forbidden`
* `pr_job_publish: forbidden`

The PR job must not contain:

* `docker/login-action`
* `secrets.`
* `push: true`

### Publish job safeguards

The publish job must satisfy:

* `publish_job_environment: ghcr-publish`
* `publish_job_platforms: linux/amd64`
* `publish_job_registry: ghcr.io`
* `publish_job_login_action: docker/login-action@v4`
* `publish_job_token: ${{ secrets.GITHUB_TOKEN }}`
* `publish_job_other_secrets: forbidden`
* `publish_job_push: true`

The publish job must use this exact condition or a strictly equivalent condition:

```yaml
if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v'))
```

Login and publish steps must exist only in the publish job and must never run for `pull_request`.

### Action pins

The workflow must use exactly these Node 24-compatible action pins:

* `actions/checkout@v5`
* `docker/setup-buildx-action@v4`
* `docker/login-action@v4`
* `docker/metadata-action@v6`
* `docker/build-push-action@v7`

### Registry and tagging

The workflow must not include:

* `Docker Hub: forbidden`
* `docker.io: forbidden`
* `Artifactory: forbidden`
* `PAT: forbidden`
* `external_registry_secret: forbidden`
* `latest: forbidden`
* `floating_main_tag: forbidden`
* `type=raw: forbidden`
* `value=main: forbidden`
* `multi_arch: forbidden`

Required tag policy:

* `main_tag_policy: sha-<shortsha> only`
* `semver_tag_policy: vX.Y.Z and optionally vX.Y`
* `latest_tag_policy: disabled`

### Container safety

The workflow must not include:

* `privileged: true`
* `/var/run/docker.sock`
* `docker_sock_mount: forbidden`
* `host_mounts: forbidden`
* `host_secret_mounts: forbidden`

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
