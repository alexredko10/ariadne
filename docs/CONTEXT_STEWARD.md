# Context Steward

## Role

Context Steward is the Ariadne role responsible for maintaining context memory
and evidence artifacts across the planning, implementation, review, QA, and
post-merge workflow.

Context Steward does NOT write application code.
Context Steward does NOT implement runtime behavior.
Context Steward does NOT perform cache backend operations.
Context Steward does NOT perform repository scanning.

Context Steward owns context integrity.

## What Context Steward is NOT

- Not a coder agent — does not write application code.
- Not a runtime service — does not run as a background service.
- Not a cache backend — does not perform cache lookups or stores.
- Not a repository scanner — does not scan the repository.
- Not a context compiler — does not compile context packs.

## Lifecycle hooks

Context Steward acts at these lifecycle points:

| Hook | Action |
|---|---|
| `before_plan` | Prepare workspace memory and context for planner |
| `after_plan_review` | Record plan decision in workspace memory |
| `after_implementation` | Record implementation summary in workspace memory |
| `after_precommit_review` | Record precommit review evidence |
| `after_qa` | Record QA evidence |
| `after_merge` | Archive workspace memory, prepare for next PR |

## Memory layers

### Layer 1: Global Project Memory

The global memory layer is persisted as project-memory contracts and schemas:

- `.project-memory/memory_index.yml` — registry of all memory labels
- `.project-memory/project_contract.yml` — contract IDs and severities
- `.project-memory/context-bundles/contracts.yml` — context bundles for agents
- `.project-memory/anchors.yml` — anchor references

### Layer 2: PR Workspace Memory (this PR)

PR/feature workspace memory is defined in `schemas/feature-workspace-memory.schema.yml`.

Operational path pattern: `.project-memory/pr/<pr-id>/workspace.yml`

### Layer 3: Future — context-pack inputs

Context pack input schema is deferred. Future PR may define
`.project-memory/pr/<pr-id>/context-pack-inputs.yml`.

## Workspace artifact path patterns

| Artifact | Path |
|---|---|
| Workspace memory | `.project-memory/pr/<pr-id>/workspace.yml` |
| QA evidence | `.project-memory/pr/<pr-id>/qa-evidence.yml` |
| Context pack inputs (future) | `.project-memory/pr/<pr-id>/context-pack-inputs.yml` |
| Plan | `.project-memory/pr/<pr-id>/PLAN.md` |
| Reviews | `.project-memory/pr/<pr-id>/reviews/` |

## QA evidence handling

QA evidence is defined in `schemas/qa-evidence-record.schema.yml`.

Operational path pattern: `.project-memory/pr/<pr-id>/qa-evidence.yml`

Policy:
- Every expected validation command must appear in either `commands_run` or `commands_not_run`.
- `commands_not_run` entries must include a reason and `mark: "not_run"`.
- Silent validation claims are impossible.

## Context pack input relationship

Context Steward prepares inputs for Context Compiler but does **not** compile
context packs in this PR.  Context Steward may record:

- task goal (from planner)
- source contracts used
- relevant anchors
- allowed/forbidden paths (from domain adapter)
- cache key refs (from PR 0052)
- prior PR refs
- QA evidence refs
- known risks
- manual checks required
- context freshness status

Context Pack Input schema is deferred to a future PR.
Context Steward must not dump raw repository contents.

## Cache contract relationship (PR 0052)

Context Steward references cache keys and entries from PR 0052 cache contracts:

- `cache_key_refs` in workspace memory references cache keys.
- `evidence_refs` in QA evidence references cache entries.
- Invalidation inputs are recorded without implementing cache backend.
- Namespace and artifact_kind taxonomy from PR 0052 is used.
- Context Steward does **not** perform cache lookups, stores, or backend operations.

## Invalidation responsibilities

Context Steward may record invalidation decisions as machine-readable records:

- `changed_paths`
- `affected_context_packs`
- `affected_workspace_memories`
- `affected_cache_key_refs`
- `stale_context_markers`
- `manual_refresh_required`

Context Steward does **not**:
- Compute repository graph
- Scan the repository
- Implement cache invalidation backend
- Automatically refresh cache entries

## Safety / privacy rules

- No secrets, credentials, or tokens.
- No raw private file dumps.
- No raw repository dumps.
- No absolute local paths in portable artifacts.
- No machine-specific paths.
- No silent validation claims.
- No invented command results.
- No broad memory writes — writes scoped to exact allowed paths.
- No `.ariadne/**` writes in this PR.
- No old project names/examples.

## Relationship to future PRs

| Future PR | Scope |
|---|---|
| Future PR | Context Steward prompt templates (agent-config-like artifact) |
| Future PR | Context pack input generation from workspace memory |
| Future PR | Context Compiler integration |
| Future PR | Repository-understanding cache integration |
| Future PR | Post-merge memory archival |
