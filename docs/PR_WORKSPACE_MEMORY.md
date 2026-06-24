# PR Workspace Memory

## What PR workspace memory is

PR workspace memory is short-term contextual memory for one PR or feature.
It is maintained by Context Steward across the planning, implementation,
review, QA, and post-merge lifecycle.

Artifact paths:

- `.project-memory/pr/<pr-id>/workspace.yml` — workspace memory
- `.project-memory/pr/<pr-id>/qa-evidence.yml` — QA evidence
- `.project-memory/pr/<pr-id>/context-pack-inputs.yml` — context pack inputs

## Why it exists

PR workspace memory gives agents structured evidence and handoff information
instead of relying on unstructured PR descriptions or chat history.

Without workspace memory, each agent must rediscover the PR context,
decisions, risks, and handoff expectations from scratch.

## Relationship to Context Steward

Context Steward owns, creates, updates, and archives workspace memory
artifacts.  It acts at six lifecycle hooks: before_plan, after_plan_review,
after_implementation, after_precommit_review, after_qa, after_merge.

## Relationship to Context Steward Prompt Templates

The prompt templates (PR 0054, `docs/CONTEXT_STEWARD_PROMPTS.md`) define
how Context Steward interacts with each artifact at each lifecycle hook.
The templates specify purpose, inputs, reads, writes, validation rules,
and anti-fabrication rules for each hook.

## Relationship to context compiler

Context pack inputs (`.project-memory/pr/<pr-id>/context-pack-inputs.yml`)
are a contract-defined bridge between workspace memory and future context
compilation.  The Context Steward prepares inputs; the context compiler
consumes them.  This PR defines the schema and template for inputs but
does not implement the compiler.

## Relationship to cache contracts

Cache key refs in workspace memory reference PR 0052 cache keys.
Invalidation inputs record staleness decisions without implementing a
cache backend.

## Relationship to review artifacts

QA evidence records (`.project-memory/pr/<pr-id>/qa-evidence.yml`)
complement but do not replace the existing review artifact schema
(`.project-memory/review-artifact.schema.yml`).  Review artifacts are
produced by review agents during reviews.  QA evidence records are
produced by Context Steward after reviews to track evidence traces.

## Lifecycle states

Ten status values defined in `schemas/feature-workspace-memory.schema.yml`:

| Status | Description |
|---|---|
| proposed | PR or feature proposed |
| planned | Planning in progress |
| plan_approved | Plan approved |
| implementing | Implementation in progress |
| implemented | Implementation complete |
| precommit_passed | Precommit review passed |
| qa_passed | QA passed |
| merged | PR merged |
| archived | Workspace archived |
| blocked | PR or feature blocked |

## Artifact path patterns

| Artifact | Path | Template |
|---|---|---|
| Workspace memory | `.project-memory/pr/<pr-id>/workspace.yml` | `.project-memory/templates/pr-workspace.yml` |
| QA evidence | `.project-memory/pr/<pr-id>/qa-evidence.yml` | `.project-memory/templates/qa-evidence.yml` |
| Context pack inputs | `.project-memory/pr/<pr-id>/context-pack-inputs.yml` | `.project-memory/templates/context-pack-inputs.yml` |

## Template usage

To create a new PR workspace memory artifact, copy the relevant template
from `.project-memory/templates/` to the PR's workspace path:

```bash
cp .project-memory/templates/pr-workspace.yml .project-memory/pr/<pr-id>/workspace.yml
```

Then fill the placeholder fields:

- `<pr-id>` — the PR number (e.g. `0055`)
- `<feature-id>` — optional feature identifier
- `<fill-me>` — short description
- `<contract-id>` — contract ID from project contract registry

Templates use safe placeholders only (`<fill-me>`, `<pr-id>`).  No shell
expressions, no `$(...)` strings.

## Anti-fabrication rules

All workspace memory artifacts must follow these rules:

1. **Command results:** Do not invent validation command results.
2. **Changed files:** Do not invent changed files.
3. **Timestamps:** Do not invent timestamps — caller-supplied only.
4. **SHAs:** Do not invent SHAs — use actual commit SHAs.
5. **Files modified:** `context_used.files_modified` must exactly match
   the files actually written.
6. **Shell placeholders:** No strings containing `$(` in any artifact.
7. **Validation tracking:** Every expected command in `commands_run` or
   `commands_not_run` with `mark: "not_run"` and a reason.

## Safety and privacy rules

- No secrets, credentials, or tokens.
- No raw repository dumps.
- No absolute local paths.
- No machine-specific paths.
- No environment-specific values unless explicitly classified.
- No `.ariadne/**` writes in this PR.
- No `.grace/**` references.

## What is intentionally not implemented in this PR

- Context compiler implementation.
- Repository scanning.
- Cache backend.
- Service implementation.
- Runtime integration.
- Automated context-pack input generation.
- Automated workspace memory creation for new PRs.
