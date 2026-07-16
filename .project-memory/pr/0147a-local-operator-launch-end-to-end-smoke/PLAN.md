# PR 0147A — Local Operator Launch and End-to-End Smoke Plan

## EVIDENCE SNAPSHOT

1. HEAD: `0b027c1b55fe302623b6c09887c60919aedd6cc4`
2. origin/main: `0b027c1b55fe302623b6c09887c60919aedd6cc4`
3. Merge base: `0b027c1b55fe302623b6c09887c60919aedd6cc4`
4. Branch: `0147a-local-operator-launch-end-to-end-smoke`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0147 merge evidence: `0b027c1 (HEAD -> 0147a-..., origin/main, origin/HEAD, main) PR 0147 — Artifact Workspace Proof and Manifest Viewer (#173)`

## CURRENT LAUNCH INVENTORY

| Item | Value | Evidence |
|---|---|---|
| Existing ASGI server | `task_intake.server:app` — async function, no framework dependency | server.py L64 |
| Existing app entrypoint | `task_intake.app:main()` with uvicorn | app.py L79-100 |
| uvicorn import | In `app.py` `main()` — try/except ImportError | app.py L89 |
| uvicorn as dependency | NOT declared in pyproject.toml — only `try/except` at runtime | pyproject.toml |
| CLI args in app.py | `--host` (default 127.0.0.1), `--port` (default 8000), `--check` | app.py L59-66 |
| Existing smoke | `task_intake.smoke:main()` — tests health, submit, blank prompt only | smoke.py |
| Existing smoke tests | `test_task_intake_smoke.py` — monkeypatched, no real server | tests/ |
| hashlib/ | Not used for runs_root security | |
| Runbook docs | None for local operator | docs/ |
| Default runs_root | `os.path.join(os.getcwd(), ".ariadne", "runs")` | server.py L944 |

## CURRENT PACKAGING INVENTORY

| Item | Value |
|---|---|
| Project name | `universal-agentic-platform` |
| Python requires | `>=3.11` |
| Runtime dependencies | `[]` (none) |
| Dev dependencies | pytest, pytest-asyncio, httpx |
| Console scripts | None |
| Makefile targets | install-dev, test, lint, smoke |
| serve target | None |

## CURRENT ASGI RUNTIME INVENTORY

The ASGI app (`app` function in server.py) is a raw ASGI3 callable — no framework. The existing `app.py` wraps it with uvicorn but only in the `main()` entrypoint. The existing `app.py` is executed via `python -m task_intake.app`.

The existing app.py does NOT:
- Normalize runs_root server-side
- Disable browser-supplied runs_root override
- Print workspace URL at startup
- Print runs root at startup
- Print read-only warning
- Have a dedicated operator mode

## CURRENT ROUTE INVENTORY

All routes from server.py:
- `GET /health` — doctor() response
- `GET /` — Local Interaction _HTML_PAGE
- `GET /workspace` — Artifact Workspace shell
- `GET /runs` — run index (version-1)
- `GET /runs/<run_id>` — run detail (version-1)
- `GET /runs/<run_id>/report` — run report (version-1)
- Plus other routes (backlog, product iterations, etc.)

## CURRENT RUNS-ROOT SECURITY INVENTORY

| Property | Value |
|---|---|
| runs_root source | Browser-supplied `?runs_root=...` query parameter |
| Default when absent | `os.path.join(os.getcwd(), ".ariadne", "runs")` |
| Validation | Only `os.path.isdir(runs_root)` check — accepts any path the server process can read |
| Browser override | FULL — browser supplies arbitrary local path |
| Operator security | NONE — current app.py does not disable the override |

## LAUNCH STRATEGY DECISION

### OPTION B — MINIMAL ASGI RUNTIME AND OPERATOR ENTRYPOINT

The repository already has an ASGI app and a uvicorn-based entrypoint in `app.py` (import uvicorn, launch server). The implementation gap is:

1. Adding uvicorn as an optional runtime dependency in pyproject.toml.
2. Creating a bounded `local_operator.py` entrypoint that wraps the existing ASGI app with server-owned runs-root configuration, disables browser-supplied runs_root overrides, and provides safe defaults, startup diagnostics, and clean shutdown.
3. Adding a `scripts/smoke-local-operator.py` that provisions an isolated canonical persisted run and proves the full route chain against the real launched server.
4. Adding `docs/LOCAL_OPERATOR.md` as the committed runbook.
5. Adding a Makefile `local-operator` target.

**Why Option B**: The existing `app.py` uses uvicorn but lacks operator safety. Modifying `app.py` to add runs-root ownership while preserving backward compatibility for tests would be fragile. A separate `local_operator.py` creates a clean boundary.

**Runs-root security policy**: POLICY A — OPERATOR APP FACTORY. The `local_operator.py` module creates a new ASGI app that wraps the existing `server.app` with a closure that provides a fixed normalized runs root. Operator routes ignore any `runs_root=...` query parameter by extracting runs_root from the closure's configuration rather than from the query string. This preserves the existing `server.py` for tests (which supply runs_root via query string) while giving the operator a secure entrypoint.

## OFFICIAL COMMAND CONTRACT

| Property | Value |
|---|---|
| Exact primary command | `make local-operator` |
| Implementation | Delegates to `python -m task_intake.local_operator` |
| Required working directory | Repository root |
| Required Python | >=3.11 |
| Installation command | `make install-dev` (pip install -e ".[dev]") — uvicorn added to dev deps |
| Default host | `127.0.0.1` |
| Default port | `8000` |
| Port override | `make local-operator PORT=8080` or `python -m task_intake.local_operator --port 8080` |
| Port validation | Reject ports < 1024 (unless explicitly permitted) and > 65535 |
| Runs-root override | NOT supported in operator mode — runs_root is server-configured |
| Runs-root default | `.ariadne/runs` relative to repository root (resolved at startup) |
| Runs-root validation | Normalized to absolute path at startup. Must exist or be created as empty directory |
| Missing runs-root behavior | Created as empty directory (`os.makedirs(exist_ok=True)`) |
| Startup output | Prints: resolved runs_root, workspace URL, health URL, read-only warning |
| Shutdown | Ctrl-C (SIGINT) — uvicorn default clean shutdown |
| Exit codes | 0 = launched and shut down cleanly. 1 = startup configuration error. |
| Workspace URL | `http://127.0.0.1:<port>/workspace` |
| Health URL | `http://127.0.0.1:<port>/health` |
| Troubleshooting | `make install-dev` then `python -m task_intake.local_operator --check` |
| Shell interpolation | None — all configuration uses argparse with validated types |
| No eval or dynamic command construction | Prohibited |

### Alias

Secondary command: `python -m task_intake.local_operator` — delegates to the exact same entrypoint.

## OPERATOR CONFIGURATION CONTRACT

| Parameter | Flag | Default | Validation |
|---|---|---|---|
| Host | `--host` | `127.0.0.1` | Must be a valid IP or hostname. Cannot be `0.0.0.0` unless overridden with explicit `--allow-public-bind` flag (documented as unsafe). |
| Port | `--port` | `8000` | Integer. Reject < 1024 (print warning, allow with `--allow-privileged-port`). Reject > 65535. |
| Runs root | `--runs-root` | `os.path.join(repo_root, ".ariadne", "runs")` | Resolved to absolute normalized path. Created if absent. |
| Check mode | `--check` | False | Print configuration as JSON and exit. |
| Allow public bind | `--allow-public-bind` | False | Must be explicitly set to bind to 0.0.0.0. Documentation warns this is unsafe. |
| Allow privileged port | `--allow-privileged-port` | False | Must be explicitly set for port < 1024. |

## RUNS-ROOT SECURITY CONTRACT

**Policy**: POLICY A — OPERATOR APP FACTORY.

Implementation approach: The `local_operator.py` module creates a new ASGI wrapper function that captures `runs_root` in a closure. The wrapper calls the original `server.app` but injects the server-owned runs_root into the ASGI scope, making it available to routes without relying on query string parsing. The GET /runs and GET /runs/<run_id> routes in server.py are modified to accept an optional `scope["runs_root"]` override that takes precedence over the query string parameter. When the operator wrapper provides scope["runs_root"], the browser-supplied runs_root query parameter is ignored.

Alternative (simpler) approach: The local_operator.py creates an ASGI middleware that intercepts requests to /runs and /runs/<run_id> and strips the runs_root query parameter before passing to the original app. The runs_root is set from server-owned configuration as the only value.

Preferred approach (narrowest change): Modify server.py to accept an optional `runs_root` keyword argument in the `app` function signature. When `app` is called by the local operator entrypoint with `runs_root=normalized_path`, the app routes use that value instead of the query string. The existing test callers (which rely on query string) continue to work because no `runs_root` argument is passed.

**Operator mode behavior**:
1. Runs root is resolved at startup and normalized.
2. Runs root is created as empty directory if it does not exist.
3. Browser-supplied `?runs_root=...` parameter is ignored.
4. All evidence routes read from the server-owned runs root only.

## STARTUP DIAGNOSTICS CONTRACT

The operator entrypoint must print:

```
Ariadne — Local Operator
  Runs root: /absolute/path/to/.ariadne/runs
  Workspace: http://127.0.0.1:8000/workspace
  Health:    http://127.0.0.1:8000/health
  Status:    READ-ONLY — no agent execution, no mutation, no orchestration.
  Press Ctrl-C to stop.
```

On configuration error:

```
Ariadne — Local Operator
  Error: <specific error message>
  Run with --check to validate configuration.
```

The `--check` flag prints the configuration as JSON and exits with code 0.

## SHUTDOWN CONTRACT

1. Ctrl-C (SIGINT) triggers uvicorn's default graceful shutdown.
2. uvicorn waits for in-flight requests (default timeout).
3. No custom shutdown hook is required — uvicorn handles this.
4. After shutdown, no server process remains.
5. No temporary files, sockets, or generated residue remain (the operator does not write to the repository runs root during normal operation).
6. The smoke test verifies process termination and cleanup.

## OPERATOR RUNBOOK CONTRACT

### docs/LOCAL_OPERATOR.md

Required sections:
1. **Prerequisites**: Python >= 3.11, git clone
2. **Installation**: `make install-dev`
3. **Launch**: `make local-operator`
4. **Expected startup output**: Include the exact diagnostics block
5. **Workspace URL**: http://127.0.0.1:8000/workspace
6. **Health check**: `curl http://127.0.0.1:8000/health` or workspace page refresh
7. **Runs root location**: `./.ariadne/runs`
8. **How persisted runs appear**: Launch workspace, select a run from Timeline
9. **How to stop**: Ctrl-C
10. **Empty workspace behavior**: Timeline shows "No runs available"
11. **Missing runs root**: Created automatically as empty directory
12. **Common startup errors**: Port in use, missing Python, missing uvicorn
13. **Read-only boundaries**: Explicit list of 13+ read-only rules
14. **No agent execution**: Explicit statement
15. **No orchestration**: Explicit statement
16. **No git push or PR creation**: Explicit statement — these remain human-run
17. **Smoke command**: `python -m scripts.smoke_local_operator`
18. **Expected smoke output**: Success markers for each checked route
19. **Cleanup guarantee**: Smoke uses isolated temp dir, no repository mutation
20. **Troubleshooting**: `make install-dev`, `python -m task_intake.local_operator --check`

## END-TO-END SMOKE CONTRACT

### scripts/smoke-local-operator.py

**Purpose**: Prove the full read-only platform works against a real launched operator with real persisted run data.

**Behavior**:
1. Create an isolated temporary directory.
2. Create a canonical persisted run using `run_persistence.persist_run_record()`.
3. Canonical run includes: run.json, manifest.json, run-report.txt.
4. Launch the official operator entrypoint (`task_intake.local_operator`) as a subprocess with server-owned runs_root pointing to the temp directory.
5. Wait for readiness via `GET /health` with bounded timeout (5 seconds). Fail clearly on timeout.
6. Check `GET /workspace` returns 200 with text/html.
7. Check `GET /runs` returns 200 with version-1 envelope containing the persisted run.
8. Check `GET /runs/<encoded_run_id>` returns 200 with version-1 detail envelope.
9. Check `GET /runs/<encoded_run_id>/report` returns 200 with report content and provenance.
10. Verify workspace HTML contains all four zone root selectors (artifact-workspace, zone-timeline, zone-canvas, zone-gates-proofs, zone-logs-captures).
11. Verify workspace HTML has detail, report, gates, and logs rendering hooks.
12. Shut down the server on success.
13. Shut down the server on failure (cleanup handler).
14. Wait for process termination.
15. Remove temporary directory.
16. Print deterministic success/failure markers.
17. Return non-zero on any failure.

### Subprocess contract

Subprocess use is strictly limited to:
- Launching the operator entrypoint (`sys.executable, "-m", "task_intake.local_operator", ...`)
- Terminating that same process (send SIGTERM, wait, escalate to SIGKILL after bounded timeout)
- Checking process completion (process.wait())

**Prohibited subprocess behavior**:
- No git
- No gh
- No Docker
- No package installation
- No arbitrary commands
- No `shell=True` with constructed input
- No network calls beyond the local loopback server

### HTTP client for smoke

Use `urllib.request` from the standard library (same pattern as existing `smoke.py`). No additional dependency required for the smoke script.

## SMOKE FIXTURE CONTRACT

The canonical persisted run is created programmatically using `run_persistence.persist_run_record()`:

```python
from runner.run_persistence import (
    RunPersistenceRequest,
    persist_run_record,
)
```

The fixture includes:
- A deterministic run_id, e.g. `smoke-run-001`
- All required fields for RunPersistenceRequest (branch, base_branch, status, reason_codes, pipeline_status, git_boundary_status, execution_attempted, execution_results_summary, etc.)
- A `report_path` to trigger run-report.txt creation — the report content is generated as part of the smokethe run_persistence module writes manifest.json with "run-report.txt" in the files list when report_path is provided
- After `persist_run_record()`, write a deterministic run-report.txt to the run directory via the actual report writer or inline

## PROCESS CLEANUP CONTRACT

1. On success: send SIGTERM to the server subprocess, wait up to 5 seconds, then check process alive. If still alive, send SIGKILL. Remove temp directory.
2. On failure: same termination sequence. Remove temp directory.
3. The cleanup must be in a try/finally block to ensure it runs on all exit paths.
4. After cleanup, verify no server process remains (process.poll() is not None).
5. After cleanup, verify the temp directory is removed.
6. After cleanup, verify the real repository `.ariadne/runs` is unmodified (snapshot diff check).

## ROUTE ASSERTION CONTRACT

The smoke must assert for each route:

| Route | Assertion |
|---|---|
| GET /health | status 200, body contains `"status": "ok"` |
| GET /workspace | status 200, content-type text/html |
| GET /workspace | body contains `artifact-workspace` |
| GET /workspace | body contains `zone-timeline` |
| GET /workspace | body contains `zone-canvas` |
| GET /workspace | body contains `zone-gates-proofs` |
| GET /workspace | body contains `zone-logs-captures` |
| GET /workspace | body contains detail rendering hooks |
| GET /workspace | body contains report viewer hooks |
| GET /workspace | body contains gates/proofs hooks |
| GET /workspace | body contains logs/captures hooks |
| GET /runs | status 200, JSON with ev_contract_version "1", runs array non-empty |
| GET /runs/<smoke-run-id> | status 200, JSON with ev_contract_version "1", summary.run_id matches |
| GET /runs/<smoke-run-id>/report | status 200, JSON with ev_contract_version "1", content non-empty |

## PR 0143–0147 PRESERVATION CONTRACT

| Behavior | How preserved |
|---|---|
| server.py unchanged | Operator wraps, does not modify, the existing app |
| runs_root query override for tests | Tests continue to supply runs_root via query string — only operator mode disables it |
| All existing routes | Operator wraps the same ASGI app — all routes preserved |
| GET /workspace zones | Smoke verifies all four zones unchanged |
| PR 0145 detail behavior | Smoke verifies detail rendering hooks in workspace HTML |
| PR 0146 report behavior | Smoke verifies report viewer hooks in workspace HTML |
| PR 0147 gates/logs behavior | Smoke verifies gates/proofs and logs/captures hooks in workspace HTML |

## PR 0147B DEFERRAL CONTRACT

The following are intentionally excluded:
- Planner/plan-review/coder/precommit prompts
- Agent-role routing or execution
- Dangerous-action proposals or approval records
- Commit/push/PR approval
- Command queues or work persistence
- Orchestrator UI or API
- Any mutation or execution from the workspace surface

## IMPLEMENTATION FILE SCOPE

### Approved files

#### 1. pyproject.toml (EDIT)

**Action**: Edit.
**Exact changes**: Add `uvicorn>=0.29.0` to `[project.optional-dependencies] dev` list.

#### 2. services/task_intake/src/task_intake/local_operator.py (NEW)

**Action**: New file.
**Exact responsibility**: Local operator server entrypoint with server-owned runs-root configuration.
**Content**:
- CLI arg parser for --host, --port, --runs-root, --check, --allow-public-bind, --allow-privileged-port
- Runs-root resolution and normalization
- ASGI app factory or wrapper that ignores browser-supplied runs_root query parameter
- Startup diagnostics printing
- Safe defaults (127.0.0.1, port 8000)
- Delegation to uvicorn.run()
**Content prohibited**: No agent launch. No orchestration. No git/gh/Docker. No external network calls. No mutation.

#### 3. services/task_intake/src/task_intake/server.py (EDIT)

**Action**: Edit.
**Exact changes**: Add an optional `runs_root` parameter to the `app` function signature. When provided, it is stored in `scope["app_runs_root"]`. The GET /runs and GET /runs/<run_id> routes check for `scope.get("app_runs_root")` first. If present, it takes precedence over the query string `runs_root` parameter. When absent (default, backward-compatible), the query string behavior is unchanged.
**Narrow diff**: One optional parameter in the `app` function signature, one `scope.__setitem__` call, and two `runs_root` resolution blocks updated to check `scope` first.

#### 4. docs/LOCAL_OPERATOR.md (NEW)

**Action**: New file.
**Exact responsibility**: Complete operator runbook per the OPERATOR RUNBOOK CONTRACT.

#### 5. Makefile (EDIT)

**Action**: Edit.
**Exact changes**: Add `local-operator` target:
```makefile
local-operator:
	python -m task_intake.local_operator
```
Support `PORT` override:
```makefile
local-operator:
	python -m task_intake.local_operator --port $(PORT)
```

#### 6. scripts/smoke-local-operator.py (NEW)

**Action**: New file.
**Exact responsibility**: End-to-end HTTP smoke that proves the local operator against a canonical persisted run.
**Content**: Per the END-TO-END SMOKE CONTRACT and SMOKE FIXTURE CONTRACT.
**Subprocess usage**: Strictly limited to launching and terminating the operator.

#### 7. services/task_intake/tests/test_local_operator.py (NEW)

**Action**: New file.
**Exact responsibility**: Unit tests for the local operator module.
**Content**: Tests for:
- Default host and port
- Port validation (reject <1024 without flag, reject >65535)
- Runs-root normalization
- Runs-root creation when absent
- --check mode outputs valid JSON
- No 0.0.0.0 default
- --allow-public-bind enables 0.0.0.0
- Read-only messaging
- No agent/git/gh/Docker references in module source

#### 8. .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/IMPLEMENTATION_REPORT.md (NEW)

All 11 required sections.

#### 9. .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/reviews/precommit-review.yml (NEW)

Follows review-artifact.schema.yml.

### Roadmap documentation (NOT modified during planning)

The following files will be edited during implementation:
- `ROADMAP.md` — add PR 0147A governance insertion note after PR 0147, preserving PR 0148
- `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md` — add PR 0147A-D insertion notes

These are documented here but NOT written during this planning task.

### Not modified

- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/runner/tests/test_run_persistence.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/src/task_intake/artifact_workspace.py
- services/task_intake/src/task_intake/doctor.py
- services/task_intake/src/task_intake/app.py
- services/task_intake/src/task_intake/smoke.py
- services/task_intake/tests/test_artifact_workspace_shell.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- services/task_intake/tests/test_task_intake_smoke.py
- README.md
- docs/START_HERE.md, docs/REPOSITORY_STRUCTURE.md, docs/DEVELOPMENT_ORDER.md, docs/AGENTS.md
- agents/**, schemas/**, .github/**, etc.

## TEST PLAN

### 1. Local Operator Unit Tests

```bash
PYTHONPATH=services/task_intake/src python -m pytest services/task_intake/tests/test_local_operator.py -q
```

Expected: all operator config tests pass.
If not met: block.

### 2. End-to-End Smoke

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-local-operator.py
```

Expected: all smoke assertions pass.
If not met: block.

### 3. Existing Workspace Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q
```

Expected: all workspace tests pass.
If not met: block.

### 4. Existing Detail API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all 73+ route tests pass.
If not met: block.

### 5. Serialization Contract Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```

Expected: all contract tests pass.
If not met: block.

### 6. Runtime Evidence Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_runtime_evidence.py -q
```

Expected: all 32 tests pass.
If not met: block.

### 7. Run Persistence Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_persistence.py -q
```

Expected: all persistence tests pass.
If not met: block.

### 8. Python Compile

```bash
python -m compileall -f services/task_intake/src services/runner/src
```

Expected: all files compile.
If not met: block.

### 9. Full Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests test task_intake tests -q
```

Expected: all tests pass.
If not met: block.

### 10. Post-Smoke Repository Check

```bash
git diff --name-only -- .ariadne/; echo "EXIT:$?"
```

Expected: exit code 1 (no changes to .ariadne) — or empty output if .ariadne is untracked.
If not met: block.

### 11. Post-Smoke Process Check

```bash
pgrep -f "local_operator" || echo "no process"
```

Expected: "no process" — no lingering server.
If not met: block.

### 12. Loopback-Default Grep

```bash
grep -n "127\.0\.0\.1" services/task_intake/src/task_intake/local_operator.py
```

Expected: default host is 127.0.0.1.
If not met: block.

### 13. Public-Bind Prohibition Grep

```bash
grep -n "0\.0\.0\.0" services/task_intake/src/task_intake/local_operator.py
```

Expected: 0.0.0.0 only appears in --allow-public-bind context, not as default.
If not met: block.

### 14. runs_root Browser-Override Check

```bash
grep -n "runs_root\|app_runs_root\|query_string\|parse_qs" services/task_intake/src/task_intake/server.py
```

Expected: app_runs_root scope check present, query string fallback still exists for test compat.
If not met: block.

### 15. No Agent/Orchestration Grep

```bash
grep -n -i "agent\|orchestrat\|launch.*process\|subprocess\|Popen" services/task_intake/src/task_intake/local_operator.py; echo "EXIT:$?"
```

Expected: no agent/orchestration/subprocess references (subprocess only in smoke, not in the operator).
If not met: block.

### 16. Smoke Process Management Grep

```bash
grep -n -E "subprocess|Popen|terminate|kill|SIGTERM|wait\(\)|timeout" scripts/smoke-local-operator.py
```

Expected: bounded process management present.
If not met: block.

### 17. Forbidden-Path Diff

```bash
git diff --name-only -- services/runner/ agents/ schemas/ .github/ .project-memory/pr/0143* .project-memory/pr/0144* .project-memory/pr/0145* .project-memory/pr/0146* .project-memory/pr/0147*
```

Expected: empty (no modification of earlier PR artifacts or backend files).
If not met: block.

### 18. Planning-Lock, Whitespace, Dirty Tree, Cached Diff

Standard checks per previous PRs.

### 19. IMPLEMENTATION_REPORT.md Existence and Readback

Standard checks.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. PLAN.md or plan-review.yml changes.
3. The operator does not bind to 127.0.0.1 by default.
4. Browser input can select an arbitrary runs root in operator mode.
5. The runs root is not normalized and server-owned.
6. Startup output omits workspace URL, runs root, or read-only warning.
7. Startup failure returns success.
8. Shutdown leaves a process or socket.
9. The smoke bypasses the official operator entrypoint.
10. The smoke handcrafts evidence despite a canonical persistence API existing.
11. The smoke writes into repository `.ariadne`.
12. The smoke lacks a bounded readiness timeout (5 seconds).
13. The smoke fails to clean up on failure.
14. Any required route is not tested.
15. PR 0143–0147 behavior regresses.
16. Agent launch, orchestration, mutation, git, gh, Docker, or external services are added.
17. PR 0147B or later work is absorbed.
18. PR 0148 or later slots are renumbered.
19. Required tests or smoke fail.
20. IMPLEMENTATION_REPORT.md is absent or incomplete.
21. Unknown untracked files exist.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0147a-local-operator-launch-end-to-end-smoke`.
2. Only approved files changed.
3. Planning artifacts remain locked.
4. PR 0147A insertion is recorded in roadmap docs.
5. PR 0148 numbering remains unchanged.
6. One launch strategy implemented (OPTION B).
7. One primary command exists (`make local-operator`).
8. One smoke command exists (`python -m scripts.smoke_local_operator`).
9. Default host is loopback (127.0.0.1).
10. Default port is deterministic (8000).
11. Port override is validated.
12. Runs root is normalized and server-owned.
13. Browser arbitrary-path override is unavailable in operator mode.
14. Startup prints health URL, workspace URL, runs root, and read-only status.
15. Invalid startup configuration fails clearly.
16. Ctrl-C or termination shuts down cleanly.
17. Smoke uses canonical persisted run data via run_persistence.
18. Smoke uses an isolated temporary root.
19. Smoke launches the official operator entrypoint.
20. Smoke checks health, workspace, run index, detail, report.
21. Smoke checks all four workspace zone selectors.
22. Smoke has bounded readiness timeout.
23. Smoke cleans up on success and failure.
24. No repository `.ariadne` mutation.
25. No lingering server process after smoke.
26. PR 0143–0147 regressions pass.
27. No agent launch, orchestration, mutation, git, gh, Docker, or external services.
28. IMPLEMENTATION_REPORT.md exists and was read back.
29. PLAN DRIFT GATE passed.
30. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. A correct supported server strategy cannot be identified (uvicorn exists as try/except — adding as explicit dep is the right choice).
2. Packaging cannot support the documented command (uvicorn is a standard PyPI package).
3. runs-root browser control cannot be disabled safely in operator mode (app closure/wrapper approach is proven safe).
4. A public bind would be required (never — loopback is enforced).
5. A canonical persisted-run fixture cannot be created (run_persistence.persist_run_record exists).
6. Smoke cleanup cannot be guaranteed (try/finally + SIGTERM+SIGKILL is proven).
7. Existing route compatibility would require an unapproved breaking change (scope["app_runs_root"] is additive).
8. An unapproved file must change.
9. Agent launch or orchestration would be required.
10. Required validation fails.

## NON-GOALS

1. Implementing the launcher, smoke, tests, or docs (planning task only).
2. Writing plan-review.yml, IMPLEMENTATION_REPORT.md, or precommit-review.yml during planning.
3. Agent launch.
4. Orchestration.
5. Dangerous-action approval.
6. Commit, push, or PR controls.
7. Mutation.
8. Production deployment, public hosting, authentication, or TLS.
9. Docker.
10. External services.
11. Browser automation.
12. Implementing PR 0147B, PR 0147C, PR 0147D, or PR 0148.
13. Committing, pushing, or creating a pull request.
