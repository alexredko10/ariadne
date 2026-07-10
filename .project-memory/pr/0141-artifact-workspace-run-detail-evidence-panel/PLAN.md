# PR 0141 — Artifact Workspace Run Detail Evidence Panel Plan

## EVIDENCE SNAPSHOT

- Branch: `0141-artifact-workspace-run-detail-evidence-panel`
- HEAD: `f5bcb08725ebac48ffb87b930525f38d58772b10`
- origin/main: `f5bcb08725ebac48ffb87b930525f38d58772b10` (HEAD == origin/main)
- Merge base: `f5bcb08725ebac48ffb87b930525f38d58772b10`
- Dirty tree: clean (no modified tracked files)
- Cached diff: empty
- Known generated residue: none present

### PR 0140 Artifacts Present

- `.project-memory/pr/0140-implementation-handoff-artifact-contract/PLAN.md` — FOUND
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/reviews/plan-review.yml` — FOUND
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/reviews/precommit-review.yml` — FOUND
- `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md` — FOUND
- `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md` — FOUND

### Current GET /runs Behavior (from server.py L909-954)

- Route: `GET /runs`
- Default runs_root: `os.path.join(os.getcwd(), ".ariadne", "runs")`
- Response: JSON with `ok`, `count`, `runs`, `runs_root`
- Each run entry has: `run_id`, `status`, `reason_codes`, `pipeline_status`,
  `git_boundary_status`, `execution_attempted`, `created_at`,
  `run_json_available`, `manifest_available`, `run_report_available`,
  `missing_evidence`, `malformed_evidence`, `pr_url`,
  `payload_cleanliness_available: False`, `readiness_available: False`
- Import: `from runner.runtime_evidence import list_run_evidence_summaries`

### Current read_run_evidence_detail() Result Shape (from runtime_evidence.py L279-414)

- Accepts: `runs_root`, `run_id`
- Returns: `RuntimeEvidenceReadResult` with `ok`, `error`, `summary`
  (`RunEvidenceSummary`), `detail` (`RunEvidenceDetail`), `missing`,
  `malformed`
- `RunEvidenceDetail` fields: `summary`, `execution_results`,
  `manifest_files`, `run_json_hash`, `report_preview`, `payload_cleanliness`,
  `readiness`, `evidence_paths`, `source_errors`
- **Payload cleanliness**: always `None` (line 401: `payload_cleanliness=None`)
- **Readiness**: always `None` (line 402: `readiness=None`)
- **Missing evidence**: `MissingEvidenceNotice` with `expected_path` and `reason`
- **Malformed evidence**: same structure

### Existing Run-List HTML/JS (from server.py inline page)

- `fetchRuns()` fetches `GET /runs` — renders run_id, status, evidence
  indicators, PR link in `.history-entry` divs
- No detail route exists
- No selection behavior exists on history entries
- No detail panel div exists
- Page already has `#run-history-list`, `#run-history-section`

## ROADMAP DRIFT AND ABSORPTION MAP

### Original Detailed Roadmap Slots

From `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`:

| Slot | Original Name | Actual PR | Status |
|------|---------------|-----------|--------|
| 0138 | UI Runtime Evidence Read Model | 0138 | Merged — run index, detail aggregator |
| 0139 | Local Run Index Reader | 0139 (absorbed into 0138) | Absorbed |
| 0140 | Run Detail Evidence Aggregator | Inserted: Implementation Handoff Contract | Merged as PR 0140 |
| 0141 | Runtime Evidence API Surface | 0141 (partially absorbed by 0139) | This PR — narrow detail panel |
| 0145 | Run Detail Evidence Panel | Absorbed into 0141 | Absorbed |

### Absorption Statement

PR 0138 absorbed the original "Local Run Index Reader" (0139) and "Run Detail
Evidence Aggregator" (0140) foundations into its single `runtime_evidence.py`
module with both `list_run_evidence_summaries()` and `read_run_evidence_detail()`.

PR 0139 absorbed part of the original "Runtime Evidence API Surface" (0141) by
adding `GET /runs` to the task_intake server and the local run-list view.

PR 0140 was inserted as workflow hardening (Implementation Handoff Artifact
Contract) between the read model and the first UI slice.

PR 0141 is now the next narrow read-only product slice: a **selected-run detail
evidence panel** backed by the existing `read_run_evidence_detail()` model.

PR 0145's original "Run Detail Evidence Panel" scope is absorbed into this PR.

## UI SLICE IDENTITY

1. PR 0141 is the **Run Detail Evidence Panel** — the first detail-level UI
   after the run list view.
2. This is a **read-only detail slice** — no mutation, no shell, no accept/reject.
3. This is **not the full Artifact Workspace Shell**.
4. This is **not a run-report full viewer or manifest full viewer**.
5. This is **not a serialization-contract PR**.

## USER INTERACTION

1. Each run-list row (`.history-entry`) becomes clickable with a button or
   accessible link-like control.
2. Clicking a row selects that run — the row is highlighted and a detail panel
   appears.
3. Selection uses a deterministic non-mutating interaction: `fetch(GET /runs/<run_id>)`.
4. The detail panel replaces its content on each new selection (no accumulation).
5. The selected `run_id` is visibly displayed in the detail panel.
6. Interaction is keyboard-accessible (native button/link elements).
7. No frontend framework is introduced.

## DETAIL ENDPOINT

**Route**: `GET /runs/<run_id>`

**runs_root handling**: Consistent with the existing `GET /runs` route — default
to `os.path.join(os.getcwd(), ".ariadne", "runs")`, accept optional query param
`runs_root`.

**run_id validation**:
- Reject path-traversal patterns (`../`, `..\\`, `/`, `\`) by checking that
  `run_id` contains only `[a-zA-Z0-9_\-]` characters.
- Reject empty or whitespace-only `run_id`.
- Reject `run_id` longer than 128 characters.

**Unknown run_id**: Return HTTP 200 with `ok: false`, `error: "run not found"`.

**Missing run.json**: Returns what `read_run_evidence_detail` returns — `ok: false`,
`missing` containing `MissingEvidenceNotice` with `reason: "file_not_found"`.

**Partial evidence**: Returns `ok: false` with `missing` notices for each absent
file and `malformed` notices for unreadable files, plus whatever `detail`
fields are available.

**Malformed evidence**: Returns `ok: false` with `malformed` notices.

**HTTP status**: Always 200 (the response body carries `ok: true/false` and error
details). This matches the existing `GET /runs` pattern.

**Deterministic JSON serialization**: Use `json.dumps(sort_keys=True, ensure_ascii=False)`
consistent with the existing route.

**No new persistence layer**: Only reads through `read_run_evidence_detail()`.

**No runtime/git/gh/Docker/agent calls**: Strictly read-only.

## DETAIL RESPONSE

```json
{
  "ok": true,
  "summary": {
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
    "pr_url": null
  },
  "detail": {
    "execution_results": [{"operation": "git_status", "exit_code": "0"}],
    "manifest_files": ["run.json", "run-report.txt"],
    "run_json_hash": "abc123def4567890",
    "report_preview": "Ariadne Run Report\nRun ID: run-001\n...",
    "evidence_paths": ["/path/to/run.json", "/path/to/manifest.json"],
    "source_errors": []
  },
  "payload_cleanliness": null,
  "readiness": null,
  "missing": [],
  "malformed": [],
  "error": null
}
```

### Unavailable-Value Policy

| Field | Unavailable Value |
|-------|-------------------|
| `payload_cleanliness` | `null` |
| `readiness` | `null` |
| `run_json_hash` | `null` |
| `report_preview` | `null` |
| `manifest_files` | `[]` |
| `evidence_paths` | `[]` |
| `source_errors` | `[]` |
| `pr_url` | `null` |

Missing and malformed evidence are always listed in the `missing` and
`malformed` arrays with `expected_path` and `reason`. These are never silently
omitted.

## DETAIL PANEL

1. A new `<div id="run-detail-panel">` is added below `#run-history-list`.
2. Initially hidden (display: none) until a run is selected.
3. On selection, `fetch(GET /runs/<run_id>)` is called and the response is
   rendered into sections.
4. Sections: Summary, Execution Results, Manifest Files, Report Preview,
   Evidence Paths, Notices.
5. Unavailable values render as "not available" or "none" rather than being
   silently omitted.
6. Persisted text values are safely rendered using `textContent` assignment
   or escaped HTML — no unsafe concatenation of report content.
7. The existing run list, summary card, trace, feedback, and all other UI
   sections are preserved.
8. No mutation buttons: no accept, reject, approve, retry, rerun, commit,
   push, or create-PR actions.
9. The panel stays within the existing page — no four-zone shell.

## EXACT FILE SCOPE

### Production Files

| File | Action | Justification |
|------|--------|---------------|
| `services/task_intake/src/task_intake/server.py` | Modify: add `GET /runs/<run_id>` route, add `read_run_evidence_detail` import, add detail panel HTML/JS | Existing server already has `GET /runs`. Adding detail route is the minimal extension. |

### Test Files

| File | Action | Justification |
|------|--------|---------------|
| `services/task_intake/tests/test_local_run_history_in_page.py` | Modify: add tests for detail endpoint and panel | Existing test file for run history and list view. Adding detail tests here keeps the run evidence tests together. |

### Artifact Files

| File | Owner | Phase |
|------|-------|-------|
| `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/PLAN.md` | Planner | Pre-planning |
| `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/plan-review.yml` | Plan-review | Post-planning |
| `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md` | Coder | Post-implementation |
| `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml` | Precommit-review | Post-implementation |

### Not Modified

- `services/runner/src/runner/runtime_evidence.py` — no evidence-triggered gap
  demonstrated. The existing `read_run_evidence_detail()` provides all needed
  fields.
- `services/runner/tests/test_runtime_evidence.py` — not modified.
- `ROADMAP.md`, `docs/`, `agents/`, `schemas/`, `pyproject.toml`, `.gitignore`
- All previous PR artifacts (0131–0140)

## TEST PLAN

### Detail Endpoint Tests

1. **Complete run detail response** — `GET /runs/run-001` returns ok=true with
   summary, detail, execution_results, manifest_files, report_preview,
   evidence_paths.
2. **Blocked or failed run detail response** — status reflected correctly.
3. **Unknown run_id** — returns ok=false, error "run not found", 200 status.
4. **Missing run.json** — returns ok=false with missing notice for run.json.
5. **Missing manifest** — ok=false with missing notice for manifest.json.
6. **Malformed manifest** — ok=false with malformed notice.
7. **Missing run-report.txt** — ok=false with missing notice.
8. **Execution results serialization** — operation, exit_code present.
9. **Manifest file list serialization** — manifest_files array present.
10. **PR URL present only when persisted** — pr_url set when in evidence.
11. **Payload cleanliness unavailable** — payload_cleanliness is null.
12. **Readiness unavailable** — readiness is null.
13. **Safe run_id rejection** — traversal-like run_id returns ok=false, error.

### Detail Panel Tests

14. **GET-only boundary** — no POST/PUT/PATCH/DELETE routes added.
15. **Existing GET /runs regression** — list route still works.
16. **Existing page still renders** — HTML page at GET / still works.
17. **Page contains new detail panel** — `#run-detail-panel` exists.
18. **Run-list entries are clickable** — each history-entry has a button/link.
19. **Selection fetches exact detail route** — click triggers fetch.
20. **Detail rendering includes all sections** — summary, execution results,
    manifest files, report preview, evidence paths.
21. **Missing evidence visibly rendered** — missing notices shown.
22. **Malformed evidence visibly rendered** — malformed notices shown.
23. **No localStorage/sessionStorage** — no added persistence.
24. **No .ariadne writes** — grep confirms no writes.
25. **No real git, gh, Docker, network, subprocess, or agents** in tests.
26. **All filesystem tests use tmp_path**.

## VALIDATION PLAN

### 1. Python Compile

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

Expected: all files compile.
If not met: block.

### 2. Focused Detail Endpoint and Panel Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_local_run_history_in_page.py \
  -k "detail or Detail or endpoint or Endpoint or panel or Panel or safe_run or traversal" -q
```

Expected: detail endpoint and panel tests pass.
If not met: block.

### 3. Existing PR 0139 Run-List Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_local_run_history_in_page.py \
  -k "History or history or Existing or existing or GET or get route" -q
```

Expected: all existing run-list tests pass.
If not met: block.

### 4. Runtime Evidence Model Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_runtime_evidence.py -q
```

Expected: all 32 tests pass (model unchanged).
If not met: block.

### 5. Task Intake and Runner Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_task_intake.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py -q
```

Expected: regression tests pass.
If not met: block.

### 6. Full Regression (following PR 0139 pattern)

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
  services/task_intake/tests -q
```

Expected: full regression passes.
If not met: block.

### 7. Grep for Detail Route and Panel

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "read_run_evidence_detail|run-detail-panel|GET.*runs|path ==.*runs/|fetchRunsDetail|run_detail_endpoint" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_run_history_in_page.py
```

Expected: detail route and panel identifiers present.
If not met: block.

### 8. Grep for Unavailable-Value Handling

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "not available|payload_cleanliness.*null|readiness.*null|missing.*notice|malformed.*notice" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_run_history_in_page.py
```

Expected: unavailable-value policy visible.
If not met: block.

### 9. Grep for Forbidden Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system|POST|PUT|PATCH|DELETE" \
  services/task_intake/src/task_intake/server.py \
  services/task_intake/tests/test_local_run_history_in_page.py
```

Expected: no unsafe mutation (POST matches only the existing `/runs/execute` route).
If not met: block.

### 10. No Forbidden Path Changed

```bash
git diff --name-only -- ROADMAP.md docs/ agents/ schemas/ pyproject.toml poetry.lock .gitignore \
  services/runner/src/runner/runtime_evidence.py \
  services/runner/tests/test_runtime_evidence.py \
  .project-memory/pr/0131* .project-memory/pr/0132* .project-memory/pr/0133* \
  .project-memory/pr/0134* .project-memory/pr/0135* .project-memory/pr/0136* \
  .project-memory/pr/0137* .project-memory/pr/0138* .project-memory/pr/0139* \
  .project-memory/pr/0140*
```

Expected: empty.
If not met: block.

### 11. Git Status

```bash
git status --short
```

Expected: only server.py, test file, PR artifacts.
If unknown untracked files exist: block.

### 12. Git Diff

```bash
git diff --name-only
```

Expected: only server.py, test file.
If services/runner unchanged files appear: block.

### 13. Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty.
If staged files exist: block.

### 14. IMPLEMENTATION_REPORT.md Presence

```bash
test -f .project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md
```

Expected: file exists.
If not met: block.

### 15. Precommit-Review Artifact Presence

```bash
test -f .project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml
```

Expected: file exists.
If not met: block.

## PLAN DRIFT GATE

### Permitted Dirty Files During Implementation

- `services/task_intake/src/task_intake/server.py` (modified)
- `services/task_intake/tests/test_local_run_history_in_page.py` (modified)
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/PLAN.md`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/plan-review.yml`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml`

### Permitted Dirty Files During Precommit-Review

Same as above + precommit-review.yml

### Block Conditions

1. Any changed file outside the approved allowlist → block.
2. `runtime_evidence.py` changed without evidence-triggered gap written in
   PLAN.md → block.
3. Route or response contract differs from approved design → block.
4. Panel adds mutation, execution, or agent controls → block.
5. Full Artifact Workspace Shell started → block.
6. Previous PR artifact modified → block.
7. PLAN.md or plan-review.yml modified after lock commit without explicit
   replanning cycle → block.
8. IMPLEMENTATION_REPORT.md absent → block.
9. Implementation report claims unsupported by actual evidence → block.
10. Validation missing or failing → block.
11. Cached diff non-empty before review begins → block.
12. Known generated residue is staged or tracked → block.
13. Unknown untracked files exist → block.

## NO-DRIFT CHECK

Require the future implementation and precommit-review to confirm:

1. Branch remains `0141-artifact-workspace-run-detail-evidence-panel`.
2. Implementation stays inside the PLAN allowlist.
3. Existing `GET /runs` behavior remains compatible.
4. Existing runtime evidence readers remain read-only.
5. No persisted run artifact is created or modified.
6. No UI mutation exists.
7. No agent launch exists.
8. No git or gh operation exists.
9. No full workspace shell exists.
10. No serialization-contract PR is silently absorbed.
11. No report or manifest viewer is silently absorbed.
12. No frozen stream is started.
13. Implementation report exists and is treated as context, not proof.
14. Actual files and validation override agent claims.
15. PLAN DRIFT GATE passed.
16. Review-artifact write and readback succeeded.

## STOP CONDITIONS

The future coder must stop when:

1. A required file outside the PLAN allowlist appears necessary.
2. Safe run-id handling cannot be achieved within the approved scope.
3. Existing read-model behavior contradicts the planned response.
4. A response field would need to be fabricated.
5. Tests require real runtime mutation or external services.
6. Existing `GET /runs` compatibility would be broken.
7. The feature expands into the full shell, viewer suite, serialization
   contract, or mutation workflow.
8. PLAN.md or plan-review.yml is missing or modified after lock.
9. IMPLEMENTATION_REPORT.md cannot be written exactly as required.
10. Dirty-tree or cached-diff gates fail.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write
`.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`
before precommit-review.

**IMPLEMENTATION_REPORT.md is handoff context, not proof.**
Agent output is not proof. Runtime-captured validation, command outputs, file
contents, diffs, persisted runtime artifacts, and accepted proof refs remain proof.

The future precommit-review must compare the implementation report with PLAN.md,
plan-review.yml, actual changed files, validation output, dirty tree, and cached
diff. If claims disagree, PLAN.md and actual evidence win.

## NON-GOALS

1. Implementation (this is a planning task only).
2. Test changes during planning.
3. Review artifact creation during planning.
4. ROADMAP.md correction.
5. Previous PR artifact modification.
6. Full Artifact Workspace Shell.
7. Full run-report viewer.
8. Full manifest viewer.
9. Versioned evidence serialization contract.
10. Artifact acceptance or rejection.
11. Runtime mutation.
12. UI mutation.
13. Agent execution from UI.
14. Git or GitHub operations from UI.
15. Visual Gate.
16. Context Core.
17. PCAM/PBS.
18. Rubrics runtime.
19. Decision Core.
20. Model Router.
21. ETL/ERP demo.
22. Dependency or frontend-framework changes.
23. Modifying `runtime_evidence.py` without demonstrated evidence-triggered gap.
