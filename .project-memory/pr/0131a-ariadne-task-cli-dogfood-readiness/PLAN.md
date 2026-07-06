# PR 0131A — Ariadne Task CLI Dogfood Readiness Fix Plan

## Summary

Plan a minimal dogfood-readiness correction discovered during the PR 0131 dogfood attempt. Five concrete fixes: (1) add `if __name__ == "__main__"` module entrypoint, (2) support `task` subcommand literal in parser, (3) fix JSON output to read from request instead of missing `result.json_output`, (4) persist stopped/blocked/failed pipeline results when `--runs-root` is provided, (5) ensure CLI result JSON includes debugging fields. No retry, no dashboard, no Pipeline Runner or Git Boundary changes.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | ecac1bda691b66b3876569a817ed5731a573ab52 |
| current_branch | 0131a-ariadne-task-cli-dogfood-readiness |
| git_status_short | clean |
| dogfood_failure_evidence | Confirmed via PR 0131 dogfood attempt: `python -m runner.ariadne_task_cli` exits silently; `task` subcommand not accepted; `result.json_output` not found; stopped pipeline produces no run record; dogfood-proof.yml, run.json, manifest.json all missing |

## Roadmap alignment

* roadmap track: Production Line — Stage 2 Closed Loop (dogfood readiness fix)
* expected PR slot: 0131A — Ariadne Task CLI Dogfood Readiness Fix
* why this PR is next: PR 0131 dogfood attempt revealed 5 concrete failures that must be corrected before the dogfood milestone can be reached
* batching policy check: minimal executable-first fix PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136; does not add architecture, retry, dashboard, or control plane

## Dogfood blocker evidence

| Blocker | Current behavior | Required behavior |
|---------|-----------------|-------------------|
| Module entrypoint missing | `python -m runner.ariadne_task_cli --help` exits silently | Module prints help and exits with expected code |
| `task` subcommand not supported | `python -m runner.ariadne_task_cli task "<desc>"` fails | Both `task "<desc>"` and `"<desc>"` must work |
| JSON output reads `result.json_output` | `AriadneTaskCliResult` has no `json_output` field → `AttributeError` | `main()` must use `request.json_output` |
| Stopped/failed pipeline not persisted | Early returns exit before persistence block | Stopped/failed results must persist when `--runs-root` and `--run-id` are provided |
| CLI result missing debugging fields | `run_id` and `run_record_path` absent in early-return results | All CLI results include `run_id` and `run_record_path` if persisted |

## Fix scope

### Fix 1 — Module entrypoint

Add at end of `ariadne_task_cli.py`:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

Also test with `main(["--help"])` to verify help output.

### Fix 2 — Parser compatibility with `task` subcommand

Modify `parse_ariadne_task_args()` to accept two forms:

```
python -m runner.ariadne_task_cli "<description>"
python -m runner.ariadne_task_cli task "<description>"
```

Implementation: allow an optional positional `command` that matches "task" literally, then shift the remaining args. Or add a `command` positional with `nargs="?"`, `choices=["task"]`, `default=None` and move `task_description` to be consumed after the `task` keyword.

The simplest fix: change the parser to accept an optional `command` that must be "task", and accept the `task_description` as the next argument. Both forms work.

### Fix 3 — JSON output fix

In `main()`, change:

```python
if result.json_output:
```

to:

```python
if request.json_output:
```

The `json_output` field is on `AriadneTaskCliRequest`, not `AriadneTaskCliResult`. The request is built before the result.

### Fix 4 — Persist stopped/blocked/failed results

Refactor `run_ariadne_task()` so that ALL exit paths (stopped, failed, blocked, completed) run through a shared persistence block at the end, rather than only the completion path.

Implementation approach:

1. Build a partial `AriadneTaskCliResult` with available fields at each early exit point
2. At the end of the function, if `request.runs_root` and `persistence_fn`, always persist the result
3. The persistence block runs for ALL terminal statuses: `COMPLETED`, `COMPLETED_WITH_WARNING`, `STOPPED`, `FAILED`, `BLOCKED`
4. If persistence fails, return the original result with persistence failure code appended

Persisted stopped record must include:
- `run_id` (from `request.run_id` or auto-generated)
- `task_description_hash`
- `status` (stopped/failed/blocked)
- `reason_codes` (including `pipeline_stopped` etc.)
- `pipeline_status`
- `pipeline_final_action`
- `pipeline_has_blockers`
- `next_action`
- `started_at` / `finished_at`
- `command_plan_summary` empty or null if no git boundary was reached
- `execution_attempted` false
- `git_boundary_status` null
- `details` explaining the stop reason

### Fix 5 — CLI result debugging fields

Ensure all `AriadneTaskCliResult` instances include:
- `run_id` set when persistence is attempted
- `run_record_path` set when persistence succeeds

The existing `AriadneTaskCliResult` and persistence block already support this — Fix 4 (shared persistence for all paths) is the enabler.

## Non-goals

- No retry loop
- No model health
- No dashboard
- No control plane
- No Pipeline Runner modification
- No Git Boundary modification
- No Prompt Composer modification
- No Verdict Parser modification
- No Agent Runner Bridge modification
- No ROADMAP/docs/agents/schemas changes

## Implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/ariadne_task_cli.py` | MODIFIED — 5 fixes |
| `services/runner/tests/test_ariadne_task_cli.py` | MODIFIED — add regression tests for all 5 fixes |

Default — not modified:
- `services/runner/src/runner/run_persistence.py` — NOT modified (API shape is correct; only call site changes)
- `services/runner/src/runner/pipeline_runner.py` — NOT modified
- `services/runner/src/runner/git_boundary.py` — NOT modified
- `services/runner/src/runner/prompt_composer.py` — NOT modified
- `services/runner/src/runner/verdict_parser.py` — NOT modified
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `ROADMAP.md`, `docs/`, `agents/`, `schemas/` — NOT modified

## Implementation steps

1. Add `if __name__ == "__main__": raise SystemExit(main())` at module end
2. Modify `parse_ariadne_task_args()` to accept `task` as an optional first positional command
3. Change `result.json_output` to `request.json_output` in `main()`
4. Refactor early-return paths in `run_ariadne_task()` to build partial results, then pass through a shared persistence block
5. Add regression tests for all 5 fixes

## Required new regression tests

| Fix | Test class |
|-----|-----------|
| 1 | `TestMainEntrypoint` — `main(["--help"])` emits help and returns 0 |
| 1 | `TestModuleRun` — `__name__ == "__main__"` path exists |
| 2 | `TestLiteralTaskAccepted` — `main(["task", "x", "--json"])` produces JSON |
| 2 | `TestDirectDescription` — `main(["x", "--json"])` still works |
| 3 | `TestJsonOutputNoAttributeError` — JSON output does not raise AttributeError |
| 4 | `TestStoppedPipelinePersists` — With `--runs-root` and fake pipeline returning stopped, run.json is persisted |
| 4 | `TestFailedPipelinePersists` — With `--runs-root` and fake pipeline returning failed, run.json is persisted |
| 4 | `TestStoppedPersistedRecordFields` — Persisted stopped record has reason_codes including `pipeline_stopped` |
| 4 | `TestStoppedNoGitBoundary` — Stopped pipeline does not call git boundary planner |
| 5 | `TestResultHasRunIdAndPath` — CLI result includes `run_id` and `run_record_path` when persisted |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_ariadne_task_cli.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  -q

# Verify module entrypoint works
PYTHONPATH=services/runner/src:services/task_intake/src python -m runner.ariadne_task_cli --help

# Verify literal task subcommand works
PYTHONPATH=services/runner/src:services/task_intake/src python -m runner.ariadne_task_cli task "debug smoke" --json

# Verify direct form works
PYTHONPATH=services/runner/src:services/task_intake/src python -m runner.ariadne_task_cli "debug smoke" --json

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "__main__|raise SystemExit\(main\(\)\)|json_output|pipeline_stopped|runs_root|run_record_path" services/runner/src/runner/ariadne_task_cli.py services/runner/tests/test_ariadne_task_cli.py 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|os.system|shell=True|docker compose|docker run|pip install|python -m pip install|gh pr create|git commit|git push|git add" services/runner/src/runner/ariadne_task_cli.py services/runner/tests/test_ariadne_task_cli.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `ariadne_task_cli.py` and `test_ariadne_task_cli.py` changed
- **behavior drift**: CLI entrypoint works; `task` subcommand accepted; JSON output no longer crashes; stopped/failed results persist; no architecture expansion
- **entrypoint drift**: `main(["--help"])` emits help and returns 0; `__name__ == "__main__"` path present
- **parser drift**: both `task "<desc>"` and `"<desc>"` forms accepted
- **JSON output drift**: reads `request.json_output`, not missing `result.json_output`
- **persistence drift**: all terminal statuses persist when `--runs-root` is provided; no exception for stopped/failed/blocked
- **predecessor drift**: no modifications to pipeline_runner.py, git_boundary.py, run_persistence.py, or other modules
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no retry, no dashboard, no control plane, no model health

## NO-DRIFT CHECK

The implementation precommit-review must confirm:
- minimal dogfood-readiness fixes only ✓
- no Pipeline Runner or Git Boundary changes ✓
- no ROADMAP/docs/agents/schemas changes ✓
- `python -m runner.ariadne_task_cli --help` works ✓
- `task` subcommand accepted ✓
- JSON output no longer crashes ✓
- stopped pipeline persists run record ✓
- no retry/dashboard/control-plane scope creep ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if branch is not `0131a-ariadne-task-cli-dogfood-readiness`
- Block if fix modifies ROADMAP/docs/agents/schemas
- Block if fix modifies Pipeline Runner or Git Boundary
- Block if fix adds retry/dashboard/control-plane/model-health/run-report scope
- Block if `python -m runner.ariadne_task_cli --help` remains silent
- Block if `main(["task", ..., "--json"])` still fails
- Block if JSON output still references missing `result.json_output`
- Block if stopped pipeline still fails to persist local run record when `--runs-root` and `--run-id` are provided
- Block if tests require real git/gh/Docker/network/agents
- Block if validation plan is incomplete
- Block if artifact write/readback expectations are missing
