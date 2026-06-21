# PR 0048 — Runtime In-Memory Store Plan

## Goal

Add an in-memory runtime store to Ariadne Core.

The store should hold runtime substrate objects across operations:

- runs
- steps
- checkpoints
- agent execution records
- verification evidence
- final reports

The store must remain deterministic, stdlib-only, and in-memory.

## Architectural Thesis

Ariadne needs a runtime store before it can run a smoke demo.

The store is still substrate, not infrastructure.

It should provide a stable Core API for the future runner demo and conductor dry-run, while avoiding persistence and distributed cache.

The model remains replaceable.
The substrate owns execution state.

## Context Snapshot

- **current HEAD sha**: `843cb128108a4353a0417428535dd3274af3c675`
- **current branch**: `0048-runtime-in-memory-store`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: not present in prior plan artifacts for PR 0048 (first PR in this branch chain); base_sha is `main` (target branch for merge)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0047, no pending changes
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
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/transitions.py`
- `services/core/src/core/runtime/verification.py`
- `services/core/src/core/runtime/__init__.py`
- `services/core/src/core/__init__.py`
- `services/core/tests/test_runtime_substrate.py` — brief scan
- `services/core/tests/test_runtime_transitions.py` — brief scan
- `services/core/tests/test_runtime_verification.py` — brief scan
- `schemas/run-state.schema.yml`
- `schemas/checkpoint.schema.yml`

## Current Runtime Substrate Snapshot

### Entities in `services/core/src/core/runtime_substrate.py`

**Enums:** RunStatus, StepStatus (with BLOCKED), RubricVerdict, AgentRole

**Frozen reference types:** ContextPackRef, StateModelRef, TransitionGraphRef, RubricPackRef, RubricJudgeResultRef, ModelCapabilityProfileRef, LongContextStressProfileRef (all with to_dict/from_dict)

**Mutable entities (with to_dict/from_dict):**
- `StepBoundary`: step_id, agent_role, status, started_at, completed_at, model_used, cost, artifact_ids, checkpoint_id, failure_mode
- `RunState`: run_id, task_id, purpose_id, domain, status, current_step_id, steps (list[StepBoundary]), created_at, updated_at
- `AgentExecutionRecord`: contract_id, run_id, step_id, role, purpose, pbs_node, plus metadata
- `FinalReportDraft`: report_id, run_id, purpose_id, domain, root_purpose, created_at, plus optional summary/risk fields

**Immutable entity:**
- `Checkpoint`: checkpoint_id, run_id, step_id, captured_at, run_state_hash, artifact_ids, context_pack_id, memory_snapshot_hash, resumable, resume_instructions

**Helper factories:** create_run_state, record_checkpoint, record_agent_execution, build_final_report_draft

### In `services/core/src/core/runtime/transitions.py`

- `TransitionError(Exception)` with current_state, attempted_transition, reason
- `validate_run_transition`, `validate_step_transition`, `validate_checkpoint_attachment`, `validate_agent_record_attachment`, `validate_final_report_attachment`

### In `services/core/src/core/runtime/verification.py`

- `VerificationError(Exception)` with subject, reason, evidence_id, step_id
- `VerificationEvidence` dataclass with to_dict/from_dict
- `_run_evidence_store: dict[str, list[VerificationEvidence]]` — module-level mutable dict
- `_reset_evidence_store()` — test helper
- `create_verification_evidence()`, `attach_verification_evidence()`, `get_evidence_for_run()`, `summarize_verification_evidence()`, `validate_final_report_readiness()`, `build_final_report()`

### Notable pattern: existing mutable global state

The `_run_evidence_store` in `verification.py` is a module-level dict. This is already in `main` and accepted per PR 0047 plan. PR 0048 will absorb this pattern into the `InMemoryRuntimeStore` class, providing a clean instance-based alternative while remaining compatible with the existing evidence store interface.

## Implementation Location Decision

**Decision: Use `services/core/src/core/runtime/store.py`**

Rationale:
- Store is a separate concern from entities (runtime_substrate.py), transition validation (transitions.py), and evidence accumulation (verification.py).
- `services/core/tests/test_runtime_store.py` is the corresponding test path.
- `services/core/src/core/runtime/__init__.py` already exists — no change needed.
- No changes to `runtime_substrate.py`, `transitions.py`, or `verification.py` are needed. The store imports from all three and delegates validation to them.

**Rejected alternative:** Adding store logic to `verification.py` — that module already has a module-level evidence dict, but extending it to also store runs/checkpoints/reports would mix concerns. A store class is cleaner.

## Store Scope

The store is in-memory only.

- No disk persistence.
- No SQLite.
- No Redis.
- No distributed cache.
- No filesystem writes.
- No network calls.

Suitable for:
- Unit tests
- Future runner smoke demo
- Future conductor dry-run
- Deterministic runtime execution experiments

## Required Future Behavior

### Core API

```python
from core.runtime.store import InMemoryRuntimeStore, RuntimeStoreError

store = InMemoryRuntimeStore()

# Lifecycle
store.create_run(run: RunState) -> RunState
store.get_run(run_id: str) -> RunState
store.has_run(run_id: str) -> bool
store.save_run(run: RunState) -> RunState
store.list_runs() -> list[RunState]
store.delete_run(run_id: str) -> None
```

### Behavior per method

**`create_run(run)`**
- Validates run_id is not empty.
- Validates run_id is not a duplicate.
- Stores the run (deep copy via serialization round-trip if the entity supports it; otherwise instance reference).
- Returns the stored run.

**`get_run(run_id)`**
- Returns a copy of the stored RunState.
- Raises `RuntimeStoreError` if run_id not found.

**`has_run(run_id)`**
- Returns True/False.

**`save_run(run)`**
- Replaces the stored run with the provided one (upsert by run_id).
- Returns the stored run.
- Raises `RuntimeStoreError` if run_id not found (strict mode — create must precede save).

**`list_runs()`**
- Returns runs in insertion order (dict preserves insertion order in Python 3.7+).
- Returns copies to prevent external mutation.

**`delete_run(run_id)`**
- Removes the run and all associated evidence.
- Raises `RuntimeStoreError` if run_id not found.

### Evidence integration

The `InMemoryRuntimeStore` should own an evidence store internally, separate from the module-level `_run_evidence_store` in `verification.py`.

**Decision:** Do **not** modify `verification.py` to redirect its evidence store. Instead, the `InMemoryRuntimeStore` will manage its own internal evidence dict and provide convenience methods that delegate to verification helpers.

Evidence convenience methods:

```python
store.attach_verification_evidence(run_id: str, evidence: VerificationEvidence) -> None
store.get_evidence_for_run(run_id: str) -> list[VerificationEvidence]
store.summarize_verification_evidence(run_id: str) -> dict[str, Any]
store.build_final_report(run_id: str) -> FinalReportDraft
store.validate_final_report_readiness(run_id: str) -> None
```

These convenience methods:
1. Retrieve the run from the store.
2. Delegate to `verification.py` functions (evidence attachment, summarization, report building).
3. Use the store's internal evidence dict rather than the module-level one.

This keeps the store usable without side effects on the module-level state.

### State transition delegation

The store does not call transition validators directly. The orchestrator (runner/conductor) is responsible for calling `validate_run_transition` etc. before calling store methods. The store is a data holder, not a state machine executor.

However, `save_run()` replaces the full run object, so the orchestrator must have already validated the transition before calling save.

**Decision:** The store does **not** call transition validators. Validation is the caller's responsibility.

## Copy Semantics

**`get_run()` returns a copy.**

Copy strategy: Use `to_dict()` / `from_dict()` round-trip since all substrate entities already support it. This creates a fully independent deep copy.

```python
def _deep_copy_run(run: RunState) -> RunState:
    return RunState.from_dict(run.to_dict())
```

This ensures:
- External modification of a returned RunState does not affect the stored version.
- Serialization round-trip is tested indirectly.
- Deterministic behavior.

`list_runs()` also returns copies.

`save_run()` stores the provided run directly (upsert semantics, no copy needed since the caller provides the new object).

**`create_run()` stores a copy.**

## Error Model

```python
class RuntimeStoreError(Exception):
    """Raised when a store operation cannot be completed."""
    def __init__(
        self,
        operation: str,
        subject: str,
        reason: str,
    ) -> None:
        self.operation = operation
        self.subject = subject
        self.reason = reason
        super().__init__(f"Store error on {operation}({subject}): {reason}")
```

No domain-specific imports.

## Determinism Rules

- `list_runs()` returns deterministic (insertion) order.
- No time generation inside store — timestamps are caller-provided.
- No random id generation inside store — ids are caller-provided.
- No hidden global singleton — the store is instantiated by the caller.
- No module-level mutable global state in store.py (the module-level evidence dict in verification.py is a separate concern and is not modified by store.py).

## Relationship to Previous Runtime Layers

| Layer | Relationship |
|---|---|
| `runtime_substrate` | Store holds RunState, StepBoundary, Checkpoint, AgentExecutionRecord, FinalReportDraft instances. |
| `transitions` | Store does not call transitions. Orchestrator validates transitions before calling store.save_run(). |
| `verification` | Store provides convenience methods that delegate to verification.py functions using the store's internal evidence dict. |

The store does not duplicate validation logic. Evidence convenience methods call `verification.py` functions directly. The store's evidence dict is independent of the module-level `_run_evidence_store` in verification.py — this means evidence attached via the store is not visible to `get_evidence_for_run()` from verification.py, and vice versa. This is acceptable because the store is the intended future path; the module-level dict in verification.py is legacy from PR 0047.

## Future Allowed Write Paths

Expected future implementation paths:

- `services/core/src/core/runtime/store.py`
- `services/core/tests/test_runtime_store.py`

Precommit review may later write only:

- `.project-memory/pr/0048-runtime-in-memory-store/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0048-runtime-in-memory-store/PLAN.md` (planner only)
- `.project-memory/pr/0048-runtime-in-memory-store/reviews/plan-review.yml` (plan-review only)
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
- `services/core/src/core/runtime_substrate.py` (no changes needed)
- `services/core/src/core/runtime/transitions.py` (no changes needed)
- `services/core/src/core/runtime/verification.py` (no changes needed)
- `services/core/src/core/runtime/__init__.py` (no changes needed)
- `services/core/tests/test_runtime_substrate.py` (no changes needed)
- `services/core/tests/test_runtime_transitions.py` (no changes needed)
- `services/core/tests/test_runtime_verification.py` (no changes needed)

## Required Tests

### Store lifecycle

- create store
- create run
- get run returns matching object
- has run returns True for existing, False for missing
- save run replaces stored run
- list runs in deterministic order
- delete run removes run
- delete run raises on missing run

### Run id rules

- duplicate run_id rejected on create_run
- missing run_id raises RuntimeStoreError on get_run
- missing run_id raises RuntimeStoreError on save_run
- missing run_id raises RuntimeStoreError on delete_run
- empty run_id rejected on create_run

### Copy/mutation behavior

- get_run returns a copy (external mutation does not affect store)
- save_run replaces stored object
- list_runs returns copies
- create_run stores a copy

### Evidence convenience methods

- attach_verification_evidence to existing run
- attach_verification_evidence to non-existent run raises RuntimeStoreError
- get_evidence_for_run returns evidence after attachment
- get_evidence_for_run returns empty list for run with no evidence
- summarize_verification_evidence counts correctly
- build_final_report produces a FinalReportDraft
- validate_final_report_readiness validates correctly
- evidence is isolated per store instance (no cross-store contamination)

### Validation delegation

- verify_store's evidence methods delegate to verification.py (check function call chain)
- verify_store does not call transition validators

### Compatibility

- existing runtime substrate tests still pass
- existing runtime transition tests still pass
- existing runtime verification tests still pass

### General

- RuntimeStoreError includes operation, subject, reason
- tests are pure in-memory
- no I/O in tests
- no network in tests
- no subprocess in tests
- no persistence in tests
- no distributed cache in tests
- no old names/examples

## Validation Commands

Future implementation should run:

```bash
python -m pytest services/core/tests/test_runtime_store.py -v
python -m pytest services/core/tests/test_runtime_verification.py -q
python -m pytest services/core/tests/test_runtime_transitions.py -q
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/core/src python -c "from core.runtime.store import InMemoryRuntimeStore; print('ok')"
grep -R -n "redis\|sqlite\|open(\|Path(.*write\|requests\|subprocess\|docker\|water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/core/src/core services/core/tests || true
git status --short
git diff --name-only
```

## Post-change Checks

Future implementation should verify:

```bash
grep -R -n "class InMemoryRuntimeStore\|class RuntimeStoreError\|def create_run\|def get_run\|def has_run\|def save_run\|def list_runs\|def delete_run" services/core/src/core/runtime/store.py
```

## Expected Changed Files

Expected future implementation files:

1. `services/core/src/core/runtime/store.py` — new module
2. `services/core/tests/test_runtime_store.py` — new tests

Expected future review artifact:
- `.project-memory/pr/0048-runtime-in-memory-store/reviews/precommit-review.yml`

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
- no changes to `runtime_substrate.py`
- no changes to `transitions.py`
- no changes to `verification.py` (module-level evidence dict remains as-is)
- no changes to `runtime/__init__.py`
- no changes to existing test files

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema changes, no docs changes, no agents changes, no apps changes, no runner changes, no forbidden path writes.
- Reviewers must verify: stdlib-only, no I/O, no network, no subprocess, no model calls, no provider hardcoding, no persistence beyond in-memory dict.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: copy semantics match plan (deep copy via round-trip).
- Reviewers must verify: store does not call transition validators.
- Reviewers must verify: evidence methods delegate to verification.py.
- Reviewers must verify: no modification to existing modules.

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
- implementation requires SQLite/Redis/distributed cache → stop
- store requires filesystem writes → stop
- implementation modifies existing substrate/transition/verification modules → stop
- implementation modifies existing test files → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should the store call transition validators in convenience methods?** **Decision: No.** The store is a data holder. Validation is the orchestrator's responsibility. This keeps the store simple and avoids stage coupling.
2. **Should evidence attached via the store be visible to verification.py's `get_evidence_for_run()`?** **Decision: No.** Two separate evidence stores coexist. The store's evidence is isolated per instance. The module-level store in verification.py is legacy from PR 0047 and remains for backward compatibility. A future PR may unify them.
3. **Should save_run be strict (must exist) or upsert (create if missing)?** **Decision: Strict.** `create_run` creates; `save_run` updates. This separates creation from mutation and prevents accidental creation via save.
4. **Should there be a `clear()` method for test isolation?** **Decision: No.** Test isolation is achieved by creating a new store instance per test. If needed later, an explicit `clear()` can be added.

## Decisions Made

### api_surface

```
InMemoryRuntimeStore class with:
- create_run(run) -> RunState
- get_run(run_id) -> RunState
- has_run(run_id) -> bool
- save_run(run) -> RunState
- list_runs() -> list[RunState]
- delete_run(run_id) -> None
- attach_verification_evidence(run_id, evidence) -> None
- get_evidence_for_run(run_id) -> list[VerificationEvidence]
- summarize_verification_evidence(run_id) -> dict[str, Any]
- build_final_report(run_id) -> FinalReportDraft
- validate_final_report_readiness(run_id) -> None

RuntimeStoreError(Exception) with operation, subject, reason.
```

### store_scope

```
In-memory only. Dict-backed by run_id. Insertion-order iteration for list_runs.
Deep copy via to_dict/from_dict round-trip for get/list operations.
Separate evidence dict per store instance (isolated from verification.py module-level store).
```

### copy_semantics

```
get_run and list_runs return deep copies via serialization round-trip.
create_run stores a copy of the provided run.
save_run stores the provided run directly (upsert by run_id, caller responsible for state).
```

### validation_delegation

```
Store does not call transition validators. Store evidence methods delegate to verification.py functions using store's internal evidence dict. Orchestrator validates transitions before calling save_run.
```

### error_type

```
RuntimeStoreError(Exception) in store.py with operation, subject, reason.
Separate from TransitionError and VerificationError.
```

### implementation_location

```
services/core/src/core/runtime/store.py (new module)
services/core/tests/test_runtime_store.py (new tests)
No changes to existing modules.
```

### test_strategy

```
Pure in-memory tests in services/core/tests/test_runtime_store.py.
One test class per feature area:
- TestCreateRun
- TestGetRun
- TestHasRun
- TestSaveRun
- TestListRuns
- TestDeleteRun
- TestRunIdRules
- TestCopySemantics
- TestEvidenceMethods
- TestRuntimeStoreError

Evidence isolation: create new store instance per test.
All tests stdlib+pytest only. No I/O, no network, no subprocess.
```

---

PLAN written: yes
