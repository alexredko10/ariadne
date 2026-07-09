# PR 0135 — Persisted Run Report Artifact Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Production Line — Stage 2/3 Closed Loop |
| **Slot** | PR 0135 (post-0134 gate) |
| **Why this PR is next** | PR 0131-0133 established dogfood proof, execution result persistence, and test residue isolation. PR 0134 added commit payload cleanliness. The runner now has substantial evidence scattered across `run.json`, `manifest.json`, dogfood proof, execution result summaries, and payload cleanliness data. PR 0135 consolidates this evidence into a single human-readable artifact so that one run is understandable without manually opening multiple files. |
| **Batching policy** | Single-purpose: run report artifact from already captured runtime evidence. No feature expansion. |
| **Drift heuristic** | Does not start a frozen capability stream. Does not add UI, dashboard, frontend, Decision Core, Context Warehouse, eval harness, faithfulness audit, or product iteration features. The report is local runtime evidence, not UI. |
| **Architect note** | This is production hardening, not a new capability. The report derives from already-persisted data; it does not create new evidence or change existing runtime behavior. |

## Summary

The runner currently persists `run.json` and `manifest.json` in
`.ariadne/runs/<run-id>/` but no single human-readable artifact
summarizes a run end-to-end.  A reviewer or operator must open
multiple files (run status, execution results, payload cleanliness
outcome, proof artifact, PR URL evidence) to understand what happened.

PR 0135 writes a local plain-text `run-report.txt` alongside
`run.json` and `manifest.json` in the run directory.  The report
consolidates already-captured runtime evidence into a single readable
artifact without replacing or modifying any existing persisted file.

## Report Location

**Path**: `.ariadne/runs/<run-id>/run-report.txt`

**Justification**: This path is under the existing `runs_root` directory
where `run.json` and `manifest.json` are already written.  The report
is a derived local artifact, not a committed project-memory artifact.
Placing it alongside `run.json` makes the run directory self-contained.

**Not under `.project-memory/`**: The report is generated runtime
evidence, not a deliberate committed project-memory artifact.

**Not staged or committed by default**: The report is written under
`.ariadne/`, which is in `IGNORED_BASELINE_PREFIXES` and the
`_KNOWN_RESIDUE_PATHS` in `conftest.py`.  It will never be presented
to `git add` or appear in dirty-tree checks for commit payload.

## Report Content

Each report includes:

| # | Field | Source |
|---|-------|--------|
| 1 | Report schema version | `report_schema: "1"` |
| 2 | `run_id` | `AriadneTaskCliResult.run_id` |
| 3 | `pr_id` | `AriadneTaskCliRequest.pr_id` |
| 4 | `branch` | `AriadneTaskCliRequest.branch` |
| 5 | `invocation_mode` | `"cli"` (fixed) |
| 6 | `status` | `AriadneTaskCliResult.status` |
| 7 | `pipeline_status` | `AriadneTaskCliResult.pipeline_status` |
| 8 | `pipeline_final_action` | `AriadneTaskCliResult.pipeline_final_action` |
| 9 | `pipeline_has_blockers` | `AriadneTaskCliResult.pipeline_has_blockers` |
| 10 | `git_boundary_status` | `AriadneTaskCliResult.git_boundary_status` |
| 11 | `execution_attempted` | `AriadneTaskCliResult.execution_attempted` |
| 12 | `reason_codes` | `AriadneTaskCliResult.reason_codes` |
| 13 | Blockers and warnings | `AriadneTaskCliResult.warnings` |
| 14 | Execution results (operation + exit_code) | `AriadneTaskCliResult.execution_results` |
| 15 | stdout/stderr summary (when present, safe) | `AriadneTaskCliResult.execution_results` |
| 16 | PR URL (from `gh_pr_create` result) | `AriadneTaskCliResult.execution_results` |
| 17 | Payload cleanliness outcome | From `PayloadCleanlinessResult` if available |
| 18 | Known generated residue observations | From `PayloadCleanlinessResult` if available |
| 19 | Artifact paths (`run.json`, `dogfood-proof.yml`) | `RunPersistenceResult`, `AriadneTaskCliRequest.files_to_stage` |
| 20 | `run_json_hash` | `RunPersistenceResult.run_json_hash` |
| 21 | `manifest.json` path | `RunPersistenceResult.manifest_path` |
| 22 | Dogfood proof path | Derived from `AriadneTaskCliRequest.files_to_stage[0]` |
| 23 | `generated_at` timestamp | Clock provider |

### Failure and Blocked Run Handling

- Blocked runs produce a report when persistence is reached.
- Failed execution runs include partial `execution_results`.
- Pre-execution blocked runs have empty `execution_results`.
- Missing fields are rendered as `not available` or `none`.
- The report does not fabricate missing PR URLs or successful execution
  evidence.

## Scope

### Implementation Files

| File | Changes | Justification |
|------|---------|---------------|
| `services/runner/src/runner/ariadne_task_cli.py` | Add `_write_run_report()` function. Integrate into `_persist_and_return()` after `run.json` is successfully written. Add `report_path` field to `AriadneTaskCliResult`. | Evidence: `_persist_and_return()` at end of `run_ariadne_task()` is the single point where all run results converge. It already receives `AriadneTaskCliResult`, `AriadneTaskCliRequest`, and `RunPersistenceResult`. Adding the report write here ensures all runs (completed, blocked, failed) produce a report when persistence is configured. |
| `services/runner/src/runner/run_persistence.py` | Add `report_path` to `manifest.json` `files` list when a report is written. | Evidence: `run_persistence.py` `persist_run_record()` builds the manifest dict at lines 296-303. Adding the report path to the manifest allows downstream consumers to discover the report. |
| `services/runner/tests/test_ariadne_task_cli.py` | Add 10+ tests for report generation scenarios. | Evidence: Primary test file for `ariadne_task_cli.py` functions. |
| `services/runner/tests/test_run_persistence.py` | Add tests proving manifest includes report path when present. | Evidence: Manifest integration lives in `run_persistence.py`. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/src/runner/git_boundary.py` | Evidence: The report consumes `AriadneTaskCliResult.execution_results` which already contains Git Boundary execution outcomes. No Git Boundary result shape change is needed. |
| `services/runner/tests/test_git_boundary.py` | Evidence: No `git_boundary.py` changes. |
| `services/runner/tests/conftest.py` | Evidence: The report is written under `.ariadne/runs/` which is already in `_KNOWN_RESIDUE_PATHS`. No fixture changes needed. |

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
- `services/runner/src/runner/git_boundary.py` — not modified

## Design

### 1. Report Writer Function

```python
def _write_run_report(
    report_path: str,
    request: AriadneTaskCliRequest,
    result: AriadneTaskCliResult,
    persist_result: RunPersistenceResult,
) -> None:
    """Write a human-readable run report artifact.

    Parameters
    ----------
    report_path:
        Absolute path for the report file.
    request:
        The CLI request (contains pr_id, branch, runs_root, etc.).
    result:
        The CLI result (contains status, reason_codes, execution_results, etc.).
    persist_result:
        The persistence result (contains run_json_hash, manifest_path, etc.).
    """
    lines: list[str] = []

    # Header
    lines.append("=" * 60)
    lines.append("Ariadne Run Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Report schema version: 1")
    lines.append(f"Generated at: {result.finished_at or 'not available'}")

    # Run identity
    lines.append("")
    lines.append("--- Run Identity ---")
    lines.append(f"Run ID: {result.run_id or 'not available'}")
    lines.append(f"PR ID: {request.pr_id or 'not available'}")
    lines.append(f"Branch: {request.branch or 'not available'}")
    lines.append(f"Invocation mode: cli")

    # Status
    lines.append("")
    lines.append("--- Status ---")
    lines.append(f"Status: {result.status or 'not available'}")
    lines.append(f"Reason codes: {', '.join(result.reason_codes) if result.reason_codes else 'none'}")

    # Pipeline
    lines.append("")
    lines.append("--- Pipeline ---")
    lines.append(f"Pipeline status: {result.pipeline_status or 'not available'}")
    lines.append(f"Final action: {result.pipeline_final_action or 'not available'}")
    lines.append(f"Has blockers: {result.pipeline_has_blockers if result.pipeline_has_blockers is not None else 'not available'}")

    # Git Boundary
    lines.append("")
    lines.append("--- Git Boundary ---")
    lines.append(f"Status: {result.git_boundary_status or 'not available'}")

    # Execution
    lines.append("")
    lines.append("--- Execution ---")
    lines.append(f"Execution attempted: {result.execution_attempted}")
    if result.execution_results:
        lines.append("Execution results:")
        for res in result.execution_results:
            op = res.get("operation", "?")
            code = res.get("exit_code", "?")
            lines.append(f"  {op}: exit_code={code}")
            stdout = res.get("stdout", "")
            stderr = res.get("stderr", "")
            if stdout and len(stdout) < 500:
                lines.append(f"    stdout: {stdout[:200]}")
            if stderr and len(stderr) < 500:
                lines.append(f"    stderr: {stderr[:200]}")
            # PR URL from gh_pr_create
            if op == "gh_pr_create":
                pr_url = res.get("pr_url", "")
                if pr_url:
                    lines.append(f"    PR URL: {pr_url}")
    else:
        lines.append("Execution results: none (pre-execution blocked or dry-run)")

    # Warnings
    if result.warnings:
        lines.append("")
        lines.append("--- Warnings ---")
        for w in result.warnings:
            lines.append(f"  - {w}")

    # Artifacts
    lines.append("")
    lines.append("--- Artifacts ---")
    lines.append(f"run.json path: {result.run_record_path or 'not available'}")
    lines.append(f"run.json hash: {persist_result.run_json_hash or 'not available'}")
    lines.append(f"manifest.json path: {persist_result.manifest_path or 'not available'}")
    if request.files_to_stage:
        dogfood_path = os.path.join(request.repo_root, request.files_to_stage[0])
        lines.append(f"Dogfood proof path: {dogfood_path}")
    lines.append(f"Report path: {report_path}")

    # Write
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
```

### 2. Integration in `_persist_and_return()`

After `run.json` is successfully persisted, write the report:

```python
# In _persist_and_return(), after persistence succeeds:
if persist_result.status == RunPersistenceStatus.PERSISTED.value:
    # Write run report
    report_path = os.path.join(run_dir, "run-report.txt")
    _write_run_report(report_path, request, result, persist_result)
    
    return AriadneTaskCliResult(
        ...
        report_path=report_path,  # new field
    )
```

### 3. `AriadneTaskCliResult` Changes

Add an optional `report_path` field:

```python
@dataclasses.dataclass(frozen=True)
class AriadneTaskCliResult:
    ...
    report_path: Optional[str] = None
```

### 4. Manifest Integration

In `run_persistence.py` `persist_run_record()`, accept an optional
`report_path` parameter and add it to the manifest `files` list:

```python
if request.report_path:
    manifest_data["files"].append("run-report.txt")
```

### 5. Injectable Provider Support

The `_write_run_report` function writes to disk (it's a local file
operation, not a side-effecting mutation).  For testability, the
report writer can be injected as an optional parameter:

```python
report_writer_fn: Optional[Callable] = None,
```

But since the function is pure file writing without external side
effects, tests can simply verify the report file exists and has
expected content after `run_ariadne_task()` returns.

### 6. Not Staged or Committed

The report is written under `.ariadne/runs/`, which is in
`IGNORED_BASELINE_PREFIXES` (from `_check_git_baseline`) and in
`_KNOWN_RESIDUE_PATHS` (from `conftest.py`).  The existing PR 0134
payload cleanliness gate classifies `.ariadne/` content as known
generated residue — acceptable when untracked, blocker if staged.
This is correct: the report is never part of the commit payload.

## Tests

### 1. Successful run writes run-report.txt

Run `run_ariadne_task()` with fake pipeline, persistence enabled,
all providers clean.

Assert `result.report_path` is not None.
Assert `Path(result.report_path).exists()` is True.
Assert report contains "Ariadne Run Report" header.
Assert report contains `Run ID: <run_id>`.

### 2. Blocked run writes run-report.txt when persistence is reached

Run `run_ariadne_task()` without `--approve` (blocked at approval gate).
Assert `result.status == BLOCKED`.
Assert `result.report_path` is not None.
Assert report exists at `result.report_path`.

### 3. Failed execution report includes partial execution results

Use an executor function that fails after the first command.
Assert report contains the partial execution results with operation
and exit_code.

### 4. Report includes operation and exit_code for all execution results

Run with fake executor that returns 4 results.
Assert report contains all 4 operations and their exit_codes.

### 5. Report includes PR URL when gh_pr_create result contains one

Use executor returning `gh_pr_create` result with `pr_url`.
Assert report contains `PR URL: <url>`.

### 6. Report includes payload cleanliness outcome when available

Run with a payload cleanliness provider that returns a non-clean result.
Assert report mentions `commit_payload_*` reason codes.

### 7. Report includes manifest path

Assert report contains `manifest.json path: <path>`.

### 8. Report includes run_json path and hash

Assert report contains `run.json path:` and `run.json hash:`.

### 9. Report does not rewrite dogfood proof

Run with `files_to_stage` and persistence.
Assert dogfood proof file is unchanged (same content before and after).

### 10. Reports are written under tmp_path during tests

Use `tmp_path` for `runs_root`.
Assert report path is under `tmp_path`.
Assert no `.ariadne/` residue remains at real repo root.

### 11. No real git mutation in tests

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

### 4. Grep for Report Generation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "run-report|run_report|RunReport|execution_results|payload_cleanliness|commit_payload|pr_url|manifest|run_json_hash|generated_at|report_path" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0135-persisted-run-report-artifact
```

Expected: report generation and tests are visible.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0135-persisted-run-report-artifact
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
| PR 0131 dogfood behaviour | `_render_dogfood_proof_yaml`, `_validate_dogfood_proof_content`, proof finalization order unchanged |
| PR 0132 execution result persistence | `persist_run_record` unchanged; report is additional artifact, not replacement |
| PR 0133 test residue isolation | `conftest.py` autouse fixture unchanged; `_cleanup_runtime_residue` unchanged |
| PR 0134 commit payload cleanliness | `_check_payload_cleanliness`, `PayloadCleanlinessResult`, `_KNOWN_RESIDUE_PATHS`, `_FORBIDDEN_TRACKED_PATHS` unchanged |
| Git Boundary authority | `git_boundary.py` not modified |
| Dirty-tree strictness | `_check_git_baseline`, `FORBIDDEN_PAYLOAD_PREFIXES`, `IGNORED_BASELINE_PREFIXES` unchanged |

## Non-Goals

- No UI
- No dashboard
- No web report viewer
- No change to proof schema
- No change to Git Boundary authority
- No real dogfood
- No GitHub PR creation
- No ORCHESTRATOR_STANDARD.txt
- No .gitignore entries added
- No dirty-tree checks weakened
- No committed project-memory artifacts deleted
- No PR 0131/0132/0133/0134 artifacts rewritten
- No dashboard, retry system, control plane, model health, parallel queue,
  Decision Core, Context Warehouse, eval harness, faithfulness audit,
  frontend, or unrelated capability work

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0135-persisted-run-report-artifact`
- PLAN does not include Roadmap Alignment section
- PLAN does not state that PR 0135 is production hardening
- PLAN does not state that the work does not start a frozen capability stream
- PLAN states that the report is UI, dashboard, or frontend
- PLAN makes the report a committed artifact
- PLAN replaces run.json, manifest.json, or dogfood proof
- PLAN adds .gitignore entries
- PLAN weakens dirty-tree checks
- PLAN modifies PR 0131/0132/0133/0134 artifacts
- PLAN runs real dogfood, Docker, installs dependencies, or creates GitHub PRs
