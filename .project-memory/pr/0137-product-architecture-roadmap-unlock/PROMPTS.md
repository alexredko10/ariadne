# PR 0137 Prompts — Product Architecture Roadmap Unlock

## Branch

```bash
git switch main
git pull --ff-only origin main
git switch -c 0137-product-architecture-roadmap-unlock
git status --short
```

## Files to create in repo

```text
.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md
.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
.project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md
.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/plan-review.yml
.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/precommit-review.yml
```

## Planner prompt

TASK

PR 0137 — Product Architecture Roadmap Unlock

AGENT

planner

MODE

planning and roadmap artifact creation

BRANCH

0137-product-architecture-roadmap-unlock

PR

0137-product-architecture-roadmap-unlock

GOAL

Create a narrow architecture transition PR that preserves the uploaded Ariadna Product Master Prompt as a source artifact and writes a derived product roadmap after PR 0136. This PR closes the Production Line hardening stream and opens Artifact Workspace Read-Only UI as the next active stream.

REQUIRED WRITES

1. .project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md
2. .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
3. .project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md

HARD RULES

1. Do not write runtime code.
2. Do not write tests.
3. Do not write UI code.
4. Do not modify agents.
5. Do not modify schemas.
6. Do not modify dependencies.
7. Do not run dogfood.
8. Do not run Docker.
9. Do not run agents.
10. Do not create GitHub PRs.
11. Do not run git add, commit, push, reset, checkout, switch, merge, rebase, clean, tag, stash, rm, mv, chmod, sudo.
12. ROADMAP.md may be modified only to summarize stream status and point to the roadmap artifact.
13. The detailed 50-PR roadmap must live in .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md.
14. The master prompt must be preserved as source input, not rewritten as implementation truth.

ROADMAP REQUIREMENTS

1. Mark Production Line stream completed after PR 0131-0136.
2. Open Artifact Workspace Read-Only stream.
3. Keep UI mutation frozen.
4. Keep agent launch from UI frozen.
5. Keep commit/PR creation from UI frozen.
6. Stage Context Core, PCAM/PBS, GRACE-style contracts, Rubrics, Decision Core, Model Router, Observatory, and ETL demo after read-only workspace foundations.
7. Include approximately 50 PRs if coherent; fewer only if justified.
8. Every PR entry must include purpose and acceptance summary.
9. Every recommendation must preserve runtime-owned state, admissible proof refs, artifact visibility, and human-verifiable decisions.

VALIDATION

1. git status --short
2. git diff --name-only
3. git diff --cached --name-only
4. grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "Artifact Workspace|runtime-owned|proof|read-only|PR 0138|PR 0186|Production Line|Decision Core|Context Core|PCAM|Rubrics|Model Router" ROADMAP.md .project-memory/product .project-memory/roadmaps .project-memory/pr/0137-product-architecture-roadmap-unlock
5. grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "services/runner/src|services/runner/tests|agents/|schemas/|pyproject|poetry.lock|requirements|docker|gh pr create|git commit|git push" .project-memory/product .project-memory/roadmaps .project-memory/pr/0137-product-architecture-roadmap-unlock ROADMAP.md

OUTPUT

Return TASK COMPLETE, BLOCKERS, WARNINGS, FILES CHANGED, VALIDATION RUN, BOUNDARY CONFIRMATIONS, NEXT REQUIRED ACTION.

## Plan-review prompt

TASK

PR 0137 — Product Architecture Roadmap Unlock Plan Review

AGENT

plan-review

MODE

review

BRANCH

0137-product-architecture-roadmap-unlock

GOAL

Review only the PR 0137 planning and roadmap artifacts. Approve only if the PR preserves the master prompt, creates a coherent roadmap artifact, safely updates ROADMAP.md, closes Production Line, opens Artifact Workspace Read-Only, and does not start runtime/UI implementation.

REQUIRED READS

1. ROADMAP.md
2. .project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md
3. .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
4. .project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md
5. .project-memory/review-artifact.schema.yml
6. .project-memory/pr/0136-production-line-final-readiness-gate/PLAN.md
7. .project-memory/pr/0136-production-line-final-readiness-gate/reviews/precommit-review.yml

WRITE ONLY

.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/plan-review.yml

BLOCK IF

1. Source prompt is not preserved.
2. Roadmap has fewer than 40 PRs without justification.
3. Artifact Workspace Read-Only is not the next active stream.
4. UI mutation is not frozen.
5. Agent launch from UI is not frozen.
6. Runtime code or UI code is modified.
7. Agents, schemas, dependencies, docs outside approved scope are modified.
8. ROADMAP.md claims implementation completion that is not evidenced.
9. PR 0137 becomes committee-mode without actionable PR sequence.

VALIDATION

Run git status, git diff --name-only, git diff --cached --name-only, find target files, grep roadmap keywords, and read back the written review artifact.

OUTPUT

Return REVIEW ARTIFACT WRITTEN, VERDICT, BLOCKERS, WARNINGS, SUMMARY, VALIDATION, FILES READ, FILES WRITTEN, BOUNDARY CONFIRMATIONS.
