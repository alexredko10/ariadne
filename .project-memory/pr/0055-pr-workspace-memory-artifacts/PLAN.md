# PR 0055 — PR Workspace Memory Artifacts Plan

## Goal

Plan concrete artifact templates and documentation for PR workspace memory.

The artifacts should define the files Context Steward will later create/update during Ariadne workflow stages:

* workspace memory
* QA evidence
* context-pack inputs

This PR defines templates/docs/schema only.

No service implementation.
No runtime integration.
No context compiler implementation.
No repository scanning.
No cache backend.
No `.ariadne/**`.

## Architectural Thesis

Ariadne needs explicit workspace artifacts before it can automate Context Steward behavior.

Prompt templates describe how Context Steward should behave.
Workspace memory artifacts define where evidence, scope, decisions, risks, and context-pack inputs are recorded.

The model is replaceable.
The workspace artifact contract is durable.

## Context Snapshot

- **current HEAD sha**: `3131559c209ca2f6ef8c86e077c60c8a899d09ff`
- **current branch**: `0055-pr-workspace-memory-artifacts`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `3131559` (merge commit of main into branch — no skew relative to main)
- **index_version**: `"0.21"` (from `.project-memory/context-bundles/contracts.yml` — PR 0054 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0054, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/review-artifact.schema.yml`
- `.project-memory/context-steward.schema.yml`
- `schemas/context-steward.schema.yml`
- `schemas/context-steward-prompt-template.schema.yml`
- `schemas/feature-workspace-memory.schema.yml`
- `schemas/qa-evidence-record.schema.yml`
- `schemas/cache-key.schema.yml`
- `schemas/cache-entry.schema.yml`
- `schemas/cache-policy.schema.yml`
- `schemas/context-pack.schema.yml`
- `docs/CONTEXT_STEWARD.md`
- `docs/CONTEXT_STEWARD_PROMPTS.md`
- `docs/CONTEXT_COMPILER.md`
- `docs/CACHE_CONTRACTS.md`
- `docs/adr/0008-cache-keys-are-substrate-contracts.md`
- `docs/adr/0009-context-steward-owns-context-memory.md`
- `.project-memory/pr/0052-cache-contracts-and-keys/PLAN.md`
- `.project-memory/pr/0053-context-steward-contract/PLAN.md`
- `.project-memory/pr/0054-context-steward-prompt-templates/PLAN.md`

## Existing Contract Snapshot

### Context Steward Contract (PR 0053)

**Role:** Owns context integrity. Does not write code.
**Lifecycle hooks:** before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge.
**Owned artifact paths:**
- `.project-memory/pr/<pr-id>/workspace.yml`
- `.project-memory/pr/<pr-id>/qa-evidence.yml`
- `.project-memory/pr/<pr-id>/context-pack-inputs.yml` (deferred)

### Context Steward Prompt Templates (PR 0054)

- `schemas/context-steward-prompt-template.schema.yml` — template contract schema.
- `docs/CONTEXT_STEWARD_PROMPTS.md` — six lifecycle hook templates with purpose, inputs, reads, writes, validation, anti-fabrication rules, stop conditions.
- Anti-fabrication rules: no invented commands/files/timestamps/SHAs, not_run with reason, no `$(`.
- Templates reference workspace memory and QA evidence paths.

### Feature Workspace Memory Schema (PR 0053)

- `schemas/feature-workspace-memory.schema.yml` — PR workspace fields: pr_id, status (10 values), goal, scope, paths, contracts, anchors, decisions, risks, handoff notes.
- Timestamps caller-supplied. Decision records append-only.

### QA Evidence Record Schema (PR 0053)

- `schemas/qa-evidence-record.schema.yml` — commands_run, commands_not_run with reasons.
- Every expected command tracked. Silent validation impossible.

### Cache Contracts (PR 0052)

- Backend-agnostic. Key/entry/policy schemas.
- Namespaces and artifact kinds for cache key refs.

### Context Pack Schema

- `schemas/context-pack.schema.yml` — structured context with source traces, base_sha, index_version.
- No raw repository dumps.

### Review Artifact Schema

- `.project-memory/review-artifact.schema.yml` — existing review artifact used by agents.
- QA evidence complements but does not replace this schema.

### Templates directory

- No `.project-memory/templates/` directory exists yet. This PR creates it.

## Implementation Location Decision

**Decision: Seven files to create.**

### Docs file

1. **`docs/PR_WORKSPACE_MEMORY.md`** — documentation for PR workspace memory artifacts.

### Schema file

2. **`schemas/context-pack-inputs.schema.yml`** — schema for context-pack inputs artifact.

### Template files

3. **`.project-memory/templates/pr-workspace.yml`** — reusable YAML template for workspace memory.
4. **`.project-memory/templates/qa-evidence.yml`** — reusable YAML template for QA evidence.
5. **`.project-memory/templates/context-pack-inputs.yml`** — reusable YAML template for context-pack inputs.

### Project-memory registry updates (justified)

6. **`.project-memory/context-bundles/contracts.yml`** — add new docs/schema to read_first, add notes, bump version.
7. **`.project-memory/memory_index.yml`** — add label for templates.

**Justification:** These follow the established registry update pattern from PR 0052, 0053, and 0054. They update metadata only — no runtime code, no agents, no anchors, no project_contract.

**Not included in this PR:**
- `.project-memory/anchors.yml` — deferred per PR 0053 precedent.
- `.project-memory/project_contract.yml` — deferred per PR 0053 precedent.
- `.ariadne/**` — not created.
- `.grace/**` — never used.

## Artifact Templates

### 1. PR Workspace Template

**Path:** `.project-memory/templates/pr-workspace.yml`

This is a reusable placeholder template conforming to `schemas/feature-workspace-memory.schema.yml`.

```yaml
# PR Workspace Memory Template
# Copy to .project-memory/pr/<pr-id>/workspace.yml and fill.
# Conforms to schemas/feature-workspace-memory.schema.yml

schema_version: "0.1"
pr_id: "<pr-id>"
feature_id: "<feature-id>"
title: "<fill-me>"
status: "proposed"
goal: "<fill-me>"
scope:
  - "<fill-me>"
allowed_write_paths:
  - "services/**"
  - "packages/**"
  - "tests/**"
forbidden_paths:
  - ".git/**"
  - ".env"
  - "secrets/**"
source_contracts:
  - "<contract-id>"
relevant_anchors: []
context_pack_refs: []
cache_key_refs: []
decisions: []
implementation_summary: ""
validation_summary: ""
qa_summary: ""
risks: []
open_questions: []
handoff_notes: ""
created_from:
  agent: "<context-steward-agent>"
  hook: "before_plan"
  template: "context-steward.before_plan.v1"
updated_by: []
```

**Design rules:**
- Safe placeholders (`<pr-id>`, `<fill-me>`) — no shell expressions (`$(...)`).
- No timestamps — caller-supplied only.
- Default status is `proposed`.
- Lists are empty by default — steward fills them.
- `created_from` references the context steward hook and prompt template.
- `updated_by` is append-only — each steward update adds an entry.

### 2. QA Evidence Template

**Path:** `.project-memory/templates/qa-evidence.yml`

Conforms to `schemas/qa-evidence-record.schema.yml`.

```yaml
# QA Evidence Record Template
# Copy to .project-memory/pr/<pr-id>/qa-evidence.yml and fill.
# Conforms to schemas/qa-evidence-record.schema.yml

schema_version: "0.1"
pr_id: "<pr-id>"
review_type: "<plan-review|precommit-review|qa>"
verdict: "pass"
reviewer: "<agent-id>"
snapshot: "<sha-or-description>"
commands_run:
  - command: "python -m pytest -q"
    exit_code: 0
    output: ""
commands_not_run:
  - command: "<command>"
    reason: "<reason-for-not-running>"
    mark: "not_run"
manual_checks: []
risks: []
blockers: []
warnings: []
accepted_risks: []
files_checked: []
files_changed: []
context_used:
  labels: []
  memory_files_read: []
  files_modified: []
  files_inspected: []
evidence_refs: []
created_from:
  agent: "<context-steward-agent>"
  hook: "<hook-name>"
  template: "<template-id>"
```

**Design rules:**
- Every command appears in `commands_run` (with result) or `commands_not_run` (with reason and `mark: "not_run"`).
- Silent validation is structurally impossible — there is no field for "omitted commands."
- `commands_not_run` example includes `mark: "not_run"` and `reason` — both required.
- `context_used.files_modified` must exactly match the files the steward wrote.

### 3. Context Pack Inputs Template

**Path:** `.project-memory/templates/context-pack-inputs.yml`

Conforms to `schemas/context-pack-inputs.schema.yml` (defined in this PR).

```yaml
# Context Pack Inputs Template
# Copy to .project-memory/pr/<pr-id>/context-pack-inputs.yml and fill.
# Conforms to schemas/context-pack-inputs.schema.yml

schema_version: "0.1"
pr_id: "<pr-id>"
feature_id: "<feature-id>"
task_goal: "<fill-me>"
source_contracts:
  - "<contract-id>"
relevant_anchors: []
allowed_paths:
  - "services/**"
  - "packages/**"
  - "tests/**"
forbidden_paths:
  - ".git/**"
  - ".env"
  - "secrets/**"
cache_key_refs: []
prior_pr_refs: []
qa_evidence_refs: []
known_risks: []
manual_checks_required: []
context_freshness:
  status: "fresh"
  last_verified_hook: "none"
invalidation_inputs: {}
requested_context_sections: []
output_preferences: {}
created_from:
  agent: "<context-steward-agent>"
  hook: "before_plan"
  template: "context-steward.before_plan.v1"
updated_by: []
```

## Context Pack Inputs Schema

**Path:** `schemas/context-pack-inputs.schema.yml`

```yaml
schema_version: "0.1"

# ContextPackInputs — structured inputs for the Context Compiler.
#
# Created by Context Steward during before_plan and updated through the
# lifecycle.  Contains references, digests, and structured data — not raw
# repository dumps.
#
# Context Steward prepares inputs but does NOT compile context packs.
```

**Required fields:**
- `schema_version: string`
- `pr_id: string`
- `feature_id: string` (optional)
- `task_goal: string`
- `source_contracts: list[string]`
- `relevant_anchors: list[string]`
- `allowed_paths: list[string]`
- `forbidden_paths: list[string]`
- `cache_key_refs: list[CacheKeyRef]`
- `prior_pr_refs: list[PriorPRRef]`
- `qa_evidence_refs: list[string]`
- `known_risks: list[Risk]`
- `manual_checks_required: list[string]`
- `context_freshness: ContextFreshness`
- `invalidation_inputs: dict` (key-value map)
- `requested_context_sections: list[string]`
- `output_preferences: dict` (key-value map)
- `created_from: SourceRef`
- `updated_by: list[UpdateRecord]`

**ContextFreshness structure:**
```yaml
status: string          # "fresh" | "stale" | "in_progress" | "unknown"
last_verified_hook: string  # lifecycle hook name or "none"
```

**Safety constraints:**
- No raw repository dumps.
- No secrets, credentials, or tokens.
- No absolute local paths.
- No machine-specific paths.
- No environment-specific values unless explicitly classified.
- No invented command results.
- All path references must be relative (within project scope).
- All contract references must exist in project contracts registry.
- Cache key refs must use valid namespaces from PR 0052 taxonomy.

**Determinism rules:**
- Lists must be sorted for deterministic key computation.
- Map keys must be sorted lexicographically.
- Empty strings and lists should be omitted from serialized form.
- No timestamps generated by steward (caller-supplied only).

## Documentation

**Path:** `docs/PR_WORKSPACE_MEMORY.md`

The docs must explain:

- **What PR workspace memory is:** Short-term contextual memory for one PR or feature, maintained by Context Steward.
- **Why it exists:** Gives agents structured evidence and handoff instead of relying on unstructured PR descriptions.
- **Relationship to Context Steward:** Context Steward owns, creates, updates, and archives workspace memory artifacts.
- **Relationship to Context Steward Prompt Templates:** The prompt templates (PR 0054) define how Context Steward interacts with each artifact at each lifecycle hook.
- **Relationship to context compiler:** Context pack inputs are a contract-defined bridge between workspace memory and future context compilation.
- **Relationship to cache contracts:** Cache key refs in workspace memory reference PR 0052 cache keys. Invalidation inputs record staleness without implementing a cache backend.
- **Relationship to review artifacts:** QA evidence records complement (do not replace) the existing `review-artifact.schema.yml`.
- **Lifecycle states:** Ten status values defined in `schemas/feature-workspace-memory.schema.yml`: proposed, planned, plan_approved, implementing, implemented, precommit_passed, qa_passed, merged, archived, blocked.
- **Artifact path patterns:**
  - `.project-memory/pr/<pr-id>/workspace.yml`
  - `.project-memory/pr/<pr-id>/qa-evidence.yml`
  - `.project-memory/pr/<pr-id>/context-pack-inputs.yml`
- **Template usage:** How to copy templates from `.project-memory/templates/` to a PR workspace.
- **Anti-fabrication rules:** Same as prompts (no invented commands, files, timestamps, SHAs; not_run with reason; no `$(`).
- **Safety/privacy rules:** No secrets, no raw dumps, no absolute paths, no old names.
- **What is intentionally not implemented in this PR:** Context compiler, repository scanning, cache backend, service implementation.

## Relationship to Future PRs

| PR | Scope |
|---|---|
| **0055 (this PR)** | Workspace artifact templates, schema for context-pack inputs, docs. No executor. |
| Future PR | Context-pack input generator — automated filling of context-pack-inputs.yml from contracts/anchors |
| Future PR | Minimal context compiler — reads context-pack-inputs, produces context packs |
| Future PR | Integrate context pack into conductor pipeline |
| Future PR | Ariadne Labs E2E demo flow |

## Future Allowed Write Paths

- `docs/PR_WORKSPACE_MEMORY.md`
- `schemas/context-pack-inputs.schema.yml`
- `.project-memory/templates/pr-workspace.yml`
- `.project-memory/templates/qa-evidence.yml`
- `.project-memory/templates/context-pack-inputs.yml`
- `.project-memory/context-bundles/contracts.yml` (registry update)
- `.project-memory/memory_index.yml` (label update)

Precommit review may later write only:
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0055-pr-workspace-memory-artifacts/PLAN.md` (planner only)
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except exact allowed template and registry files listed above
- `.project-memory/anchors.yml` — deferred
- `.project-memory/project_contract.yml` — deferred
- `services/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `schemas/**` except exact allowed context-pack-inputs schema
- `docs/**` except exact allowed PR_WORKSPACE_MEMORY.md
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`

## Required Tests / Validation

### File presence

```bash
python - <<'PY'
from pathlib import Path
required = [
    "docs/PR_WORKSPACE_MEMORY.md",
    "schemas/context-pack-inputs.schema.yml",
    ".project-memory/templates/pr-workspace.yml",
    ".project-memory/templates/qa-evidence.yml",
    ".project-memory/templates/context-pack-inputs.yml",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, f"Missing files: {missing}"
print("PR workspace memory artifact files present")
PY
```

### No shell placeholders

```bash
grep -R -n "\$(" docs/PR_WORKSPACE_MEMORY.md schemas/context-pack-inputs.schema.yml .project-memory/templates || true
```

Expect zero matches. Shell placeholders (`$(...)`) are forbidden in all artifacts.

### No old names / forbidden patterns

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|backend implementation\|subprocess\|requests\|httpx\|docker\|git " docs/PR_WORKSPACE_MEMORY.md schemas/context-pack-inputs.schema.yml .project-memory/templates || true
```

Expect zero matches.

### Template content checks

- `pr-workspace.yml` uses safe placeholders (`<pr-id>`, `<fill-me>`) — no shell placeholders.
- `pr-workspace.yml` has `status: "proposed"` as default.
- `pr-workspace.yml` has an empty `decisions: []` — not omitted.
- `pr-workspace.yml` has `created_from` with agent, hook, template fields.
- `qa-evidence.yml` has `commands_run` and `commands_not_run` with `mark: "not_run"` and `reason`.
- `qa-evidence.yml` has `context_used` with `files_modified` field.
- `context-pack-inputs.yml` has `context_freshness` structure.
- `context-pack-inputs.yml` uses references, not raw content.

### Schema content checks

- `context-pack-inputs.schema.yml` defines all required fields listed in the plan.
- Schema includes `context_freshness` with `status` and `last_verified_hook`.
- Schema includes safety constraints (no raw dumps, no secrets, no absolute paths).
- Schema includes determinism rules (sorted lists, no empty/null, no steward-generated timestamps).

### Documentation content checks

- `docs/PR_WORKSPACE_MEMORY.md` explains what PR workspace memory is.
- Documents relationship to Context Steward, prompt templates, context compiler, cache contracts, review artifacts.
- Documents lifecycle states.
- Documents artifact path patterns.
- Documents template usage.
- Documents anti-fabrication rules.
- Documents safety/privacy rules.
- Documents what is intentionally not implemented.

### Boundary checks

- No `services/**` files changed.
- No `packages/**` files changed.
- No `agents/**` files changed.
- No `apps/**` files changed.
- No `.ariadne/**` or `.grace/**` created.
- No `.project-memory/anchors.yml` or `.project-memory/project_contract.yml` changed.

### Validation commands

```bash
python - <<'PY'
from pathlib import Path
required = [
    "docs/PR_WORKSPACE_MEMORY.md",
    "schemas/context-pack-inputs.schema.yml",
    ".project-memory/templates/pr-workspace.yml",
    ".project-memory/templates/qa-evidence.yml",
    ".project-memory/templates/context-pack-inputs.yml",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print("PR workspace memory artifact files present")
PY

grep -R -n "\$(" docs/PR_WORKSPACE_MEMORY.md schemas/context-pack-inputs.schema.yml .project-memory/templates || true

grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|backend implementation\|subprocess\|requests\|httpx\|docker\|git " docs/PR_WORKSPACE_MEMORY.md schemas/context-pack-inputs.schema.yml .project-memory/templates || true

python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

## Post-change Checks

```bash
grep -R -n "PR_WORKSPACE_MEMORY\|context-pack-inputs\|pr-workspace\|qa-evidence" docs/PR_WORKSPACE_MEMORY.md schemas/context-pack-inputs.schema.yml .project-memory/templates .project-memory/context-bundles/contracts.yml .project-memory/memory_index.yml
```

## Expected Changed Files

1. `docs/PR_WORKSPACE_MEMORY.md`
2. `schemas/context-pack-inputs.schema.yml`
3. `.project-memory/templates/pr-workspace.yml`
4. `.project-memory/templates/qa-evidence.yml`
5. `.project-memory/templates/context-pack-inputs.yml`
6. `.project-memory/context-bundles/contracts.yml` (registry update)
7. `.project-memory/memory_index.yml` (label update)

Expected future review artifact:
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/reviews/precommit-review.yml`

## Non-goals

- no service implementation
- no runtime integration
- no context compiler implementation
- no repository scanning
- no cache backend
- no prompt execution engine
- no GitHub integration
- no UI/CLI implementation
- no application code
- no `agents/**` changes
- no `.ariadne/**`
- no `.grace/**`
- no `.project-memory/anchors.yml` changes
- no `.project-memory/project_contract.yml` changes

## Stop Conditions

- about to write `services/**` → stop
- about to write `packages/**` → stop
- about to write `agents/**` → stop
- about to write `apps/**` → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `.project-memory/anchors.yml` → stop (deferred)
- about to modify `.project-memory/project_contract.yml` → stop (deferred)
- about to implement execution/runtime behavior → stop
- about to implement context compiler → stop
- about to implement repository scanning → stop
- about to implement cache backend → stop
- about to create per-PR runtime artifacts beyond allowed review artifacts → stop
- shell placeholders (`$(...)`) would be introduced → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should the templates directory be `.project-memory/templates/` or `.project-memory/pr/templates/`?** **Decision:** `.project-memory/templates/`. The templates are cross-PR reusable artifacts, not per-PR artifacts. Per-PR artifacts live under `.project-memory/pr/<pr-id>/`.

2. **Should the context-pack-inputs template include an example section showing filled values?** **Decision:** No. The template uses placeholders. Examples would be documentation, not templates. `docs/PR_WORKSPACE_MEMORY.md` can include inline examples.

3. **Should `schemas/context-pack-inputs.schema.yml` include a `requested_context_sections` enum?** **Decision:** No — it's a free-form list of strings. Future PRs may define an enum once Context Compiler exists. For now, flexibility is preferred.

## Decisions Made

### docs_files

```
docs/PR_WORKSPACE_MEMORY.md
```

### schema_files

```
schemas/context-pack-inputs.schema.yml
```

### template_files

```
.project-memory/templates/pr-workspace.yml
.project-memory/templates/qa-evidence.yml
.project-memory/templates/context-pack-inputs.yml
```

### project_memory_registry_updates

```
.project-memory/context-bundles/contracts.yml  — add new docs/schema/templates to read_first, add notes, bump version
.project-memory/memory_index.yml               — add label for templates
```

### artifact_path_patterns

```
Workspace memory:  .project-memory/pr/<pr-id>/workspace.yml
QA evidence:       .project-memory/pr/<pr-id>/qa-evidence.yml
Context inputs:    .project-memory/pr/<pr-id>/context-pack-inputs.yml
Templates:         .project-memory/templates/<filename>.yml
```

### context_pack_inputs_shape

```
Schema with: pr_id, feature_id, task_goal, source_contracts, relevant_anchors,
allowed_paths, forbidden_paths, cache_key_refs, prior_pr_refs, qa_evidence_refs,
known_risks, manual_checks_required, context_freshness (status + last_verified_hook),
invalidation_inputs, requested_context_sections, output_preferences, created_from, updated_by.
Safety: no raw dumps, no secrets, no absolute paths, no machine-specific paths.
Determinism: sorted lists, sorted map keys, no empty/null, no steward-generated timestamps.
```

### validation_strategy

```
File presence check via Python script.
Shell placeholder check via grep (expect zero matches).
Forbidden pattern check via grep (old names, backends, subprocess).
Template content review (safe placeholders, not_run structure, context_used.files_modified).
Schema content review (required fields, context_freshness, safety constraints).
Doc content review (relationships, lifecycle states, path patterns, anti-fabrication).
Boundary check (no services/packages/agents/apps).
```

---

PLAN written: yes
