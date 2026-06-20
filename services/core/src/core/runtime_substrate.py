"""
Ariadne Runtime Substrate — domain-agnostic data models and pure-Python helpers.

This module implements the first minimal runtime substrate skeleton defined by
PR 0044, extended with serialization (``to_dict`` / ``from_dict``) in PR 0045.

It maps the Phase 0 blueprint schemas (run-state, checkpoint,
agent-execution-contract, final-report) to importable Python dataclasses,
and provides stub reference types for the remaining blueprint schemas.

No orchestrator logic, no model calls, no I/O, no domain-specific behavior.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENTINEL = object()


def _to_iso8601(dt: datetime.datetime | None) -> str | None:
    """Convert a datetime to an ISO8601 string with Z suffix."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _from_iso8601(s: str | None) -> datetime.datetime | None:
    """Parse an ISO8601 string (Z suffix or +00:00) to a UTC datetime."""
    if s is None:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(s).replace(tzinfo=None)


def _enum_to_str(v: Any) -> Any:
    """Convert an enum member to its value string; pass through non-enums."""
    if isinstance(v, enum.Enum):
        return v.value
    return v


def _str_to_enum(cls: type[enum.Enum], val: str | None, default: Any = _SENTINEL) -> Any:
    """Convert a string back to an enum member, returning *default* if not found."""
    if val is None:
        if default is not _SENTINEL:
            return default
        return None
    try:
        return cls(val)
    except ValueError:
        if default is not _SENTINEL:
            return default
        raise


def _dt_dict(d: dict[str, Any], key: str) -> datetime.datetime | None:
    """Extract an optional datetime field from a dict (ISO8601 string or None)."""
    raw = d.get(key)
    return _from_iso8601(raw) if raw is not None else None


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
    """Reference to a ``schemas/context-pack.schema.yml`` artifact.

    Serialized as ``{"context_pack_id": "..."}`` — no raw repo dumps.
    """
    context_pack_id: str

    def to_dict(self) -> dict[str, str]:
        return {"context_pack_id": self.context_pack_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextPackRef:
        return cls(context_pack_id=data.get("context_pack_id", ""))


@dataclasses.dataclass(frozen=True)
class StateModelRef:
    """Reference to a ``schemas/state-model.schema.yml`` artifact."""
    state_model_id: str

    def to_dict(self) -> dict[str, str]:
        return {"state_model_id": self.state_model_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateModelRef:
        return cls(state_model_id=data.get("state_model_id", ""))


@dataclasses.dataclass(frozen=True)
class TransitionGraphRef:
    """Reference to a ``schemas/transition-graph.schema.yml`` artifact."""
    transition_graph_id: str

    def to_dict(self) -> dict[str, str]:
        return {"transition_graph_id": self.transition_graph_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransitionGraphRef:
        return cls(transition_graph_id=data.get("transition_graph_id", ""))


@dataclasses.dataclass(frozen=True)
class RubricPackRef:
    """Reference to a ``schemas/rubric-pack.schema.yml`` artifact."""
    rubric_pack_id: str

    def to_dict(self) -> dict[str, str]:
        return {"rubric_pack_id": self.rubric_pack_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RubricPackRef:
        return cls(rubric_pack_id=data.get("rubric_pack_id", ""))


@dataclasses.dataclass(frozen=True)
class RubricJudgeResultRef:
    """Reference to a ``schemas/rubric-judge-result.schema.yml`` artifact."""
    judge_result_id: str

    def to_dict(self) -> dict[str, str]:
        return {"judge_result_id": self.judge_result_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RubricJudgeResultRef:
        return cls(judge_result_id=data.get("judge_result_id", ""))


@dataclasses.dataclass(frozen=True)
class ModelCapabilityProfileRef:
    """Reference to a ``schemas/model-capability-profile.schema.yml`` artifact.

    ``model_id`` is a generic identifier — no provider hardcoding.
    """
    model_id: str

    def to_dict(self) -> dict[str, str]:
        return {"model_id": self.model_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelCapabilityProfileRef:
        return cls(model_id=data.get("model_id", ""))


@dataclasses.dataclass(frozen=True)
class LongContextStressProfileRef:
    """Reference to a ``schemas/long-context-stress-profile.schema.yml`` artifact."""
    profile_id: str

    def to_dict(self) -> dict[str, str]:
        return {"profile_id": self.profile_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LongContextStressProfileRef:
        return cls(profile_id=data.get("profile_id", ""))


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_role": self.agent_role.value,
            "status": self.status.value,
            "started_at": _to_iso8601(self.started_at),
            "completed_at": _to_iso8601(self.completed_at),
            "model_used": self.model_used,
            "cost": self.cost,
            "artifact_ids": list(self.artifact_ids),
            "checkpoint_id": self.checkpoint_id,
            "failure_mode": self.failure_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepBoundary:
        return cls(
            step_id=data.get("step_id", ""),
            agent_role=_str_to_enum(AgentRole, data.get("agent_role"), AgentRole.CUSTOM),
            status=_str_to_enum(StepStatus, data.get("status"), StepStatus.PENDING),
            started_at=_dt_dict(data, "started_at"),
            completed_at=_dt_dict(data, "completed_at"),
            model_used=data.get("model_used"),
            cost=data.get("cost"),
            artifact_ids=list(data.get("artifact_ids", [])),
            checkpoint_id=data.get("checkpoint_id"),
            failure_mode=data.get("failure_mode"),
        )


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "captured_at": _to_iso8601(self.captured_at),
            "run_state_hash": self.run_state_hash,
            "artifact_ids": list(self.artifact_ids),
            "context_pack_id": self.context_pack_id,
            "memory_snapshot_hash": self.memory_snapshot_hash,
            "resumable": self.resumable,
            "resume_instructions": self.resume_instructions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            run_id=data.get("run_id", ""),
            step_id=data.get("step_id", ""),
            captured_at=_from_iso8601(data.get("captured_at", "1970-01-01T00:00:00Z")) or datetime.datetime(1970, 1, 1),
            run_state_hash=data.get("run_state_hash", ""),
            artifact_ids=list(data.get("artifact_ids", [])),
            context_pack_id=data.get("context_pack_id"),
            memory_snapshot_hash=data.get("memory_snapshot_hash"),
            resumable=data.get("resumable", True),
            resume_instructions=data.get("resume_instructions"),
        )


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "purpose_id": self.purpose_id,
            "domain": self.domain,
            "status": self.status.value,
            "current_step_id": self.current_step_id,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": _to_iso8601(self.created_at),
            "updated_at": _to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunState:
        steps_raw = data.get("steps", [])
        steps = [StepBoundary.from_dict(s) if isinstance(s, dict) else s for s in steps_raw]
        return cls(
            run_id=data.get("run_id", ""),
            task_id=data.get("task_id", ""),
            purpose_id=data.get("purpose_id", ""),
            domain=data.get("domain", ""),
            status=_str_to_enum(RunStatus, data.get("status"), RunStatus.PENDING),
            current_step_id=data.get("current_step_id"),
            steps=steps,
            created_at=_dt_dict(data, "created_at"),
            updated_at=_dt_dict(data, "updated_at"),
        )


@dataclasses.dataclass
class AgentExecutionRecord:
    """Metadata for one agent's input/output during a step.

    .. include serialization: to_dict() / from_dict() for checkpoint/audit.
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "role": self.role.value,
            "purpose": self.purpose,
            "pbs_node": self.pbs_node,
            "context_pack_id": self.context_pack_id,
            "state_model_id": self.state_model_id,
            "transition_graph_id": self.transition_graph_id,
            "rubric_pack_id": self.rubric_pack_id,
            "domain": self.domain,
            "domain_adapter_id": self.domain_adapter_id,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "stop_conditions": list(self.stop_conditions),
            "agent": self.agent,
            "actions_taken": list(self.actions_taken),
            "files_changed": list(self.files_changed),
            "claims": list(self.claims),
            "evidence": list(self.evidence),
            "uncertainties": list(self.uncertainties),
            "stop_condition_triggered": self.stop_condition_triggered,
            "next_recommended_step": self.next_recommended_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentExecutionRecord:
        return cls(
            contract_id=data.get("contract_id", ""),
            run_id=data.get("run_id", ""),
            step_id=data.get("step_id", ""),
            role=_str_to_enum(AgentRole, data.get("role"), AgentRole.CUSTOM),
            purpose=data.get("purpose", ""),
            pbs_node=data.get("pbs_node", ""),
            context_pack_id=data.get("context_pack_id"),
            state_model_id=data.get("state_model_id"),
            transition_graph_id=data.get("transition_graph_id"),
            rubric_pack_id=data.get("rubric_pack_id"),
            domain=data.get("domain"),
            domain_adapter_id=data.get("domain_adapter_id"),
            allowed_actions=list(data.get("allowed_actions", [])),
            forbidden_actions=list(data.get("forbidden_actions", [])),
            stop_conditions=list(data.get("stop_conditions", [])),
            agent=data.get("agent"),
            actions_taken=list(data.get("actions_taken", [])),
            files_changed=list(data.get("files_changed", [])),
            claims=list(data.get("claims", [])),
            evidence=list(data.get("evidence", [])),
            uncertainties=list(data.get("uncertainties", [])),
            stop_condition_triggered=data.get("stop_condition_triggered"),
            next_recommended_step=data.get("next_recommended_step"),
        )


@dataclasses.dataclass
class FinalReportDraft:
    """Structure for a final report — runtime assembly deferred.

    .. include serialization: to_dict() / from_dict() for audit trail.
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "purpose_id": self.purpose_id,
            "domain": self.domain,
            "root_purpose": self.root_purpose,
            "created_at": _to_iso8601(self.created_at),
            "pbs_summary": self.pbs_summary,
            "model_routing_summary": self.model_routing_summary,
            "context_used": self.context_used,
            "changes": list(self.changes),
            "verification_summary": self.verification_summary,
            "rubric_judge_result_ids": list(self.rubric_judge_result_ids),
            "security_summary": self.security_summary,
            "risks": list(self.risks),
            "human_approval_required": self.human_approval_required,
            "cost_summary": self.cost_summary,
            "next_steps": list(self.next_steps),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinalReportDraft:
        return cls(
            report_id=data.get("report_id", ""),
            run_id=data.get("run_id", ""),
            purpose_id=data.get("purpose_id", ""),
            domain=data.get("domain", ""),
            root_purpose=data.get("root_purpose", ""),
            created_at=_from_iso8601(data.get("created_at", "1970-01-01T00:00:00Z")) or datetime.datetime(1970, 1, 1),
            pbs_summary=data.get("pbs_summary"),
            model_routing_summary=data.get("model_routing_summary"),
            context_used=data.get("context_used"),
            changes=list(data.get("changes", [])),
            verification_summary=data.get("verification_summary"),
            rubric_judge_result_ids=list(data.get("rubric_judge_result_ids", [])),
            security_summary=data.get("security_summary"),
            risks=list(data.get("risks", [])),
            human_approval_required=data.get("human_approval_required", False),
            cost_summary=data.get("cost_summary"),
            next_steps=list(data.get("next_steps", [])),
        )


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
