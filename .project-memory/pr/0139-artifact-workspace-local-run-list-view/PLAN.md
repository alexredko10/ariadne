# PR 0139 — Artifact Workspace Local Run List View Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Artifact Workspace Read-Only UI (Stream 1) |
| **Slot** | PR 0139 (second read-only UI stream PR, after PR 0138 read model) |
| **Why this PR is next** | PR 0138 added the read-only runtime evidence read model (`runtime_evidence.py`) with `list_run_evidence_summaries()` and `read_run_evidence_detail()`. PR 0139 adds the first read-only UI slice on top: a local run list view. The existing ASGI server (`services/task_intake/src/task_intake/server.py`) serves an inline HTML/JS page at `GET /` with a mock run history panel (`__ariadne_run_history` JS array). This PR replaces the browser-only mock run history with evidence-backed data from `runtime_evidence.py` via a new `GET /runs` route. |
| **Batching policy** | Single-purpose: local run list view. No run detail panel, no Artifact Workspace Shell, no mutation. |
| **Drift heuristic** | Does not open UI mutation, agent launch from UI, commit from UI, or PR creation from UI. Does not implement Visual Gate, Context Core, PCAM/PBS, Rubrics, Decision Core, Model Router, or ETL/ERP demo. No new frontend stack, no new dependencies. |

## Discovery Evidence

### Existing UI Stack

The repository has **one existing local UI stack** — an ASGI server in
`services/task_intake/src/task_intake/server.py` that serves an inline
HTML/JS page at `GET /`. Key characteristics:

- **No React, Vite, Playwright, Jest, or Vitest** — no config files found
  for any of these tools.
- **`package.json`** exists at repo root but no `node_modules/` or frontend
  build files are present.
- **`apps/web/src/README.md`** exists but no `.tsx`, `.ts`, or `.jsx` files
  were found in the repo outside vendor directories.
- The page in `server.py` uses **vanilla JavaScript** (no framework) with
  inline `<style>` and `<script>` tags.
- The existing **run history** (`#run-history-section`) is populated by a
  browser-only JS array (`__ariadne_run_history`) that stores entries when
  `POST /runs/execute` returns. This is mock data, not evidence-backed.
- Tests for the existing UI (`services/task_intake/tests/`) parse the
  rendered HTML string and assert on element presence. The test file
  `test_local_run_history_in_page.py` has tests like
  `test_page_contains_run_history_section`, `test_history_empty_before_submit`,
  `test_history_has_list_container`.

### Import Path

`services/task_intake/src/task_intake/test_mode.py` already demonstrates
that modules from `services/runner/src/runner/` are importable when
`PYTHONPATH` includes `services/runner/src`. The `test_mode.py` file uses:

```python
from task_intake.execution_handoff import run_mock_execution_handoff
```

PR 0139 will import `runtime_evidence` from `runner.runtime_evidence` in
the same way.  The test runner uses `PYTHONPATH=services/runner/src:services/task_intake/src`.

### PR 0138 Read Model

`services/runner/src/runner/runtime_evidence.py` provides:

- `list_run_evidence_summaries(runs_root)` — returns `tuple[RunEvidenceSummary]`
- `read_run_evidence_detail(runs_root, run_id)` — returns `RuntimeEvidenceReadResult`
- `RunEvidenceSummary` with: `run_id`, `status`, `reason_codes`,
  `pipeline_status`, `git_boundary_status`, `execution_attempted`,
  `created_at`, `run_json_path`, `manifest_path`, `run_report_path`,
  `pr_url`, `missing_evidence`, `malformed_evidence`.

## UI Slice Identity

1. PR 0139 is the **Artifact Workspace Local Run List View**.
2. This is the **first read-only UI slice** after the runtime evidence
   read model.
3. This is **not the full Artifact Workspace Shell** (Stream 2, PR 0143+).
4. This is **not a run detail panel** (PR 0145).
5. This is **not a mutation surface**.
6. This view exists to support **dogfooding across multiple projects**.
7. The view reads from **runtime-owned persisted evidence** and does not
   trust agent claims.

## Implementation Scope

| File | Action | Justification |
|------|--------|---------------|
| `services/task_intake/src/task_intake/server.py` | Add `GET /runs` route. Update HTML/JS to fetch evidence-backed run list from `GET /runs` and display in the run history panel. | Evidence: `server.py` is the existing ASGI server with the inline HTML/JS UI. Adding a `GET /runs` route that calls `list_run_evidence_summaries()` from `runner.runtime_evidence` provides the evidence-backed data. Updating the HTML/JS replaces the browser-only mock `__ariadne_run_history` with real evidence. |
| `services/task_intake/tests/test_local_run_history_in_page.py` | Update tests to verify evidence-backed run list displays correctly. | Evidence: This test file already tests the run history panel. Tests must be updated to verify `GET /runs` data appears. |
| *(Optional)* `services/runner/src/runner/runtime_evidence.py` | Add optional `runs_root_finder()` helper if the default `.ariadne/runs` path needs derivation from `repo_root`. | Evidence: The existing `list_run_evidence_summaries()` requires an explicit `runs_root`. The server needs to derive the runs root from the repo root. A small helper `default_runs_root(repo_root)` is justified if the derivation logic is non-trivial or needs testing. The alternative is inline `os.path.join(repo_root, ".ariadne", "runs")` in the route handler. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/src/runner/run_persistence.py` | Not modified. Read model imports types but does not modify persistence. |
| `services/runner/src/runner/ariadne_task_cli.py` | Not modified. Read model imports types only. |
| `services/runner/src/runner/git_boundary.py` | Not modified. No git interaction. |
| `services/runner/tests/conftest.py` | Not modified. Existing residue fixture handles `.ariadne/`. |
| `services/task_intake/tests/test_runs.py` | Not modified. Existing mock run tests remain unchanged. |
| `services/task_intake/tests/test_task_intake.py` | Not modified. Task intake acceptance tests remain unchanged. |

### Not Modified

- `ROADMAP.md`
- `docs/`, `agents/`, `schemas/`
- `pyproject.toml`, `poetry.lock`, `requirements*.txt`
- `.gitignore`
- All previous PR artifacts (0131–0138)
- `services/runner/src/runner/git_boundary.py`, `run_persistence.py`, `ariadne_task_cli.py`

## Required View Content

The run list view must display, at minimum, for each run:

1. `run_id`
2. `status` (with visual distinction: completed/blocked/failed/unknown)
3. `reason_codes` (summary or count)
4. `pipeline_status`
5. `git_boundary_status`
6. `execution_attempted`
7. `run.json` availability indicator
8. `manifest.json` availability indicator
9. `run-report.txt` availability indicator
10. Missing evidence count or indicator
11. Malformed evidence count or indicator
12. PR URL if persisted
13. Payload cleanliness indicator if available
14. Readiness indicator if available
15. Deterministic ordering (newest first, matching `runtime_evidence.py`)

The view must **not fabricate missing data**. Missing and malformed
evidence must be rendered explicitly (e.g. "missing", "malformed" labels).

### Read Model Integration

1. The view uses `runner.runtime_evidence.list_run_evidence_summaries()`
   directly. No thin adapter is needed because the existing import path
   (`services/task_intake/src/task_intake/` importing from
   `runner.runtime_evidence`) is already established by `test_mode.py`.

2. If a `runs_root` derivation helper is added, it must be read-only and
   must not change `runtime_evidence.py` behavior.

3. The `/runs` route accepts an optional `runs_root` query parameter, or
   defaults to `<repo_root>/.ariadne/runs` where `repo_root` is the
   `server.py`'s working directory or a configured constant.

4. The view does not assume production secrets or external services.
5. The view does not require a real git repo (it reads filesystem artifacts
   only).

## Dogfood Purpose

PR 0139 is for Ariadne dogfood usability across parallel projects.

The run list view answers:

1. Which Ariadne runs exist locally?
2. Which project/task/PR does a run appear to belong to, if available
   from persisted evidence (branch, pr_id)?
3. Which runs completed, blocked, or failed?
4. Which runs have missing or malformed evidence?
5. Which runs have execution evidence?
6. Which runs have PR URL evidence?
7. Which runs need a detail view next?

## Route Design

### GET /runs

**Request**: `GET /runs` (optional query param `runs_root`)

**Response**:
```json
{
  "ok": true,
  "count": 2,
  "runs": [
    {
      "run_id": "run-001",
      "status": "completed",
      "reason_codes": ["completed"],
      "pipeline_status": "completed",
      "git_boundary_status": "approved",
      "execution_attempted": true,
      "created_at": "2026-07-10T12:05:00Z",
      "run_json_available": true,
      "manifest_available": true,
      "run_report_available": true,
      "missing_evidence": [],
      "malformed_evidence": [],
      "pr_url": null,
      "payload_cleanliness_available": false,
      "readiness_available": false
    }
  ],
  "runs_root": "/path/to/.ariadne/runs"
}
```

**Error response**:
```json
{
  "ok": false,
  "count": 0,
  "runs": [],
  "error": "runs_root not found or unreadable"
}
```

### HTML Integration

The existing `#run-history-section` in the HTML page at `GET /` will be
updated to:

1. Fetch `GET /runs` on page load and after each `POST /runs/execute`.
2. Populate `#run-history-list` with evidence-backed run entries.
3. Show per-run status, evidence indicators, and PR URL when available.
4. Show empty/missing state when no runs or runs root not found.
5. Keep the existing `pushRunHistory`/`renderRunHistory` pattern but source
   data from the server instead of the browser-only JS array.

The existing mock run history (`__ariadne_run_history`) may be preserved
for backward compatibility with the feedback/session-report pipeline, or
replaced entirely.  The integration approach that preserves the existing
JS function signatures while sourcing data from the evidence API is
preferred.

## Tests

### Test Requirements (20 tests)

1. **Empty run list renders without crash** — `GET /runs` with empty
   runs directory returns `{"ok": true, "count": 0, "runs": []}`.
2. **Missing runs root renders empty state** — `GET /runs` with
   nonexistent runs root returns `{"ok": false, "error": "..."}`.
3. **Complete run appears in list** — `GET /runs` returns a run entry
   with `status: "completed"`.
4. **Blocked run appears in list** — `GET /runs` returns blocked run.
5. **Failed run appears in list** — `GET /runs` returns failed run.
6. **Missing manifest indicator is visible** — Run entry has
   `"manifest_available": false`.
7. **Missing run-report indicator is visible** — Run entry has
   `"run_report_available": false`.
8. **Malformed run.json indicator is visible** — Run entry has
   `"malformed_evidence"` containing `"run.json"`.
9. **PR URL appears only when present** — Run entry has non-null
   `pr_url` when PR URL is in execution results.
10. **No PR URL fabricated** — Run entry has `pr_url: null` when absent.
11. **reason_codes displayed or summarized** — Run entry includes
    `reason_codes` array.
12. **execution_attempted displayed** — Run entry includes
    `execution_attempted` boolean.
13. **Payload cleanliness available indicator** — Run entry includes
    `payload_cleanliness_available` boolean (initially `false` until
    PR 0140 adds detail aggregation).
14. **Readiness available indicator** — Run entry includes
    `readiness_available` boolean (initially `false` until PR 0140).
15. **Deterministic ordering** — Runs sorted by `run_id` descending
    (newest first).
16. **Tests use temporary/local fixtures only** — No real `.ariadne/runs`.
17. **Tests do not use real project .ariadne** — Assertion that real
    `.ariadne/runs` is not accessed.
18. **Tests do not shell out** — No subprocess, os.system, shell=True.
19. **Tests do not run agents** — No agent invocation.
20. **Tests do not mutate runtime state** — No writes to `.ariadne/`.

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
  services/task_intake/tests/test_local_run_history_in_page.py \
  services/task_intake/tests/test_runs.py \
  services/runner/tests/test_runtime_evidence.py \
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
  services/runner/tests/test_runtime_evidence.py \
  services/task_intake/tests/test_task_intake.py \
  services/task_intake/tests/test_app_runtime.py \
  -q
```

Expected: regression subset passes.
If not met: block.

### 4. Grep for Run List View

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "runs_root|list_run_evidence_summaries|RunEvidenceSummary|run_json_available|manifest_available|run_report_available|missing_evidence|malformed_evidence|pr_url|payload_cleanliness|readiness" \
  services/task_intake/src/task_intake \
  services/task_intake/tests \
  .project-memory/pr/0139-artifact-workspace-local-run-list-view
```

Expected: run list route and view implementation are visible.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system" \
  services/task_intake/src/task_intake \
  services/task_intake/tests \
  .project-memory/pr/0139-artifact-workspace-local-run-list-view
```

Expected: no unsafe real mutation authority added.
If unsafe new mutation is found: block.

### 6. Git Status

```bash
git status --short
```

Expected: only expected PR 0139 files are dirty (server.py, test file,
optional runtime_evidence.py helper, PLAN.md, review artifacts).
If services/runner unchanged files are modified: block.
If agents/, schemas/, docs/, dependencies, .gitignore modified: block.
If unknown untracked files exist: block.

### 7. Git Diff

```bash
git diff --name-only
```

Expected: only expected PR 0139 implementation files are listed.
If `ROADMAP.md`, `agents/`, `schemas/`, `pyproject.toml`, `.gitignore`,
or previous PR artifacts appear: block.

### 8. Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty during planning.
If staged files exist: block.

### 9. PLAN DRIFT GATE

Verify that only the planned files are changed:
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_local_run_history_in_page.py`
- (optional) `services/runner/src/runner/runtime_evidence.py`
- `.project-memory/pr/0139-artifact-workspace-local-run-list-view/PLAN.md`
- `.project-memory/pr/0139-artifact-workspace-local-run-list-view/reviews/plan-review.yml`
- `.project-memory/pr/0139-artifact-workspace-local-run-list-view/reviews/precommit-review.yml`

If any other file is modified: block.

### 10. NO-DRIFT CHECK

- No changes to `git_boundary.py`, `run_persistence.py`, `ariadne_task_cli.py`,
  `conftest.py`, `agents/`, `schemas/`, `pyproject.toml`, `.gitignore`,
  `ROADMAP.md`.
- No UI mutation code.
- No agent launch code.
- No commit/PR creation code.
- No run detail panel code.
- No new frontend dependencies.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131–0136 Production Line | All existing code unchanged. View only reads their output. |
| PR 0137 Roadmap Unlock | Not modified. |
| PR 0138 Read Model | `runtime_evidence.py` functions unchanged (optional helper may be added without changing existing API). |
| Git Boundary authority | `git_boundary.py` not modified. View has no git interaction. |
| Run persistence | `run_persistence.py` not modified. View reads through read model. |
| Residue isolation | `conftest.py` not modified. Tests use `tmp_path`. |
| Commit payload cleanliness | `ariadne_task_cli.py` not modified. |
| Run report | `_write_run_report` not modified. View reads report path from summary. |
| Readiness gate | `_evaluate_readiness` not modified. |

## Non-Goals

- No run detail panel.
- No Artifact Workspace Shell.
- No visual design system.
- No Mermaid gate.
- No artifact gallery.
- No artifact accept/reject.
- No runtime mutation.
- No agent execution.
- No git or gh execution.
- No PR creation.
- No run creation.
- No persistence mutation.
- No Context Core.
- No PCAM/PBS.
- No Rubrics.
- No Decision Core.
- No Model Router.
- No ETL/ERP demo.
- No new frontend framework or dependencies.

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0139-artifact-workspace-local-run-list-view`
- PLAN does not define PR 0139 as the first read-only UI slice after the read model
- PLAN states that this PR creates a run detail panel, Artifact Workspace Shell, or mutation surface
- PLAN implements mutation (write, git, gh, agents, commit, PR)
- PLAN modifies `git_boundary.py`, `run_persistence.py`, `ariadne_task_cli.py`, `conftest.py`
- PLAN modifies `agents/`, `schemas/`, dependencies, `.gitignore`, `ROADMAP.md`
- PLAN adds a new frontend stack or framework dependency
- PLAN adds .gitignore entries
- PLAN opens UI mutation, agent launch from UI, commit from UI, or PR creation from UI
- PLAN implements any capability from frozen streams
