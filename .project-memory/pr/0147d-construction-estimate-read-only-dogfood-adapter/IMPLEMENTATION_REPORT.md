# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0147D — Construction Estimate Read-Only Dogfood Adapter Implementation.

Implemented OPTION A (Strict UTF-8 CSV) reading a 12-column construction estimate
and mapping it to a PR 0147C version-1 run-profile sidecar. The adapter uses
Decimal arithmetic for all financial values, enforces source immutability via
SHA-256 before/after copy, and writes four run-owned artifacts (source copy,
normalized JSON, line items CSV, validation report). Profile_key is
`construction-estimate-v1`. No PR 0147C core files are modified. No HTTP routes,
workspace branches, new types, or execution behavior is added.

## FILES READ

All files listed in REQUIRED READS: ORCHESTRATOR_STANDARD, workflow standards,
coder.yml, ROADMAP.md, detailed roadmap, ADR 0011, README, Makefile, pyproject.toml,
docs/RUN_ARTIFACT_PROFILE.md, PLAN.md, plan-review.yml, PR 0147C PLAN.md,
IMPLEMENTATION_REPORT.md, precommit-review.yml, run_profile.py, run_persistence.py,
artifacts.py, server.py, artifact_workspace.py, test_run_profile.py, test_run_profile_api.py,
create-run-profile.py, smoke-run-profile.py, plus all actual changed files read back.

## FILES CHANGED

### Exact 10-path implementation allowlist:

1. **services/runner/src/runner/construction_estimate_adapter.py** (NEW) — Core adapter: CSV parser, validator, profile mapper, one-call entrypoint. `import csv` at call time inside `read_estimate_csv()`.
2. **services/runner/tests/test_construction_estimate_adapter.py** (NEW) — 43 tests covering schema validation, decimal parsing, line-total policy, header validation, duplicate detection, currency validation, path safety, source immutability, profile mapping.
3. **tests/fixtures/construction-estimate-sample.csv** (NEW) — Synthetic 7-line construction estimate fixture (fictional Warehouse project, no real data).
4. **scripts/create-construction-estimate-profile.py** (NEW) — CLI entrypoint with --source, --runs-root, --run-id, --create-run, --json flags.
5. **scripts/smoke-construction-estimate-profile.py** (NEW) — End-to-end dogfood smoke: 16+ assertion groups covering full lifecycle.
6. **docs/CONSTRUCTION_ESTIMATE_DOGFOOD.md** (NEW) — Documented adapter schema, CLI usage, boundaries.
7. **ROADMAP.md** (EDIT) — Added PR 0147D governance insertion section.
8. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** (EDIT) — Added PR 0147D governance insertion section.
9. **.project-memory/pr/0147d-construction-estimate-read-only-dogfood-adapter/IMPLEMENTATION_REPORT.md** (NEW) — This file.
10. `.project-memory/pr/0147d-construction-estimate-read-only-dogfood-adapter/reviews/precommit-review.yml` (NEW) — Not written by coder.

## IMPLEMENTATION DECISIONS

1. **csv import at call time**: Per PLAN.md required pattern (`import csv as _csv` inside `read_estimate_csv()`). This is unusual but explicitly required by the accepted warning.
2. **Profile constructed directly not via create_run_profile()**: The PR 0147C `create_run_profile()` hardcodes `domain-neutral-v1` as profile_key. Since run_profile.py cannot be modified, the adapter builds the profile JSON directly using `validate_profile_dict`, `compute_profile_sha256`, and atomic write — the same building blocks used internally by `create_run_profile()`. This is documented as a deviation.
3. **Decimal→float for profile API compatibility**: The PR 0147C profile validator checks `isinstance(value, (int, float))` for currency types. The adapter converts `Decimal` to `float` for these values, keeping Decimal for internal calculations.

## PLAN ALIGNMENT

| Requirement | Status |
|---|---|
| OPTION A — Strict UTF-8 CSV | Implemented |
| 12 ordered columns (exact PLAN.md header) | Implemented |
| csv import at call time | Implemented (inside read_estimate_csv) |
| Decimal arithmetic, ROUND_HALF_UP | Implemented |
| Line-total policy (authoritative if present, recalculated if absent, mismatch rejected) | Implemented |
| 19 allowed units (plus unrecognized_unit escape) | Implemented (19 including "piece") |
| Source immutability via SHA-256 before/after copy | Implemented |
| Max 1 MB, max 1000 rows | Implemented |
| Duplicate line_item_id rejection | Implemented |
| Currency validation against 16 known codes | Implemented |
| profile_key "construction-estimate-v1" | Implemented |
| Schema version "1" unchanged | Implemented |
| 9 neutral facts (text, number, currency types only) | Implemented |
| 3 artifact groups (original, normalized, validation) | Implemented |
| 4 artifact descriptors (source, normalized, line items, validation) | Implemented |
| Only run-relative: references | Implemented |
| No new profile types, roles, or reference forms | Verified |
| No core PR 0147C files modified | Verified |
| No server.py/artifact_workspace.py modification | Verified |
| No HTTP mutation | Verified |
| No execution boundaries | Verified (grep checks) |
| docs/CONSTRUCTION_ESTIMATE_DOGFOOD.md | Implemented |
| smoke passes | Verified |
| PR 0148 numbering unchanged | Verified |

## DEVIATIONS FROM PLAN

1. **Profile constructed directly** (not via `create_run_profile()`): The PR 0147C `create_run_profile()` hardcodes `profile_key: domain-neutral-v1`. To use `construction-estimate-v1`, the adapter builds the profile JSON directly using the same building blocks (`validate_profile_dict`, `compute_profile_sha256`, atomic write). All validation logic is reused from run_profile.py. No run_profile.py behavior is modified.

2. **Decimal→float for currency values**: The PR 0147C profile validator checks `isinstance(value, (int, float))`. The adapter converts `Decimal` to `float` for currency fact values to maintain compatibility without modifying run_profile.py.

3. **19 units includes "piece"**: The PLAN.md lists 18 units but plan-review confirms "19 allowed units". "piece" was added as the 19th to match the confirmed contract.

## VALIDATION RUN

### 1. Python compile check
- All files compile

### 2. Adapter unit tests
- **43 passed**

### 3. Existing profile tests
- **39 passed**

### 4. Existing API tests
- **8 passed**

### 5. Existing workspace tests
- **310 passed**

### 6. Full regression
- **701 passed** (43 adapter + 39 profile + 8 API + 310 workspace + 301 other)

### 7. Construction dogfood smoke
- **PASSED** — "CONSTRUCTION ESTIMATE DOGFOOD SMOKE PASSED"

### 8. Source non-mutation grep
- No source-write patterns in CLI

### 9. Construction workspace grep
- No matches in artifact_workspace.py

### 10. Planning locks
- PLAN.md and plan-review.yml unchanged

### 11. Core files diff
- run_profile.py, server.py, artifact_workspace.py, etc. — all unchanged

## BOUNDARY CONFIRMATIONS

- Exact 10-path scope followed
- No PR 0147C core files modified
- No server.py, artifact_workspace.py, local_operator.py changes
- No new dependencies
- No HTTP mutation
- No execution boundaries violated
- Source CSV unchanged (verified by smoke)
- PR 0148 numbering preserved
- All existing tests pass (701)

## NON-GOALS PRESERVED

- No XLSX, PDF, OCR, BIM, IFC
- No quantity takeoff or drawing measurement
- No procurement, scheduling, WBS, Gantt
- No Artifact Registry or acceptance state
- No Mermaid or Visual Gate
- No agent, provider, shell, git, gh, Docker execution

## RISKS OR WARNINGS

1. **Direct profile construction**: The adapter builds profile JSON directly instead of calling `create_run_profile()`. The same validation and hashing code is reused, but the atomic write logic is duplicated. If run_profile.py's write logic changes, the adapter may become inconsistent.

2. **csv import at call time**: Per PLAN.md requirement, `csv` is imported inside `read_estimate_csv()` rather than at module level. This is an unusual pattern that may mask import errors until the function is first called.

3. **Decimal→float conversion**: Currency fact values use `float` instead of `Decimal` for profile API compatibility. For large values (>10^15), float precision may lose sub-unit accuracy. Construction estimates rarely reach these magnitudes.

## NEXT REVIEWER FOCUS

1. Verify that source immutability is enforced: the smoke proves source SHA-256 before and after matches, and the source file is never modified by the adapter.
2. Verify that no PR 0147C core files were modified (`git diff -- services/runner/src/runner/run_profile.py` should be empty).
3. Verify that all 701 existing tests pass.
4. Verify that the profile_key in the generated run-profile.json is `construction-estimate-v1` (not `domain-neutral-v1`).
5. Verify PR 0148 numbering is preserved in both roadmap files.
