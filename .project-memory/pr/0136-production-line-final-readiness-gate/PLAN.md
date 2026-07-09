# PR 0136 — Production Line Final Readiness Gate Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Production Line — Stage 2/3 Closed Loop (final gate) |
| **Slot** | PR 0136 (post-0135 report) |
| **Why this PR is next** | PR 0131-0135 established the full production-line evidence chain: dogfood proof (0131), execution result persistence (0132), test residue isolation (0133), commit payload cleanliness gate (0134), and local run report artifact (0135). PR 0136 adds the final readiness gate that evaluates whether a local run has all required evidence present and internally consistent. This closes the production-line hardening stream. |
| **Batching policy** | Single-purpose: readiness evaluation from existing persisted evidence. No feature expansion. |
| **Drift heuristic** | Does not start a frozen capability stream. Does not add UI, dashboard, frontend, Decision Core, Context Warehouse, eval harness, faithfulness audit, or product iteration features. The gate evaluates locally persisted data; it does not create new evidence or change existing runtime behavior. |
| **Architect note** | This is **executable hardening**, not docs-only. The gate is a deterministic function with an injectable provider pattern, testable with temporary roots and fake data. It validates the evidence chain produced by PR 0131-0135 but does not modify those systems. |

## Summary

After PR 0131-0136 (planned), the runner has six evidence layers:

1. **Dogfood proof** (PR 0131): YAML artifact validating runtime execution.
2. **Execution result persistence** (PR 0132): `run.json` + `manifest.json`.
3. **Test residue isolation** (PR 0133): `conftest.py` autouse fixture.
4. **Commit payload cleanliness** (PR 0134): `_check_payload_cleanliness()`.
5. **Run report artifact** (PR 0135): `run-report.txt`.
6. **Production Line Readiness Gate** (PR 0136, this PR): evaluates 1-5.

PR 0136 adds a deterministic `_evaluate_readiness()` function that
inspects persisted evidence and returns a structured readiness result.
The gate answers the question: "Does this local run have enough evidence
to be considered production-line ready?"

The gate does not run new git checks, create new artifacts, or modify
existing behavior.  It consumes existing data and returns a verdict.

## Readiness Criteria

1. `run.json` must exist when evaluating a completed persisted run.
2. `manifest.json` must exist when evaluating a completed persisted run.
3. `run-report.txt` must exist when PR 0135 report generation is expected.
4. `run_id` must be present.
5. `status` must be present.
6. `pipeline_status` must be present.
7. `pipeline_final_action` must be present.
8. `git_boundary_status` must be present.
9. `reason_codes` must be present.
10. `execution_attempted` must be present.
11. If `execution_attempted` is true, `execution_results` must be non-empty
    unless the run explicitly records a blocked pre-execution state.
12. If `execution_results` are present, each result must include
    `operation` and `exit_code`.
13. If `gh_pr_create` succeeded, PR URL evidence must be preserved when
    available.
14. Payload cleanliness result must be available when PR 0134 gate was
    evaluated.
15. Payload cleanliness must block forbidden tracked files, staged
    residue, unknown untracked files, and cached diff drift.
16. Known generated residue may be present only as untracked non-payload.
17. Dogfood proof path must be included when evaluating dogfood-style
    runs.
18. `run-report.txt` must not replace `run.json`.
19. `run-report.txt` must not replace `manifest.json`.
20. `run-report.txt` must not rewrite dogfood proof.
21. Git Boundary authority must remain the only approved side-effect
    authority.

## Readiness Result

The gate produces a structured result:

```python
@dataclasses.dataclass(frozen=True)
class ProductionLineReadinessResult:
    ready: bool
    reason_codes: tuple[str, ...]
    run_id: Optional[str]
    run_json_path: Optional[str]
    manifest_path: Optional[str]
    report_path: Optional[str]
    dogfood_proof_path: Optional[str]
    evidence_paths: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    warnings: tuple[str, ...]
```

### Reason Codes

| Code | Condition |
|------|-----------|
| `readiness_missing_run_json` | `run.json` does not exist at expected path |
| `readiness_missing_manifest` | `manifest.json` does not exist at expected path |
| `readiness_missing_run_report` | `run-report.txt` does not exist when expected |
| `readiness_missing_execution_results` | `execution_attempted` is true but `execution_results` is empty and run is not explicitly pre-execution blocked |
| `readiness_missing_payload_cleanliness` | Payload cleanliness data not available when gate was evaluated |
| `readiness_payload_not_clean` | Payload cleanliness result was not clean |
| `readiness_missing_git_boundary_status` | `git_boundary_status` is absent from run record |
| `readiness_missing_dogfood_proof` | Dogfood proof path is expected but file does not exist |

## Scope

### Implementation Files

| File | Changes | Justification |
|------|---------|---------------|
| `services/runner/src/runner/ariadne_task_cli.py` | Add `_evaluate_readiness()` function and `ProductionLineReadinessResult` dataclass. Add injectable `readiness_fn` parameter to `run_ariadne_task()`. | Evidence: `ariadne_task_cli.py` already contains `AriadneTaskCliResult`, `PayloadCleanlinessResult`, and all orchestration. The readiness gate evaluates the same result structure. Adding the function here keeps the evaluation with the data it evaluates. |
| `services/runner/tests/test_ariadne_task_cli.py` | Add 15+ tests for readiness evaluation. | Evidence: Primary test file for `ariadne_task_cli.py` functions. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/src/runner/run_persistence.py` | Evidence: Readiness evaluates persisted data via `load_run_record()` but does not change persistence logic. The evaluation function reads from disk — it does not modify persistence structures. |
| `services/runner/src/runner/git_boundary.py` | Evidence: Readiness consumes `git_boundary_status` from the result, not from `git_boundary.py` directly. No Git Boundary result shape change needed. |
| `services/runner/tests/test_run_persistence.py` | Evidence: No `run_persistence.py` changes. |
| `services/runner/tests/test_git_boundary.py` | Evidence: No `git_boundary.py` changes. |
| `services/runner/tests/conftest.py` | Evidence: Readiness tests use temporary roots, not real repo. No fixture changes needed. |

### Not Modified

- `ROADMAP.md` — not modified
- `docs/` — not modified
- `agents/` — not modified
- `schemas/` — not modified
- `pyproject.toml` — not modified
- `.gitignore` — not modified
- `.project-memory/pr/0131-*` — not modified
- `.project-memory/pr/0132-*` — not modified
- `.project-memory/pr/0133-*` — not modified
- `.project-memory/pr/0134-*` — not modified
- `.project-memory/pr/0135-*` — not modified
- `services/runner/src/runner/run_persistence.py` — not modified
- `services/runner/src/runner/git_boundary.py` — not modified

## Design

### 1. Readiness Evaluation Function

The function evaluates existing persisted data.  It does not run git
commands, create files, or modify state.

```python
def _evaluate_readiness(
    run_json_path: str,
    manifest_path: str,
    report_path: Optional[str] = None,
    dogfood_proof_path: Optional[str] = None,
    payload_cleanliness: Optional[PayloadCleanlinessResult] = None,
) -> ProductionLineReadinessResult:
    """Evaluate production-line readiness from persisted evidence.

    Parameters
    ----------
    run_json_path:
        Path to run.json.
    manifest_path:
        Path to manifest.json.
    report_path:
        Path to run-report.txt (optional).
    dogfood_proof_path:
        Path to dogfood-proof.yml (optional).
    payload_cleanliness:
        Payload cleanliness result from PR 0134 gate (optional).

    Returns
    -------
    ProductionLineReadinessResult
        Structured readiness result.
    """
    codes: list[str] = []
    evidence_paths: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    run_id: Optional[str] = None
    run_json: Optional[str] = run_json_path if os.path.exists(run_json_path) else None
    manifest: Optional[str] = manifest_path if os.path.exists(manifest_path) else None
    report: Optional[str] = report_path if report_path and os.path.exists(report_path) else None

    # 1. Check run.json
    if not run_json:
        codes.append("readiness_missing_run_json")
        missing.append("run.json")
    else:
        evidence_paths.append(run_json_path)
        # Read and parse run.json for evidence checks
        try:
            with open(run_json_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)
            run_id = run_data.get("run_id")
            status = run_data.get("status")
            pipeline_status = run_data.get("pipeline_status")
            pipeline_final_action = run_data.get("pipeline_final_action")
            git_boundary_status = run_data.get("git_boundary_status")
            reason_codes = run_data.get("reason_codes", [])
            execution_attempted = run_data.get("execution_attempted", False)
            execution_results = run_data.get("execution_results_summary", [])

            if not status:
                codes.append("readiness_missing_status")
                missing.append("status")
            if not pipeline_status:
                codes.append("readiness_missing_pipeline_status")
                missing.append("pipeline_status")
            if not pipeline_final_action:
                codes.append("readiness_missing_pipeline_final_action")
                missing.append("pipeline_final_action")
            if not git_boundary_status:
                codes.append("readiness_missing_git_boundary_status")
                missing.append("git_boundary_status")
            if not reason_codes:
                codes.append("readiness_missing_reason_codes")
                missing.append("reason_codes")
            if execution_attempted and not execution_results:
                # Check if this is a pre-execution blocked run
                is_pre_exec_blocked = (
                    "dirty_tree_out_of_scope" in reason_codes
                    or "pipeline_stopped" in reason_codes
                    or "pipeline_failed" in reason_codes
                    or "pipeline_not_eligible" in reason_codes
                )
                if not is_pre_exec_blocked:
                    codes.append("readiness_missing_execution_results")
                    missing.append("execution_results")
        except (OSError, json.JSONDecodeError):
            codes.append("readiness_missing_run_json")
            missing.append("run.json (unreadable)")

    # 2. Check manifest.json
    if not manifest:
        codes.append("readiness_missing_manifest")
        missing.append("manifest.json")
    else:
        evidence_paths.append(manifest_path)

    # 3. Check run-report.txt
    if report_path and not report:
        codes.append("readiness_missing_run_report")
        missing.append("run-report.txt")
    elif report:
        evidence_paths.append(report_path)

    # 4. Check dogfood proof
    if dogfood_proof_path:
        if os.path.exists(dogfood_proof_path):
            evidence_paths.append(dogfood_proof_path)
        else:
            codes.append("readiness_missing_dogfood_proof")
            missing.append(dogfood_proof_path)

    # 5. Check payload cleanliness
    if payload_cleanliness is not None:
        if not payload_cleanliness.clean:
            codes.append("readiness_payload_not_clean")
            codes.extend(
                rc for rc in payload_cleanliness.reason_codes
                if rc not in codes
            )
    else:
        warnings.append("payload_cleanliness: not evaluated")

    ready = len(codes) == 0

    return ProductionLineReadinessResult(
        ready=ready,
        reason_codes=tuple(codes),
        run_id=run_id,
        run_json_path=run_json_path if run_json else None,
        manifest_path=manifest_path if manifest else None,
        report_path=report_path if report else None,
        dogfood_proof_path=dogfood_proof_path if dogfood_proof_path and os.path.exists(dogfood_proof_path) else None,
        evidence_paths=tuple(evidence_paths),
        missing_evidence=tuple(missing),
        warnings=tuple(warnings),
    )
```

### 2. Injectable Provider Pattern

Like other boundary functions, readiness evaluation supports an
injectable provider:

```python
readiness_fn: Optional[Callable] = None,
```

Tests inject a fake provider that returns controlled
`ProductionLineReadinessResult` values.

### 3. Integration

The readiness gate is a standalone function, not integrated into the
`run_ariadne_task()` execution flow (which would change runtime
behavior).  It is available for:

- **CLI invocation**: A future `ariadne readiness` subcommand could
  call it on an existing run directory.
- **Run report inclusion**: The PR 0135 `_write_run_report()` could
  append readiness outcome if data is available.
- **Review support**: A reviewer can inspect the readiness result
  alongside the run report.

This plan does not mandate a specific integration point; the gate
function itself is the deliverable.  Tests prove the function works
correctly with fake and real persisted data.

### 4. Pre-Execution Blocked Run Handling

When `execution_attempted` is true but `execution_results` is empty,
the gate checks whether the run `reason_codes` indicate a pre-execution
blocked state (e.g., `dirty_tree_out_of_scope`, `pipeline_stopped`,
`pipeline_failed`, `pipeline_not_eligible`).  If blocked, the gate
does not require `execution_results`.  This prevents false negatives
for runs that were blocked before reaching git boundary execution.

### 5. No Changes to Previous Artifacts

The readiness gate does not:
- Modify `run.json`, `manifest.json`, or `run-report.txt`.
- Rewrite dogfood proof.
- Create new files at evaluation time.
- Change Git Boundary authority.
- Weaken dirty-tree checks.

## Tests

### 1. Complete run with all evidence is ready

Create a temporary run directory with `run.json`, `manifest.json`,
`run-report.txt`, and dogfood proof.  Provide a clean
`PayloadCleanlinessResult`.

Assert `ready=True`, no blocker reason codes.

### 2. Missing run.json blocks readiness

Create directory without `run.json`.

Assert `ready=False`, `readiness_missing_run_json` in reason_codes.

### 3. Missing manifest blocks readiness

Create directory with `run.json` but without `manifest.json`.

Assert `ready=False`, `readiness_missing_manifest` in reason_codes.

### 4. Missing run-report blocks when report is expected

Create directory with `run.json` and `manifest.json` but without
`run-report.txt`.  Pass a `report_path` parameter.

Assert `ready=False`, `readiness_missing_run_report` in reason_codes.

### 5. Execution attempted with empty results blocks (non-blocked)

Create a `run.json` with `execution_attempted=true` and empty
`execution_results_summary`, with no pre-execution block reason codes.

Assert `ready=False`, `readiness_missing_execution_results` in
reason_codes.

### 6. Pre-execution blocked run with empty results does not block

Create `run.json` with `execution_attempted=true`, empty
`execution_results_summary`, and `reason_codes` containing
`dirty_tree_out_of_scope`.

Assert `ready=True` (no missing execution results error).

### 7. Failed execution with partial results produces non-ready result

Create `run.json` with `execution_attempted=true`,
`reason_codes` containing `execution_failed`, and partial
`execution_results_summary`.

Assert `ready=False` (due to execution_failed), but evidence paths
include the partial results.

### 8. Payload cleanliness failure blocks readiness

Provide a `PayloadCleanlinessResult` with `clean=False` containing
`commit_payload_forbidden_tracked_change`.

Assert `ready=False`, `readiness_payload_not_clean` in reason_codes.

### 9. Untracked known generated residue does not block readiness

Provide a `PayloadCleanlinessResult` with `clean=True` and
`known_generated_residue_files` containing untracked paths.

Assert `ready=True`.

### 10. Staged known residue blocks readiness

Provide a `PayloadCleanlinessResult` with `clean=False` containing
`commit_payload_staged_residue`.

Assert `ready=False`.

### 11. Forbidden tracked files block readiness

Provide a `PayloadCleanlinessResult` with `clean=False` containing
`commit_payload_forbidden_tracked_change`.

Assert `ready=False`.

### 12. Unknown untracked files block readiness

Provide a `PayloadCleanlinessResult` with `clean=False` containing
`commit_payload_unknown_untracked`.

Assert `ready=False`.

### 13. Dogfood proof path is required for dogfood-style readiness

Create a run without dogfood proof, but pass a `dogfood_proof_path`.

Assert `ready=False`, `readiness_missing_dogfood_proof` in reason_codes.

### 14. Readiness result includes evidence paths and reason codes

Create a complete run.

Assert `evidence_paths` is non-empty, `missing_evidence` is empty,
`reason_codes` is empty.

### 15. No real git mutation in tests

Assert tests use only fake providers and temporary roots.
No `subprocess.run` for git mutation, no `gh`, no Docker, no network.

## Validation Checklist

### 1. Compile Check

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

Expected: all Python files compile.
If not met: block.

### 2. Focused Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  -q
```

Expected: focused tests pass.
If not met: block.

### 3. Regression Subset

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  -q
```

Expected: regression subset passes.
If not met: block.

### 4. Grep for Readiness Gate

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "readiness|readiness_gate|ProductionLineReadiness|production_line_ready|run-report|run_report|manifest|run_json|payload_cleanliness|commit_payload|git_boundary_status|dogfood_proof|readiness_missing|readiness_payload" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0136-production-line-final-readiness-gate
```

Expected: readiness gate implementation and tests are visible.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0136-production-line-final-readiness-gate
```

Expected: no unsafe real mutation authority added.
If unsafe new mutation is found: block.

### 6. Git Status

```bash
git status --short
```

Expected: only allowed files are dirty, plus untracked known generated
residue if produced by validation.
If forbidden tracked files are modified: block.
If unknown untracked files exist: block.

### 7. Git Diff

```bash
git diff --name-only
```

Expected: only allowed files are listed.
If not met: block.

### 8. Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty during review unless human staged expected files after
implementation.
If staged known residue or forbidden files appear: block.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131 dogfood proof | `_render_dogfood_proof_yaml`, `_validate_dogfood_proof_content`, proof finalization order unchanged |
| PR 0132 execution result persistence | `persist_run_record` unchanged; readiness reads, does not write |
| PR 0133 test residue isolation | `conftest.py` autouse fixture unchanged; `_cleanup_runtime_residue` unchanged |
| PR 0134 commit payload cleanliness | `_check_payload_cleanliness`, `PayloadCleanlinessResult`, `_KNOWN_RESIDUE_PATHS`, `_FORBIDDEN_TRACKED_PATHS` unchanged |
| PR 0135 run report artifact | `_write_run_report` unchanged; readiness only reads report path |
| Git Boundary authority | `git_boundary.py` not modified |
| Dirty-tree strictness | `_check_git_baseline`, `FORBIDDEN_PAYLOAD_PREFIXES`, `IGNORED_BASELINE_PREFIXES` unchanged |

## Non-Goals

- No UI
- No dashboard
- No web readiness viewer
- No change to proof schema
- No change to Git Boundary authority
- No real dogfood
- No GitHub PR creation
- No ORCHESTRATOR_STANDARD.txt
- No .gitignore entries added
- No dirty-tree checks weakened
- No committed project-memory artifacts deleted
- No PR 0131/0132/0133/0134/0135 artifacts rewritten
- No dashboard, retry system, control plane, model health, parallel queue,
  Decision Core, Context Warehouse, eval harness, faithfulness audit,
  frontend, or unrelated capability work

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0136-production-line-final-readiness-gate`
- PLAN does not include Roadmap Alignment section
- PLAN does not state that PR 0136 closes the production-line hardening stream
- PLAN is docs-only (no executable function specified)
- PLAN does not state that no frozen capability stream starts
- PLAN states that the gate implements UI, dashboard, or frontend
- PLAN adds .gitignore entries
- PLAN weakens dirty-tree checks
- PLAN modifies PR 0131/0132/0133/0134/0135 artifacts
- PLAN modifies `git_boundary.py`
- PLAN runs real dogfood, Docker, installs dependencies, or creates GitHub PRs
