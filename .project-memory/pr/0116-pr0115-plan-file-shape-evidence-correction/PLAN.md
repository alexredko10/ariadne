# PR 0116 — PR 0115 Plan/File-Shape Evidence Correction

## Summary

Plan a narrow project-memory correction that records the post-merge file-shape drift between PR 0115 PLAN.md (which proposed `decision_trace.py` / `test_decision_trace.py`) and the final accepted implementation (which merged `decision_backlog_trace_summary.py` / `test_decision_backlog_trace_summary.py`). The runtime files are correct and must not change. The correction prevents future agents from resurrecting the obsolete `decision_trace.py` names.

## Background

PR 0115 was merged as GitHub PR 122. The runtime implementation is accepted and validated. The precommit-review.yml correctly records the actual runtime file names. However, the PR 0115 PLAN.md still references the proposed names `decision_trace.py` and `test_decision_trace.py` in multiple locations. This creates a risk that future agents or reviewers will interpret the PLAN.md as authoritative and attempt to create the `decision_trace.py` module, conflicting with the existing `decision_backlog_trace_summary.py`.

## Exact PR 0115 file-shape note

| Aspect | PLAN.md (proposed) | Implementation (merged) | Drift |
|--------|-------------------|------------------------|-------|
| Module file | `services/task_intake/src/task_intake/decision_trace.py` | `services/task_intake/src/task_intake/decision_backlog_trace_summary.py` | Name mismatch — `decision_trace` vs `decision_backlog_trace_summary` |
| Test file | `services/task_intake/tests/test_decision_trace.py` | `services/task_intake/tests/test_decision_backlog_trace_summary.py` | Name mismatch — `test_decision_trace` vs `test_decision_backlog_trace_summary` |
| Server import | `from task_intake.decision_trace import ...` | `from task_intake.decision_backlog_trace_summary import DecisionTraceInput, build_decision_trace` | Import source differs |
| PLAN.md routes section | `/backlog/decision/trace` | `/backlog/decision/trace` | Route path correct — no drift |
| URL referenced in app.py | `/backlog/decision/trace` | `/backlog/decision/trace` | Route correct — no drift |
| Object shape names | `DecisionTraceInput`, `DecisionTraceItem`, etc. | `DecisionTraceInput`, `DecisionTraceItem`, etc. | Object shape names correct — no semantic drift |
| Precommit-review.yml | N/A (not yet written when PLAN.md created) | Records `decision_backlog_trace_summary.py` | Records actual names correctly |

This is a file-naming drift only. No semantic drift occurred. The route, object shapes, and behavior match the PLAN.md specification.

## Non-goals

- No runtime source changes
- No test changes
- No route changes
- No object-shape changes
- No validation behavior changes
- No ROADMAP changes
- No schema changes
- No docs/ADR changes
- No dependency changes
- No agent changes
- No editing of PR 0113 or PR 0114 artifacts
- No resurrection of `decision_trace.py` or `test_decision_trace.py` names
- No silent history rewrite

## Allowed files

| File | Action |
|------|--------|
| `.project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/PLAN.md` | NEW — this plan |
| `.project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/reviews/precommit-review.yml` | Implementation stage — repair evidence artifact |

## Forbidden files

- `services/task_intake/src/task_intake/decision_trace.py`
- `services/task_intake/tests/test_decision_trace.py`
- Any file under `services/`
- Any file under `docs/`
- Any file under `schemas/`
- Any file under `agents/`
- Any file under `.github/`
- `.project-memory/post-0100/**`
- `.project-memory/pr/0115-decision-backlog-trace-summary/**` (no edits to PR 0115 artifacts)
- `.project-memory/pr/0113-*/**`
- `.project-memory/pr/0114-*/**`
- `ROADMAP.md`
- `pyproject.toml`, `setup.cfg`, `setup.py`, `package.json`, `Makefile`

## Implementation steps for evidence note only

1. Keep this PR limited to project-memory evidence correction.
2. Record the exact file-shape drift in the PR 0116 repair artifact.
3. Confirm the merged runtime names are `decision_backlog_trace_summary.py` and `test_decision_backlog_trace_summary.py`.
4. Confirm the obsolete names `decision_trace.py` and `test_decision_trace.py` are not to be recreated.
5. Preserve the existing PR 0115 runtime behavior and route shape.
6. Do not modify PR 0115 artifacts.
7. Do not modify runtime source or tests.
8. Do not modify ROADMAP.md, docs, schemas, agents, or dependency files.

## Validation commands

```bash
git rev-parse --verify HEAD
git branch --show-current
git status --short
git diff --name-only
find .project-memory/pr/0115-decision-backlog-trace-summary -maxdepth 4 -type f | sort
find .project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction -maxdepth 4 -type f | sort 2>/dev/null || true
grep -R -n "decision_trace.py|test_decision_trace.py|decision_backlog_trace_summary.py|test_decision_backlog_trace_summary.py" .project-memory/pr/0115-decision-backlog-trace-summary .project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction 2>/dev/null || true
find .ariadne -maxdepth 5 -type f | sort 2>/dev/null || true
date -u +%Y-%m-%dT%H:%M:%SZ
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- file drift: only `.project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/reviews/precommit-review.yml` added; no other files changed
- behavior drift: no runtime behavior changes
- repair-scope drift: correction limited to documenting drift, not modifying PR 0115 artifacts
- runtime-source drift: no new files created under `services/`
- test drift: no test files changed or created
- roadmap/schema/dependency drift: none
- old-name resurrection drift: `decision_trace.py` and `test_decision_trace.py` must not exist after correction
- validation drift: fresh validation commands executed
- dirty-tree residue drift: no `.ariadne/` residue

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- correction is project-memory-only
- no runtime source changes
- no test changes
- no route changes
- no object-shape changes
- no ROADMAP/schema/doc/agent/dependency changes
- no PR 0115 artifact modifications
- no resurrection of `decision_trace.py` or `test_decision_trace.py`
- no `.ariadne/` residue after validation

## Dirty-tree expectations

The working tree will contain:
- `.project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/PLAN.md` (this plan)
- `.project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/reviews/precommit-review.yml` (to be written at implementation)

No changes to runtime files. No `.ariadne/` residue.

## Artifact write/readback requirements

The implementation precommit-review artifact must:
1. Record the exact drift statement
2. Verify actual runtime file names exist (`decision_backlog_trace_summary.py`)
3. Verify old file names do not exist (`decision_trace.py`)
4. State that the runtime shape is correct and must be preserved
5. Record fresh validation commands with exit codes
6. Read back the artifact after writing
7. Verify the artifact is listed by `find` and `test -f` exits 0

## Stop conditions

- Block if `decision_backlog_trace_summary.py` does not exist
- Block if `test_decision_backlog_trace_summary.py` does not exist
- Block if `decision_trace.py` exists
- Block if `test_decision_trace.py` exists
- Block if PR 0115 PLAN.md would be modified
- Block if any runtime source files would be changed
- Block if any test files would be changed
- Block if forbidden legacy names/examples are introduced
- Block if non-semantic placeholder strings are required
- Block if `.ariadne/` residue is left in the repo root

## Roadmap alignment

* roadmap track: project-memory correction / post-merge evidence note
* expected PR slot: PR 0116
* why this PR is next: it records a file-shape correction for the already-merged PR 0115 evidence trail without changing runtime behavior
* batching policy check: satisfied because this is narrow evidence correction work, not a new isolated runtime feature
* drift heuristic check: not triggered; no repeated UI-only runtime work is being added
* architect sign-off required: no
* architect sign-off reference if required: none
