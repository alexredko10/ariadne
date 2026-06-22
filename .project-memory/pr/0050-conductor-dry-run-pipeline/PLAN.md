# PR 0050 — Conductor Dry-Run Pipeline Plan

## Goal

Add a deterministic conductor dry-run pipeline that exercises Ariadne Core runtime substrate through a conductor-level loop.

The dry-run should simulate conductor orchestration without model calls, provider routing, agent execution, domain adapter behavior, persistence, or external infrastructure.

## Architectural Thesis

The conductor is responsible for driving execution boundaries.

This PR introduces the first conductor loop, but keeps it dry-run and deterministic.

The model remains replaceable.
The substrate owns execution state.
The conductor coordinates state transitions without depending on model output.

## Context Snapshot

- **current HEAD sha**: `3d0b1e6e16769535db6fa58ee4bd75d1185ab826`
- **current branch**: `0049-runner-runtime-smoke-demo` (planning PR 0050 from the PR 0049 commit — PR 0049 is committed but not merged to main)
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `c229979` (main after PR 0048 merge — PR 0049 not yet merged)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: true — current HEAD (`3d0b1e6`) is ahead of `base_sha` (`c229979`) by PR 0049. This is expected since PR 0050 builds on PR 0049. No blocking delta.
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
- `.project-memory/pr/0049-runner-runtime-smoke-demo/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/transitions.py`
- `services/core/src/core/runtime/verification.py`
- `services/core/src/core/runtime/store.py`
- `services/runner/src/runner/runtime_smoke.py`
- `services/runner/src/runner/__main__.py`
- `services/conductor/src/conductor/__init__.py`
- `services/conductor/tests/test_conductor_smoke.py`
- `services/conductor/README.md`
- `schemas/run-state.schema.yml`
- `schemas/checkpoint.schema.yml`

## Current Runtime Snapshot

### Core runtime (`services/core/src/core/`)

**Substrate entities** (in `runtime_substrate.py`):
- `RunStatus` enum: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- `StepStatus` enum: PENDING, RUNNING, COMPLETED, FAILED, BLOCKED
- `AgentRole` enum: 9 roles
- `RunState` (mutable, with `steps: list[StepBoundary]`, `to_dict`/`from_dict`)
- `StepBoundary` (mutable, with `status`, `to_dict`/`from_dict`)
- `Checkpoint` (frozen, with `to_dict`/`from_dict`)
- `AgentExecutionRecord` (mutable, with `to_dict`/`from_dict`)
- `FinalReportDraft` (mutable, with `to_dict`/`from_dict`)
- 7 frozen reference types
- Factory helpers: `create_run_state`, `record_checkpoint`, `record_agent_execution`, `build_final_report_draft`

**Transition validators** (in `runtime/transitions.py`):
- `TransitionError` with current_state, attempted_transition, reason
- `validate_run_transition`, `validate_step_transition`, `validate_checkpoint_attachment`, `validate_agent_record_attachment`, `validate_final_report_attachment`

**Verification evidence** (in `runtime/verification.py`):
- `VerificationError` with subject, reason, evidence_id, step_id
- `VerificationEvidence` dataclass with `to_dict`/`from_dict`
- `create_verification_evidence`, `attach_verification_evidence`, `get_evidence_for_run`, `summarize_verification_evidence`, `validate_final_report_readiness`, `build_final_report`
- Module-level `_run_evidence_store: dict[str, list[VerificationEvidence]]`

**In-memory store** (in `runtime/store.py`):
- `RuntimeStoreError` with operation, subject, reason
- `InMemoryRuntimeStore` class: `create_run`, `get_run`, `has_run`, `save_run`, `list_runs`, `delete_run`, `attach_verification_evidence`, `get_evidence_for_run`, `summarize_verification_evidence`, `validate_final_report_readiness`, `build_final_report`

### Runner smoke demo (`services/runner/src/runner/runtime_smoke.py`)

Proves a full lifecycle: create run → add 2 steps → transitions → checkpoint → 2 evidence records → readiness → build report → COMPLETED. Deterministic output with fixed timestamps. CLI: `python -m runner runtime-smoke`.

## Current Runner Smoke Snapshot

PR 0049 `run_runtime_smoke_demo()` exercises:
1. Create `InMemoryRuntimeStore`
2. Create `RunState` with fixed timestamps
3. Create 2 steps (`StepBoundary`), transition each `PENDING → RUNNING → COMPLETED`
4. Create checkpoint via `Checkpoint` constructor, attach via `validate_checkpoint_attachment`
5. Attach 2 `VerificationEvidence` records (1 passed, 1 warning)
6. `validate_final_report_readiness` + `build_final_report`
7. Transition run to `COMPLETED` via `validate_final_report_attachment`
8. Return deterministic dict

The runner smoke is a proof of the runtime vertical slice. The conductor dry-run is a proof of conductor coordination. The dry-run must not simply call the runner smoke demo — it must implement a phase-driven loop that the conductor would use in production.

## Current Conductor Snapshot

```
services/conductor/
    README.md  — placeholder
    src/conductor/
        __init__.py  — """conductor service package."""
    tests/
        __init__.py
        test_conductor_smoke.py  — assert True
```

Conductor is a blank placeholder. No modules, no entrypoint, no CLI. The first substantive conductor module will be `dry_run.py`. A `__main__.py` is needed for CLI access.

## Implementation Location Decision

**Decision: Three files to create**

1. **`services/conductor/src/conductor/dry_run.py`** (new) — `run_conductor_dry_run()` function and `main()` CLI entrypoint.
2. **`services/conductor/tests/test_dry_run.py`** (new) — tests for the dry-run callable.
3. **`services/conductor/src/conductor/__main__.py`** (new) — module entrypoint for `python -m conductor dry-run`.

**Rationale for `__main__.py`:**
- Conductor has no entrypoint today. The eventual conductor CLI will need `__main__.py`.
- A minimal `__main__.py` follows the same pattern as runner's `__main__.py`: inspect `sys.argv` and route to the correct module.
- No changes to existing conductor files (only `__init__.py` exists as a docstring).

**Rejected alternatives:**
- Adding dry-run to a non-existent `__main__.py` by modifying `__init__.py` — wrong pattern.
- Using runner's CLI for conductor — mixes service boundaries.
- Skipping `__main__.py` and only providing a callable — insufficient for CLI demo.

## Dry-Run Pipeline Behavior

### Callable: `run_conductor_dry_run() -> dict`

The dry-run produces a deterministic dict:

```python
{
    "dry_run": "conductor",
    "run_id": "dry-run-001",
    "run_status": "completed",
    "planned_step_count": 2,
    "completed_step_count": 2,
    "checkpoint_count": 2,
    "evidence_summary": {
        "total": 2,
        "passed": 2,
        "failed": 0,
        "warning": 0,
    },
    "final_report_present": True,
    "final_report_id": "dry-run-001-report",
    "conductor_events": [
        "initialize_run",
        "plan_steps",
        "start_run",
        "start_step:step-001",
        "complete_step:step-001",
        "checkpoint:step-001",
        "start_step:step-002",
        "complete_step:step-002",
        "checkpoint:step-002",
        "attach_evidence",
        "build_final_report",
        "complete_run",
    ],
}
```

### Conductor phase model

The dry-run implements a deterministic phase loop. Rather than manually calling each transition (as the runner smoke does), the dry-run demonstrates a phase-driven pattern that the real conductor would use:

```python
def run_conductor_dry_run() -> dict:
    phases = [
        ("initialize_run", _phase_initialize_run),
        ("plan_steps", _phase_plan_steps),
        ("start_run", _phase_start_run),
        ("start_step:step-001", _phase_start_step),
        ("complete_step:step-001", _phase_complete_step),
        ("checkpoint:step-001", _phase_checkpoint),
        ("start_step:step-002", _phase_start_step),
        ("complete_step:step-002", _phase_complete_step),
        ("checkpoint:step-002", _phase_checkpoint),
        ("attach_evidence", _phase_attach_evidence),
        ("build_final_report", _phase_build_report),
        ("complete_run", _phase_complete_run),
    ]
    events = []
    for name, phase_fn in phases:
        phase_fn(store, run_id, timestamps, events)
        events.append(name)
    return build_output(store, run_id, events)
```

Each phase function:
- Takes the store, run_id, a timestamps dict, and the events list.
- Calls the appropriate Core runtime API.
- Raises on invalid transitions.
- Is deterministic (fixed timestamps, no random values).

This phase-driven structure is where the conductor dry-run differs architecturally from the runner smoke. The runner smoke manually calls transitions step by step. The dry-run demonstrates a phase loop that the production conductor would iterate over.

### Phase functions

**`_phase_initialize_run(store, run_id, ts, events)`**
- Creates `RunState` with fixed timestamps, `RunStatus.PENDING`.
- Calls `store.create_run(run)`.

**`_phase_plan_steps(store, run_id, ts, events)`**
- Creates 2 `StepBoundary` objects (worker_coder + reviewer).
- Appends to run via `run.append_step()`.
- Calls `store.save_run(run)`.

**`_phase_start_run(store, run_id, ts, events)`**
- Calls `validate_run_transition(PENDING, RUNNING)`.
- Gets run, sets status to `RUNNING`, saves via `store.save_run()`.

**`_phase_start_step(store, run_id, ts, events)`** — called per step
- Gets current step from run.
- Calls `validate_step_transition(PENDING, RUNNING)`.
- Sets step status to `RUNNING`, `started_at` to fixed timestamp.
- Calls `store.save_run(run)`.

**`_phase_complete_step(store, run_id, ts, events)`** — called per step
- Gets current step.
- Calls `validate_step_transition(RUNNING, COMPLETED)`.
- Sets step status to `COMPLETED`, `completed_at` to fixed timestamp.
- Calls `store.save_run(run)`.

**`_phase_checkpoint(store, run_id, ts, events)`** — called per step
- Creates `Checkpoint` with fixed values.
- Calls `validate_checkpoint_attachment(run, checkpoint)`.
- Sets step's `checkpoint_id`.
- Calls `store.save_run(run)`.

**`_phase_attach_evidence(store, run_id, ts, events)`**
- Creates 2 `VerificationEvidence` records (both passed, one per step).
- Calls `store.attach_verification_evidence()` for each.

**`_phase_build_report(store, run_id, ts, events)`**
- Calls `store.validate_final_report_readiness(run_id)`.
- Calls `store.build_final_report(run_id)`.
- Does NOT transition the run (phase_complete_run handles that).

**`_phase_complete_run(store, run_id, ts, events)`**
- Calls `validate_final_report_attachment(run, report)`.
- Sets run status to `COMPLETED`.
- Calls `store.save_run(run)`.

### Output dict construction

`build_output(store, run_id, events)`:
```python
report = store.build_final_report(run_id)  # returns cached or rebuilt
evidence_summary = store.summarize_verification_evidence(run_id)
run = store.get_run(run_id)
return {
    "dry_run": "conductor",
    "run_id": run_id,
    "run_status": run.status.value,
    "planned_step_count": len(run.steps),
    "completed_step_count": sum(1 for s in run.steps if s.status.value == "completed"),
    "checkpoint_count": sum(1 for s in run.steps if s.checkpoint_id is not None),
    "evidence_summary": {
        "total": evidence_summary["total"],
        "passed": evidence_summary["passed"],
        "failed": evidence_summary["failed"],
        "warning": evidence_summary["warning"],
    },
    "final_report_present": True,
    "final_report_id": report.report_id,
    "conductor_events": events,
}
```

## Output Rules

- No raw repository dumps.
- No absolute local paths.
- No environment-specific values.
- No random ids.
- No current time — fixed deterministic timestamps are used.
- JSON output is serializable with `json.dumps(sort_keys=True)`.
- Output is stable across repeated calls (deterministic).

## Error Model

- `run_conductor_dry_run()` raises existing Core errors (TransitionError, VerificationError, RuntimeStoreError) if phase sequence or operations are invalid.
- `main(argv)` catches Exception and prints to stderr, returns 1.
- Tests call `run_conductor_dry_run()` directly.
- No broad exception swallowing.
- No large new conductor error hierarchy — existing Core error types cover dry-run needs.

## API Surface

```python
# services/conductor/src/conductor/dry_run.py

def run_conductor_dry_run() -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

```python
# Test usage

from conductor.dry_run import run_conductor_dry_run

result = run_conductor_dry_run()
assert result["dry_run"] == "conductor"
assert result["completed_step_count"] == 2
```

```python
# CLI usage
# PYTHONPATH=services/core/src:services/conductor/src python -m conductor dry-run
```

```python
# services/conductor/src/conductor/__main__.py

import sys
from .dry_run import main as dry_run_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dry-run":
        raise SystemExit(dry_run_main(sys.argv[2:]))
    print("usage: python -m conductor dry-run", file=sys.stderr)
    raise SystemExit(2)
```

## Implementation Rules

Future implementation must be:

- stdlib only
- deterministic
- no LLM calls
- no model-provider routing
- no network
- no subprocess (within callable; subprocess acceptable only for CLI integration test)
- no persistence
- no filesystem writes
- no SQLite
- no Redis
- no distributed cache
- no Docker behavior
- no Git behavior
- no domain-adapter behavior
- no real agent execution
- no human approval UI
- no broad conductor rewrite
- no schema changes
- no docs changes
- no changes to Core runtime modules
- no changes to runner modules

## Future Allowed Write Paths

- `services/conductor/src/conductor/dry_run.py` (new)
- `services/conductor/tests/test_dry_run.py` (new)
- `services/conductor/src/conductor/__main__.py` (new)

Precommit review may later write only:
- `.project-memory/pr/0050-conductor-dry-run-pipeline/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0050-conductor-dry-run-pipeline/PLAN.md` (planner only)
- `.project-memory/pr/0050-conductor-dry-run-pipeline/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- `agents/**`
- `schemas/**`
- `docs/**`
- `services/core/**` (no Core module changes)
- `services/runner/**` (no runner changes)
- `services/conductor/**` except exact allowed files listed above
- `services/task_intake/**`
- `services/model_gateway/**`
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

### Dry-run callable

- returns a dict with expected keys
- `result["dry_run"] == "conductor"`
- `result["run_id"] == "dry-run-001"`
- `result["planned_step_count"] >= 2`
- `result["completed_step_count"] == result["planned_step_count"]`
- `result["checkpoint_count"] == result["planned_step_count"]` (checkpoint per step)
- `result["final_report_present"] is True`
- `result["evidence_summary"]["passed"] == 2`
- `result["evidence_summary"]["failed"] == 0`
- `result["evidence_summary"]["warning"] == 0`
- `result["conductor_events"]` is a list with expected phase names in order
- produces same output across repeated calls (deterministic)

### Output safety

- `json.dumps(result, sort_keys=True)` succeeds
- no absolute paths in output
- no current timestamp (all timestamps are fixed `2026-06-21T...`)
- no random ids
- no raw repository dumps
- no model-generated summaries

### Phase behavior

- `initialize_run` creates a run in PENDING status
- `plan_steps` adds exactly 2 steps to the run
- `start_run` transitions run to RUNNING
- each `start_step` transitions step PENDING → RUNNING
- each `complete_step` transitions step RUNNING → COMPLETED
- each `checkpoint` attaches a valid checkpoint
- `attach_evidence` adds 2 evidence records
- `build_final_report` produces a FinalReportDraft
- `complete_run` transitions run to COMPLETED

### Conductor CLI

- `python -m conductor dry-run` succeeds (subprocess test or direct test)
- `python -m conductor` with no args exits non-zero (usage shown)
- `python -m conductor unknown` exits non-zero

### Compatibility

- runner runtime smoke tests still pass
- Core runtime store tests still pass
- Core runtime verification tests still pass
- Core runtime transitions tests still pass
- Core runtime substrate tests still pass

### General

- tests are pure in-memory
- no I/O in tests except optional stdout capture
- no network in tests
- no subprocess in tests except the conductor CLI backward-compat test
- no persistence in tests
- no distributed cache in tests
- no old names/examples

## Validation Commands

Future implementation should run:

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_dry_run.py -v
PYTHONPATH=services/core/src:services/conductor/src python -m conductor dry-run
PYTHONPATH=services/core/src:services/runner/src python -m pytest services/runner/tests/test_runtime_smoke.py -q
python -m pytest services/core/tests/test_runtime_store.py -q
python -m pytest services/core/tests/test_runtime_verification.py -q
python -m pytest services/core/tests/test_runtime_transitions.py -q
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
grep -R -n "redis\|sqlite\|open(\|Path(.*write\|requests\|subprocess\|docker\|water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/conductor/src/conductor services/conductor/tests || true
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -R -n "def run_conductor_dry_run\|dry-run\|conductor_events\|_phase_" services/conductor/src/conductor services/conductor/tests
```

## Expected Changed Files

1. `services/conductor/src/conductor/dry_run.py` — new module
2. `services/conductor/tests/test_dry_run.py` — new tests
3. `services/conductor/src/conductor/__main__.py` — new entrypoint

## Non-goals

- no LLM integration
- no model-provider integration
- no real agent execution
- no Git operations
- no Docker
- no domain adapter
- no persistence or database
- no SQLite
- no Redis
- no distributed cache
- no HTTP server
- no human approval UI
- no changes to `agents/**`
- no changes to `schemas/**`
- no changes to `docs/**`
- no changes to `runner/**`
- no changes to Core runtime internals
- no changes to `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- no `.ariadne/**` namespace creation
- no root dependency/build changes
- no old `.grace` namespace
- no water_meter / broken_clock / old Flask examples

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema changes, no docs changes, no agents changes, no apps changes, no Core changes, no runner changes, no forbidden path writes.
- Reviewers must verify: stdlib-only, no LLM calls, no network, no persistence, no Git/Docker.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: dry-run uses phase-driven loop (not manual step-by-step transitions like runner smoke).
- Reviewers must verify: output is deterministic and contains expected keys.
- Reviewers must verify: `conductor_events` list matches phase execution order.
- Reviewers must verify: no timestamps are generated at runtime (fixed timestamps only).

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `.project-memory/**` except PLAN.md by planner → stop
- about to write to `schemas/**` → stop
- about to write to `docs/**` → stop
- about to modify Core runtime internals → stop
- about to write to `runner/**` → stop
- about to write to `task_intake/model_gateway` → stop
- implementation requires LLM SDK → stop
- implementation requires model-generated output → stop
- implementation requires real agent execution → stop
- implementation requires subprocess or network → stop
- implementation requires third-party dependency → stop
- implementation requires persistence/storage → stop
- implementation requires SQLite/Redis/distributed cache → stop
- dry-run requires filesystem writes → stop
- dry-run requires Git or Docker → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should the dry-run store evidence in the store's internal dict or the verification module's dict?** **Decision:** Use the store's internal evidence dict (which the store swaps into verification.py). This is the same pattern used by the runner smoke demo and keeps evidence scoped to the store instance.
2. **Should `conductor_events` be a list of strings or structured dicts?** **Decision:** List of strings for simplicity. Structured dicts would be more expressive but unnecessary for a dry-run. The real conductor will use structured event records in a future PR.
3. **Should evidence be attached per step or batch after all steps complete?** **Decision:** Batch after all steps complete. The `attach_evidence` phase attaches evidence for all completed steps at once. This simplifies the phase model while still demonstrating evidence accumulation. In the real conductor, evidence would likely be attached per step.
4. **Should `build_output` call `build_final_report` again (redundant since phase already did it)?** **Decision:** Store the report reference from the `build_final_report` phase and pass it to `build_output`. This avoids redundant computation and ensures the output function uses the exact report produced during the pipeline.

## Decisions Made

### api_surface

```
conductor.dry_run:
  run_conductor_dry_run() -> dict
  main(argv=None) -> int

conductor.__main__:
  argv routing: "dry-run" → dry_run_main, otherwise → usage + exit 2
```

### conductor_entrypoint

```
python -m conductor dry-run
```

Implemented via new `__main__.py` that inspects `sys.argv`.

### dry_run_phase_scope

```
12 phases in deterministic order:
  initialize_run → plan_steps → start_run →
  start_step:step-001 → complete_step:step-001 → checkpoint:step-001 →
  start_step:step-002 → complete_step:step-002 → checkpoint:step-002 →
  attach_evidence → build_final_report → complete_run

Each phase is a separate callable function.
Phase loop is a list of (name, fn) tuples.
```

### output_contract

```
{
    "dry_run": "conductor",
    "run_id": "dry-run-001",
    "run_status": "completed",
    "planned_step_count": 2,
    "completed_step_count": 2,
    "checkpoint_count": 2,
    "evidence_summary": {"total": 2, "passed": 2, "failed": 0, "warning": 0},
    "final_report_present": True,
    "final_report_id": "dry-run-001-report",
    "conductor_events": ["initialize_run", "plan_steps", "start_run", ...]
}

Deterministic. No runtime timestamps. No random ids. No absolute paths.
```

### implementation_location

```
services/conductor/src/conductor/dry_run.py       (new)
services/conductor/tests/test_dry_run.py           (new)
services/conductor/src/conductor/__main__.py       (new)
```

### test_strategy

```
Direct callable tests for run_conductor_dry_run().
One CLI backward-compat subprocess test for `python -m conductor dry-run`.
No changes to Core or runner test files.

Test classes:
- TestRunConductorDryRun (callable contract, determinism, output shape)
- TestConductorPhaseSequence (events match expected phase order)
- TestConductorCLI (subprocess for dry-run, unknown command, no args)
- TestConductorBackwardCompat (no change to existing conductor tests)
```

---

PLAN written: yes
