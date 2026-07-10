# PR 0140 — Implementation Handoff Artifact Contract Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Artifact Workspace Read-Only UI (Stream 1) — workflow hardening interlude |
| **Slot** | PR 0140 (post-0139 run list view, before 0141 evidence API surface) |
| **Why this PR is next** | PR 0137 unlocked the roadmap. PR 0138 added the read model. PR 0139 added the first UI slice. During these implementation PRs, a workflow gap was identified: the coder produces implementation but no durable handoff artifact exists for the precommit-review to read before issuing its gatekeeper verdict. PR 0140 encodes this workflow decision into durable project-memory workflow artifact(s) without changing runtime, UI, or agent behavior. |
| **Batching policy** | Single-purpose: Implementation Handoff Artifact Contract workflow hardening. No runtime code, no UI code, no agent config changes. |
| **Drift heuristic** | Workflow documentation and templates only. Does not change runtime, UI, runner, task_intake, or persisted evidence behavior. Does not open UI mutation, agent launch from UI, commit from UI, or PR creation from UI. Does not weaken evidence gates. Does not make implementation reports admissible proof. |

## Summary

PR 0140 encodes a durable workflow decision: after implementation, the coder
must write an **IMPLEMENTATION_REPORT.md** in the PR directory as a handoff
context artifact.  The precommit-review must read this report and compare it
against PLAN.md, plan-review.yml, actual changed files, validation outputs,
dirty tree, and no-drift evidence before issuing its final verdict.

This PR creates:
1. A **workflow contract artifact** at `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md`
   defining the decision, the precommit gatekeeper rule, and the proof boundary.
2. A **reusable template** at `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md`
   with the required 11 sections and proof boundary disclaimer.

## Discovery Evidence

### Existing Workflow Convention Files

| File | Content | Relevance |
|------|---------|-----------|
| `.project-memory/ORCHESTRATOR_STANDARD.txt` | Defines orchestrator prompt generation rules, agent roles (planner, plan-review, coder, precommit-review), and mandatory task structure. No mention of `IMPLEMENTATION_REPORT.md`. | PR 0140 may update this file to include `IMPLEMENTATION_REPORT.md` in the coder and precommit-review task specifications. |
| `.project-memory/review-artifact-workflow.yml` | Defines review artifact paths and workflow steps: `implementation_completed`, `plan_review`, `precommit_review`. No mention of implementation handoff report. | Not modified — the workflow YAML is a review artifact contract, not an implementation handoff contract. |
| `agents/coder.yml` | Coder agent prompt: "Do not write review artifacts." Lists `IMPLEMENTATION_REPORT.md` in forbidden writes? No — not mentioned. | PR 0140 may update to include `IMPLEMENTATION_REPORT.md` in allowed files. |
| `agents/precommit-review.yml` | Precommit-review agent prompt: "Read PLAN.md, plan-review.yml, every changed file" etc. No mention of `IMPLEMENTATION_REPORT.md`. | PR 0140 may update to include `IMPLEMENTATION_REPORT.md` in required reads. |
| `.project-memory/review-artifact.schema.yml` | Schema for review artifacts. Not modified. | Schema change not needed — implementation report is handoff context, not a review artifact. |

### Existing Maturation Conventions

- `PLAN DRIFT GATE` and `NO-DRIFT CHECK` exist as conventions in PLAN.md files
  as far back as PR 0109. These are already used by plan-review to validate
  scope.
- No existing `IMPLEMENTATION_REPORT.md` exists in any PR directory — this is a
  new artifact.
- The existing `project-memory/pr/<PR-ID>/` directory convention is well
  established for PLAN.md and `reviews/` subdirectory for review artifacts.

## Workflow Decision

After implementation, every coder must write:

```
.project-memory/pr/<PR-ID>-<slug>/IMPLEMENTATION_REPORT.md
```

before precommit-review is invoked.

The implementation report must include:

1. **Task summary** — what was implemented.
2. **Files read** — exact list of files read during implementation.
3. **Files changed** — exact list of files created or modified.
4. **Implementation decisions** — key design choices made during implementation.
5. **Plan alignment** — how the implementation matches PLAN.md.
6. **Deviations from PLAN.md** — any deviation, with justification.
7. **Validation commands and results** — exact commands run and their outputs.
8. **Boundary confirmations** — what scope boundaries were preserved.
9. **Non-goals preserved** — what was explicitly not done.
10. **Known risks or warnings** — what the reviewer should be aware of.
11. **Next reviewer focus** — what the precommit-review should pay most
    attention to.

## Precommit Gatekeeper Rule

Precommit-review must read, at minimum:

1. `.project-memory/pr/<PR-ID>-<slug>/PLAN.md`
2. `.project-memory/pr/<PR-ID>-<slug>/reviews/plan-review.yml`
3. `.project-memory/pr/<PR-ID>-<slug>/IMPLEMENTATION_REPORT.md`
4. The actual changed files (from git diff or file inspection)
5. Relevant previous PR artifacts

Precommit-review must compare:

- **PLAN.md** — what was planned
- **plan-review.yml** — what was approved
- **IMPLEMENTATION_REPORT.md** — what the coder claims was done
- **Actual changed files** — what was actually changed
- **Validation outputs** — whether validation commands passed
- **Dirty tree** — whether the working tree matches expectations
- **Cached diff** — whether staged files are within scope
- **PLAN DRIFT GATE** — whether implementation scope drifted from PLAN.md
- **NO-DRIFT CHECK** — whether evidence boundaries were preserved

If these disagree, **actual file evidence, validation evidence, and PLAN.md
win**.  The coder's claims in IMPLEMENTATION_REPORT.md must be independently
verified.

## Proof Boundary

**Implementation reports are handoff context, not proof.**

- Agent output is not proof.
- Runtime-captured validation, command outputs, file contents, diffs, persisted
  runtime artifacts, and accepted proof refs remain proof.
- Precommit-review must not pass solely because `IMPLEMENTATION_REPORT.md`
  claims success.
- Precommit-review must block or warn if `IMPLEMENTATION_REPORT.md` claims are
  unsupported by files or validation.

## Template Requirements

The implementation report template must include these 11 sections:

```
TASK SUMMARY
FILES READ
FILES CHANGED
IMPLEMENTATION DECISIONS
PLAN ALIGNMENT
DEVIATIONS FROM PLAN
VALIDATION RUN
BOUNDARY CONFIRMATIONS
NON-GOALS PRESERVED
RISKS OR WARNINGS
NEXT REVIEWER FOCUS
```

The template must include a header stating:

```
> This document is handoff context, not proof.
> Agent output is not proof.
> Runtime-captured validation, command outputs, file contents, diffs,
> persisted runtime artifacts, and accepted proof refs remain proof.
```

The template must instruct the coder to include exact command outputs or
references when available, but the reviewer must independently validate.

## Scope

### Allowed Implementation Files

| File | Action | Justification |
|------|--------|---------------|
| `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md` | Create | New workflow contract artifact defining the decision, precommit gatekeeper rule, and proof boundary. |
| `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md` | Create | New reusable handoff report template with 11 required sections and proof boundary disclaimer. |
| `.project-memory/ORCHESTRATOR_STANDARD.txt` | Update (narrow) | Add references to `IMPLEMENTATION_REPORT.md` in CODER TASKS and PRECOMMIT-REVIEW TASKS sections. Update the precommit-review task specification to include IMPLEMENTATION_REPORT.md in required reads and comparison gate. |
| `agents/coder.yml` | Update (narrow) | Include `IMPLEMENTATION_REPORT.md` in allowed write paths and require it before precommit-review. |
| `agents/precommit-review.yml` | Update (narrow) | Include `IMPLEMENTATION_REPORT.md` in required reads and in the comparison gate section of the prompt. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `.project-memory/review-artifact.schema.yml` | Not modified. Implementation report is not a review artifact. Schema change not needed. |
| `.project-memory/review-artifact-workflow.yml` | Not modified. This YAML defines review artifact workflow, not implementation handoff. |
| All runtime/UI/test files | No runtime, UI, runner, or task_intake code changes. |
| All previous PR artifacts | Not modified. |

### Not Modified

- `ROADMAP.md`
- `docs/`, `schemas/`
- `pyproject.toml`, `poetry.lock`, `requirements*.txt`
- `.gitignore`
- All previous PR artifacts (0131–0139)
- All service code files
- `.project-memory/review-artifact.schema.yml`
- `.project-memory/review-artifact-workflow.yml`

## Validation Design

### Artifact Presence Check

```bash
test -f .project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md
test -f .project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md
```

Expected: both files exist.
If not met: block.

### Grep for Contract Content

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "IMPLEMENTATION_REPORT|handoff context|not proof|precommit-review|comparison gate|PLAN DRIFT GATE|NO-DRIFT CHECK" \
  .project-memory/workflow \
  .project-memory/templates \
  .project-memory/ORCHESTRATOR_STANDARD.txt \
  agents/coder.yml \
  agents/precommit-review.yml \
  .project-memory/pr/0140-implementation-handoff-artifact-contract
```

Expected: implementation handoff contract, template, precommit gatekeeper
rule, and comparison gate references are visible.
If not met: block.

### Grep for Proof Boundary

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "handoff context|not proof|agent output is not proof|implementation reports are" \
  .project-memory/workflow \
  .project-memory/templates
```

Expected: proof boundary statement exists in contract and template.
If not met: block.

### Grep for Unchanged Files

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  .project-memory/workflow \
  .project-memory/templates
```

Expected: no unsafe mutation authority added.
If unsafe new mutation is found: block.

### Git Status

```bash
git status --short
```

Expected: only allowed PR 0140 files are dirty.
If services/, agents/ (if not planned), schemas/, docs/, dependencies,
.gitignore, ROADMAP.md, or previous PR artifacts modified: block.
If unknown untracked files exist: block.

### Git Diff

```bash
git diff --name-only
```

Expected: only expected PR 0140 files listed.
If services/, pyproject.toml, poetry.lock, requirements*.txt, .gitignore,
ROADMAP.md, schemas/, or previous PR artifacts appear: block.

### Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty during planning.
If staged files exist: block.

### PLAN DRIFT GATE

Verify that implementation expands only to:
- `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md` (new)
- `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md` (new)
- `.project-memory/ORCHESTRATOR_STANDARD.txt` (narrow update to coder and precommit-review sections)
- `agents/coder.yml` (narrow update to allow IMPLEMENTATION_REPORT.md)
- `agents/precommit-review.yml` (narrow update to require IMPLEMENTATION_REPORT.md in reads)
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/PLAN.md`
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/reviews/plan-review.yml`
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/reviews/precommit-review.yml`

If implementation expands beyond these files: block.

### NO-DRIFT CHECK

Verify that:
- No runtime code is changed.
- No UI code is changed.
- No tests are changed.
- No schemas are changed.
- No dependencies are changed.
- No ROADMAP.md changes unless explicitly planned.
- No product roadmap artifacts are modified.
- No previous PR artifacts are modified.
- No evidence boundaries are weakened.
- No agent output is promoted to proof.

### Artifact Write/Readback Check

After writing each file:
```bash
test -f <path> && head -5 <path>
```

Expected: file exists and first 5 lines are readable.
If not met: block.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131–0136 Production Line | Not modified. No runtime code changes. |
| PR 0137 Roadmap Unlock | Not modified. |
| PR 0138 Read Model | Not modified. No code changes. |
| PR 0139 Run List View | Not modified. No code changes. |
| PR 0134 Payload Cleanliness | Not modified. Implementation reports are not proof. |
| PR 0135 Run Report | Not modified. Run report remains runtime evidence. |
| PR 0136 Readiness Gate | Not modified. Readiness gate still evaluates persisted evidence. |
| Git Boundary authority | Not modified. Implementation reports do not authorize git mutation. |
| Evidence-first principle | Implementation reports are handoff context, not proof. |

## Non-Goals

- No runtime code.
- No UI code.
- No task_intake code.
- No runner code.
- No tests (workflow documentation only — compileall/pytest not required).
- No dependency changes.
- No schema changes.
- No ROADMAP.md change.
- No previous PR artifact changes.
- No dogfood execution.
- No agent execution.
- No change that treats agent output as proof.
- No retroactive requirement for PRs 0137, 0138, or 0139.
- No change to `review-artifact.schema.yml` or `review-artifact-workflow.yml`.
- The contract applies to future implementation PRs after merge.

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0140-implementation-handoff-artifact-contract`
- PLAN does not define the Implementation Handoff Artifact Contract
- PLAN does not require IMPLEMENTATION_REPORT.md before precommit-review
- PLAN does not require precommit-review to read IMPLEMENTATION_REPORT.md
- PLAN states that IMPLEMENTATION_REPORT.md is proof
- PLAN changes runtime code, UI code, tests, schemas, dependencies
- PLAN modifies ROADMAP.md, product roadmap artifacts, or previous PR artifacts
- PLAN makes implementation reports admissible proof
- PLAN modifies `review-artifact.schema.yml` or `review-artifact-workflow.yml`
- PLAN adds .gitignore entries
