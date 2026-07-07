# PR 0131B — Persist Stopped Ariadne Task Runs

## Root Cause

`main()` calls `run_ariadne_task(request)` without passing `persistence_fn` or
`clock_provider`.  The injectable parameters default to `None`, so
`_persist_and_return` takes the early-exit path:

```python
if not request.runs_root or not persistence_fn:
    return result
```

Result: even when `--runs-root` and `--run-id` are provided, no `run.json` or
`manifest.json` is ever written, `run_id` stays `None` in the JSON output, and
`run_record_path` stays `None`.

The stop/block early-return paths in `run_ariadne_task` all call
`_persist_and_return`, so fixing the wiring in `main()` is sufficient — no
changes needed to the persistence logic itself.

## Fix Scope

**Strictly limited to:**
- `services/runner/src/runner/ariadne_task_cli.py` — wire persistence in `main()`
- `services/runner/tests/test_ariadne_task_cli.py` — add stopped-run persistence tests

**Not modified:**
- ROADMAP.md
- docs/**
- agents/**
- schemas/**
- `services/runner/src/runner/pipeline_runner.py`
- `services/runner/src/runner/git_boundary.py`
- `services/runner/src/runner/prompt_composer.py`
- `services/runner/src/runner/verdict_parser.py`
- `services/runner/src/runner/agent_runner_bridge.py`
- `services/runner/src/runner/run_persistence.py` (no API-shape change needed)
- `services/runner/tests/test_run_persistence.py` (no change needed)
- pyproject.toml / package.json / Makefile

## Files

| File | Change |
|------|--------|
| `services/runner/src/runner/ariadne_task_cli.py` | Wire `persist_run_record` and a clock provider in `main()`. |
| `services/runner/tests/test_ariadne_task_cli.py` | Add `TestStoppedPipelinePersistence` class. |

## Changes

### 1. `ariadne_task_cli.py` — Wire persistence in `main()`

**Import addition** (add after `from runner.pipeline_runner import ...`):

```python
from runner.run_persistence import persist_run_record
```

**Import addition** (add after existing `import` block — or use `from datetime import datetime, timezone`):

```python
from datetime import datetime, timezone
```

**`main()` change** — pass real implementations to `run_ariadne_task`:

```python
def _utc_clock() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: Optional[list[str]] = None) -> int:
    ...
    result = run_ariadne_task(
        request,
        persistence_fn=persist_run_record,
        clock_provider=_utc_clock,
    )
    ...
```

This is the **only** production code change.

### 2. `test_ariadne_task_cli.py` — Stopped-run persistence tests

Add a `TestStoppedPipelinePersistence` class after `TestPipelineBlockers`:

```python
# ---------------------------------------------------------------------------
# Stopped pipeline persistence (PR 0131B)
# ---------------------------------------------------------------------------


class TestStoppedPipelinePersistence:
    """Stopped pipeline with runs_root/run_id persists run records."""

    def test_stopped_pipeline_writes_run_json(self, tmp_path: Path):
        """Stopped pipeline with runs_root writes run.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert result.run_id == "stopped-test"
        assert result.run_record_path is not None
        run_json = Path(result.run_record_path)
        assert run_json.exists()
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["status"] == "stopped"
        assert "pipeline_stopped" in data["reason_codes"]

    def test_stopped_pipeline_writes_manifest_json(self, tmp_path: Path):
        """Stopped pipeline writes manifest.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-manifest",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert result.run_record_path is not None
        manifest_path = Path(result.run_record_path).parent / "manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data["run_json_hash"] is not None
        assert "run.json" in manifest_data.get("files", [])

    def test_stopped_pipeline_json_includes_run_id_and_path(self, tmp_path: Path):
        """JSON output includes run_id and run_record_path."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-json",
            json_output=True,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        # Build the same output dict as main()
        output_dict = {
            "status": result.status,
            "reason_codes": list(result.reason_codes),
            "task_description": result.task_description,
            "task_description_hash": result.task_description_hash,
            "pipeline_status": result.pipeline_status,
            "pipeline_final_action": result.pipeline_final_action,
            "pipeline_has_blockers": result.pipeline_has_blockers,
            "git_boundary_status": result.git_boundary_status,
            "command_plan": result.command_plan,
            "execution_attempted": result.execution_attempted,
            "execution_results": list(result.execution_results),
            "warnings": list(result.warnings),
            "next_action": result.next_action,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "details": result.details,
            "run_id": result.run_id,
            "run_record_path": result.run_record_path,
        }
        assert output_dict["run_id"] == "stopped-test-json"
        assert output_dict["run_record_path"] is not None
        assert "stopped" in output_dict["status"]

    def test_load_run_record_can_read_stopped_run(self, tmp_path: Path):
        """load_run_record can read a stopped persisted run."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-readback",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        read_result = load_run_record(runs_root, "stopped-test-readback")
        assert read_result.status == "read_ok"
        assert read_result.record is not None
        assert read_result.record.status == "stopped"
        assert "pipeline_stopped" in read_result.record.reason_codes
        assert read_result.record.execution_attempted is False
        assert read_result.record.git_boundary_status is None

    def test_stopped_run_git_boundary_not_called(self, tmp_path: Path):
        """Stopped run does not call git boundary planner."""
        planner_call_count = [0]
        executor_call_count = [0]

        def counting_planner(request):
            planner_call_count[0] += 1
            return _fake_git_boundary_planner()(request)

        def counting_executor(request, plan, executor=None, clock_provider=None):
            executor_call_count[0] += 1
            return _fake_git_boundary_executor()(request, plan, executor, clock_provider)

        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-no-git",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=counting_planner,
            git_boundary_executor_fn=counting_executor,
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert planner_call_count[0] == 0
        assert executor_call_count[0] == 0

    def test_stopped_run_no_repo_ariadne_residue(self, tmp_path: Path):
        """Stopped run uses tmp_path, not .ariadne/."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-residue",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert not Path(".ariadne").exists()
```

**Imports needed** (add to existing test imports):
```python
from runner.run_persistence import persist_run_record, load_run_record
```

## Stopped-Run Persistence Contract

When `runs_root` and `run_id` are provided and pipeline stops:

**`run.json` fields:**
| Field | Value |
|-------|-------|
| `run_id` | Provided or auto-generated |
| `task_description_hash` | SHA-256[:16] of task description |
| `task_description_redacted` | First 80 chars of task description |
| `status` | `"stopped"` |
| `reason_codes` | Contains `"pipeline_stopped"` |
| `pipeline_status` | `"stopped"` |
| `pipeline_final_action` | `"stop"` or pipeline result value |
| `pipeline_has_blockers` | `true`/`false` |
| `git_boundary_status` | `null` |
| `command_plan_summary` | `[]` |
| `execution_attempted` | `false` |
| `execution_results_summary` | `[]` |
| `warnings` | `[]` |
| `next_action` | `"stop"` |
| `started_at` / `finished_at` | Timestamps if clock provider available |
| `details` | `"Pipeline stopped"` or equivalent |
| `artifact_hashes` | `{}` |

**`manifest.json` fields:**
| Field | Value |
|-------|-------|
| `schema_version` | `"1"` |
| `run_id` | Provided or auto-generated |
| `run_json_hash` | SHA-256[:16] of canonical run.json |
| `files` | `["run.json"]` |

**JSON output contract:**
Includes `run_id` (non-null) and `run_record_path` (non-null) when
`--runs-root` and `--run-id` are provided.

**Readback contract:**
`load_run_record(runs_root, run_id)` returns `status="read_ok"` with a
`PersistedRunRecord` where `status="stopped"` and
`execution_attempted=False` and `git_boundary_status=None`.

## Non-Goals

- No modification to `run_persistence.py` API or internals
- No modification to Pipeline Runner or Git Boundary
- No retry logic, dashboard, control plane, or model health
- No run-report generation beyond persisted JSON files
- No change to existing test classes or test assertions
- No change to `--help`, parser, or `--json` output format (except `run_id`/`run_record_path` are now populated)

## Validation

```bash
# Compile check
python -m compileall -f services/runner/src services/task_intake/src

# New tests only
PYTHONPATH=services/runner/src:services/task_intake/src \
  python -m pytest services/runner/tests/test_ariadne_task_cli.py -q

# All runner tests
PYTHONPATH=services/runner/src:services/task_intake/src \
  python -m pytest \
    services/runner/tests/test_ariadne_task_cli.py \
    services/runner/tests/test_run_persistence.py \
    services/runner/tests/test_git_boundary.py \
    services/runner/tests/test_pipeline_runner.py \
    services/runner/tests/test_verdict_parser.py \
    services/runner/tests/test_prompt_composer.py \
    services/runner/tests/test_agent_runner_bridge.py \
    -q

# --help still works
PYTHONPATH=services/runner/src:services/task_intake/src \
  python -m runner.ariadne_task_cli --help

# Dogfood smoke test with persistence
rm -rf /tmp/ariadne-debug-runs && \
PYTHONPATH=services/runner/src:services/task_intake/src \
  python -m runner.ariadne_task_cli task "debug smoke" \
    --runs-root /tmp/ariadne-debug-runs \
    --run-id debug-smoke --json

# Verify files exist
test -f /tmp/ariadne-debug-runs/debug-smoke/run.json
test -f /tmp/ariadne-debug-runs/debug-smoke/manifest.json

# Readback via load_run_record
PYTHONPATH=services/runner/src:services/task_intake/src python - <<'PY'
from pathlib import Path
from runner.run_persistence import load_run_record
result = load_run_record("/tmp/ariadne-debug-runs", "debug-smoke")
print(dataclasses.asdict(result) if hasattr(result, '__dataclass_fields__') else result)
PY

# No forbidden patterns
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "pipeline_stopped|run_record_path|runs_root|run_id|persist_run_record|load_run_record|manifest.json|run.json" \
  services/runner/src/runner/ariadne_task_cli.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/src/runner/run_persistence.py \
  services/runner/tests/test_run_persistence.py

# No shell/git mutation in changed files
grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "subprocess.run|os.system|shell=True|docker compose|docker run|pip install|python -m pip install|gh pr create|git commit|git push|git add" \
  services/runner/src/runner/ariadne_task_cli.py \
  services/runner/tests/test_ariadne_task_cli.py

# No repo .ariadne residue
if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

# Only touched files
git status --short
git diff --name-only
```
