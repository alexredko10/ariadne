# PR 0047 — Runtime Verification Evidence Plan

## Goal

Add deterministic verification evidence helpers and final report building to Ariadne runtime Core.

The implementation should make it possible to accumulate verification evidence and produce a final report from runtime state without model calls or domain-specific behavior.

## Architectural Thesis

Ariadne Core should own verification evidence as runtime substrate data.

Verification evidence is not a prompt preference.
It is part of the durable execution record.

Final report building must be deterministic and model-independent.

The model remains replaceable.
The substrate owns evidence integrity.

## Context Snapshot

- **current HEAD sha**: `7a0d6526e148d0b2413c041e7103952f645f032a`
- **current branch**: `0047-runtime-verification-evidence`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: not present in prior plan artifacts for PR 0047 (first PR in this branch chain); base_sha is `main` (target branch for merge)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0046, no pending changes
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
- `.project-memory/pr/0046-runtime-state-transitions/reviews/plan-review.yml` — not inspected (no added value for this plan)
- `.project-memory/pr/0046-runtime-state-transitions/reviews/precommit-review.yml` — not inspected
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/transitions.py`
- `services/core/src/core/runtime/__init__.py`
- `services/core/src/core/__init__.py`
- `services/core/tests/test_runtime_substrate.py`
- `services/core/tests/test_runtime_transitions.py`
- `schemas/run-state.schema.yml`
- `schemas/checkpoint.schema.yml`

## Current Runtime Substrate Snapshot

### Entities in `services/core/src/core/runtime_substrate.py`

**Enums:**
- `RunStatus`: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- `StepStatus`: PENDING, RUNNING, COMPLETED, FAILED, BLOCKED
- `RubricVerdict`: PASS, WARNING, FAIL, NEEDS_HUMAN_REVIEW
- `AgentRole`: ARCHITECT, PLANNER, LEAD_CODER, WORKER_CODER, TESTER, REVIEWER, SECURITY, VERIFIER, CUSTOM

**Frozen reference types** (ID wrappers with `to_dict`/`from_dict`):
- `ContextPackRef`, `StateModelRef`, `TransitionGraphRef`, `RubricPackRef`, `RubricJudgeResultRef`, `ModelCapabilityProfileRef`, `LongContextStressProfileRef`

**Mutable entities** (with `to_dict`/`from_dict`):
- `StepBoundary`: step_id, agent_role, status, started_at, completed_at, model_used, cost, artifact_ids, checkpoint_id, failure_mode
- `RunState`: run_id, task_id, purpose_id, domain, status, current_step_id, steps, created_at, updated_at
- `AgentExecutionRecord`: contract_id, run_id, step_id, role, purpose, pbs_node, plus many optional metadata fields (agent, actions_taken, files_changed, claims, evidence, uncertainties, etc.)
- `FinalReportDraft`: report_id, run_id, purpose_id, domain, root_purpose, created_at, plus optional summary/risk fields (pbs_summary, model_routing_summary, context_used, changes, verification_summary, rubric_judge_result_ids, security_summary, risks, human_approval_required, cost_summary, next_steps)

**Immutable entity:**
- `Checkpoint`: checkpoint_id, run_id, step_id, captured_at, run_state_hash, artifact_ids, context_pack_id, memory_snapshot_hash, resumable, resume_instructions

**Helper factory functions:**
- `create_run_state(...)` → RunState
- `record_checkpoint(...)` → Checkpoint
- `record_agent_execution(...)` → AgentExecutionRecord
- `build_final_report_draft(...)` → FinalReportDraft

### Entities in `services/core/src/core/runtime/transitions.py`

**Exception:**
- `TransitionError(Exception)` with `current_state`, `attempted_transition`, `reason`

**Validator functions:**
- `validate_run_transition(current_status, new_status) -> None`
- `validate_step_transition(current_status, new_status) -> None`
- `validate_checkpoint_attachment(run, checkpoint) -> None`
- `validate_agent_record_attachment(step, record) -> None`
- `validate_final_report_attachment(run, report) -> None`

**Internal tables:**
- `_RUN_ALLOWED`: dict[RunStatus, set[RunStatus]]
- `_STEP_ALLOWED`: dict[StepStatus, set[StepStatus]]

### Tests

- `test_runtime_substrate.py`: 40+ tests covering creation, defaults, immutability, enums, helpers, serialization, round-trip
- `test_runtime_transitions.py`: TestValidateRunTransition (12), TestValidateStepTransition (9), TestValidateCheckpointAttachment (7), TestValidateAgentRecordAttachment (4), TestValidateFinalReportAttachment (6), TestTransitionError (4) = 42 total

## Implementation Location Decision

**Decision: Use `services/core/src/core/runtime/verification.py`**

Rationale:
- Evidence creation, attachment, summarization, and final report building are all verification-domain behavior within Core.
- They follow the same pattern as `transitions.py` — a single module within the `core.runtime` package.
- `services/core/tests/test_runtime_verification.py` is the corresponding test path.
- `services/core/src/core/runtime/__init__.py` already exists as a package init — no change needed.
- No new `final_report.py` is needed because `FinalReportDraft` already exists in `runtime_substrate.py`. The building logic lives in `verification.py` and produces the existing `FinalReportDraft`.

**Rejected alternatives:**
- A separate `final_report.py` module — unnecessary because `FinalReportDraft` already exists in the substrate and building logic is deterministic enough to coexist in verification module.
- Adding to `runtime_substrate.py` — violates separation of concerns (entities vs. behavioral logic).
- Adding to `transitions.py` — different responsibility (transitions validate state changes; verification accumulates evidence and builds reports).

## VerificationEvidence Entity — New Addition

The current substrate has no `VerificationEvidence` dataclass. A minimal Core-only entity must be added to `services/core/src/core/runtime/verification.py`.

```python
@dataclasses.dataclass
class VerificationEvidence:
    """Deterministic verification evidence for a single check during a run step.

    Parameters
    ----------
    evidence_id
        Unique identifier for this evidence record.
    step_id
        The step this evidence belongs to.
    check_name
        Name of the validation or check that produced this evidence.
    status
        One of: "passed", "failed", "warning", "skipped", "not_run".
    message
        Human-readable summary of the evidence.
    command
        The validation command or check identifier, if applicable.
    artifact_ref
        Reference to an artifact produced by this check, if applicable.
    rubric_ref
        Reference to a rubric pack entry, if applicable.
    recorded_at
        When this evidence was recorded (caller-provided or deterministic timestamp).
    metadata
        Optional dict for additional structured data (no secrets, no raw repo dumps).
    """

    evidence_id: str
    step_id: str
    check_name: str
    status: str  # "passed" | "failed" | "warning" | "skipped" | "not_run"
    message: str = ""
    command: Optional[str] = None
    artifact_ref: Optional[str] = None
    rubric_ref: Optional[str] = None
    recorded_at: Optional[datetime.datetime] = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
```

This entity is placed in `verification.py` (not `runtime_substrate.py`) because it is verification-domain behavior — an accumulating evidence record, not a substrate primitive like `RunState` or `StepBoundary`. If it later needs to be serialized as part of run state, it can be promoted.

**Serialization:** `VerificationEvidence` will include `to_dict()` / `from_dict()` following the same pattern as substrate entities, for evidence persistence and audit purposes.

## Required Future Behavior

### 1. Evidence creation

```python
def create_verification_evidence(
    evidence_id: str,
    step_id: str,
    check_name: str,
    status: str,
    message: str = "",
    command: Optional[str] = None,
    artifact_ref: Optional[str] = None,
    rubric_ref: Optional[str] = None,
    recorded_at: Optional[datetime.datetime] = None,
    **metadata: Any,
) -> VerificationEvidence: ...
```

- Pure and deterministic (except caller-provided timestamps/ids).
- Validates `status` is one of: `"passed"`, `"failed"`, `"warning"`, `"skipped"`, `"not_run"`.
- Raises `VerificationError` if status is invalid.
- Raises `VerificationError` if `evidence_id` or `step_id` is empty.

### 2. Evidence attachment

```python
def attach_verification_evidence(
    run: RunState,
    evidence: VerificationEvidence,
) -> None: ...
```

- Validates that the referenced `step_id` exists in the run.
- Validates that `evidence.evidence_id` is not a duplicate.
- Does **not** forbid attaching evidence to terminal runs — evidence may be attached post-mortem for audit purposes. Transition rules govern state changes; evidence is metadata.
- Stores evidence in `run` metadata. Since `RunState` has no `evidence` field currently, the attachment function will store evidence in a new runtime-level evidence store pattern. **Decision: Store evidence on RunState via an `evidence: list[VerificationEvidence]` field added as a new attribute to RunState.**

### 3. `RunState.evidence` field

`RunState` in `runtime_substrate.py` gains an optional `evidence` field:

```python
@dataclasses.dataclass
class RunState:
    ...
    evidence: list[VerificationEvidence] = dataclasses.field(default_factory=list)
```

This import creates a dependency from `runtime_substrate.py` to `runtime/verification.py`. To avoid circular imports, `VerificationEvidence` must be importable from `core.runtime.verification` and `RunState` must import it. Since `runtime_substrate.py` is at `core.runtime_substrate` (not `core.runtime.runtime_substrate`), and `verification.py` is at `core.runtime.verification`, the import chain is:

- `core.runtime_substrate` ← no import of `verification.py` initially (the evidence field is forward-declared as `Optional[...]` or imported at type-checking time)
- `core.runtime.verification` imports from `core.runtime_substrate` (for `RunState`, `StepBoundary`, etc.)

**Resolution:** Import `VerificationEvidence` in `runtime_substrate.py` using a TYPE_CHECKING guard, or defer the field addition and store evidence on a separate run-to-evidence mapping in `verification.py`. **Decision: Defer the `RunState.evidence` field. Instead, store evidence in a separate `run_evidence: dict[str, list[VerificationEvidence]]` managed by `verification.py` functions.** This avoids coupling the substrate entity to the verification module entirely.

Revised approach:

```python
# In verification.py:

_run_evidence_store: dict[str, list[VerificationEvidence]] = {}

def attach_verification_evidence(run: RunState, evidence: VerificationEvidence) -> None:
    # validate step exists in run
    # validate no duplicate evidence_id
    _run_evidence_store.setdefault(run.run_id, []).append(evidence)

def get_evidence_for_run(run: RunState) -> list[VerificationEvidence]:
    return _run_evidence_store.get(run.run_id, [])
```

This uses a module-level dict — which is an in-memory runtime store, not persistence. It is acceptable for Core because:
- It is stdlib only (plain dict).
- No I/O, no network, no subprocess.
- No database or external storage.
- It exists only within the lifetime of the Python process.
- It is testable and deterministic within a single process.

If the orchestrator later needs durable evidence, the evidence dict can be serialized alongside the run state. For PR 0047, in-memory is sufficient.

### 4. Evidence summarization

```python
def summarize_verification_evidence(run: RunState) -> dict[str, Any]: ...
```

Returns deterministic summary data:

```python
{
    "total": int,
    "passed": int,
    "failed": int,
    "warning": int,
    "skipped": int,
    "not_run": int,
    "failing_evidence_ids": list[str],
    "warning_evidence_ids": list[str],
}
```

- Counts are aggregated from all evidence attached to the run.
- `failing_evidence_ids` and `warning_evidence_ids` are sorted for determinism.

### 5. Final report readiness

```python
def validate_final_report_readiness(run: RunState) -> None: ...
```

Checks:
- Run has at least one completed step (reuses transition rule logic).
- Run is in RUNNING state (eligible for transition to COMPLETED via final report).
- No unresolved failed evidence remains (failing evidence with no corresponding new evidence that resolves it). **Decision:** For initial scope, require that `summarize_verification_evidence` returns zero failed evidence. This is a conservative gate. If a run has failed evidence, the report is not ready.

Raises `VerificationError` with reason if not ready.

### 6. Final report building

```python
def build_final_report(run: RunState) -> FinalReportDraft: ...
```

- Deterministic.
- No LLM calls.
- No natural-language model generation.
- Produces a `FinalReportDraft` (existing entity).

Content populated from run state:
- `report_id`: auto-generated from `run.run_id + "-report"`.
- `run_id`: from run.
- `purpose_id`: from run.
- `domain`: from run.
- `root_purpose`: from run's purpose_id (use purpose_id as string — no lookup).
- `created_at`: current UTC timestamp.
- `pbs_summary`: set to `f"run {run.run_id}: {len(run.steps)} steps"`.
- `changes`: list of step summary strings `"step {s.step_id}: {s.status.value}"`.
- `verification_summary`: set to JSON-like summary of `summarize_verification_evidence(run)`.
- `risks`: populated from any failed/warning evidence messages.
- `human_approval_required`: set to True if any evidence is status "failed".
- `next_steps`: populated from incomplete step statuses.

All other fields remain None/empty. No model-generated text is injected.

## Error Model

**Introduce `VerificationError` in `services/core/src/core/runtime/verification.py`.**

`TransitionError` remains reserved for state lifecycle violations in `transitions.py`.

```python
class VerificationError(Exception):
    """Raised when verification evidence or final report validation fails."""
    def __init__(
        self,
        subject: str,
        reason: str,
        evidence_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> None:
        self.subject = subject
        self.reason = reason
        self.evidence_id = evidence_id
        self.step_id = step_id
        super().__init__(f"Verification error on {subject}: {reason}")
```

## API Surface

Exported from `services/core/src/core/runtime/verification.py`:

```python
# Entities
VerificationEvidence (dataclass)

# Exceptions
VerificationError(Exception)

# Evidence functions
create_verification_evidence(...) -> VerificationEvidence
attach_verification_evidence(run, evidence) -> None
get_evidence_for_run(run) -> list[VerificationEvidence]
summarize_verification_evidence(run) -> dict[str, Any]

# Final report functions
validate_final_report_readiness(run) -> None
build_final_report(run) -> FinalReportDraft
```

## Implementation Rules

Future implementation must be:

- stdlib only
- pure functions where possible
- deterministic
- no side effects beyond the in-memory evidence dict
- no I/O
- no network
- no subprocess
- no hidden global state beyond the evidence dict
- no provider-specific model logic
- no persistence/storage
- no distributed cache
- no domain-adapter behavior
- no Git/Docker behavior
- no CLI demo
- no conductor pipeline

The `_run_evidence_store` module-level dict is the only mutable state. It is an in-memory runtime store, not persistence. Acceptable for Core at this development stage.

## Future Allowed Write Paths

Expected future implementation paths:

- `services/core/src/core/runtime/verification.py`
- `services/core/tests/test_runtime_verification.py`

Precommit review may later write only:

- `.project-memory/pr/0047-runtime-verification-evidence/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0047-runtime-verification-evidence/PLAN.md` (planner only)
- `.project-memory/pr/0047-runtime-verification-evidence/reviews/plan-review.yml` (plan-review only)
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

### Evidence creation

- creates evidence with deterministic fields
- invalid status raises VerificationError
- empty evidence_id raises VerificationError
- empty step_id raises VerificationError
- metadata is stored as provided

### Evidence attachment

- valid: attach evidence to existing step
- invalid: attach evidence to non-existent step raises VerificationError
- invalid: duplicate evidence_id raises VerificationError
- valid: attach evidence to terminal run (no error — evidence is metadata)

### Evidence retrieval and summarization

- get_evidence_for_run returns empty list for run with no evidence
- get_evidence_for_run returns evidence after attachment
- summarize_verification_evidence counts passed/failed/warning/skipped/not_run correctly
- summarize_verification_evidence returns deterministic ordering
- summarize_verification_evidence handles no evidence (all zero counts)

### Final report readiness

- valid: run with completed step, no failed evidence, RUNNING status
- invalid: no completed steps raises VerificationError
- invalid: unresolved failed evidence raises VerificationError
- invalid: run is PAUSED raises VerificationError

### Final report building

- builds deterministic report object
- report includes run_id
- report includes final status
- report includes step summaries
- report includes verification summary
- report includes risks from failed/warning evidence
- report sets human_approval_required=True when failed evidence exists
- report does not include raw repository dumps
- round-trip serialization works (FinalReportDraft already supports to_dict/from_dict)

### Compatibility

- existing runtime substrate tests still pass
- existing runtime transition tests still pass

### General

- VerificationError includes subject and reason
- evidence_id and step_id are included in VerificationError when applicable
- tests are pure in-memory
- no I/O in tests
- no network in tests
- no subprocess in tests
- no old names/examples

## Validation Commands

Future implementation should run:

```bash
python -m pytest services/core/tests/test_runtime_verification.py -v
python -m pytest services/core/tests/test_runtime_transitions.py -q
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/core/src python -c "from core.runtime.verification import build_final_report, VerificationEvidence; print('ok')"
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/core/src/core services/core/tests || true
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -R -n "def create_verification_evidence\|def attach_verification_evidence\|def get_evidence_for_run\|def summarize_verification_evidence\|def validate_final_report_readiness\|def build_final_report\|class VerificationError\|class VerificationEvidence" services/core/src/core/runtime/verification.py
```

## Expected Changed Files

Expected future implementation files:

1. `services/core/src/core/runtime/verification.py` — new module
2. `services/core/tests/test_runtime_verification.py` — new tests

Expected future review artifact:
- `.project-memory/pr/0047-runtime-verification-evidence/reviews/precommit-review.yml`

## Non-goals

- no LLM integration
- no model-provider integration
- no Git operations
- no Docker
- no domain adapter
- no persistence or database
- no distributed cache
- no HTTP server
- no CLI demo
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
- no changes to `runtime_substrate.py` (evidence stored in-memory in verification module, not on RunState)
- no changes to `transitions.py` (evidence is its own concern)
- no changes to `runtime/__init__.py` (already exists, no re-exports needed)
- no changes to existing test files

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema changes, no docs changes, no agents changes, no apps changes, no runner changes, no forbidden path writes.
- Reviewers must verify: stdlib-only, no I/O, no network, no subprocess, no model calls, no provider hardcoding, no persistence beyond in-memory dict.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: evidence dict is in-memory only (no file writes, no database).
- Reviewers must verify: `VerificationEvidence.to_dict()`/`from_dict()` follow existing substrate patterns.
- Reviewers must verify: `build_final_report` does not call any LLM or model function.

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `.project-memory/**` except PLAN.md by planner or precommit-review.yml by precommit-review → stop
- about to write to `schemas/**` → stop
- about to write to `docs/**` → stop
- about to write to `runner/conductor/task_intake/model_gateway` → stop
- implementation requires LLM SDK → stop
- implementation requires subprocess or network → stop
- implementation requires third-party dependency → stop
- implementation requires persistence/storage (beyond in-memory dict) → stop
- implementation requires distributed cache → stop
- final report building requires model-generated text → stop
- evidence model requires raw repository dumps → stop
- implementation modifies `runtime_substrate.py` or `transitions.py` → stop (not needed per plan)
- implementation modifies existing test files → stop
- old names/examples would be introduced → stop

## Open Questions

1. **In-memory evidence store vs. RunState field?** Decision: In-memory dict in verification module. Avoids coupling substrate entity to verification module. Evidence can be serialized alongside run state in a future PR if needed.
2. **Should validate_final_report_readiness block on failed evidence?** Decision: Yes, for initial scope. Failed evidence means the run has unresolved verification failures. A conservative gate is appropriate for MVP.
3. **Should build_final_report be allowed to attach the report (transition run to COMPLETED)?** Decision: No. `build_final_report` produces the report object. Attachment and status transition are separate concerns handled by the orchestrator using `validate_final_report_attachment` from `transitions.py`. This keeps functions pure and composable.
4. **What populates changes list in FinalReportDraft?** Decision: Step summaries of the form `"step {step_id}: {status.value}"`. This is deterministic and model-independent.

## Decisions Made

### api_surface

```
VerificationEvidence (dataclass) – new entity in verification.py
VerificationError(Exception) – new exception in verification.py

create_verification_evidence(evidence_id, step_id, check_name, status, message="", command=None, artifact_ref=None, rubric_ref=None, recorded_at=None, **metadata) -> VerificationEvidence
attach_verification_evidence(run: RunState, evidence: VerificationEvidence) -> None
get_evidence_for_run(run: RunState) -> list[VerificationEvidence]
summarize_verification_evidence(run: RunState) -> dict[str, Any]
validate_final_report_readiness(run: RunState) -> None
build_final_report(run: RunState) -> FinalReportDraft
```

### evidence_scope

```
VerificationEvidence entity in verification.py with fields: evidence_id, step_id, check_name, status (str enum: passed/failed/warning/skipped/not_run), message, command, artifact_ref, rubric_ref, recorded_at, metadata (dict).
In-memory evidence store via module-level dict keyed by run_id.
Evidence is created, attached, retrieved, summarized. No evidence removal or modification (append-only).
```

### final_report_builder_scope

```
build_final_report(run) -> FinalReportDraft. Pure deterministic builder using existing FinalReportDraft entity.
Populates: report_id, run_id, purpose_id, domain, root_purpose, created_at, pbs_summary, changes (step status summaries), verification_summary (from summarize), risks (from failed/warning evidence), human_approval_required (True if any failed evidence), next_steps (incomplete step statuses).
Does not transition the run. Does not call LLMs. Does not invoke domain adapters.
```

### error_type

```
VerificationError(Exception) in verification.py with fields: subject, reason, evidence_id (optional), step_id (optional).
Separate from TransitionError. TransitionError remains for state lifecycle violations only.
```

### implementation_location

```
services/core/src/core/runtime/verification.py  (new module)
services/core/tests/test_runtime_verification.py (new tests)
```

### test_strategy

```
Pure in-memory tests in services/core/tests/test_runtime_verification.py.
One test class per function:
- TestCreateVerificationEvidence
- TestAttachVerificationEvidence
- TestGetEvidenceForRun
- TestSummarizeVerificationEvidence
- TestValidateFinalReportReadiness
- TestBuildFinalReport
- TestVerificationError

All tests are stdlib+pytest only. No I/O, no network, no subprocess.
Evidence store is reset between tests (new evidence dict created or cleared per test class setup).
```

---

PLAN written: yes
