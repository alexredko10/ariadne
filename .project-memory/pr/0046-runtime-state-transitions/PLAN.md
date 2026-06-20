# PR 0046 — Runtime State Transitions Plan

## Goal

Add minimal state transition validation to Ariadne runtime substrate.

Make `RunState`, `StepBoundary`, `Checkpoint`, `AgentExecutionRecord`, and `FinalReportDraft` behave as a validated state machine, not arbitrary data containers.

## Architectural Thesis

Ariadne Core should encode domain-agnostic execution invariants.

Transition validation belongs in Core because it governs the substrate lifecycle, not coding-domain behavior.

The model remains replaceable.
The substrate owns state integrity.

## Context Snapshot

- **current HEAD sha**: `3b8a5336c94faaee671286a877b1b6c8feea1c00`
- **current branch**: `0046-runtime-state-transitions`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: not present in prior plan artifacts for PR 0046 (first PR in this branch chain); base_sha is `main` (target branch for merge)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml` — the memory_index.yml does not publish a numeric index version; contracts.yml version is used as the canonical reference)
- **stale_snapshot**: false — HEAD is current with merged PR 0045, no pending changes
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
- `.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md` (presumed — PR 0045 is merged, plan-review.yml not present but approved/merged)
- `services/core/src/core/runtime_substrate.py`
- `services/core/tests/test_runtime_substrate.py`
- `services/core/src/core/__init__.py`
- `schemas/run-state.schema.yml`
- `schemas/checkpoint.schema.yml`
- `schemas/agent-execution-contract.schema.yml` — not read (not needed for transition rules)
- `schemas/final-report.schema.yml` — not read (not needed for transition rules)
- `schemas/state-model.schema.yml` — not read (blueprint-only reference)
- `schemas/transition-graph.schema.yml` — not read (blueprint-only reference)

## Current Runtime Substrate Snapshot

### Entities in `services/core/src/core/runtime_substrate.py`

**Enums:**
- `RunStatus`: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- `StepStatus`: PENDING, RUNNING, COMPLETED, FAILED
- `RubricVerdict`: PASS, WARNING, FAIL, NEEDS_HUMAN_REVIEW
- `AgentRole`: ARCHITECT, PLANNER, LEAD_CODER, WORKER_CODER, TESTER, REVIEWER, SECURITY, VERIFIER, CUSTOM

**Frozen reference types** (ID wrappers with `to_dict`/`from_dict`):
- ContextPackRef, StateModelRef, TransitionGraphRef, RubricPackRef, RubricJudgeResultRef, ModelCapabilityProfileRef, LongContextStressProfileRef

**Mutable entities** (with `to_dict`/`from_dict`):
- `StepBoundary`: step_id, agent_role, status (StepStatus), started_at, completed_at, model_used, cost, artifact_ids, checkpoint_id, failure_mode
- `RunState`: run_id, task_id, purpose_id, domain, status (RunStatus), current_step_id, steps, created_at, updated_at
- `AgentExecutionRecord`: contract_id, run_id, step_id, role, purpose, pbs_node, plus many optional metadata fields
- `FinalReportDraft`: report_id, run_id, purpose_id, domain, root_purpose, created_at, plus optional summary/risk fields

**Immutable entity:**
- `Checkpoint`: checkpoint_id, run_id, step_id, captured_at, run_state_hash, artifact_ids, context_pack_id, memory_snapshot_hash, resumable, resume_instructions (frozen dataclass)

**Helper factory functions:**
- `create_run_state(...)` → RunState
- `record_checkpoint(...)` → Checkpoint
- `record_agent_execution(...)` → AgentExecutionRecord
- `build_final_report_draft(...)` → FinalReportDraft

**Notable gap:** `StepStatus` lacks `BLOCKED`. The `schemas/run-state.schema.yml` also lists only `pending | running | completed | failed` for step status. Adding BLOCKED extends the model — this is an additive change that does not break existing code.

### Tests in `services/core/tests/test_runtime_substrate.py`

- TestRunStateCreation (3 tests)
- TestAppendStep (3 tests)
- TestStepBoundaryDefaults (3 tests)
- TestCheckpointImmutability (1 test)
- TestAgentExecutionRecord (2 tests)
- TestFinalReportDraft (2 tests)
- TestReferenceTypes (7 tests)
- TestEnums (4 tests)
- TestHelpers (2 tests)
- TestSerialization (3 tests)
- TestToDict (13 tests including round-trip, deterministic, no-provider-hardcoding)

## Implementation Location Decision

**Decision: Use `services/core/src/core/runtime/transitions.py`**

Rationale:
- Current package structure is flat (`services/core/src/core/`). Creating `core/runtime/` follows the project's own conventions for module grouping without introducing a deep hierarchy.
- The future path anticipated by PR 0044/0045 decomposition — keeping transition logic in a separate module from substrate entities — is cleanest.
- `services/core/tests/test_runtime_transitions.py` is the corresponding test path.
- `services/core/src/core/runtime/__init__.py` is required as a package init; it will be minimal (empty or re-export docstring only).
- No other `core/` subpackages exist today, so this is the first subpackage. This is architecturally safe and follows Python package conventions.

**Rejected alternatives:**
- Adding transition logic to `runtime_substrate.py` — violates separation of concerns (entities vs. behavior).
- Creating `services/core/src/core/transitions.py` — possible but less clean for future grouping of runtime behavior (checkpoints, recovery, resume logic).

## StepStatus BLOCKED — Required Enum Extension

Before implementing transition rules, the `BLOCKED` status must be added to `StepStatus` in `services/core/src/core/runtime_substrate.py`.

Current `StepStatus`:
```python
class StepStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

After change:
```python
class StepStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
```

This is additive. Existing code referencing `StepStatus.PENDING`, `StepStatus.RUNNING`, `StepStatus.COMPLETED`, `StepStatus.FAILED` is unaffected. Only the enum class in `runtime_substrate.py` changes — no schema files are modified.

**Schema note:** `schemas/run-state.schema.yml` lists step status as `"pending | running | completed | failed"`. This is a blueprint schema, not an operational schema. The plan extends the Python model to include "blocked". Schema alignment with the blueprint is deferred to a future Phase 0 integration PR.

## Required State Transition Rules

### RunState transition rules

| From | To | Allowed | Condition |
|---|---|---|---|
| PENDING | RUNNING | yes | Run started |
| RUNNING | PAUSED | yes | Checkpoint captured |
| RUNNING | COMPLETED | yes | Final report must be attached |
| RUNNING | FAILED | yes | Unrecoverable error |
| PAUSED | RUNNING | yes | Resumed from checkpoint |
| PAUSED | FAILED | yes | Abandoned |
| COMPLETED | any | **no** | Terminal |
| FAILED | any | **no** | Terminal |
| CANCELLED | any | **no** | Terminal |
| RUNNING | CANCELLED | yes | Explicit cancellation |

### StepBoundary lifecycle rules

| From | To | Allowed | Condition |
|---|---|---|---|
| PENDING | RUNNING | yes | Step started |
| RUNNING | COMPLETED | yes | Step finished with evidence |
| RUNNING | FAILED | yes | Step error |
| RUNNING | BLOCKED | yes | Human approval required |
| BLOCKED | RUNNING | yes | Human approved |
| BLOCKED | FAILED | yes | Human rejected or timeout |
| COMPLETED | any | **no** | Terminal |
| FAILED | any | **no** | Terminal |

### Checkpoint attachment rules

- Checkpoint may only be attached to a run in RUNNING or PAUSED state.
- Checkpoint must reference an existing `step_id` in the run.
- Checkpoint must not be attached to COMPLETED, FAILED, or CANCELLED run.
- Duplicate `checkpoint_id` must be rejected.

### AgentExecutionRecord consistency rules

- Record may only be added to a step in RUNNING state.
- Record must not be added to terminal step (COMPLETED, FAILED).
- `agent_id` (mapped to `role` field) must not be None.
- `step_id` in record must match the target step.

### FinalReportDraft readiness rules

- Final report may only be attached when run is in RUNNING state.
- Final report attachment transitions run to COMPLETED.
- Final report must have at least one step_id reference (via changes list or equivalent).
- Run without completed steps cannot attach final report.

## Error Model

A single catchable Core-only error type:

```python
class TransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(
        self,
        current_state: str,
        attempted_transition: str,
        reason: str,
    ) -> None:
        self.current_state = current_state
        self.attempted_transition = attempted_transition
        self.reason = reason
        super().__init__(f"Cannot transition from {current_state} via {attempted_transition}: {reason}")
```

`TransitionError` belongs in `services/core/src/core/runtime/transitions.py`. An `errors.py` is not needed — a single exception class within the transitions module is sufficient for this scope.

## API Surface

Pure function API exported from `services/core/src/core/runtime/transitions.py`:

```python
def validate_run_transition(
    current_status: RunStatus,
    new_status: RunStatus,
) -> None: ...

def validate_step_transition(
    current_status: StepStatus,
    new_status: StepStatus,
) -> None: ...

def validate_checkpoint_attachment(
    run: RunState,
    checkpoint: Checkpoint,
) -> None: ...

def validate_agent_record_attachment(
    step: StepBoundary,
    record: AgentExecutionRecord,
) -> None: ...

def validate_final_report_attachment(
    run: RunState,
    report: FinalReportDraft,
) -> None: ...
```

All functions raise `TransitionError` on invalid transitions or attachment rules. No return values.

## Implementation Rules

Future implementation must be:

- stdlib only
- pure functions where possible
- no side effects
- no I/O
- no network
- no subprocess
- no hidden global state
- no provider-specific model logic
- no persistence/storage
- no domain-adapter behavior
- no Git/Docker behavior
- no CLI demo
- no conductor pipeline

## Future Allowed Write Paths

Expected future implementation paths:

- `services/core/src/core/runtime/transitions.py`
- `services/core/tests/test_runtime_transitions.py`
- `services/core/src/core/runtime/__init__.py`
- `services/core/src/core/runtime_substrate.py` (only to add BLOCKED to StepStatus enum)

Precommit review may later write only:

- `.project-memory/pr/0046-runtime-state-transitions/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0046-runtime-state-transitions/PLAN.md` (planner only)
- `.project-memory/pr/0046-runtime-state-transitions/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- `agents/**`
- `schemas/**`
- `docs/**`
- `services/runner/**`
- `services/task_intake/**`
- `services/model_gateway/**`
- `services/conductor/**`
- `services/**` except exact allowed Core runtime/test files listed above
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

Future tests must cover:

### RunState transitions

- valid: PENDING → RUNNING
- valid: RUNNING → PAUSED
- valid: RUNNING → COMPLETED when final report rule is satisfied
- valid: RUNNING → FAILED
- valid: PAUSED → RUNNING
- valid: RUNNING → CANCELLED
- invalid: COMPLETED → RUNNING raises TransitionError
- invalid: FAILED → RUNNING raises TransitionError
- invalid: COMPLETED → COMPLETED raises TransitionError
- invalid: CANCELLED → RUNNING raises TransitionError
- invalid: PAUSED → COMPLETED raises TransitionError (no final report)
- invalid: RUNNING → PENDING raises TransitionError (no backward transition)

### StepBoundary transitions

- valid: PENDING → RUNNING
- valid: RUNNING → COMPLETED
- valid: RUNNING → FAILED
- valid: RUNNING → BLOCKED
- valid: BLOCKED → RUNNING
- valid: BLOCKED → FAILED
- invalid: COMPLETED → RUNNING raises TransitionError
- invalid: FAILED → RUNNING raises TransitionError
- invalid: COMPLETED → FAILED raises TransitionError

### Checkpoint attachment

- valid: attach to RUNNING run with existing step
- valid: attach to PAUSED run with existing step
- invalid: attach to COMPLETED run raises TransitionError
- invalid: attach to FAILED run raises TransitionError
- invalid: attach to CANCELLED run raises TransitionError
- invalid: attach with non-existent step_id raises TransitionError
- invalid: duplicate checkpoint_id raises TransitionError

### AgentExecutionRecord

- valid: add to RUNNING step
- invalid: add to COMPLETED step raises TransitionError
- invalid: add to FAILED step raises TransitionError
- invalid: empty agent_id (role is None) raises TransitionError
- invalid: record step_id does not match target step raises TransitionError

### FinalReportDraft

- valid: attach when run is RUNNING and has at least one completed step
- invalid: attach when run is PAUSED raises TransitionError
- invalid: attach when run has no completed steps raises TransitionError
- invalid: attach to COMPLETED run raises TransitionError
- invalid: attach to FAILED run raises TransitionError
- invalid: attach to CANCELLED run raises TransitionError

### General

- TransitionError includes current_state, attempted_transition, reason
- tests are pure in-memory
- no I/O in tests
- no network in tests
- no subprocess in tests
- no old names/examples

## Validation Commands

Future implementation should run:

```bash
python -m pytest services/core/tests/test_runtime_transitions.py -v
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/core/src python -c "from core.runtime.transitions import validate_run_transition, TransitionError; print('ok')"
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/core/src/core services/core/tests || true
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -n "def validate_run_transition\|def validate_step_transition\|def validate_checkpoint\|def validate_agent_record\|def validate_final_report\|class TransitionError" services/core/src/core/runtime/transitions.py
```

## Expected Changed Files

Expected future implementation files:

1. `services/core/src/core/runtime_substrate.py` — add BLOCKED to StepStatus enum
2. `services/core/src/core/runtime/__init__.py` — new package init
3. `services/core/src/core/runtime/transitions.py` — new transitions module
4. `services/core/tests/test_runtime_transitions.py` — new test module

Expected future review artifact:
- `.project-memory/pr/0046-runtime-state-transitions/reviews/precommit-review.yml`

## Non-goals

- no LLM integration
- no model-provider integration
- no Git operations
- no Docker
- no domain adapter
- no persistence or database
- no HTTP server
- no CLI demo
- no conductor pipeline
- no human approval UI
- no distributed cache
- no changes to `agents/**`
- no changes to `schemas/**`
- no changes to `docs/**`
- no changes to `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- no `.ariadne/**` namespace creation
- no root dependency/build changes
- no old `.grace` namespace
- no water_meter / broken_clock / old Flask examples
- no changes to existing test file `test_runtime_substrate.py` (only new test file `test_runtime_transitions.py`)

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema changes, no docs changes, no agents changes, no apps changes, no runner changes, no forbidden path writes.
- Reviewers must verify: stdlib-only transitions, no I/O, no network, no subprocess, no model calls, no provider hardcoding, no persistence.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: `StepStatus.BLOCKED` is added correctly; `.value == "blocked"`.

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `.project-memory/**` except PLAN.md by planner or precommit-review.yml by precommit-review → stop
- about to write to `schemas/**` → stop
- about to write to `docs/**` → stop
- about to write to `runner/conductor/task_intake/model_gateway` → stop
- implementation requires LLM SDK → stop
- implementation requires subprocess or network → stop
- implementation requires third-party dependency → stop
- implementation requires persistence/storage → stop
- implementation requires distributed cache → stop
- transition table conflicts with existing runtime status model and cannot be safely mapped → stop
- old names/examples would be introduced → stop
- implementation modifies existing `test_runtime_substrate.py` instead of creating `test_runtime_transitions.py` → stop
- implementation modifies `schemas/` to add BLOCKED → stop (schema alignment deferred)

## Open Questions

1. **Should `BLOCKED` step status be added to `StepStatus` now or deferred?** Decision: Add now. Without BLOCKED, the `running → blocked` and `blocked → running` transitions cannot be validated. The enum extension is minimal and additive.
2. **Schema alignment for BLOCKED:** `schemas/run-state.schema.yml` lists step status as `"pending | running | completed | failed"`. This is a blueprint schema, and the plan does not modify it. The Python model extends beyond the blueprint. Should a future PR align the blueprint schema? Deferred to Phase 0 integration PR.
3. **Should `RUNNING → CANCELLED` be allowed for RunState?** Decision: Yes — cancellation from RUNNING is an expected operational pattern (explicit cancellation mid-run).
4. **Should `PAUSED → CANCELLED` be allowed?** Decision: Not required for this PR. Can be added later if needed.
5. **Should human_approval_required on FinalReportDraft affect final report attachment validation?** Decision: Not in this PR. The human_approval_required flag is metadata for the orchestrator, not a transition constraint.
6. **Should there be a `StepBoundary` `agent_id` or `role` None check in AgentExecutionRecord validation?** The AGEC schema shows `role` as required. The current `StepBoundary` has `agent_role: AgentRole` as required (no None). The `AgentExecutionRecord` has `role: AgentRole` required. The validation rule "agent_id must not be empty" maps to checking that the step's `agent_role` is set (which it always is in current model). Decision: Keep rule as "step and record role must match" rather than "not None" since both are already required non-None fields.

## Decisions Made

### api_surface

```
Validators are pure functions in `core.runtime.transitions`:

- validate_run_transition(current_status: RunStatus, new_status: RunStatus) -> None
- validate_step_transition(current_status: StepStatus, new_status: StepStatus) -> None
- validate_checkpoint_attachment(run: RunState, checkpoint: Checkpoint) -> None
- validate_agent_record_attachment(step: StepBoundary, record: AgentExecutionRecord) -> None
- validate_final_report_attachment(run: RunState, report: FinalReportDraft) -> None

All raise TransitionError on invalid transitions.
```

### transition_rules_scope

```
Full state transition tables for RunStatus and StepStatus (as documented in "Required State Transition Rules").
Checkpoint attachment rules, AgentExecutionRecord consistency rules, FinalReportDraft readiness rules.
No orchestrator logic, no persistence, no model calls.
```

### error_type

```
TransitionError(Exception) in core.runtime.transitions with fields:
- current_state: str
- attempted_transition: str
- reason: str
```

### implementation_location

```
services/core/src/core/runtime/transitions.py  (new)
services/core/src/core/runtime/__init__.py      (new package init)
services/core/tests/test_runtime_transitions.py (new)
services/core/src/core/runtime_substrate.py     (add BLOCKED to StepStatus)
```

### test_strategy

```
Pure in-memory tests in services/core/tests/test_runtime_transitions.py.
One test class per validation function:
- TestValidateRunTransition
- TestValidateStepTransition
- TestValidateCheckpointAttachment
- TestValidateAgentRecordAttachment
- TestValidateFinalReportAttachment
- TestTransitionError

All tests are stdlib+pytest only. No I/O, no network, no subprocess.
```

---

PLAN written: yes
