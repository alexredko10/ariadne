# PR 0049 — Runner Runtime Smoke Demo Plan

## Goal

Add a runner-level smoke demo that exercises the Core runtime substrate end to end:

1. create an in-memory store
2. create a run
3. add at least one step
4. transition run/step through valid lifecycle states
5. attach checkpoint if supported by current Core API
6. attach verification evidence
7. build deterministic final report
8. print deterministic JSON output

## Architectural Thesis

This is the first visible proof that Ariadne can run as a platform substrate.

The demo must stay deterministic and model-free.

It should demonstrate Core runtime behavior without introducing conductor orchestration, coding-domain adapter behavior, persistence, or external infrastructure.

The model remains replaceable.
The substrate owns execution state.

## Context Snapshot

- **current HEAD sha**: `c229979fda440566bd560d7938d871e70b19507e`
- **current branch**: `0049-runner-runtime-smoke-demo`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: not present in prior plan artifacts for PR 0049 (first PR in this branch chain); base_sha is `main` (target branch for merge)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0048, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/review-artifact.schema.yml`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md`
- `.project-memory/pr/0044-runtime-substrate-skeleton/reviews/plan-review.yml`
- `.project-memory/pr/0044-runtime-substrate-skeleton/reviews/precommit-review.yml`
- `.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md` — presumed
- `.project-memory/pr/0046-runtime-state-transitions/PLAN.md`
- `.project-memory/pr/0047-runtime-verification-evidence/PLAN.md`
- `.project-memory/pr/0048-runtime-in-memory-store/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/transitions.py`
- `services/core/src/core/runtime/verification.py`
- `services/core/src/core/runtime/store.py`
- `services/core/src/core/runtime/__init__.py`
- `services/core/src/core/__init__.py`
- `services/runner/src/runner/__init__.py`
- `services/runner/src/runner/__main__.py`
- `services/runner/src/runner/doctor.py`
- `services/runner/src/runner/models.py` — not read (runner-specific models, not needed for runtime smoke)
- `services/runner/src/runner/apply.py` — not read
- `services/runner/tests/test_doctor_cli.py`
- `schemas/run-state.schema.yml`

## Current Core Runtime Snapshot

### Entities in `services/core/src/core/runtime_substrate.py`

- **Enums:** RunStatus, StepStatus (PENDING, RUNNING, COMPLETED, FAILED, BLOCKED), RubricVerdict, AgentRole
- **Frozen ref types:** ContextPackRef, StateModelRef, TransitionGraphRef, RubricPackRef, RubricJudgeResultRef, ModelCapabilityProfileRef, LongContextStressProfileRef
- **Mutable entities:** StepBoundary, RunState, AgentExecutionRecord, FinalReportDraft (all with to_dict/from_dict)
- **Immutable entity:** Checkpoint (frozen, with to_dict/from_dict)
- **Helpers:** create_run_state, record_checkpoint, record_agent_execution, build_final_report_draft

### In `services/core/src/core/runtime/transitions.py`

- `TransitionError(Exception)` with current_state, attempted_transition, reason
- `validate_run_transition`, `validate_step_transition`, `validate_checkpoint_attachment`, `validate_agent_record_attachment`, `validate_final_report_attachment`
- Internal transition tables: `_RUN_ALLOWED`, `_STEP_ALLOWED`

### In `services/core/src/core/runtime/verification.py`

- `VerificationError(Exception)` with subject, reason, evidence_id, step_id
- `VerificationEvidence` dataclass with to_dict/from_dict
- `_run_evidence_store: dict[str, list[VerificationEvidence]]` — module-level dict
- Functions: create_verification_evidence, attach_verification_evidence, get_evidence_for_run, summarize_verification_evidence, validate_final_report_readiness, build_final_report

### In `services/core/src/core/runtime/store.py`

- `RuntimeStoreError(Exception)` with operation, subject, reason
- `InMemoryRuntimeStore` class with:
  - `create_run(run) -> RunState`
  - `get_run(run_id) -> RunState`
  - `has_run(run_id) -> bool`
  - `save_run(run) -> RunState`
  - `list_runs() -> list[RunState]`
  - `delete_run(run_id) -> None`
  - `attach_verification_evidence(run_id, evidence) -> None`
  - `get_evidence_for_run(run_id) -> list[VerificationEvidence]`
  - `summarize_verification_evidence(run_id) -> dict`
  - `validate_final_report_readiness(run_id) -> None`
  - `build_final_report(run_id) -> FinalReportDraft`

## Current Runner Snapshot

### Runner package structure

```
services/runner/src/runner/
    __init__.py       — re-exports ApplyPatch, ArtifactStore, MockCoder
    __main__.py       — calls doctor.main() (no argv inspection)
    apply.py          — ApplyPatch
    artifacts.py      — ArtifactStore
    diff.py           — diff utilities
    doctor.py         — run_doctor(), main(argv) with argparse subcommands
    mock_coder.py     — MockCoder
    models.py         — runner-specific models
    normalize.py      — patch normalization
    patch.py          — patch safety
    worktree.py       — worktree management
```

### Current entrypoint behavior

`services/runner/src/runner/__main__.py`:
```python
from .doctor import main

if __name__ == "__main__":
    raise SystemExit(main())
```

`doctor.main()` uses `argparse` with a `doctor` subcommand (`required=True`). When called with no arguments (as `__main__.py` does), `argparse` will raise `SystemExit(2)` and print usage — because `dest="command", required=True` means at least one subcommand argument is required. This means `python -m runner` (with no subcommand) currently fails with exit code 2.

### Runner tests

```
services/runner/tests/
    __init__.py
    test_apply_gate.py
    test_artifact_store.py
    test_doctor_cli.py       — subprocess tests for `python -m runner doctor`
    test_mock_coder_sandbox.py
    test_patch_normalizer.py
    test_raw_diff_normalization.py
    test_raw_diff.py
    test_runner_models.py
    test_runner_smoke.py
    test_sandbox_paths.py
    test_worktree_manager.py
```

`test_doctor_cli.py` runs `python -m runner doctor` as a subprocess and asserts output lines.

## Implementation Location Decision

**Decision: Three files to modify/create**

1. **`services/runner/src/runner/runtime_smoke.py`** (new) — smoke demo module with `run_runtime_smoke_demo()` function.

2. **`services/runner/tests/test_runtime_smoke.py`** (new) — tests for the smoke demo callable.

3. **`services/runner/src/runner/__main__.py`** (modified) — route CLI to `runtime_smoke` subcommand when `python -m runner runtime-smoke` is invoked.

**Decision rationale for `__main__.py` change:**

The current `__main__.py` unconditionally calls `doctor.main()`, which requires the `doctor` subcommand. To add a `runtime-smoke` subcommand, `__main__.py` must inspect `sys.argv` and route to the correct module. The minimal change is:

```python
import sys
from .doctor import main as doctor_main
from .runtime_smoke import main as smoke_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "runtime-smoke":
        raise SystemExit(smoke_main(sys.argv[2:]))
    raise SystemExit(doctor_main())
```

This preserves backward compatibility with `python -m runner doctor` and adds `python -m runner runtime-smoke` without modifying `doctor.py`'s arg parser.

**Rejected alternatives:**
- Adding a wrapper argparse in `__main__.py` — unnecessary for a single additional subcommand. Direct argv inspection is simpler and doesn't require restructuring the existing `doctor.main()` parser.
- Adding all commands to `doctor.py`'s parser — mixes concerns. `runtime-smoke` is a different category of runner behavior.

## Smoke Demo Behavior

### Callable: `run_runtime_smoke_demo() -> dict`

The smoke demo produces a deterministic dict with these keys:

```python
{
    "smoke_demo": "runtime",
    "run_id": "smoke-run-001",
    "run_status": "completed",
    "step_count": 2,
    "checkpoint_count": 1,
    "evidence_summary": {
        "total": 2,
        "passed": 1,
        "failed": 0,
        "warning": 1,
        "failing_evidence_ids": [],
        "warning_evidence_ids": ["ev-warn-001"],
    },
    "final_report_present": True,
    "final_report_id": "smoke-run-001-report",
}
```

### Lifecycle sequence

```python
def run_runtime_smoke_demo() -> dict:
    import datetime

    from core.runtime_substrate import (
        AgentRole, RunStatus, StepStatus,
        RunState, StepBoundary, Checkpoint,
        create_run_state,
    )
    from core.runtime.transitions import (
        validate_run_transition, validate_step_transition,
        validate_checkpoint_attachment,
    )
    from core.runtime.verification import (
        VerificationEvidence, create_verification_evidence,
    )
    from core.runtime.store import InMemoryRuntimeStore

    store = InMemoryRuntimeStore()

    # Fixed deterministic timestamps
    T0 = datetime.datetime(2026, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)
    T1 = datetime.datetime(2026, 6, 21, 12, 5, 0, tzinfo=datetime.timezone.utc)
    T2 = datetime.datetime(2026, 6, 21, 12, 10, 0, tzinfo=datetime.timezone.utc)

    # 1. Create run
    run = RunState(
        run_id="smoke-run-001",
        task_id="smoke-task-001",
        purpose_id="smoke-purpose-001",
        domain="smoke",
        status=RunStatus.PENDING,
        steps=[],
        created_at=T0,
        updated_at=T0,
    )
    store.create_run(run)

    # 2. Create step 1, transition to RUNNING, then COMPLETED
    step1 = StepBoundary(
        step_id="step-001",
        agent_role=AgentRole.WORKER_CODER,
        status=StepStatus.PENDING,
    )
    run = store.get_run("smoke-run-001")  # deep copy
    run.append_step(step1)

    # Transition step PENDING -> RUNNING -> COMPLETED
    validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
    validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)
    run.steps[0].status = StepStatus.RUNNING
    run.steps[0].started_at = T1
    run.steps[0].status = StepStatus.COMPLETED
    run.steps[0].completed_at = T2

    # Transition run PENDING -> RUNNING
    validate_run_transition(RunStatus.PENDING, RunStatus.RUNNING)
    run.status = RunStatus.RUNNING
    store.save_run(run)

    # 3. Create checkpoint
    cp1 = Checkpoint(
        checkpoint_id="cp-001",
        run_id="smoke-run-001",
        step_id="step-001",
        captured_at=T2,
        run_state_hash="smoke-hash-001",
        artifact_ids=["artifact-001"],
    )
    validate_checkpoint_attachment(run, cp1)
    run.steps[0].checkpoint_id = "cp-001"
    store.save_run(run)

    # 4. Create step 2 (for more lifecycle)
    run = store.get_run("smoke-run-001")
    step2 = StepBoundary(
        step_id="step-002",
        agent_role=AgentRole.REVIEWER,
        status=StepStatus.PENDING,
    )
    validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
    run.append_step(step2)
    run.steps[1].status = StepStatus.RUNNING
    run.steps[1].started_at = T2
    store.save_run(run)

    # 5. Attach verification evidence
    ev_pass = create_verification_evidence(
        evidence_id="ev-pass-001",
        step_id="step-001",
        check_name="lint",
        status="passed",
        message="All lint checks passed",
    )
    ev_warn = create_verification_evidence(
        evidence_id="ev-warn-001",
        step_id="step-002",
        check_name="coverage",
        status="warning",
        message="Coverage below threshold",
    )
    store.attach_verification_evidence("smoke-run-001", ev_pass)
    store.attach_verification_evidence("smoke-run-001", ev_warn)

    # 6. Build final report
    store.validate_final_report_readiness("smoke-run-001")
    report = store.build_final_report("smoke-run-001")

    # 7. Transition run to COMPLETED via final report attachment
    from core.runtime.transitions import validate_final_report_attachment
    run = store.get_run("smoke-run-001")
    validate_final_report_attachment(run, report)
    run.status = RunStatus.COMPLETED
    store.save_run(run)

    # 8. Produce deterministic output
    evidence_summary = store.summarize_verification_evidence("smoke-run-001")
    return {
        "smoke_demo": "runtime",
        "run_id": "smoke-run-001",
        "run_status": "completed",
        "step_count": 2,
        "checkpoint_count": 1,
        "evidence_summary": {
            "total": evidence_summary["total"],
            "passed": evidence_summary["passed"],
            "failed": evidence_summary["failed"],
            "warning": evidence_summary["warning"],
            "failing_evidence_ids": evidence_summary["failing_evidence_ids"],
            "warning_evidence_ids": evidence_summary["warning_evidence_ids"],
        },
        "final_report_present": True,
        "final_report_id": report.report_id,
    }
```

### CLI entrypoint: `python -m runner runtime-smoke`

A `main(argv)` function in `runtime_smoke.py` that:
1. Calls `run_runtime_smoke_demo()`
2. Prints JSON via `json.dumps(result, indent=2, sort_keys=True)`
3. Returns 0 on success, 1 on failure

### `__main__.py` change

The existing `__main__.py` changes from:
```python
from .doctor import main
if __name__ == "__main__":
    raise SystemExit(main())
```

To:
```python
import sys
from .doctor import main as doctor_main
from .runtime_smoke import main as smoke_main
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "runtime-smoke":
        raise SystemExit(smoke_main(sys.argv[2:]))
    raise SystemExit(doctor_main())
```

This is backward-compatible:
- `python -m runner` → calls `doctor_main()` → argparse requires `doctor` subcommand → exit 2 (unchanged)
- `python -m runner doctor` → calls `doctor_main()` → exit 0 (unchanged)
- `python -m runner runtime-smoke` → calls `smoke_main()` → exit 0

## Output Rules

- No raw repository dumps.
- No absolute local paths.
- No environment-specific values.
- No random ids.
- No current time — fixed deterministic timestamps are used.
- JSON output is serializable with `json.dumps(sort_keys=True)`.
- Output is stable across repeated calls (deterministic).

## Error Model

- `run_runtime_smoke_demo()` raises existing Core errors naturally (TransitionError, VerificationError, RuntimeStoreError) if the lifecycle sequence is invalid.
- `main(argv)` catches Exception and prints to stderr, returns 1.
- Tests call `run_runtime_smoke_demo()` directly (not via subprocess) where possible.
- No broad exception swallowing.

## API Surface

```python
# services/runner/src/runner/runtime_smoke.py

def run_runtime_smoke_demo() -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

```python
# Test usage

from runner.runtime_smoke import run_runtime_smoke_demo

result = run_runtime_smoke_demo()
assert result["smoke_demo"] == "runtime"
assert result["step_count"] == 2
```

```python
# CLI usage
# PYTHONPATH=services/core/src:services/runner/src python -m runner runtime-smoke
```

## Implementation Rules

Future implementation must be:

- stdlib only
- deterministic
- no LLM calls
- no model-provider routing
- no network
- no subprocess (within callable; subprocess is acceptable for the CLI test)
- no persistence
- no filesystem writes
- no SQLite
- no Redis
- no distributed cache
- no Docker behavior
- no Git behavior
- no domain-adapter behavior
- no conductor pipeline
- no human approval UI
- no broad runner rewrite
- no schema changes
- no docs changes
- no changes to Core runtime modules

## Future Allowed Write Paths

- `services/runner/src/runner/runtime_smoke.py` (new)
- `services/runner/tests/test_runtime_smoke.py` (new)
- `services/runner/src/runner/__main__.py` (modify — minimal argv routing)

Precommit review may later write only:
- `.project-memory/pr/0049-runner-runtime-smoke-demo/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0049-runner-runtime-smoke-demo/PLAN.md` (planner only)
- `.project-memory/pr/0049-runner-runtime-smoke-demo/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- `agents/**`
- `schemas/**`
- `docs/**`
- `services/core/**` (no Core module changes)
- `services/runner/**` except exact allowed files listed above
- `services/task_intake/**`
- `services/model_gateway/**`
- `services/conductor/**`
- `packages/**`
- `apps/**`
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `PHASE_0_DECOMPOSITION.md`
- `ROADMAP_PHASE_0_PR_PLAN.md`

## Required Tests

### Smoke callable

- returns a dict with expected keys
- `result["smoke_demo"] == "runtime"`
- `result["run_id"] == "smoke-run-001"`
- `result["final_report_present"] is True`
- `result["evidence_summary"]["total"] == 2`
- `result["evidence_summary"]["passed"] == 1`
- produces same output across repeated calls (deterministic)

### Evidence summary integrity

- evidence summary contains passed=1, warning=1
- failing_evidence_ids is empty
- warning_evidence_ids contains "ev-warn-001"

### JSON serializability

- `json.dumps(result, sort_keys=True)` succeeds

### Runner CLI entrypoint

- `python -m runner runtime-smoke` succeeds with expected output
- `python -m runner doctor` still succeeds (backward compat)

### Compatibility

- Core runtime store tests still pass
- Core runtime verification tests still pass
- Core runtime transitions tests still pass
- Core runtime substrate tests still pass
- Runner doctor CLI tests still pass

### General

- tests are pure in-memory (no I/O except optional stdout capture)
- no network in tests
- no subprocess in tests except the single doctor CLI backward-compat test
- no persistence in tests
- no distributed cache in tests
- no old names/examples

## Validation Commands

Future implementation should run:

```bash
PYTHONPATH=services/core/src:services/runner/src python -m pytest services/runner/tests/test_runtime_smoke.py -v
PYTHONPATH=services/core/src:services/runner/src python -m runner runtime-smoke
PYTHONPATH=services/core/src:services/runner/src python -m runner doctor
python -m pytest services/core/tests/test_runtime_store.py -q
python -m pytest services/core/tests/test_runtime_verification.py -q
python -m pytest services/core/tests/test_runtime_transitions.py -q
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
grep -R -n "redis\|sqlite\|open(\|Path(.*write\|requests\|subprocess\|docker\|water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/runner/src/runner services/runner/tests || true
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -R -n "def run_runtime_smoke_demo\|runtime-smoke\|runtime_smoke" services/runner/src/runner services/runner/tests
```

## Expected Changed Files

1. `services/runner/src/runner/runtime_smoke.py` — new module
2. `services/runner/tests/test_runtime_smoke.py` — new tests
3. `services/runner/src/runner/__main__.py` — modified (argv routing)

## Non-goals

- no LLM integration
- no model-provider integration
- no Git operations
- no Docker
- no domain adapter
- no persistence or database
- no SQLite
- no Redis
- no distributed cache
- no HTTP server
- no conductor pipeline
- no human approval UI
- no changes to `agents/**`
- no changes to `schemas/**`
- no changes to `docs/**`
- no changes to `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- no `.ariadne/**` namespace creation
- no root dependency/build changes
- no old `.grace` namespace
- no water_meter / broken_clock / old Flask examples
- no changes to Core runtime modules (`services/core/**`)
- no changes to `doctor.py`, `models.py`, `apply.py`, or other runner modules (except `__main__.py`)
- no changes to existing test files

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema changes, no docs changes, no agents changes, no apps changes, no Core changes, no forbidden path writes.
- Reviewers must verify: stdlib-only, no LLM calls, no network, no persistence, no Git/Docker.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: `__main__.py` backward compatibility (doctor still works).
- Reviewers must verify: output is deterministic and contains expected keys.
- Reviewers must verify: no timestamps are generated at runtime (fixed timestamps only).
- Reviewers must verify: `run_runtime_smoke_demo()` exercise is a full lifecycle (create → transition → evidence → report → output).

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `.project-memory/**` except PLAN.md by planner → stop
- about to write to `schemas/**` → stop
- about to write to `docs/**` → stop
- about to modify Core runtime internals → stop
- about to write to `conductor/task_intake/model_gateway` → stop
- about to modify `doctor.py`, `models.py`, `apply.py`, or other runner modules beyond `__main__.py` → stop
- implementation requires LLM SDK → stop
- implementation requires subprocess or network → stop
- implementation requires third-party dependency → stop
- implementation requires persistence/storage → stop
- implementation requires SQLite/Redis/distributed cache → stop
- demo requires filesystem writes → stop
- demo requires Git or Docker → stop
- demo uses runtime-generated timestamps → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Evidence dict-swapping pattern in store.** The store's evidence methods temporarily replace the module-level `_run_evidence_store` in verification.py. This is fragile but functional. **Decision:** Accept as-is for the smoke demo. A future PR can refactor verification.py to accept an explicit evidence store parameter.

2. **Should step-002 be completed or left running?** **Decision:** Leave it RUNNING (not completed). This demonstrates a realistic multi-step scenario where some steps are still in progress when the final report is built. However, `validate_final_report_readiness` requires all completed steps — and step-002 is RUNNING, so it's incomplete. **Resolution:** The smoke demo should set step-002 to COMPLETED before building the final report. Updated lifecycle: step-002 transitions PENDING → RUNNING → COMPLETED.

3. **Does `save_run` after the deep copy from `get_run` work correctly?** Yes — `get_run` returns a deep copy, the caller modifies it, then `save_run` stores the modified copy. The caller is responsible for state validity per the store's design.

## Decisions Made

### api_surface

```
runner.runtime_smoke:
  run_runtime_smoke_demo() -> dict
  main(argv=None) -> int

runner.__main__:
  argv routing: "runtime-smoke" → smoke_main, otherwise → doctor_main
```

### runner_entrypoint

```
python -m runner runtime-smoke
```

Implemented via argv inspection in `__main__.py`. Backward compatible with `python -m runner doctor`.

### smoke_lifecycle_scope

```
1. Create store
2. Create RunState with fixed timestamps
3. Create step-001, transition PENDING → RUNNING → COMPLETED
4. Create checkpoint for step-001
5. Create step-002, transition PENDING → RUNNING → COMPLETED
6. Attach 2 evidence records (1 passed, 1 warning)
7. Validate final report readiness
8. Build final report
9. Transition run to COMPLETED
10. Return deterministic dict with smoke_demo, run_id, step_count, checkpoint_count, evidence_summary, final_report_present, final_report_id
```

### output_contract

```
{
    "smoke_demo": "runtime",
    "run_id": "smoke-run-001",
    "run_status": "completed",
    "step_count": 2,
    "checkpoint_count": 1,
    "evidence_summary": {"total": 2, "passed": 1, "failed": 0, "warning": 1, "failing_evidence_ids": [], "warning_evidence_ids": ["ev-warn-001"]},
    "final_report_present": True,
    "final_report_id": "smoke-run-001-report"
}

Deterministic. No runtime timestamps. No random ids. No absolute paths.
```

### implementation_location

```
services/runner/src/runner/runtime_smoke.py  (new)
services/runner/tests/test_runtime_smoke.py  (new)
services/runner/src/runner/__main__.py        (modified — minimal argv routing)
```

### test_strategy

```
Direct callable tests for run_runtime_smoke_demo().
One CLI backward-compat subprocess test for `python -m runner runtime-smoke`.
No changes to Core test files.

Test classes:
- TestRunRuntimeSmokeDemo (callable contract and determinism)
- TestRuntimeSmokeCLI (subprocess, if needed — preferred direct callable)
- TestBackwardCompat (doctor still works after __main__.py change)
```

---

PLAN written: yes
