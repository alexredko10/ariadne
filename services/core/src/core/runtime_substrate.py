"""
Ariadne Runtime Substrate — domain-agnostic data models and pure-Python helpers.

This module implements the first minimal runtime substrate skeleton defined by
PR 0044.  It maps the Phase 0 blueprint schemas (run-state, checkpoint,
agent-execution-contract, final-report) to importable Python dataclasses,
and provides stub reference types for the remaining blueprint schemas.

No orchestrator logic, no model calls, no I/O, no domain-specific behavior.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(enum.Enum):
    """Status of a full run (orchestrator-level)."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(enum.Enum):
    """Status of a single step within a run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RubricVerdict(enum.Enum):
    """Verdict returned by the rubric judge."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AgentRole(enum.Enum):
    """Agent roles that may be assigned to a step."""
    ARCHITECT = "architect"
    PLANNER = "planner"
    LEAD_CODER = "lead_coder"
    WORKER_CODER = "worker_coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    SECURITY = "security"
    VERIFIER = "verifier"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Reference types (frozen ID-wrappers for blueprinted schemas)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ContextPackRef:
    """Reference to a ``schemas/context-pack.schema.yml`` artifact."""
    context_pack_id: str


@dataclasses.dataclass(frozen=True)
class StateModelRef:
    """Reference to a ``schemas/state-model.schema.yml`` artifact."""
    state_model_id: str


@dataclasses.dataclass(frozen=True)
class TransitionGraphRef:
    """Reference to a ``schemas/transition-graph.schema.yml`` artifact."""
    transition_graph_id: str


@dataclasses.dataclass(frozen=True)
class RubricPackRef:
    """Reference to a ``schemas/rubric-pack.schema.yml`` artifact."""
    rubric_pack_id: str


@dataclasses.dataclass(frozen=True)
class RubricJudgeResultRef:
    """Reference to a ``schemas/rubric-judge-result.schema.yml`` artifact."""
    judge_result_id: str


@dataclasses.dataclass(frozen=True)
class ModelCapabilityProfileRef:
    """Reference to a ``schemas/model-capability-profile.schema.yml`` artifact."""
    model_id: str


@dataclasses.dataclass(frozen=True)
class LongContextStressProfileRef:
    """Reference to a ``schemas/long-context-stress-profile.schema.yml`` artifact."""
    profile_id: str


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class StepBoundary:
    """A single atomic agent execution slot within a run.

    Parameters
    ----------
    step_id
        Unique identifier for this step.
    agent_role
        The agent role assigned to this step.
    status
        Current step status (default: ``PENDING``).
    started_at
        When the step started (set by orchestrator).
    completed_at
        When the step completed.
    model_used
        Model identifier in ``provider:model`` format — no hardcoded
        provider names in the substrate.
    cost
        Estimated cost of this step.
    artifact_ids
        Identifiers of artifacts produced during this step.
    checkpoint_id
        Identifier of the checkpoint captured after this step.
    failure_mode
        Description of the failure mode if the step failed.
    """
    step_id: str
    agent_role: AgentRole
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    model_used: Optional[str] = None
    cost: Optional[float] = None
    artifact_ids: list[str] = dataclasses.field(default_factory=list)
    checkpoint_id: Optional[str] = None
    failure_mode: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Checkpoint:
    """Immutable checkpoint record captured after a completed step.

    Parameters
    ----------
    checkpoint_id
        Unique identifier.
    run_id
        The run this checkpoint belongs to.
    step_id
        The step this checkpoint was captured for.
    captured_at
        When the checkpoint was captured.
    run_state_hash
        Hash of the run state at capture time.
    artifact_ids
        Artifact identifiers produced by this step.
    context_pack_id
        Context pack used during this step.
    memory_snapshot_hash
        Hash of the memory snapshot at capture time.
    resumable
        Whether the run may be resumed from this checkpoint.
    resume_instructions
        Instructions for resumption from this checkpoint.
    """
    checkpoint_id: str
    run_id: str
    step_id: str
    captured_at: datetime.datetime
    run_state_hash: str
    artifact_ids: list[str] = dataclasses.field(default_factory=list)
    context_pack_id: Optional[str] = None
    memory_snapshot_hash: Optional[str] = None
    resumable: bool = True
    resume_instructions: Optional[str] = None


@dataclasses.dataclass
class RunState:
    """Primary orchestrator record for a single run.

    Parameters
    ----------
    run_id
        Unique run identifier.
    task_id
        Task identifier this run belongs to.
    purpose_id
        Purpose identifier (references ``schemas/purpose.schema.yml``).
    domain
        Domain name — kept domain-agnostic.
    status
        Current run status (default: ``PENDING``).
    current_step_id
        Identifier of the currently active or most recently completed step.
    steps
        Ordered list of step boundaries in this run.
    created_at
        When the run was created.
    updated_at
        When the run was last updated.
    """
    run_id: str
    task_id: str
    purpose_id: str
    domain: str
    status: RunStatus = RunStatus.PENDING
    current_step_id: Optional[str] = None
    steps: list[StepBoundary] = dataclasses.field(default_factory=list)
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    def append_step(self, step: StepBoundary) -> None:
        """Append *step* to this run, making it the current step."""
        self.steps.append(step)
        self.current_step_id = step.step_id
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)


@dataclasses.dataclass
class AgentExecutionRecord:
    """Metadata for one agent's input/output during a step.

    Parameters
    ----------
    contract_id
        Unique contract identifier for this execution.
    run_id
        Run identifier.
    step_id
        Step identifier.
    role
        Agent role assigned to this execution.
    purpose
        Purpose description for this execution.
    pbs_node
        PBS node identifier.
    context_pack_id
        Reference to context pack used.
    state_model_id
        Reference to state model used.
    transition_graph_id
        Reference to transition graph used.
    rubric_pack_id
        Reference to rubric pack used.
    domain
        Domain name.
    domain_adapter_id
        Domain adapter identifier.
    allowed_actions
        Actions the agent is permitted to take.
    forbidden_actions
        Actions the agent must not take.
    stop_conditions
        Conditions that should halt this step.
    --- Output-side fields ---
    agent
        Agent identifier that executed.
    actions_taken
        Actions actually taken by the agent.
    files_changed
        File paths changed by the agent.
    claims
        Claims made by the agent.
    evidence
        Evidence references supporting claims.
    uncertainties
        Uncertainties reported by the agent.
    stop_condition_triggered
        Which stop condition was triggered, if any.
    next_recommended_step
        Agent's recommendation for the next step.
    """
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
    allowed_actions: list[str] = dataclasses.field(default_factory=list)
    forbidden_actions: list[str] = dataclasses.field(default_factory=list)
    stop_conditions: list[str] = dataclasses.field(default_factory=list)
    # Output-side metadata
    agent: Optional[str] = None
    actions_taken: list[str] = dataclasses.field(default_factory=list)
    files_changed: list[str] = dataclasses.field(default_factory=list)
    claims: list[str] = dataclasses.field(default_factory=list)
    evidence: list[str] = dataclasses.field(default_factory=list)
    uncertainties: list[str] = dataclasses.field(default_factory=list)
    stop_condition_triggered: Optional[str] = None
    next_recommended_step: Optional[str] = None


@dataclasses.dataclass
class FinalReportDraft:
    """Structure for a final report — runtime assembly deferred.

    Parameters
    ----------
    report_id
        Unique report identifier.
    run_id
        Run identifier.
    purpose_id
        Purpose identifier.
    domain
        Domain name.
    root_purpose
        The root purpose the run was meant to fulfil.
    created_at
        When the draft was created.
    pbs_summary
        Summary of purpose breakdown.
    model_routing_summary
        Summary of model routing decisions.
    context_used
        Description of context used.
    changes
        List of change descriptions.
    verification_summary
        Summary of verification results.
    rubric_judge_result_ids
        Identifiers of rubric judge results.
    security_summary
        Summary of security checks.
    risks
        List of identified risks.
    human_approval_required
        Whether human approval is needed.
    cost_summary
        Summary of costs incurred.
    next_steps
        Recommended next steps.
    """
    report_id: str
    run_id: str
    purpose_id: str
    domain: str
    root_purpose: str
    created_at: datetime.datetime
    pbs_summary: Optional[str] = None
    model_routing_summary: Optional[str] = None
    context_used: Optional[str] = None
    changes: list[str] = dataclasses.field(default_factory=list)
    verification_summary: Optional[str] = None
    rubric_judge_result_ids: list[str] = dataclasses.field(default_factory=list)
    security_summary: Optional[str] = None
    risks: list[str] = dataclasses.field(default_factory=list)
    human_approval_required: bool = False
    cost_summary: Optional[str] = None
    next_steps: list[str] = dataclasses.field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure data-model helpers
# ---------------------------------------------------------------------------


def create_run_state(
    run_id: str,
    task_id: str,
    purpose_id: str,
    domain: str,
) -> RunState:
    """Create a new ``RunState`` in ``PENDING`` status with current timestamp.

    Parameters
    ----------
    run_id
        Unique run identifier.
    task_id
        Task identifier this run belongs to.
    purpose_id
        Purpose identifier.
    domain
        Domain name.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return RunState(
        run_id=run_id,
        task_id=task_id,
        purpose_id=purpose_id,
        domain=domain,
        status=RunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


def record_checkpoint(
    checkpoint_id: str,
    run_id: str,
    step_id: str,
    run_state_hash: str,
    artifact_ids: list[str] | None = None,
    context_pack_id: str | None = None,
) -> Checkpoint:
    """Record an immutable checkpoint for a step.

    Parameters
    ----------
    checkpoint_id
        Unique checkpoint identifier.
    run_id
        Run identifier.
    step_id
        Step identifier.
    run_state_hash
        Hash of the run state at capture time.
    artifact_ids
        Artifact identifiers produced by this step.
    context_pack_id
        Context pack identifier used during this step.
    """
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        step_id=step_id,
        captured_at=datetime.datetime.now(datetime.timezone.utc),
        run_state_hash=run_state_hash,
        artifact_ids=artifact_ids or [],
        context_pack_id=context_pack_id,
        memory_snapshot_hash=None,
        resumable=True,
        resume_instructions=None,
    )


def record_agent_execution(
    contract_id: str,
    run_id: str,
    step_id: str,
    role: AgentRole,
    purpose: str,
    pbs_node: str,
    **kwargs: str | list[str] | None,
) -> AgentExecutionRecord:
    """Record agent execution input/output metadata.

    Parameters
    ----------
    contract_id
        Unique contract identifier.
    run_id
        Run identifier.
    step_id
        Step identifier.
    role
        Agent role assigned to this execution.
    purpose
        Purpose description.
    pbs_node
        PBS node identifier.
    **kwargs
        Additional fields forwarded to the record (e.g. ``domain``,
        ``allowed_actions``, ``actions_taken``, ``evidence``).
    """
    return AgentExecutionRecord(
        contract_id=contract_id,
        run_id=run_id,
        step_id=step_id,
        role=role,
        purpose=purpose,
        pbs_node=pbs_node,
        **kwargs,
    )


def build_final_report_draft(
    report_id: str,
    run_id: str,
    purpose_id: str,
    domain: str,
    root_purpose: str,
) -> FinalReportDraft:
    """Create an empty final report draft structure.

    Parameters
    ----------
    report_id
        Unique report identifier.
    run_id
        Run identifier.
    purpose_id
        Purpose identifier.
    domain
        Domain name.
    root_purpose
        The root purpose description.
    """
    return FinalReportDraft(
        report_id=report_id,
        run_id=run_id,
        purpose_id=purpose_id,
        domain=domain,
        root_purpose=root_purpose,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
