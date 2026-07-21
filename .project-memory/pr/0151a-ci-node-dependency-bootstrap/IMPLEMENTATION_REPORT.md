# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0151A — CI Node Dependency Bootstrap Correction.

Added two steps to `.github/workflows/ci.yml`: `actions/setup-node@v4` (Node 22
with npm caching) and `npm ci --ignore-scripts`. No product code, tests,
fixtures, dependency manifests, or render scripts were modified.

## FILES CHANGED

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | EDIT — added setup-node@v4 and npm ci steps |
| `.project-memory/pr/0151a-ci-node-dependency-bootstrap/IMPLEMENTATION_REPORT.md` | NEW |

## IMPLEMENTATION DECISIONS

- **Node version**: 22 (satisfies lockfile engine constraint >=20.19.0, current LTS).
- **Install command**: `npm ci --ignore-scripts` (deterministic, safe for pure JS rendering).
- **Cache**: `actions/setup-node@v4` with `cache: "npm"` and `cache-dependency-path: package-lock.json`.
- **No product changes**: Root cause is exclusively CI bootstrap gap, not an implementation defect.

## PLAN ALIGNMENT

Every PLAN.md requirement is met:
- Two exact workflow steps added (setup-node@v4, npm ci --ignore-scripts).
- Node 22 selected per lockfile engine requirement.
- --ignore-scripts used (confirmed safe by PR 0150 validation).
- No package.json, package-lock.json, or scripts/mermaid-render.cjs modified.
- No Python source, test, or fixture files modified.
- No PR 0150 or PR 0151 artifacts modified.

## DEVIATIONS FROM PLAN

None.

## VALIDATION RUN

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | Workflow diff inspection | 0 | Only two new steps added |
| 2 | YAML syntax check | 0 | YAML OK |
| 3 | `npm ci --ignore-scripts` | 0 | 150 packages, 0 vulnerabilities |
| 4 | `require.resolve('jsdom'); require.resolve('mermaid')` | 0 | NODE DEPENDENCIES RESOLVED |
| 5 | Focused renderer tests | 0 | 12 passed, 1 skipped |
| 6 | Readiness + API tests | 0 | 24 passed, 1 skipped |
| 7 | Full test suite | 0 | 3148 passed, 2 skipped |
| 8 | `python3 -m compileall services packages` | 0 | All compiled without error |
| 9 | `git diff --check` | 0 | Clean |
| 10 | `git diff --cached --name-only` | 0 | Empty |
| 11 | Residue check | 0 | Only ci.yml + PR directory |
| 12 | Manifest stability | 0 | No changes to package.json or package-lock.json |
| 13 | Product code unchanged | 0 | No changes under services/, scripts/, tests/ |
| 14 | No failure waivers | 1 | No continue-on-error, fail-fast, or if: false |

## SEVEN FAILURES RESOLVED

Three primary renderer failures (require('jsdom') → Cannot find module) and
four cascade readiness/API failures (renderer_unavailable → is_ready=False)
all pass with zero failures after npm ci.

## MARKER

```
CI NODE DEPENDENCY BOOTSTRAP PASSED
```

## BOUNDARY CONFIRMATIONS

- Confirm: no forbidden files changed (package.json, package-lock.json, scripts/mermaid-render.cjs, all Python/test/fixture files untouched).
- Confirm: no review artifact written by coder.
- Confirm: PLAN.md not modified.
- Confirm: plan-review.yml not modified.
- Confirm: ROADMAP.md not modified.
- Confirm: only PLAN.md-approved files changed (ci.yml, IMPLEMENTATION_REPORT.md).
- Confirm: no git mutation commands run.
- Confirm: no Docker commands run.
- Confirm: no node_modules staged or committed.
- Confirm: no failure waivers added.

## NON-GOALS PRESERVED

- No PR 0152 scope consumed.
- No product behavior, renderer, sanitizer, readiness, or approval semantics changed.
- No npm install (used npm ci per plan).
- No Node version omitted.

## RISKS OR WARNINGS

None. The change is a two-step CI workflow addition with no product impact.
Rollback is a single-file revert of ci.yml.

## NEXT REVIEWER FOCUS

Precommit-review should verify:
1. The unapproved display-test file from PR 0151 B001 is still deleted.
2. Only ci.yml and IMPLEMENTATION_REPORT.md are in the dirty tree.
3. All 14 validation commands pass.
4. No product code, dependency manifests, or render scripts modified.
