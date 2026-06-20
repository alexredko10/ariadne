# PR 0044 — Runtime Substrate Skeleton Plan

## Goal

Create the first minimal runtime substrate skeleton for Ariadne — the domain-agnostic data model and pure-Python helpers that orchestration, state management, and agent execution records depend on.

This is the smallest useful surface that implements the `schemas/run-state.schema.yml`, `schemas/checkpoint.schema.yml`, `schemas/agent-execution-contract.schema.yml`, and `schemas/final-report.schema.yml` contracts as importable Python types — while stub-referencing the remaining Phase 0 schemas (state-model, transition-graph, rubric-pack, rubrics-judge-result, context-pack, model-capability-profile) without implementing their runtime behavior.

No orchestrator, no model calls, no task intake, no patch application, no Git/Docker-specific runtime behavior.

## Architectural Thesis

```text
Ariadne is not a chatbot wrapper.
Ariadne is not a model-centered agent framework.
Ariadne is an execution substrate for agentic software production.

The model is replaceable.
The substrate is the product.
```

Coding-specific behavior belongs to a Domain Adapter, not Ariadne Core.

## Context Snapshot

```yaml
context_snapshot:
  base_sha: "bc9d4b09952b8c9746b05c7cd728c7840bdc9d7b"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.19"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "bc9d4b09952b8c9746b05c7cd728c7840bdc9d7b"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Inputs Read

- ARIADNE_ARCHITECTURE.md — full blueprint including subsystem map and artifact flow
- ROADMAP.md — 10-phase roadmap (Phase 0 complete, Phase 1 is Runtime Substrate)
- ROADMAP_PHASE_0_PR_PLAN.md — not present (PR 0042 decomposition was not implemented as separate files; decomposition artifacts implied in PR sequence)
- PHASE_0_DECOMPOSITION.md — not present
- .project-memory/project_contract.yml — version "0.1" with Phase 0 contract IDs registered
- .project-memory/anchors.yml — version "0.1" with Phase 0 anchors registered
- .project-memory/context-bundles/contracts.yml — version "0.16" with Phase 0 read_first entries
- .project-memory/memory_index.yml — version "0.19" with Phase 0 labels
- .project-memory/pr/0043-phase-0-contracts-integration/PLAN.md
- .project-memory/pr/0043-phase-0-contracts-integration/reviews/plan-review.yml
- .project-memory/pr/0043-phase-0-contracts-integration/reviews/precommit-review.yml
- All 13 schemas under schemas/
- docs/adr/0004-ariadne-is-domain-agnostic.md
- docs/adr/0005-rubrics-as-runtime-contracts.md
- docs/adr/0006-model-replaceability.md
- docs/adr/0007-cached-repository-understanding.md
- services/runners/services/conductor/src/ — existing service file tree
- services/core/src/core/ — existing placeholder
- packages/common/src/ — existing placeholder
- packages/contracts/src/ — existing placeholder
- packages/policy/src/ — existing placeholder
- pyproject.toml — includes testpaths and pythonpath config

## Repository Structure Snapshot

```
schemas/
  13 YAML schema documents (purpose, pbs, context-pack, state-model, transition-graph,
  rubric-pack, rubric-judge-result, model-capability-profile, agent-execution-contract,
  run-state, checkpoint, long-context-stress-profile, final-report)

packages/
  common/src/__init__.py          (empty)
  contracts/src/__init__.py       (empty)
  policy/src/__init__.py          (empty)

services/
  conductor/src/conductor/__init__.py  (placeholder)
  conductor/tests/test_conductor_smoke.py  (assert True)
  core/src/core/__init__.py             (placeholder)
  core/tests/test_core_smoke.py         (assert True)
  model_gateway/src/model_gateway/     (has model_selection_dry_run.py)
  model_gateway/tests/                  (has smoke + dry run tests)
  runner/src/runner/                    (existing runner with diff/patch/apply/worktree)
  runner/tests/                         (10 test files)
  task_intake/src/task_intake/          (has app, server, models, normalizer)
  task_intake/tests/                    (4 test files)

agents/
  architect.yml, coder.yml, plan-review.yml, precommit-review.yml (agent configs)
  01_platform_architect.md, 02_repository_scaffolder.md, ... (doc-based agent configs)

pyproject.toml:
  testpaths = ["services"]
  pythonpath includes core, conductor, runner, task_intake, model_gateway
```

## Contract Inputs

The skeleton implements types from these schemas, mapping schema YAML definitions to Python dataclasses:

| Schema | File | Role in Skeleton |
|---|---|---|
| `schemas/run-state.schema.yml` | `RunState` | Primary entity — run id, step records, status, timestamps |
| `schemas/checkpoint.schema.yml` | `Checkpoint` | Immutable checkpoint records per step |
| `schemas/agent-execution-contract.schema.yml` | `AgentExecutionRecord` | Agent input/output contract metadata |
| `schemas/final-report.schema.yml` | `FinalReportDraft` | Report structure (draft only, runtime assembly deferred) |
| `schemas/state-model.schema.yml` | `StateModelRef` | Reference type only (no extraction) |
| `schemas/transition-graph.schema.yml` | `TransitionGraphRef` | Reference type only (no graph engine) |
| `schemas/rubric-pack.schema.yml` | `RubricPackRef` | Reference type only (no judging) |
| `schemas/rubric-judge-result.schema.yml` | `RubricJudgeResultRef` | Reference type only (no judging) |
| `schemas/context-pack.schema.yml` | `ContextPackRef` | Reference type only (no compiler) |
| `schemas/model-capability-profile.schema.yml` | `ModelCapabilityProfileRef` | Reference type only (no routing) |
| `schemas/long-context-stress-profile.schema.yml` | `LongContextStressProfileRef` | Reference type only (no profiling) |

## Runtime Substrate Definition

**In scope for the first skeleton:**

1. Python dataclasses mapping the 4 primary schemas (run-state, checkpoint, agent-execution-contract, final-report)
2. Simple reference types (string-based IDs) for the 7 referenced schemas
3. Pure data-model helpers: `create_run_state`, `append_step`, `record_checkpoint`, `record_agent_execution`, `build_final_report_draft`
4. Typed enums for status values, verdicts, and role constants
5. Tests for creation, serialization, boundary cases
6. The `py.typed` marker file (PEP 561)

**Out of scope:**

- Orchestrator loop
- Model provider integration or model calls
- Task intake changes
- Patch application or Apply Gate
- File-system persistence (state is in-memory data models only)
- Network calls or HTTP endpoints
- Docker / Git-specific runtime behavior
- Context compiler
- State extraction
- Rubric judging
- Model routing
- Final report assembly from real artifacts

## Proposed Future Write Paths

**Chosen location: `services/core/src/core/`** — because:

1. The repository already has `services/core/` as a dedicated placeholder with its own `src/core/` namespace and `tests/` directory
2. `pyproject.toml` already includes `services/core/src` in `pythonpath`
3. The architecture document's subsystem map includes `context_core` and `state_core` — these names logically belong under `core`
4. This avoids creating a new top-level `packages/` or `services/` entry, minimizing structural churn
5. The existing `services/core/tests/test_core_smoke.py` gives a natural test entry point for extension

The implementation must create/modify only:

```
services/core/src/core/__init__.py             (update from placeholder)
services/core/src/core/runtime_substrate.py    (primary — domain-agnostic entities + helpers)
services/core/tests/__init__.py                (test package, already exists)
services/core/tests/test_runtime_substrate.py  (test file)
services/core/tests/test_core_smoke.py         (update smoke test to import substrate)
```

**Do NOT create:**

- Additional files under `services/core/src/core/` beyond these
- Files under `packages/`, `services/conductor/`, `services/runner/`, or any other service
- `services/core/pyproject.toml` or `services/core/README.md` (unless missing and needed for package integrity)

## Future Forbidden Write Paths

```text
.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md
.project-memory/pr/0044-runtime-substrate-skeleton/reviews/plan-review.yml
.project-memory/**
schemas/**
docs/**
agents/**
apps/**
.ariadne/**
.github/**
docker/**
Dockerfile*
package.json
Makefile
ARIADNE_ARCHITECTURE.md
ROADMAP.md
PHASE_0_DECOMPOSITION.md
ROADMAP_PHASE_0_PR_PLAN.md
services/runner/**
services/task_intake/**
services/model_gateway/**
services/conductor/**
packages/**
```

## Minimal Entities

```python
# services/core/src/core/runtime_substrate.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Status / Role / Verdict enums ──

class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RubricVerdict(Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AgentRole(Enum):
    ARCHITECT = "architect"
    PLANNER = "planner"
    LEAD_CODER = "lead_coder"
    WORKER_CODER = "worker_coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    SECURITY = "security"
    VERIFIER = "verifier"
    CUSTOM = "custom"


# ── Reference types (ID-wrappers for blueprinted schemas) ──

@dataclass(frozen=True)
class ContextPackRef:
    context_pack_id: str

@dataclass(frozen=True)
class StateModelRef:
    state_model_id: str

@dataclass(frozen=True)
class TransitionGraphRef:
    transition_graph_id: str

@dataclass(frozen=True)
class RubricPackRef:
    rubric_pack_id: str

@dataclass(frozen=True)
class RubricJudgeResultRef:
    judge_result_id: str

@dataclass(frozen=True)
class ModelCapabilityProfileRef:
    model_id: str

@dataclass(frozen=True)
class LongContextStressProfileRef:
    profile_id: str


# ── Step boundary (a single atomic agent execution slot) ──

@dataclass
class StepBoundary:
    step_id: str
    agent_role: AgentRole
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_used: Optional[str] = None          # provider:model — no hardcoding
    cost: Optional[float] = None
    artifact_ids: list[str] = field(default_factory=list)
    checkpoint_id: Optional[str] = None
    failure_mode: Optional[str] = None


# ── Checkpoint (immutable snapshot ref per step) ──

@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    run_id: str
    step_id: str
    captured_at: datetime
    run_state_hash: str
    artifact_ids: list[str] = field(default_factory=list)
    context_pack_id: Optional[str] = None
    memory_snapshot_hash: Optional[str] = None
    resumable: bool = True
    resume_instructions: Optional[str] = None


# ── Run state (primary orchestrator record) ──

@dataclass
class RunState:
    run_id: str
    task_id: str
    purpose_id: str
    domain: str
    status: RunStatus = RunStatus.PENDING
    current_step_id: Optional[str] = None
    steps: list[StepBoundary] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def append_step(self, step: StepBoundary) -> None:
        self.steps.append(step)
        self.current_step_id = step.step_id
        self.updated_at = datetime.utcnow()


# ── Agent execution record (one agent's input/output metadata) ──

@dataclass
class AgentExecutionRecord:
    contract_id: str
    run_id: str
    step_id: str
    role: AgentRole
    purpose: str
    pbs_node: str
    context_pack_id: Optional[str] = None
    state_model_id: Optional[str] = None
    transition_graph_id: Optional[str] = None
    rubric_pack_id: Optional[str] = None
    domain: Optional[str] = None
    domain_adapter_id: Optional[str] = None
    allowed_actions: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    # Output-side metadata
    agent: Optional[str] = None
    actions_taken: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    stop_condition_triggered: Optional[str] = None
    next_recommended_step: Optional[str] = None


# ── Final report draft (structure only, assembly deferred) ──

@dataclass
class FinalReportDraft:
    report_id: str
    run_id: str
    purpose_id: str
    domain: str
    root_purpose: str
    created_at: datetime
    # Runtime-assembled fields start as None/empty
    pbs_summary: Optional[str] = None
    model_routing_summary: Optional[str] = None
    context_used: Optional[str] = None
    changes: list[str] = field(default_factory=list)
    verification_summary: Optional[str] = None
    rubric_judge_result_ids: list[str] = field(default_factory=list)
    security_summary: Optional[str] = None
    risks: list[str] = field(default_factory=list)
    human_approval_required: bool = False
    cost_summary: Optional[str] = None
    next_steps: list[str] = field(default_factory=list)
```

## Minimal APIs

Pure data-model helpers — no orchestration, no I/O, no model calls:

```python
def create_run_state(run_id: str, task_id: str, purpose_id: str, domain: str) -> RunState:
    """Create a new RunState in PENDING status with current timestamp."""
    ...

def record_checkpoint(checkpoint_id: str, run_id: str, step_id: str,
                      run_state_hash: str,
                      artifact_ids: list[str] | None = None,
                      context_pack_id: str | None = None) -> Checkpoint:
    """Record an immutable checkpoint for a step."""
    ...

def record_agent_execution(contract_id: str, run_id: str, step_id: str,
                           role: AgentRole, purpose: str,
                           pbs_node: str, **kwargs) -> AgentExecutionRecord:
    """Record agent execution input/output metadata."""
    ...

def build_final_report_draft(report_id: str, run_id: str, purpose_id: str,
                              domain: str, root_purpose: str) -> FinalReportDraft:
    """Create an empty final report draft structure."""
    ...
```

## Test Plan

Tests under `services/core/tests/test_runtime_substrate.py`:

1. **RunState creation** — default status is PENDING, timestamps non-null after helpers
2. **Append step** — step count increments, current_step_id matches last step
3. **StepBoundary defaults** — status PENDING, cost None, artifacts empty
4. **Checkpoint immutability** — frozen dataclass cannot be mutated after creation
5. **AgentExecutionRecord creation** — all fields settable, no provider hardcoding in model_used
6. **FinalReportDraft creation** — empty fields by default, human_approval_required default False
7. **Reference types** — ContextPackRef, StateModelRef, RubricPackRef etc. are hashable
8. **RunStatus enum** — values match schema: "pending", "running", "paused", "completed", "failed", "cancelled"
9. **StepStatus enum** — values match schema: "pending", "running", "completed", "failed"
10. **AgentRole enum** — all expected roles present: architect, planner, lead_coder, worker_coder, tester, reviewer, security, verifier, custom
11. **RubricVerdict** — values match schema: pass, warning, fail, needs_human_review
12. **Serialization round-trip** — dataclasses.asdict() produces valid dict structures (schema-compatible)

## Validation Commands

```bash
python -m pytest services/core/tests/ -q
python -m compileall -f services/core
git status --short
git diff --name-only
```

**First-run import check** (to verify `pyproject.toml` pythonpath resolves):

```bash
python -c "from core.runtime_substrate import RunState, Checkpoint, AgentExecutionRecord, FinalReportDraft, ContextPackRef; print('import ok')"
```

**Skip policy**: `PYTHONPATH=services/runner/src python -m runner doctor` must be skipped — no runner code changes. The review artifact must document why.

## Expected Changed Files

For future implementation:

```text
services/core/src/core/__init__.py
services/core/src/core/runtime_substrate.py
services/core/tests/__init__.py
services/core/tests/test_runtime_substrate.py
.services/core/tests/test_core_smoke.py  (optional: update smoke import)
.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md
.project-memory/pr/0044-runtime-substrate-skeleton/reviews/precommit-review.yml
```

## Non-goals

```text
- no full orchestrator
- no model provider integration
- no model calls
- no task intake changes
- no patch application
- no Apply Gate changes
- no Git/Docker-specific runtime behavior
- no domain-adapter implementation
- no .ariadne namespace creation
- no schema rewrites
- no docs/ADR rewrites
- no filesystem persistence (all in-memory data models)
- no network calls, no HTTP endpoints
- no change to packages/ or services outside core
- no old .grace namespace
- no water_meter / broken_clock / old Flask examples
```

## Review Requirements

- **Architect review** — required (runtime substrate is the first importable Python implementation of Phase 0 schemas)
- **Precommit review** — required (importable code in an existing service)
- **Human approval** — not required for skeleton data models, but recommended before merge since this is the first runtime code in the substrate

## Stop Conditions

Stop if future implementation:

- adds orchestrator logic (loops, state machines, conditional branching across steps)
- imports from `model_gateway`, `runner`, `task_intake`, or any domain-specific service
- adds Git/Docker file system operations
- adds HTTP endpoints or network calls
- adds file persistence or database connections
- modifies `schemas/**`, `docs/**`, `.project-memory/**`, `agents/**`
- creates `\.ariadne/**` files or directories
- hardcodes a model provider name in any string constant or enum
- uses old project names (water_meter, broken_clock, .grace, @grace-*)
- modifies `services/runner/`, `services/task_intake/`, `services/model_gateway/`, `services/conductor/`
- modifies `packages/`, `pyproject.toml`, `Makefile`
- produces import errors or test failures

## Open Questions

1. **Should the skeleton include a `create_step_boundary` helper?** Yes — recommended for API consistency but not strictly required. The PLAN proposes `create_run_state`, `record_checkpoint`, `record_agent_execution`, and `build_final_report_draft`. A `create_step_boundary` would be a natural fifth helper. Decision deferred to implementation.

2. **Should the skeleton live under `services/core/` or `packages/ariadne-core/`?** The PLAN chooses `services/core/` because it already exists as a placeholder, is in pyproject.toml's pythonpath, and has a test directory. Creating a new top-level package is premature without knowing the distribution mechanism.

3. **Should `FinalReportDraft` be a separate file?** No — a single `runtime_substrate.py` file is sufficient for the skeleton. File splitting can happen when the substrate grows past ~500 lines.

4. **Should `VerificationEvidence` be its own entity or part of `AgentExecutionRecord`?** This PLAN maps verification evidence into `AgentExecutionRecord.evidence: list[str]`. A separate `VerificationEvidence` entity can be extracted when the verifier subsystem is implemented.

## Decisions Made

- **Location**: `services/core/src/core/runtime_substrate.py` — uses existing placeholder service, aligns with ADR 0001 namespace, no structural churn
- **Scope**: 4 primary entity types + 7 reference types + enums + 4 helpers — minimal viable surface for Phase 1
- **No persistence**: In-memory data models only. File-system persistence belongs to dedicated storage PRs.
- **No orchestration**: Pure data helpers. No step execution logic, no state machine, no async.
- **Domain-agnostic**: All types avoid domain-specific concepts. `agent_role` uses a generic enum. `model_used` is a generic string.
- **No new dependencies**: Uses only `dataclasses`, `datetime`, `enum`, `typing` from the standard library.
- **Schemas remain authoritative**: The YAML schemas under `schemas/**` are the source of truth. Python types are derived implementations.

CONTEXT SNAPSHOT:
- base_sha: bc9d4b09952b8c9746b05c7cd728c7840bdc9d7b
- base_sha_source: git rev-parse --verify HEAD at PLAN creation time
- index_version: "0.19"
- index_version_source: .project-memory/memory_index.yml
- current_head: bc9d4b09952b8c9746b05c7cd728c7840bdc9d7b
- stale_snapshot: false
- snapshot_verified: true
- snapshot_verified_by: git introspection

DECISIONS MADE:
- Location: services/core/src/core/runtime_substrate.py (existing placeholder, no new top-level dirs)
- Scope: 4 primary entities (RunState, Checkpoint, AgentExecutionRecord, FinalReportDraft) + 7 reference types + enums + 4 helpers
- No persistence, no orchestration, no model calls, no domain-specific logic
- Single file skeleton, maintainable at <500 lines
- Domain-agnostic types with generic enums
- No new dependencies — stdlib only
- No change to pyproject.toml, packages/, or other services
- Reference types are frozen dataclass ID-wrappers

CONTEXT USED:
- labels: architecture, contracts, development-order, context-pack, ariadne-anchors, state-first, model-routing, conductor-prompt
- memory files read: memory_index.yml, project_contract.yml, anchors.yml, context-bundles/contracts.yml
- ADRs inspected: 0004 (domain-agnostic), 0005 (rubrics), 0006 (model-replaceability), 0007 (cached-understanding)
- files inspected: ARIADNE_ARCHITECTURE.md, ROADMAP.md, all 13 schemas, PR 0043 review artifacts, services/core/, services/conductor/, packages/, pyproject.toml
- files modified: .project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md
- files intentionally ignored: services/runner/, services/task_intake/, services/model_gateway/, agents/, .git/, .venv/, node_modules/
