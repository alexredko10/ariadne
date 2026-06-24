# PR 0054 — Context Steward Prompt Templates Plan

## Goal

Plan reusable prompt templates for Context Steward lifecycle hooks.

Context Steward is responsible for preserving context integrity, PR workspace memory, QA evidence, context-pack inputs, invalidation notes, and handoff summaries.

This PR is prompt-contract/documentation/schema work only.

## Architectural Thesis

Context Steward should be executable through controlled prompts before Ariadne has a dedicated service implementation.

Prompt templates are part of the substrate contract.

The model is replaceable.
The prompt contract and artifacts are durable.

## Context Snapshot

- **current HEAD sha**: `5d501e8e4f661982a25a92f15601a0e4e01eb789`
- **current branch**: `0054-context-steward-prompt-templates`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `5d501e8` (main after PR 0053 merge — no delta since first commit on this branch)
- **index_version**: `"0.20"` (from `.project-memory/context-bundles/contracts.yml` — PR 0053 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0053, no pending changes
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
- `schemas/feature-workspace-memory.schema.yml`
- `schemas/qa-evidence-record.schema.yml`
- `schemas/cache-key.schema.yml`
- `schemas/cache-entry.schema.yml`
- `schemas/cache-policy.schema.yml`
- `schemas/context-pack.schema.yml`
- `docs/CONTEXT_STEWARD.md`
- `docs/CONTEXT_COMPILER.md`
- `docs/CACHE_CONTRACTS.md`
- `docs/adr/0008-cache-keys-are-substrate-contracts.md`
- `docs/adr/0009-context-steward-owns-context-memory.md`
- `.project-memory/pr/0052-cache-contracts-and-keys/PLAN.md`
- `.project-memory/pr/0053-context-steward-contract/PLAN.md`

## Existing Contract Snapshot

### Context Steward Contract (PR 0053)

**Role:** Context Steward owns context integrity, not code changes.

**Lifecycle hooks:** before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge.

**Owned artifacts:**
- `.project-memory/pr/<pr-id>/workspace.yml` (feature workspace memory)
- `.project-memory/pr/<pr-id>/qa-evidence.yml` (QA evidence records)
- `.project-memory/pr/<pr-id>/context-pack-inputs.yml` (deferred)

**Write boundaries:**
- May write: workspace memory, QA evidence, approved project-memory registry updates.
- Must NOT write: application code, runtime/conductor/runner/adapter, cache backend, `.ariadne/**`, `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`.

**Read boundaries:**
- May read: project contracts, memory index, anchors, context packs, cache contracts, runtime state, workspace memories, review artifacts.

**QA evidence policy:** Every expected command in either `commands_run` or `commands_not_run`. Silent validation claims impossible.

**Invalidation:** Records invalidation decisions but does not implement cache backend or repository scanning.

### Cache Contracts (PR 0052)

- Backend-agnostic key/entry/policy schemas.
- Deterministic normalization: sorted keys, sorted lists, SHA-256 digests, no timestamps/random ids.
- Namespaces: core.runtime, conductor, runner, domain_adapter.coding, context, repository_understanding, rubric, model_capability.

### Feature Workspace Memory Schema (PR 0053)

- PR workspace with 10 status values (proposed → archived).
- Scope boundaries, decisions, risks, handoff notes.
- Cache key refs from PR 0052.

### QA Evidence Record Schema (PR 0053)

- Commands_run and commands_not_run with reasons.
- Silent validation structurally impossible.

## Implementation Location Decision

**Decision: Two files to create.**

1. **`schemas/context-steward-prompt-template.schema.yml`** — schema for Context Steward prompt templates.
2. **`docs/CONTEXT_STEWARD_PROMPTS.md`** — documentation with six lifecycle prompt templates.

### Project-memory registry updates (optional, justified)

3. **`.project-memory/context-bundles/contracts.yml`** — add prompt-template schema and docs to read_first, add notes, bump version.
4. **`.project-memory/memory_index.yml`** — add `context-steward-prompts` label with new files.

**Justification:** These follow the established pattern from PR 0052 and PR 0053. They update registry metadata without modifying runtime code, agents, or broader schemas/docs.

**Not included in this PR:**
- `.project-memory/anchors.yml` — deferred as established by PR 0053.
- `.project-memory/project_contract.yml` — deferred as established by PR 0053.
- `.ariadne/**` — not created per namespace policy.
- `.grace/**` — never used.

## Prompt Template Contract

### Schema: `schemas/context-steward-prompt-template.schema.yml`

```yaml
schema_version: "0.1"

# ContextStewardPromptTemplate — reusable prompt template for a Context Steward
# lifecycle hook.
#
# Each template defines the purpose, inputs, reads, writes, outputs,
# validation rules, anti-fabrication rules, and stop conditions for one
# lifecycle hook.
#
# Context Steward does NOT write application code, modify runtime behavior,
# or perform cache backend operations per the Context Steward contract.
```

**Required fields:**
- `schema_version: string`
- `template_id: string` — e.g. `"context-steward.before_plan.v1"`
- `lifecycle_hook: string` — one of the six hooks
- `purpose: string` — what this template achieves
- `required_inputs: list[InputSpec]` — inputs the agent must receive
- `allowed_reads: list[string]` — what the agent may read
- `allowed_writes: list[string]` — exact write paths
- `forbidden_writes: list[string]` — what must not be written
- `required_outputs: list[OutputSpec]` — output artifacts
- `validation_rules: list[string]` — rules for output correctness
- `anti_fabrication_rules: list[string]` — anti-fabrication requirements
- `stop_conditions: list[string]` — conditions that stop this hook
- `final_output_format: string` — expected output structure
- `context_used_policy: string` — how context_used is reported

**Anti-fabrication rules (must be in every template):**
- Do not invent command results.
- Do not invent changed files.
- Do not invent timestamps.
- Do not invent SHAs.
- If a command was not run, mark `not_run` with reason.
- `context_used.files_modified` must exactly match actual writes.
- No shell placeholders in artifacts.
- No `$(` strings in artifacts.

## Lifecycle Prompt Templates

All six templates are documented in `docs/CONTEXT_STEWARD_PROMPTS.md`.

### 1. `before_plan`

**Template ID:** `context-steward.before_plan.v1`

**Purpose:** Prepare context for planning — gather source contracts, anchors, domain adapter policy, cache key refs, and produce a structured workspace memory entry and optional context-pack inputs document.

**Required inputs:**
- PR id
- Feature id or task id
- Domain
- Domain adapter policy reference
- Cache contracts (PR 0052)
- Existing project-memory registry (memory_index, project_contract, context bundles, anchors)

**Allowed reads:**
- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/domain-adapter.schema.yml`
- `schemas/context-pack.schema.yml`
- `schemas/cache-key.schema.yml`
- `schemas/cache-entry.schema.yml`
- `schemas/cache-policy.schema.yml`
- `docs/CONTEXT_COMPILER.md`
- `docs/DOMAIN_ADAPTER_CONTRACT.md`

**Allowed writes:**
- `.project-memory/pr/<pr-id>/workspace.yml` — create if not exists (status: proposed or planned)
- `.project-memory/pr/<pr-id>/context-pack-inputs.yml` — if defined (schema deferred, write deferred to future PR)

**Forbidden writes:**
- Application code
- Runtime/conductor/runner/adapter files
- `.ariadne/**`
- `.grace/**`
- `.project-memory/anchors.yml`
- `.project-memory/project_contract.yml`

**Validation rules:**
- workspace.yml must conform to `schemas/feature-workspace-memory.schema.yml`.
- `cache_key_refs` must reference valid namespaces from PR 0052.
- `source_contracts` must be verifiable (exist in project_contract.yml or schemas/).
- No raw repository dumps.
- No absolute local paths.
- No timestamps generated by steward (caller-supplied only).

**Anti-fabrication rules:**
- Do not invent contract IDs.
- Do not invent anchors.
- Do not invent cache keys.
- `context_used.files_modified` must list exactly the workspace.yml path.

### 2. `after_plan_review`

**Template ID:** `context-steward.after_plan_review.v1`

**Purpose:** Record plan approval/warning/block decision in workspace memory.

**Required inputs:**
- PR id
- Workspace memory path (`.project-memory/pr/<pr-id>/workspace.yml`)
- Plan review artifact (`.project-memory/pr/<pr-id>/reviews/plan-review.yml`)

**Allowed reads:**
- `.project-memory/pr/<pr-id>/workspace.yml`
- `.project-memory/pr/<pr-id>/reviews/plan-review.yml`

**Allowed writes:**
- `.project-memory/pr/<pr-id>/workspace.yml` — update status to `plan_approved`, `blocked`, or update with plan review verdict
- `.project-memory/pr/<pr-id>/qa-evidence.yml` — record plan review as QA evidence

**Forbidden writes:** same as before_plan.

**Validation rules:**
- workspace.yml status must transition validly (e.g., `proposed` → `plan_approved`, not `proposed` → `implementing`).
- Verdict from plan-review.yml must be recorded accurately.
- If blocked, stop conditions must capture the blocker.

### 3. `after_implementation`

**Template ID:** `context-steward.after_implementation.v1`

**Purpose:** Record implementation summary, changed paths, decisions, and possible invalidation inputs.

**Required inputs:**
- PR id
- Workspace memory path
- Implementation summary (from coder agent or PR description)
- Changed files list

**Allowed reads:**
- `.project-memory/pr/<pr-id>/workspace.yml`
- Prior review artifacts

**Allowed writes:**
- `.project-memory/pr/<pr-id>/workspace.yml` — update status, implementation_summary, decisions, risks, changed paths, invalidation inputs

**Validation rules:**
- Changed paths must not include forbidden write paths (from domain adapter policy).
- Invalidation inputs must be recorded if any changed paths affect source contracts or cache keys.
- Status must be updated to `implemented`.

### 4. `after_precommit_review`

**Template ID:** `context-steward.after_precommit_review.v1`

**Purpose:** Record precommit outcome and prepare PR handoff state.

**Required inputs:**
- PR id
- Workspace memory path
- Precommit review artifact (`.project-memory/pr/<pr-id>/reviews/precommit-review.yml`)

**Allowed reads:**
- `.project-memory/pr/<pr-id>/workspace.yml`
- `.project-memory/pr/<pr-id>/reviews/precommit-review.yml`

**Allowed writes:**
- `.project-memory/pr/<pr-id>/workspace.yml` — update status to `precommit_passed` or handle blockers
- `.project-memory/pr/<pr-id>/qa-evidence.yml` — record precommit QA evidence

**Validation rules:**
- Every validation command from the review artifact must appear in either `commands_run` or `commands_not_run` in QA evidence.
- If review verdict is `block`, do not change workspace status to `precommit_passed`.

### 5. `after_qa`

**Template ID:** `context-steward.after_qa.v1`

**Purpose:** Record QA evidence and manual checks.

**Required inputs:**
- PR id
- Workspace memory path
- QA evidence from manual/automated checks
- Validation commands run and not run

**Allowed reads:**
- `.project-memory/pr/<pr-id>/workspace.yml`

**Allowed writes:**
- `.project-memory/pr/<pr-id>/qa-evidence.yml` — record full QA evidence
- `.project-memory/pr/<pr-id>/workspace.yml` — update qa_summary, status to `qa_passed` or `blocked`

**Validation rules:**
- Every expected command in `commands_run` or `commands_not_run`.
- `commands_not_run` entries must have `mark: "not_run"` and a reason.
- `verdict` must match the combined QA result.

### 6. `after_merge`

**Template ID:** `context-steward.after_merge.v1`

**Purpose:** Prepare post-merge memory update summary and archive handoff.

**Required inputs:**
- PR id
- Workspace memory path
- QA evidence path

**Allowed reads:**
- `.project-memory/pr/<pr-id>/workspace.yml`
- `.project-memory/pr/<pr-id>/qa-evidence.yml`

**Allowed writes:**
- `.project-memory/pr/<pr-id>/workspace.yml` — update status to `merged` or `archived`, add archival notes and handoff summary
- Nothing else — this is the terminal hook; no new artifacts created

**Validation rules:**
- Workspace status must be `qa_passed` or equivalent before transitioning to `merged`.
- Archival notes must include: what changed, what cache keys may be affected, what follow-up PRs are needed.
- Handoff summary must be sufficient for the next PR's `before_plan` to pick up.

## Anti-fabrication Requirements

Every prompt template must include these anti-fabrication rules:

1. **Command results:** Do not invent validation command results. If a command was not run, record it in `commands_not_run` with `mark: "not_run"` and a reason.
2. **Changed files:** Do not invent changed files. Only record paths that were actually changed.
3. **Timestamps:** Do not invent timestamps. Use caller-provided timestamps only. Record `None` if no timestamp is available.
4. **SHAs:** Do not invent SHAs. Use actual commit SHAs from the environment. Record `None` if no SHA is available.
5. **Files modified:** The `context_used.files_modified` field must contain exactly the list of files actually written by the steward in this lifecycle step. No extra files. No missing files.
6. **Shell placeholders:** No strings containing `$(` in any artifact. Shell expressions are never valid artifact content.
7. **No silent omission:** Every validation command that was expected must appear in either `commands_run` or `commands_not_run`. Silent omission is fabrication.

## Safety and Scope Rules

- No application code writes.
- No `services/**` changes.
- No `packages/**` changes.
- No `apps/**` changes.
- No runtime/conductor/runner/adapter changes.
- No cache backend.
- No repository scanning.
- No context compiler implementation.
- No `.ariadne/**` writes.
- No `.grace/**` writes.
- No `.project-memory/anchors.yml` changes.
- No `.project-memory/project_contract.yml` changes.
- No old project examples/names (`water_meter`, `water-meter`, `Broken Clock`, `broken_clock`, `daily-consumption`, `.grace`, `@grace-*`, old Flask).

## Relationship to Future PRs

| PR | Scope |
|---|---|
| **0054 (this PR)** | Prompt template schema + documentation. No runtime, no agent configs, no cache backend. |
| Future PR | PR workspace memory artifact creation (`.project-memory/pr/<pr-id>/workspace.yml`) for a real feature PR. |
| Future PR | Context-pack input generator using workspace memory. |
| Future PR | Minimal context compiler that reads context-pack-inputs and produces context packs. |
| Future PR | Integrate context pack into conductor pipeline. |
| Future PR | Ariadne Labs E2E demo flow. |

## Future Allowed Write Paths

- `schemas/context-steward-prompt-template.schema.yml`
- `docs/CONTEXT_STEWARD_PROMPTS.md`
- `.project-memory/context-bundles/contracts.yml` (registry update)
- `.project-memory/memory_index.yml` (registry update)

Precommit review may later write only:
- `.project-memory/pr/0054-context-steward-prompt-templates/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0054-context-steward-prompt-templates/PLAN.md` (planner only)
- `.project-memory/pr/0054-context-steward-prompt-templates/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except exact allowed registry files listed above
- `.project-memory/anchors.yml` — deferred
- `.project-memory/project_contract.yml` — deferred
- `services/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `schemas/**` except exact allowed prompt-template schema file
- `docs/**` except exact allowed CONTEXT_STEWARD_PROMPTS.md
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`

## Required Tests / Validation

### Schema presence

```bash
python - <<'PY'
from pathlib import Path
required = [
    "schemas/context-steward-prompt-template.schema.yml",
    "docs/CONTEXT_STEWARD_PROMPTS.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, f"Missing files: {missing}"
print("context steward prompt template files present")
PY
```

### Schema content checks

- Schema defines `template_id`, `lifecycle_hook`, `purpose`, `required_inputs`, `allowed_reads`, `allowed_writes`, `forbidden_writes`, `required_outputs`, `validation_rules`, `anti_fabrication_rules`, `stop_conditions`, `final_output_format`, `context_used_policy`.
- Lifecycle_hook values include all six hooks (before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge).

### Docs content checks

- CONTEXT_STEWARD_PROMPTS.md describes all six lifecycle hooks.
- Each hook has: purpose, required inputs, allowed reads, allowed writes, forbidden writes, validation rules, anti-fabrication rules, stop conditions.
- Anti-fabrication rules include: no invented command results, no invented files, no invented timestamps, no invented SHAs, not_run with reason, context_used.files_modified must match actual writes, no `$(` in artifacts.
- Docs contain no old examples/names.

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
    "schemas/context-steward-prompt-template.schema.yml",
    "docs/CONTEXT_STEWARD_PROMPTS.md",
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print("context steward prompt template files present")
PY

grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|backend implementation\|subprocess\|requests\|httpx\|docker\|git " schemas/context-steward-prompt-template.schema.yml docs/CONTEXT_STEWARD_PROMPTS.md || true

python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

## Post-change Checks

```bash
grep -R -n "context-steward-prompt-template\|CONTEXT_STEWARD_PROMPTS\|before_plan\|after_qa\|after_merge" schemas/context-steward-prompt-template.schema.yml docs/CONTEXT_STEWARD_PROMPTS.md .project-memory/context-bundles/contracts.yml .project-memory/memory_index.yml
```

## Expected Changed Files

1. `schemas/context-steward-prompt-template.schema.yml` — new prompt template schema
2. `docs/CONTEXT_STEWARD_PROMPTS.md` — lifecycle prompt template documentation
3. `.project-memory/context-bundles/contracts.yml` — registry update
4. `.project-memory/memory_index.yml` — label update

Expected future review artifact:
- `.project-memory/pr/0054-context-steward-prompt-templates/reviews/precommit-review.yml`

## Non-goals

- no service implementation
- no runtime integration
- no context compiler implementation
- no repository scanning
- no cache backend
- no prompt execution engine
- no GitHub integration
- no UI/CLI implementation
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
- about to implement cache backend → stop
- about to implement repository scanning → stop
- about to implement context compiler → stop
- about to create per-PR runtime artifacts beyond allowed review artifacts → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should each lifecycle hook have its own template_id or share one?** **Decision:** Each hook has its own `template_id` (e.g., `context-steward.before_plan.v1`, `context-steward.after_qa.v1`). This enables independent versioning and lifecycle management.
2. **Should the schema define the exact structure of InputSpec and OutputSpec?** **Decision:** Yes, as nested maps with `field: string` and `description: string`. This keeps the schema self-documenting without requiring a separate type system.
3. **Should context-pack-inputs.yml schema be created alongside prompt templates?** **Decision:** No — deferred per PR 0053 contract. The prompt templates reference the future path but do not create or require it.

## Decisions Made

### schema_files

```
schemas/context-steward-prompt-template.schema.yml
```

### docs_files

```
docs/CONTEXT_STEWARD_PROMPTS.md
```

### project_memory_registry_updates

```
.project-memory/context-bundles/contracts.yml  — add prompt schema/docs to read_first, add notes, bump version
.project-memory/memory_index.yml               — add context-steward-prompts label
```

### lifecycle_hooks

```
before_plan, after_plan_review, after_implementation, after_precommit_review, after_qa, after_merge
```

### prompt_template_shape

```
Schema with: template_id, lifecycle_hook, purpose, required_inputs, allowed_reads,
allowed_writes, forbidden_writes, required_outputs, validation_rules,
anti_fabrication_rules, stop_conditions, final_output_format, context_used_policy.
Anti-fabrication rules include: no invented command results/files/timestamps/SHAs,
not_run with reason, context_used.files_modified exactly matches writes, no "$(".
```

### operational_namespace

```
Current: .project-memory/**
Long-term: .ariadne/** (deferred)
Allowed writes: exact PR workspace and QA evidence paths only.
```

### validation_strategy

```
Schema/doc presence checks via Python script.
Content checks via grep and manual review.
Safety checks via grep for forbidden patterns (old names, backends, subprocess).
No runtime tests (no runtime code).
```

---

PLAN written: yes
