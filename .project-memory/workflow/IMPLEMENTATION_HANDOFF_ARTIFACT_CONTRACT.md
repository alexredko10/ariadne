# Implementation Handoff Artifact Contract

## Version

1.0.0 — effective from PR 0140 merge.

## Contract Purpose

This contract defines the workflow requirement that every future Ariadne
implementation agent must produce an `IMPLEMENTATION_REPORT.md` handoff
artifact before precommit-review is invoked.

The report is **handoff context, not proof**.

Agent output is not proof.
Runtime-captured validation, command outputs, file contents, diffs,
persisted runtime artifacts, and accepted proof refs remain proof.

Precommit-review remains the final gatekeeper.

## When This Applies

| Condition | Rule |
|-----------|------|
| PR is a future implementation PR (post-0140) | `IMPLEMENTATION_REPORT.md` is required before precommit-review. |
| PR PLAN.md explicitly exempts the report with justification | Exemption is valid for that PR only. |
| PR is a review-only, planning-only, or roadmap-only PR | No implementation report required. |
| PR is a retroactive review of PRs 0137, 0138, or 0139 | No implementation report required. This contract does not apply retroactively. |

## Required Artifact Path

```
.project-memory/pr/<PR-ID>-<slug>/IMPLEMENTATION_REPORT.md
```

The artifact must live in the PR directory alongside `PLAN.md`.

## Required Report Sections

The implementation report must include exactly these 11 sections:

1. `TASK SUMMARY` — what was implemented.
2. `FILES READ` — exact list of files read during implementation.
3. `FILES CHANGED` — exact list of files created or modified.
4. `IMPLEMENTATION DECISIONS` — key design choices made during implementation.
5. `PLAN ALIGNMENT` — how the implementation matches PLAN.md.
6. `DEVIATIONS FROM PLAN` — any deviation, with justification.
7. `VALIDATION RUN` — exact commands run and their outputs (exit code, result).
8. `BOUNDARY CONFIRMATIONS` — what scope boundaries were preserved.
9. `NON-GOALS PRESERVED` — what was explicitly not done.
10. `RISKS OR WARNINGS` — what the reviewer should be aware of.
11. `NEXT REVIEWER FOCUS` — what the precommit-review should pay most attention to.

## Proof Boundary Disclaimer

Every `IMPLEMENTATION_REPORT.md` must include a header stating:

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## Coder Obligations

After implementation, before precommit-review, the coder must:

1. Write `IMPLEMENTATION_REPORT.md` in the PR directory.
2. Include all 11 required sections.
3. Include the proof boundary disclaimer.
4. Include exact validation commands and their outputs.
5. Not treat the report as proof of correctness.

## Precommit-Review Obligations

The precommit-review agent must:

1. Read `PLAN.md`.
2. Read `reviews/plan-review.yml`.
3. Read `IMPLEMENTATION_REPORT.md`.
4. Read the actual changed files (from `git diff` or file inspection).
5. Read relevant previous PR artifacts.
6. Read validation outputs.
7. Inspect the dirty tree.
8. Inspect the cached diff.
9. Apply `PLAN DRIFT GATE`.
10. Apply `NO-DRIFT CHECK`.

The precommit-review agent must **compare** claims in `IMPLEMENTATION_REPORT.md`
against `PLAN.md`, `plan-review.yml`, actual changed files, validation outputs,
dirty tree evidence, and drift checks.

**Evidence precedence**: If `IMPLEMENTATION_REPORT.md` claims disagree with
`PLAN.md` or actual file/validation evidence, `PLAN.md` and actual evidence
win. Precommit-review must not pass solely because the implementation report
claims success.

**Unsupported claims**: If `IMPLEMENTATION_REPORT.md` makes claims not supported
by files or validation, precommit-review must block or warn.

**Missing report**: If `IMPLEMENTATION_REPORT.md` is absent for a future
implementation PR (post-0140) and the PR PLAN.md does not explicitly exempt it
with justification, precommit-review must block.

## What This Contract Does Not Change

- Does not change runtime behavior.
- Does not change UI behavior.
- Does not change runner behavior.
- Does not change task_intake behavior.
- Does not change evidence boundaries.
- Does not make implementation reports admissible proof.
- Does not weaken PLAN DRIFT GATE or NO-DRIFT CHECK.
- Does not apply retroactively to PRs 0137, 0138, or 0139.

## Maintenance

This contract is maintained in:
`.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md`

Updates require a plan-review and precommit-review cycle.
