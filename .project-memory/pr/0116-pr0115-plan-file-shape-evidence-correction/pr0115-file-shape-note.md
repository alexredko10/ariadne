# PR 0115 File-Shape Post-Merge Note

## Scope

This is a project-memory evidence note only. It records the file-shape history
of PR 0115 (Decision-to-Backlog Trace Summary / Read-Only Evidence Map) for
future agents and reviewers.

## History

PR 0115 PLAN.md originally referenced the following proposed file names:

- `services/task_intake/src/task_intake/decision_trace.py`
- `services/task_intake/tests/test_decision_trace.py`

These names appeared in the PLAN.md "Proposed Files" section, the "New module"
section, the validation commands, and the PLAN DRIFT GATE file-drift check.

## Final Accepted File Shape

PR 0115 final merged implementation uses:

- `services/task_intake/src/task_intake/decision_backlog_trace_summary.py`
- `services/task_intake/tests/test_decision_backlog_trace_summary.py`

The route path `/backlog/decision/trace` and all object shape names
(`DecisionTraceInput`, `DecisionTraceItem`, `DecisionTraceSummary`,
`DecisionTraceResult`, `DecisionTraceStatus`, `build_decision_trace()`) are
correct and match the PLAN.md specification. Only the file names changed.

## Authority

The final accepted names are authoritative for future work. Any future PR that
references the trace summary module must use:

- `services/task_intake/src/task_intake/decision_backlog_trace_summary.py`
- `services/task_intake/tests/test_decision_backlog_trace_summary.py`

## Obsolete-Name Rule

Future agents must not create, restore, import, or test against:

- `services/task_intake/src/task_intake/decision_trace.py`
- `services/task_intake/tests/test_decision_trace.py`

These names are historical only. They appear in the PR 0115 PLAN.md as proposed
names but were corrected during implementation. Any attempt to create or import
these files would conflict with the existing `decision_backlog_trace_summary.py`
module.

## Runtime No-Change Statement

PR 0116 does not change runtime source, runtime tests, app routes, object
shape, validation behavior, dependencies, docs, schemas, agents, or ROADMAP.

## PR 0115 No-Rewrite Statement

PR 0116 does not modify `.project-memory/pr/0115-decision-backlog-trace-summary/**`.

## Evidence

### Final files present

```
services/task_intake/src/task_intake/decision_backlog_trace_summary.py  — EXISTS
services/task_intake/tests/test_decision_backlog_trace_summary.py       — EXISTS
```

### Obsolete files absent

```
services/task_intake/src/task_intake/decision_trace.py  — MISSING
services/task_intake/tests/test_decision_trace.py       — MISSING
```

### `.ariadne` residue absent

```
find .ariadne -maxdepth 5 -type f | sort 2>/dev/null || true
→ No such file or directory
```

### Dirty tree limited to PR 0116 project-memory files

```
git status --short
→ Only .project-memory/pr/0116-pr0115-plan-file-shape-evidence-correction/ files
```

### Git tree confirms final names

```
git ls-tree -r --name-only HEAD | grep -E 'decision_backlog_trace_summary|decision_trace'
→ services/task_intake/src/task_intake/decision_backlog_trace_summary.py
→ services/task_intake/tests/test_decision_backlog_trace_summary.py
```

No `decision_trace.py` or `test_decision_trace.py` files exist in the committed
tree.
