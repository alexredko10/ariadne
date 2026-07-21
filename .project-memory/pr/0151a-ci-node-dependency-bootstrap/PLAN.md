# PR 0151A — CI Node Dependency Bootstrap Correction

## ROOT-CAUSE ANALYSIS

### Observed CI failure

GitHub Actions run after PR 0151 merge: **3141 passed, 2 skipped, 7 failed**.

### Direct failures (3)

1. `test_mermaid_renderer.py::TestMermaidRenderer::test_valid_requirement_diagram_produces_svg`
2. `test_mermaid_renderer.py::TestMermaidRenderer::test_valid_state_diagram_produces_svg`
3. `test_mermaid_renderer.py::TestMermaidRenderer::test_valid_sequence_diagram_produces_svg`

All three fail with:

```
Error: Cannot find module 'jsdom'
Require stack:
- scripts/mermaid-render.cjs
```

**Root cause:** The CI workflow (`ci.yml`) never installs the Node.js dependencies declared in `package.json`. On a clean GitHub-hosted runner, `node_modules/` does not exist. `scripts/mermaid-render.cjs` calls `require('jsdom')` at the top of the script, and Node.js cannot resolve it because no `npm install` or `npm ci` was ever run.

### Downstream cascade failures (4)

4. `test_visual_gate_readiness.py::TestVisualGateReadiness::test_all_required_diagrams_valid_ready`
5. `test_visual_gate_readiness.py::TestVisualGateReadiness::test_renderer_unavailable_state`
6. `test_visual_gate_readiness.py::TestVisualGateReadiness::test_render_failure_state`
7. `test_visual_gate_readiness_api.py::TestVisualGateReadinessAPI::test_ready_state_returns_is_ready_true`

Failures 4 and 7 expect `is_ready=True` but receive `is_ready=False` with reason code `renderer_unavailable`. Failures 5 and 6 test renderer-unavailable and render-failure states — these are fail-closed by design: when the renderer cannot produce SVG, readiness returns `not_ready`. The cascade is expected and correct given the primary root cause.

**The shared root cause is the single CI bootstrap gap. There is no implementation defect.**

## EVIDENCE SNAPSHOT

1. HEAD: 52683afbf6a7bb95b392875ae3002d3c3be3cad3
2. Branch: 0151a-ci-node-dependency-bootstrap
3. Dirty tree: clean
4. Cached diff: empty
5. PR 0151 merged: present — "PR 0151 — Visual Gate Readiness Checker (#181)" at HEAD
6. package.json devDependencies declare: mermaid ^11.0.0, jsdom ^29.0.0
7. package-lock.json locks both trees (lockfileVersion 3)
8. scripts/mermaid-render.cjs uses require('jsdom') and dynamic import('mermaid')
9. ci.yml has no Node setup or npm install step
10. No PR 0151A implementation exists

## ENGINE REQUIREMENTS

From `package-lock.json`:

- jsdom v29.1.1 transitively depends on `@asamuzakjp/css-color` which requires `node ^20.19.0 || ^22.12.0 || >=24.0.0`.
- The minimum supported Node for the locked dependency tree is **20.19.0**.

**Selected Node version: 22** — widely available on `ubuntu-latest` GitHub runners, satisfies all engine constraints, and is the current LTS release line. Node 20 would also work but 22 is the safer forward-looking choice.

## PROPOSED WORKFLOW EDIT

### Exact edit to `.github/workflows/ci.yml`

Insert after the `actions/checkout@v4` step and before `actions/setup-python@v5`:

```yaml
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: package-lock.json

      - name: Install Node dependencies
        run: npm ci --ignore-scripts
```

The full resulting workflow:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  smoke:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: package-lock.json

      - name: Install Node dependencies
        run: npm ci --ignore-scripts

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install test tooling
        run: |
          python -m pip install --upgrade pip
          python -m pip install pytest

      - name: Run tests
        run: python -m pytest -q

      - name: Compile Python files
        run: python -m compileall services packages
```

### Why `npm ci` not `npm install`

`npm ci` is the correct command for CI environments:
- Installs from `package-lock.json` exactly — no version negotiation.
- Fails if `package-lock.json` is out of sync with `package.json`.
- Faster than `npm install` (skips dependency resolution).
- Produces deterministic `node_modules/`.

### Why `--ignore-scripts`

Mermaid v11 includes `postinstall` scripts that may attempt to download platform-specific binaries or run build steps. `--ignore-scripts` skips these, which is safe because:
- The renderer uses pure JS (mermaid render logic + jsdom virtual DOM).
- No native addons, binary downloads, or platform-specific code is required for rendering.
- The existing local install (PR 0150) confirmed that `--ignore-scripts` is safe.

## IMPLEMENTATION ALLOWLIST

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | EDIT — add two steps (setup-node, npm ci) |
| `.project-memory/pr/0151a-ci-node-dependency-bootstrap/IMPLEMENTATION_REPORT.md` | NEW — coder writes per contract |
| `.project-memory/pr/0151a-ci-node-dependency-bootstrap/reviews/precommit-review.yml` | PREEXISTING — written only by precommit-review |

Total: 1 workflow file edited, 1 implementation report written, 1 review artifact created by reviewer.

## FORBIDDEN FILES

The implementation must NOT modify:

- `package.json` — dependency declarations are correct.
- `package-lock.json` — lockfile is correct and committed.
- `scripts/mermaid-render.cjs` — render script is correct.
- All Python source files.
- All test files.
- All fixture files.
- PR 0150 and PR 0151 artifacts, plans, and reviews.
- `ROADMAP.md` and all roadmap artifacts.
- Dockerfiles, runtime images, Makefile.
- GitHub issue templates or other workflow files.

## VALIDATION PLAN

### 1. Workflow diff inspection

```bash
git diff .github/workflows/ci.yml
```

Expected: only the two new steps (setup-node, npm ci) added. No other changes. If not met: block.

### 2. Workflow YAML syntax

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"
```

Expected: prints "YAML OK". If not met: block.

### 3. Install Node dependencies locally (simulate CI)

```bash
npm ci --ignore-scripts
```

Expected: exit code 0. If not met: block.

### 4. Verify both modules resolve

```bash
node -e "require.resolve('jsdom'); require.resolve('mermaid'); console.log('NODE DEPENDENCIES RESOLVED')"
```

Expected: prints "NODE DEPENDENCIES RESOLVED". If not met: block.

### 5. Focused renderer tests

```bash
python -m pytest services/runner/tests/test_mermaid_renderer.py -q
```

Expected: zero failures (all previously failing three SVG-producing tests pass). 12 passed, 1 skipped. If not met: block.

### 6. Focused readiness tests

```bash
python -m pytest services/runner/tests/test_visual_gate_readiness.py services/task_intake/tests/test_visual_gate_readiness_api.py -q
```

Expected: zero failures (all four previously failing cascade tests pass). If not met: block.

### 7. Complete test suite

```bash
python -m pytest -q
```

Expected: zero failures. All seven previously failing tests pass. If not met: block.

### 8. Python compile

```bash
python -m compileall services packages
```

Expected: exit code 0. If not met: block.

### 9. Whitespace check

```bash
git diff --check
```

Expected: clean. If not met: block.

### 10. Staged diff check

```bash
git diff --cached --name-only
```

Expected: empty (no staged changes). If not met: block.

### 11. Residue check

```bash
git status --short
```

Expected: only the approved files appear modified. No untracked residue. If not met: block.

### 12. Manifest stability

```bash
git diff --name-only -- package.json package-lock.json
```

Expected: empty. If not met: block.

### 13. No product code changed

```bash
git diff --name-only -- services/ scripts/ tests/
```

Expected: empty. If not met: block.

### 14. No failure waivers

```bash
grep -n "continue-on-error\|if:.*false\|fail-fast" .github/workflows/ci.yml
```

Expected: exit code 1 (no matches). If not met: block.

## CLEAN-RUNNER ACCEPTANCE

After merge, verify by inspecting the GitHub Actions CI run for the merged commit on `main`:

- Workflow triggered on push.
- All steps execute in order.
- `npm ci --ignore-scripts` completes without error.
- All Python tests pass (zero failures).
- `compileall` succeeds.

A passing CI on a clean GitHub-hosted runner is the conclusive evidence. The validation commands in this plan simulate that environment locally using the same commands.

## ROLLBACK BOUNDARY

If the workflow change causes CI to fail (e.g., Node version incompatibility, npm registry timeout, or unexpected package resolution), the rollback is to revert `.github/workflows/ci.yml` to its pre-PR-0151A state. No product code is affected — the rollback is a single-file revert.

## RISKS AND MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `npm ci` fails because package-lock.json is out of date | Low | CI blocked | `npm ci` validates lockfile against package.json; if inconsistent, re-run `npm install` locally and commit updated lockfile |
| Node 22 not available on ubuntu-latest runner | Very low | CI blocked | `actions/setup-node@v4` installs the requested version. If ubuntu-latest image lacks it, setup-node downloads it |
| npm registry timeout | Low | CI blocked | Retry. `npm ci` is idempotent. No runtime network dependency after install |
| `--ignore-scripts` breaks mermaid rendering | Very low | Tests fail | PR 0150 confirmed offline rendering works with `--ignore-scripts`. JSDOM + mermaid pure JS render has no native deps |
| `node_modules/` size causes runner disk pressure | Low | CI slow | `npm ci --ignore-scripts` installs ~176MB. GitHub ubuntu-latest has 14GB+ free. Caching reduces install time on re-runs |

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist (ci.yml, IMPLEMENTATION_REPORT.md, precommit-review.yml).
2. PLAN.md or plan-review.yml changes during implementation.
3. package.json, package-lock.json, or scripts/mermaid-render.cjs modified.
4. Any Python source, test, or fixture file modified.
5. Any PR 0150 or PR 0151 source, test, fixture, or script modified.
6. Any product behavior, renderer, sanitizer, readiness, or approval semantics changed.
7. `npm install` used instead of `npm ci`.
8. `--ignore-scripts` omitted.
9. Node version not specified (uses runner default).
10. Failure waivers (`continue-on-error`, conditional skip, mock fallback) added.
11. `node_modules/` committed or staged.
12. npm cache step omitted.
13. ci.yml changes beyond the two required steps.
14. Any validation command fails.
15. Repository residue exists after validation.
16. Missing or inaccurate IMPLEMENTATION_REPORT.md.
17. Workflow YAML invalid.

## NO-DRIFT CHECK

Require affirmative confirmation:

1. Correct branch: `0151a-ci-node-dependency-bootstrap`.
2. Correct base: PR 0151 merged at HEAD.
3. Exact allowlist: only ci.yml edited, plus IMPLEMENTATION_REPORT.md and precommit-review.yml.
4. No product code changed (services/, scripts/, tests/, fixtures/ all untouched).
5. No dependency manifests changed (package.json, package-lock.json untouched).
6. No render script or renderer modified.
7. Root cause is exclusively CI bootstrap (not implementation defect).
8. Three primary failures are renderer tests requiring jsdom.
9. Four cascade failures are downstream fail-closed readiness/API results.
10. Proposed fix: add setup-node@v4 + npm ci --ignore-scripts to ci.yml.
11. Node version: 22 (satisfies locked engine >=20.19.0).
12. Install command: `npm ci --ignore-scripts`.
13. Validation includes 14 commands covering syntax, install, module resolution, focused tests, full suite, compile, whitespace, residue.
14. Zero test failures after correction.
15. No failure waivers, conditional bypasses, or mock fallbacks added.
16. node_modules not committed or staged.
17. Clean-runner acceptance: CI passes on GitHub-hosted runner after merge.
18. Rollback boundary: single-file revert of ci.yml.
19. Physical evidence precedence: file contents, test results, diffs, and validation evidence override agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The locked plan cannot be followed (scope, allowlist).
2. Any file outside the approved allowlist requires modification.
3. `npm ci --ignore-scripts` fails in the local environment.
4. Module resolution (`require.resolve`) fails for jsdom or mermaid after install.
5. Any test fails under the corrected CI environment.
6. Workflow YAML is invalid.
7. GitHub Actions runner environment cannot be validated locally.
8. Architect authority is required beyond documented scope.

## SMOKE MARKER

After all validation commands pass, the deterministic marker is:

```
CI NODE DEPENDENCY BOOTSTRAP PASSED
```

This marker confirms that the CI bootstrap correction works locally. The GitHub-hosted runner CI run on the merged commit is the final acceptance.
