# PR 0138 — UI Runtime Evidence Read Model Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Artifact Workspace Read-Only UI (Stream 1) |
| **Slot** | PR 0138 (first read-only stream PR after PR 0137 unlock) |
| **Why this PR is next** | PR 0137 unlocked the post-0136 roadmap. The next active stream is Artifact Workspace Read-Only UI. PR 0138 starts that stream by defining a stable read-only runtime evidence view model — the foundation that all future UI panels will consume. No UI shell, no screens, no mutation. |
| **Batching policy** | Single-purpose: read-only run evidence read model. No feature expansion. |
| **Drift heuristic** | Does not open UI mutation, agent launch from UI, commit from UI, or PR creation from UI. Does not implement Artifact Workspace Shell, Visual Gate, Context Core, PCAM/PBS, Rubrics, Decision Core, Model Router, or ETL/ERP demo. |
| **Architect note** | This PR creates a typed read model in `services/runner/src/runner/` — the same service where `run_persistence.py`, `readiness_gate.py`, and the PR 0136 `_evaluate_readiness()` live. The read model reads local `.ariadne/runs/` persisted artifacts only, is read-only, and requires no changes to existing runtime behavior. |

## Summary

PR 0138 defines and implements a minimal read-only runtime evidence read
model.  The read model normalizes local persisted evidence artifacts
(`run.json`, `manifest.json`, `run-report.txt`) into stable typed/structured
outputs that future UI panels (PR 0139–0147) can consume.

The read model:
- Reads only from `.ariadne/runs/<run_id>/` persisted files.
- Never mutates files.
- Never runs agents.
- Never shells out to git, gh, or Docker.
- Reports missing or malformed evidence explicitly (no silent fallback).
- Returns typed structures: `RunEvidenceSummary`, `RunEvidenceDetail`,
  `ArtifactEvidenceRef`, `MissingEvidenceNotice`, `RuntimeEvidenceReadResult`.

## Discovery Evidence

### Existing Package Boundaries

The repository has two relevant Python services:

1. **`services/runner/`** — `pyproject.toml` at project root. Contains:
   - `run_persistence.py` — persists `run.json`, `manifest.json`;
     exports `persist_run_record()`, `load_run_record()`, and
     `RunPersistenceReadResult`.
   - `ariadne_task_cli.py` — contains `_evaluate_readiness()`,
     `PayloadCleanlinessResult`, and all production-line gates.
   - `readiness_gate.py` — pre-0100 readiness gate (not the PR 0136 gate).
   - Existing read paths: `load_run_record()` (from `run_persistence.py`)
     reads `run.json`, validates `run_id`, computes hash.

2. **`services/task_intake/`** — `pyproject.toml` at
   `services/task_intake/pyproject.toml`. Contains:
   - `server.py` — ASGI server with `/runs/execute` POST route and HTML
     page at `GET /`. The HTML page has inline JavaScript for run history
     (browser-only `__ariadne_run_history` array), summary card rendering,
     and execution trace. This is legacy mock UI, not evidence-backed.
   - `runs.py` — `create_mock_run()` produces mock run objects without
     real persistence. Not used by the read model.
   - `app.py` — `accept_task()` and uvicorn entrypoint.

### Target Module Location

The read model belongs in **`services/runner/src/runner/runtime_evidence.py`**:

- It reads persisted files written by `run_persistence.py`.
- It consumes `PayloadCleanlinessResult` from `ariadne_task_cli.py`.
- It calls `load_run_record()` from `run_persistence.py` for structured
  `run.json` reading.
- Existing tests in `services/runner/tests/` already use `tmp_path` and
  the `conftest.py` residue fixture.

Tests go in **`services/runner/tests/test_runtime_evidence.py`**.

## Read Model Identity

1. PR 0138 is the **first Artifact Workspace Read-Only UI stream PR**.
2. This PR creates a **read model, not a UI shell**.
3. The read model is **read-only**.
4. The read model must **not mutate runtime state**.
5. The read model must **not run agents**.
6. The read model must **not run git, gh, Docker, or shell mutation commands**.
7. The read model reads **persisted local runtime artifacts only**.
8. **Missing or malformed evidence must be represented explicitly, not hidden.**

## Source Artifacts to Read

| Path | Source | Required? |
|------|--------|-----------|
| `<runs_root>/<run_id>/run.json` | PR 0132 persistence | Yes |
| `<runs_root>/<run_id>/manifest.json` | PR 0132 persistence | Optional |
| `<runs_root>/<run_id>/run-report.txt` | PR 0135 report | Optional |
| Dogfood proof path | PR 0131 proof artifact | Optional, by reference |
| `.project-memory/pr/*` artifacts | PR project-memory | Static metadata only |

The read model never creates or modifies any of these artifacts.

## Output Structures

### RunEvidenceSummary (run list)

```python
@dataclasses.dataclass(frozen=True)
class RunEvidenceSummary:
    run_id: str
    status: str
    reason_codes: tuple[str, ...]
    pipeline_status: Optional[str]
    git_boundary_status: Optional[str]
    execution_attempted: bool
    created_at: Optional[str]
    run_json_path: Optional[str]
    manifest_path: Optional[str]
    run_report_path: Optional[str]
    pr_url: Optional[str]
    missing_evidence: tuple[str, ...]
    malformed_evidence: tuple[str, ...]
```

### RunEvidenceDetail (single run with all evidence)

```python
@dataclasses.dataclass(frozen=True)
class RunEvidenceDetail:
    summary: RunEvidenceSummary
    execution_results: tuple[dict, ...]
    manifest_files: tuple[str, ...]
    run_json_hash: Optional[str]
    report_preview: Optional[str]
    payload_cleanliness: Optional[PayloadCleanlinessResult]
    readiness: Optional[ProductionLineReadinessResult]
    evidence_paths: tuple[str, ...]
    source_errors: tuple[str, ...]
```

### ArtifactEvidenceRef

```python
@dataclasses.dataclass(frozen=True)
class ArtifactEvidenceRef:
    path: str
    exists: bool
    file_size: int
    description: str
```

### MissingEvidenceNotice

```python
@dataclasses.dataclass(frozen=True)
class MissingEvidenceNotice:
    expected_path: str
    reason: str  # e.g. "file_not_found", "unreadable", "malformed"
```

### RuntimeEvidenceReadResult

```python
@dataclasses.dataclass(frozen=True)
class RuntimeEvidenceReadResult:
    ok: bool
    error: Optional[str]
    summary: Optional[RunEvidenceSummary]
    detail: Optional[RunEvidenceDetail]
    missing: tuple[MissingEvidenceNotice, ...]
    malformed: tuple[MissingEvidenceNotice, ...]
```

## Directory and Path Rules

1. The read model must accept an explicit `runs_root` or `repo_root`
   parameter.
2. The read model must not assume the current working directory unless
   explicitly passed.
3. The read model must not read outside the configured repo root or
   runs root.
4. The read model must handle missing `.ariadne/runs` gracefully.
5. The read model must sort runs deterministically.
6. The read model must avoid filesystem mutation.

## Implementation Scope

| File | Action | Justification |
|------|--------|---------------|
| `services/runner/src/runner/runtime_evidence.py` | Create new module | New read model module in the runner service alongside `run_persistence.py`. Contains `RunEvidenceSummary`, `RunEvidenceDetail`, `ArtifactEvidenceRef`, `MissingEvidenceNotice`, `RuntimeEvidenceReadResult`, `list_run_evidence_summaries()`, `read_run_evidence_detail()`. |
| `services/runner/tests/test_runtime_evidence.py` | Create new test file | Tests for the read model using `tmp_path` and the existing `conftest.py` residue fixture. |

### Files Excluded

| File | Exclusion Reason |
|------|-----------------|
| `services/runner/src/runner/run_persistence.py` | No change needed. The read model imports and uses existing `load_run_record()` and `RunPersistenceReadResult`. |
| `services/runner/src/runner/ariadne_task_cli.py` | No change needed. The read model imports `PayloadCleanlinessResult` and `ProductionLineReadinessResult` types from their existing locations. |
| `services/runner/src/runner/git_boundary.py` | No change needed. Read model does not interact with git. |
| `services/task_intake/` | No change needed. The read model lives in `services/runner/`. Future PRs (0139–0141) may add a task_intake route that returns read model output. |
| `services/runner/tests/conftest.py` | No change needed. Existing residue fixture handles `.ariadne/` paths. |

### Not Modified

- `ROADMAP.md`
- `docs/`, `agents/`, `schemas/`
- `pyproject.toml`, `poetry.lock`, `requirements*.txt`
- `.gitignore`
- All previous PR artifacts (0131–0137)
- `services/runner/src/runner/git_boundary.py`
- `services/task_intake/src/task_intake/*.py`

## Tests

### Test Requirements (20 tests)

1. **Empty runs directory returns empty list** without failure.
2. **Missing runs directory returns empty list** or explicit missing-root
   result without failure.
3. **Complete run** with `run.json`, `manifest.json`, `run-report.txt` is
   summarized correctly.
4. **Run detail includes execution results** from `run.json`.
5. **Run detail includes manifest file list** from `manifest.json`.
6. **Run detail includes run-report path or preview**.
7. **Missing manifest** is reported as missing evidence, not crash.
8. **Missing run-report** is reported as missing evidence, not crash.
9. **Malformed run.json** is reported as malformed evidence, not crash.
10. **Malformed manifest.json** is reported as malformed evidence, not crash.
11. **PR URL** is surfaced only when present in persisted evidence.
12. **No PR URL** is fabricated when absent.
13. **Payload cleanliness fields** are surfaced when present.
14. **Readiness indicators** are surfaced when present or reported unavailable.
15. **Reader uses explicit tmp roots** in tests.
16. **Reader does not shell out** (grep for subprocess, os.system, etc.).
17. **Reader does not mutate files** (verify no write operations).
18. **Reader does not invoke `run_ariadne_task`**.
19. **Reader does not require real git repo**.
20. **Tests do not use real project `.ariadne`**.

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
  services/runner/tests/test_runtime_evidence.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  -q
```

Expected: focused tests pass (including new read model tests).
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
  -q
```

Expected: regression subset passes.
If not met: block.

### 4. Grep for Read Model

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "RunEvidenceSummary|RunEvidenceDetail|ArtifactEvidenceRef|MissingEvidenceNotice|RuntimeEvidenceReadResult|list_run_evidence_summaries|read_run_evidence_detail|runs_root|run_json|manifest|run_report|payload_cleanliness|readiness|pr_url" \
  services/runner/src/runner \
  services/runner/tests \
  .project-memory/pr/0138-ui-runtime-evidence-read-model
```

Expected: read model types and functions are visible.
If not met: block.

### 5. Grep for Unsafe Mutation

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "git add|git commit|git push|gh pr create|git reset|git checkout|git switch|git merge|git rebase|git clean|git tag|docker|docker compose|docker run|pip install|python -m pip install|shell=True|os.system|subprocess.run" \
  services/runner/src/runner services/runner/tests \
  .project-memory/pr/0138-ui-runtime-evidence-read-model
```

Expected: no unsafe real mutation authority added.
If unsafe new mutation is found: block.

### 6. Git Status

```bash
git status --short
```

Expected: only allowed files are dirty, plus untracked known generated
residue if present.
If forbidden tracked files are modified: block.
If unknown untracked files exist: block.

### 7. Git Diff

```bash
git diff --name-only
```

Expected: only expected PR 0138 files listed (runtime_evidence.py,
test_runtime_evidence.py, PLAN.md, review artifacts).
If `services/`, `agents/`, `schemas/`, `docs/`, dependencies, `.gitignore`,
`ROADMAP.md`, or previous PR artifacts appear: block.

### 8. Git Diff Cached

```bash
git diff --cached --name-only
```

Expected: empty during planning.
If staged files exist: block.

### 9. PLAN DRIFT GATE

Verify that only the planned files are changed:
- `services/runner/src/runner/runtime_evidence.py`
- `services/runner/tests/test_runtime_evidence.py`
- `.project-memory/pr/0138-ui-runtime-evidence-read-model/PLAN.md`
- `.project-memory/pr/0138-ui-runtime-evidence-read-model/reviews/plan-review.yml`
- `.project-memory/pr/0138-ui-runtime-evidence-read-model/reviews/precommit-review.yml`

If any other file is modified: block.

### 10. NO-DRIFT CHECK

- No changes to `git_boundary.py`, `run_persistence.py`, `ariadne_task_cli.py`,
  `conftest.py`, `agents/`, `schemas/`, `pyproject.toml`, `.gitignore`,
  `ROADMAP.md`.
- No UI mutation code.
- No agent launch code.
- No commit/PR creation code.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131–0136 Production Line | All existing code unchanged. Read model only reads their output. |
| PR 0137 Roadmap Unlock | Not modified. |
| Git Boundary authority | `git_boundary.py` not modified. Read model has no git interaction. |
| Run persistence | `run_persistence.py` not modified. Read model calls `load_run_record()`. |
| Residue isolation | `conftest.py` not modified. Tests use `tmp_path`. |
| Commit payload cleanliness | `ariadne_task_cli.py` not modified. Read model imports types. |
| Run report | `_write_run_report` not modified. Read model reads report path. |
| Readiness gate | `_evaluate_readiness` not modified. Read model imports types. |

## Non-Goals

- No UI pages, screens, or shell
- No visual design
- No Mermaid gate
- No artifact gallery
- No artifact accept/reject
- No runtime mutation
- No agent execution
- No git or gh execution
- No PR creation
- No run creation
- No persistence mutation
- No Context Core
- No PCAM/PBS
- No Rubrics
- No Decision Core
- No Model Router
- No ETL/ERP demo

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0138-ui-runtime-evidence-read-model`
- PLAN does not define PR 0138 as the first Artifact Workspace Read-Only UI stream PR
- PLAN states that this PR creates a UI shell or screens
- PLAN implements mutation (write, git, gh, agents, commit, PR)
- PLAN modifies `git_boundary.py`, `run_persistence.py`, `ariadne_task_cli.py`,
  `conftest.py`, agents, schemas, dependencies, `.gitignore`, `ROADMAP.md`
- PLAN adds .gitignore entries
- PLAN opens UI mutation, agent launch from UI, commit from UI, or PR creation from UI
- PLAN implements any capability from frozen streams (Context Core, PCAM/PBS, Rubrics, Decision Core, Model Router, ETL/ERP demo)
