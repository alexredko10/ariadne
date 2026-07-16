# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0147A — Local Operator Launch and End-to-End Smoke Implementation.

Added a safe, deterministic local operator launch command (`make local-operator`),
an ASGI runtime wrapper with server-owned runs-root configuration (OPTION B),
loopback-only safe defaults, startup diagnostics, configuration check mode
(`--check`), explicit uvicorn packaging, a committed operator runbook
(`docs/LOCAL_OPERATOR.md`), and one canonical end-to-end HTTP smoke
(`scripts/smoke-local-operator.py`) that proves the full read-only Artifact
Workspace through the official entrypoint.

## FILES READ

All files listed in the REQUIRED READS section of the task prompt, including:

- .project-memory/ORCHESTRATOR_STANDARD.txt
- .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
- .project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md
- .project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md
- agents/coder.yml
- README.md
- Makefile (original and modified)
- pyproject.toml (original and modified)
- ROADMAP.md (original and modified)
- docs/START_HERE.md
- docs/REPOSITORY_STRUCTURE.md
- docs/DEVELOPMENT_ORDER.md
- docs/AGENTS.md
- docs/adr/0011-pr-batching-and-roadmap-discipline.md
- .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md (original and modified)
- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/PLAN.md
- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/reviews/plan-review.yml
- .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/PLAN.md
- .project-memory/pr/0143-artifact-workspace-4-zone-shell-skeleton/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0144-artifact-workspace-local-run-list-page/PLAN.md
- .project-memory/pr/0144-artifact-workspace-local-run-list-page/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/PLAN.md
- .project-memory/pr/0145-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0146-artifact-workspace-run-report-viewer/PLAN.md
- .project-memory/pr/0146-artifact-workspace-run-report-viewer/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/PLAN.md
- .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/reviews/precommit-review.yml
- services/task_intake/src/task_intake/server.py (original and modified)
- services/task_intake/src/task_intake/local_operator.py (new)
- services/task_intake/src/task_intake/artifact_workspace.py
- services/task_intake/src/task_intake/doctor.py
- services/task_intake/src/task_intake/app.py
- services/task_intake/src/task_intake/smoke.py
- services/task_intake/tests/test_local_operator.py (new)
- services/task_intake/tests/test_artifact_workspace_shell.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- services/runner/src/runner/run_persistence.py
- services/runner/src/runner/runtime_evidence.py
- services/runner/tests/test_run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- docs/LOCAL_OPERATOR.md (new)
- scripts/smoke-local-operator.py (new)

## FILES CHANGED

### Modified files (tracked, git diff shows changes):

1. **pyproject.toml** — Added `uvicorn>=0.29.0` to `[project.optional-dependencies] dev` list.
2. **Makefile** — Added `.PHONY` entry and `local-operator` target delegating to `python -m task_intake.local_operator` with optional PORT override.
3. **services/task_intake/src/task_intake/server.py** — Added optional `runs_root` parameter to `app()` function. Stores in `scope["app_runs_root"]`. Routes prefer `scope.get("app_runs_root")` over query string.
4. **ROADMAP.md** — Added PR 0147A governance insertion documentation after PR 0147 entry.
5. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** — Added PR 0147A governance insertion section.

### New files (untracked):

6. **services/task_intake/src/task_intake/local_operator.py** — Local operator module with CLI arg parser, runs-root resolution/normalization, host/port validation, check mode, startup diagnostics, uvicorn delegation via wrapper ASGI app.
7. **services/task_intake/tests/test_local_operator.py** — Unit tests for default configuration, host validation, port validation, runs-root resolution, check mode output, read-only messaging.
8. **docs/LOCAL_OPERATOR.md** — Complete operator runbook with prerequisites, installation, launch, configuration, troubleshooting, read-only boundaries.
9. **scripts/smoke-local-operator.py** — End-to-end smoke script that creates canonical persisted run via `persist_run_record()`, launches operator as subprocess, asserts 13+ route checks, and cleans up.

### Implementation report:

10. **.project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/IMPLEMENTATION_REPORT.md** — This file.

## IMPLEMENTATION DECISIONS

1. **OPTION B — Minimal ASGI Runtime wrapper**: The `local_operator.py` creates a wrapper ASGI app that captures runs_root in a closure and calls `server.app()` with the `runs_root` parameter. This is cleaner than modifying existing test callers.

2. **POLICY A — Operator App Factory**: The ASGI app `server.py` now accepts an optional `runs_root` parameter. When provided by the operator entrypoint, it is stored in `scope["app_runs_root"]`. All evidence routes check `scope.get("app_runs_root")` first, then fall back to query string. This preserves backward compatibility for tests that supply runs_root via query string.

3. **Validation via sys.exit with main() catch**: Validation functions (`_validate_host`, `_validate_port`) call `sys.exit(1)` which raises `SystemExit`. `main()` catches `SystemExit` and returns 1, enabling unit tests to assert exit code without catching exceptions.

4. **Venv-aware smoke**: The smoke script checks for `.venv/bin/python` and prefers it when available, since uvicorn is installed in the venv but not in the system Python.

5. **Canonical fixture via persist_run_record()**: The smoke creates the canonical run using the real `run_persistence.persist_run_record()` API with all required fields, then appends run-report.txt content. This avoids handcrafting evidence JSON.

## PLAN ALIGNMENT

| PLAN.md requirement | Status |
|---|---|
| OPTION B — Minimal ASGI Runtime wrapper | Implemented |
| POLICY A — Operator App Factory (server-owned runs_root) | Implemented |
| `make local-operator` command → `python -m task_intake.local_operator` | Implemented |
| Default host 127.0.0.1, port 8000 | Implemented |
| --host, --port, --runs-root, --check, --allow-public-bind, --allow-privileged-port | Implemented |
| Host validation (reject 0.0.0.0 without flag) | Implemented |
| Port validation (reject <1024 without flag, reject >65535) | Implemented |
| Runs-root normalization and creation | Implemented |
| Check mode prints deterministic JSON | Implemented |
| Startup diagnostics (runs root, health URL, workspace URL, read-only) | Implemented |
| Graceful shutdown (Ctrl-C/SIGTERM via uvicorn) | Implemented |
| uvicorn>=0.29.0 in pyproject.toml dev dependencies | Implemented |
| docs/LOCAL_OPERATOR.md runbook | Implemented |
| scripts/smoke-local-operator.py smoke | Implemented |
| Canonical persistence via persist_run_record() | Implemented |
| Isolated temp directory for smoke | Implemented |
| SIGTERM → wait 5s → SIGKILL cleanup | Implemented |
| try/finally for cleanup | Implemented |
| No agent launch, orchestration, mutation, git, gh, Docker | Verified |
| PR 0143–0147 behavior preserved | Tests pass |
| PR 0148 numbering unchanged | Verified in ROADMAP.md |
| Roadmap insertion documented | ROADMAP.md and detailed roadmap updated |

## DEVIATIONS FROM PLAN

1. **Smoke venv fallback**: PLAN.md assumes `sys.executable` is sufficient for the subprocess. In the current environment, uvicorn is only installed in `.venv`. The smoke was updated to detect `.venv/bin/python` and prefer it. This is an environment compatibility fix, not a behavioral deviation.

2. **No test for invalid port 99999 exit code**: The PLAN.md specifies `main()` should return 1 for invalid config, but `_validate_port()` calls `sys.exit(1)` internally. The fix wraps validation calls in try/except SystemExit in `main()`. This matches PLAN.md intent (non-zero exit on invalid input) while making the API testable.

3. **test_no_agent_references_in_module_source assertion**: The original test asserted `"orchestrat" not in source.lower()` which would fail because the required startup diagnostics message includes "no orchestration". The assertion was refined to check that the module does not implement agent launch behavior, while allowing the required status message. This is consistent with PLAN.md which requires startup diagnostics to state "no orchestration".

## VALIDATION RUN

### 1. Python compile check
- **Command**: `python3 -m compileall -f services/task_intake/src services/runner/src scripts`
- **Exit code**: 0
- **Result**: All files compile clean
- **Pass**: YES

### 2. Local operator unit tests
- **Command**: `PYTHONPATH=services/task_intake/src python3 -m pytest services/task_intake/tests/test_local_operator.py -q`
- **Exit code**: 0
- **Result**: 35 passed
- **Pass**: YES

### 3. Existing workspace tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q`
- **Exit code**: 0
- **Result**: 310 passed
- **Pass**: YES

### 4. Existing detail API tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q`
- **Exit code**: 0
- **Result**: 73 passed
- **Pass**: YES

### 5. Serialization contract tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q`
- **Exit code**: 0
- **Result**: 76 passed
- **Pass**: YES

### 6. Task intake tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_task_intake.py -q`
- **Exit code**: 0
- **Result**: 19 passed
- **Pass**: YES

### 7. Runtime evidence tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/runner/tests/test_runtime_evidence.py -q`
- **Exit code**: 0
- **Result**: 32 passed
- **Pass**: YES

### 8. Run persistence tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/runner/tests/test_run_persistence.py -q`
- **Exit code**: 0
- **Result**: 27 passed
- **Pass**: YES

### 9. Full regression
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/ services/runner/tests/ -q`
- **Exit code**: 0
- **Result**: 2504 passed
- **Pass**: YES

### 10. Check mode output
- **Command**: `PYTHONPATH=services/task_intake/src python3 -m task_intake.local_operator --check --runs-root /tmp/check-test-runs`
- **Exit code**: 0
- **Result**: Valid JSON with all required fields
- **Pass**: YES

### 11. End-to-end smoke
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 scripts/smoke-local-operator.py`
- **Exit code**: 0
- **Result**: "smoke: ALL CHECKS PASSED"
- **Pass**: YES

### 12. Post-smoke process check
- **Command**: `pgrep -f "local_operator" || echo "no process"`
- **Exit code**: 0 (grep exit 1, but echo runs)
- **Result**: "no process"
- **Pass**: YES

### 13. Post-smoke repository check
- **Command**: `git diff --name-only -- .ariadne/; echo "EXIT:$?"`
- **Exit code**: 0
- **Result**: No output (no .ariadne changes)
- **Pass**: YES

### 14. Loopback default
- **Command**: `grep -n "127\.0\.0\.1" services/task_intake/src/task_intake/local_operator.py`
- **Result**: Lines 146-147 show default="127.0.0.1"
- **Pass**: YES

### 15. Public-bind prohibition
- **Command**: `grep -n "0\.0\.0\.0" services/task_intake/src/task_intake/local_operator.py`
- **Result**: 0.0.0.0 only in validation/warning context, not as default
- **Pass**: YES

### 16. Runs-root browser-override check
- **Command**: `grep -n "runs_root\|app_runs_root\|query_string\|parse_qs" services/task_intake/src/task_intake/server.py`
- **Result**: scope.get("app_runs_root") checked before query string
- **Pass**: YES

### 17. No agent/orchestration in operator
- **Command**: `grep -n -i "agent\|orchestrat\|launch.*process\|subprocess\|Popen" services/task_intake/src/task_intake/local_operator.py`
- **Result**: Only the status message "no agent execution... no orchestration"
- **Pass**: YES

### 18. Smoke process management
- **Command**: `grep -n -E "subprocess|Popen|terminate|kill|SIGTERM|wait\(\)|timeout" scripts/smoke-local-operator.py`
- **Result**: Bounded process management present (Popen, SIGTERM, wait, SIGKILL escalation)
- **Pass**: YES

### 19. Forbidden-path diff
- **Command**: `git diff --name-only -- services/runner/ agents/ schemas/ .github/ .project-memory/pr/0143* .project-memory/pr/0144* .project-memory/pr/0145* .project-memory/pr/0146* .project-memory/pr/0147*`
- **Result**: Empty (no modification of protected files)
- **Pass**: YES

### 20. Planning lock check
- **Command**: `git diff -- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/PLAN.md .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/reviews/plan-review.yml`
- **Result**: Empty (artifacts locked)
- **Pass**: YES

### 21. Whitespace check
- **Command**: `git diff --check`
- **Result**: No whitespace errors
- **Pass**: YES

### 22. Cached diff
- **Command**: `git diff --cached --name-only`
- **Result**: Empty
- **Pass**: YES

### 23. IMPLEMENTATION_REPORT.md exists
- **Command**: `test -s .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/IMPLEMENTATION_REPORT.md`
- **Exit code**: 0
- **Pass**: YES

## BOUNDARY CONFIRMATIONS

- **No forbidden files changed**: Confirmed via git diff and checks above.
- **No review artifacts written by coder**: precommit-review.yml was not written. Only IMPLEMENTATION_REPORT.md written.
- **No PLAN.md modification**: Locked artifacts unchanged.
- **No plan-review.yml modification**: Locked artifact unchanged.
- **ROADMAP.md modification**: Explicitly allowed by PLAN.md for PR 0147A governance insertion.
- **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md modification**: Explicitly allowed by PLAN.md for governance insertion.
- **Only PLAN.md-approved implementation/test paths changed**: All 10 changed files are in the PLAN.md allowlist.
- **No git mutation commands run**: Verified against command policy.
- **No Docker commands run**: Verified.
- **No runtime/UI/runner/task_intake behavior changed beyond planned scope**: server.py change is additive (optional parameter). No routes removed. No response envelopes changed.
- **PR 0143–0147 behavior preserved**: All existing workspace, detail, report, and evidence tests pass.

## NON-GOALS PRESERVED

- **No agent launch**: Verified — no agent references in operator module (only status message).
- **No orchestration**: Verified — no orchestration pipeline or role routing.
- **No mutation**: Verified — no POST routes added, no evidence modification.
- **No git push or PR creation**: Verified — no git/gh operations in operator or smoke.
- **No Docker**: Verified — no Docker references.
- **No browser auto-open**: Verified — no webbrowser.open calls.
- **No external network calls**: Verified — loopback only.
- **No runs-root browser override**: Verified — scope["app_runs_root"] takes precedence over query string.
- **No public bind by default**: Verified — 0.0.0.0 requires --allow-public-bind.
- **No PR 0147B or later work absorbed**: Verified — only operator launch, no orchestration or agent routing.
- **PR 0148 numbering unchanged**: Verified — ROADMAP.md preserves PR 0148 slot.

## RISKS OR WARNINGS

1. **Uvicorn dependency**: uvicorn was added to dev dependencies, but is also required for the operator to run. If installed via `pip install -e .` (without `[dev]`), uvicorn won't be available. The installation instructions in LOCAL_OPERATOR.md recommend `make install-dev` which includes `[dev]`. This is consistent with PLAN.md's statement that uvicorn is a dev dependency.

2. **Venv detection in smoke**: The smoke script detects `.venv/bin/python` as a fallback. This is an environment-specific adjustment. In a clean CI environment where uvicorn is installed in the system Python, `sys.executable` would work correctly.

3. **test_no_agent_references_in_module_source adjustment**: This test was refined to allow the required "no orchestration" status message. The original assertion would have blocked valid startup diagnostics. The refined assertion checks that the module does not implement agent launch behavior, which is the actual PLAN.md constraint.

## NEXT REVIEWER FOCUS

1. Verify that the `app()` function signature change in server.py is backward-compatible with all existing test callers (all 2504 tests pass, confirming compatibility).
2. Verify that the operator wrapper ASGI app in `local_operator.py` correctly injects runs_root into scope (smoke security assertions verify this).
3. Verify that the smoke's canonical fixture via `persist_run_record()` creates valid run.json/manifest.json that the existing read pipeline can consume (smoke GET /runs, /runs/<id>, /runs/<id>/report all pass).
4. Verify that no commit/push/Docker/networking boundaries are violated (grep checks confirm).
5. Verify that the roadmap documentation accurately reflects the governance insertion without renumbering PR 0148.
