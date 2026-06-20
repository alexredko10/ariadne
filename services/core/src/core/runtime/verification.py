"""
Ariadne runtime verification evidence — deterministic evidence accumulation,
summarization, and final report building.

Evidence is stored in an in-process memory dict.  No I/O, no persistence,
no model calls, no domain-specific behavior.
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import Any, Optional

from core.runtime_substrate import (
    FinalReportDraft,
    RunState,
    StepStatus,
    create_run_state,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class VerificationError(Exception):
    """Raised when verification evidence or final report validation fails.

    Attributes
    ----------
    subject
        The subject of the validation failure.
    reason
        Human-readable explanation.
    evidence_id
        Identifier of the evidence record, if applicable.
    step_id
        Identifier of the step, if applicable.
    """

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


# ---------------------------------------------------------------------------
# Valid status values
# ---------------------------------------------------------------------------

_VALID_EVIDENCE_STATUSES = frozenset({
    "passed", "failed", "warning", "skipped", "not_run",
})


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


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
    status: str
    message: str = ""
    command: Optional[str] = None
    artifact_ref: Optional[str] = None
    rubric_ref: Optional[str] = None
    recorded_at: Optional[datetime.datetime] = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "step_id": self.step_id,
            "check_name": self.check_name,
            "status": self.status,
            "message": self.message,
            "command": self.command,
            "artifact_ref": self.artifact_ref,
            "rubric_ref": self.rubric_ref,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationEvidence:
        raw_date = data.get("recorded_at")
        dt = datetime.datetime.fromisoformat(raw_date) if raw_date else None
        return cls(
            evidence_id=data.get("evidence_id", ""),
            step_id=data.get("step_id", ""),
            check_name=data.get("check_name", ""),
            status=data.get("status", ""),
            message=data.get("message", ""),
            command=data.get("command"),
            artifact_ref=data.get("artifact_ref"),
            rubric_ref=data.get("rubric_ref"),
            recorded_at=dt,
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# In-memory evidence store
# ---------------------------------------------------------------------------

_run_evidence_store: dict[str, list[VerificationEvidence]] = {}


def _reset_evidence_store() -> None:
    """Clear the in-memory evidence store (used in tests)."""
    _run_evidence_store.clear()


# ---------------------------------------------------------------------------
# Evidence creation
# ---------------------------------------------------------------------------


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
) -> VerificationEvidence:
    """Create a new VerificationEvidence instance with validation.

    Parameters
    ----------
    evidence_id
        Unique identifier for this evidence record.
    step_id
        The step this evidence belongs to.
    check_name
        Name of the validation or check.
    status
        One of: "passed", "failed", "warning", "skipped", "not_run".
    message
        Human-readable summary.
    command
        The validation command or check identifier.
    artifact_ref
        Reference to an artifact.
    rubric_ref
        Reference to a rubric pack entry.
    recorded_at
        When this evidence was recorded.
    **metadata
        Additional structured data.

    Raises
    ------
    VerificationError
        If status is invalid, or evidence_id/step_id is empty.
    """
    if not evidence_id:
        raise VerificationError(
            subject="create_verification_evidence",
            reason="evidence_id must not be empty.",
        )
    if not step_id:
        raise VerificationError(
            subject="create_verification_evidence",
            reason="step_id must not be empty.",
        )
    if status not in _VALID_EVIDENCE_STATUSES:
        raise VerificationError(
            subject="create_verification_evidence",
            reason=(
                f"Invalid status: {status!r}. "
                f"Expected one of: {sorted(_VALID_EVIDENCE_STATUSES)}."
            ),
        )

    return VerificationEvidence(
        evidence_id=evidence_id,
        step_id=step_id,
        check_name=check_name,
        status=status,
        message=message,
        command=command,
        artifact_ref=artifact_ref,
        rubric_ref=rubric_ref,
        recorded_at=recorded_at,
        metadata=dict(metadata),
    )


# ---------------------------------------------------------------------------
# Evidence attachment
# ---------------------------------------------------------------------------


def attach_verification_evidence(
    run: RunState,
    evidence: VerificationEvidence,
) -> None:
    """Attach *evidence* to *run*.

    Parameters
    ----------
    run
        The run to attach evidence to.
    evidence
        The evidence record.

    Raises
    ------
    VerificationError
        If the referenced step does not exist in the run, or if a duplicate
        evidence_id already exists.
    """
    # Validate that referenced step exists
    step_ids = {s.step_id for s in run.steps}
    if evidence.step_id not in step_ids:
        raise VerificationError(
            subject="attach_verification_evidence",
            reason=(
                f"Step {evidence.step_id!r} does not exist in run "
                f"{run.run_id!r}."
            ),
            evidence_id=evidence.evidence_id,
            step_id=evidence.step_id,
        )

    # Validate no duplicate evidence_id
    existing = _run_evidence_store.get(run.run_id, [])
    existing_ids = {e.evidence_id for e in existing}
    if evidence.evidence_id in existing_ids:
        raise VerificationError(
            subject="attach_verification_evidence",
            reason=(
                f"Duplicate evidence_id {evidence.evidence_id!r} "
                f"for run {run.run_id!r}."
            ),
            evidence_id=evidence.evidence_id,
            step_id=evidence.step_id,
        )

    _run_evidence_store.setdefault(run.run_id, []).append(evidence)


# ---------------------------------------------------------------------------
# Evidence retrieval
# ---------------------------------------------------------------------------


def get_evidence_for_run(run: RunState) -> list[VerificationEvidence]:
    """Return all evidence attached to *run*.

    Parameters
    ----------
    run
        The run to retrieve evidence for.
    """
    return list(_run_evidence_store.get(run.run_id, []))


# ---------------------------------------------------------------------------
# Evidence summarization
# ---------------------------------------------------------------------------


def summarize_verification_evidence(run: RunState) -> dict[str, Any]:
    """Return a deterministic summary of verification evidence for *run*.

    Returns
    -------
    dict
        A dictionary with counts per status and ordered lists of
        evidence IDs for failing and warning evidence.
    """
    evidence = get_evidence_for_run(run)

    total = len(evidence)
    passed = sum(1 for e in evidence if e.status == "passed")
    failed = sum(1 for e in evidence if e.status == "failed")
    warning = sum(1 for e in evidence if e.status == "warning")
    skipped = sum(1 for e in evidence if e.status == "skipped")
    not_run = sum(1 for e in evidence if e.status == "not_run")

    failing_ids = sorted(
        e.evidence_id for e in evidence if e.status == "failed"
    )
    warning_ids = sorted(
        e.evidence_id for e in evidence if e.status == "warning"
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "warning": warning,
        "skipped": skipped,
        "not_run": not_run,
        "failing_evidence_ids": failing_ids,
        "warning_evidence_ids": warning_ids,
    }


# ---------------------------------------------------------------------------
# Final report readiness
# ---------------------------------------------------------------------------


def validate_final_report_readiness(run: RunState) -> None:
    """Validate that *run* is ready for a final report.

    Checks:
    - Run has at least one completed step.
    - Run is in RUNNING state.
    - No unresolved failed evidence.

    Raises
    ------
    VerificationError
        If the run is not ready.
    """
    # Must have at least one completed step
    completed_steps = [s for s in run.steps if s.status == StepStatus.COMPLETED]
    if not completed_steps:
        raise VerificationError(
            subject="validate_final_report_readiness",
            reason="Run has no completed steps.",
        )

    # Must be RUNNING (eligible for transition to COMPLETED)
    if run.status.value != "running":
        raise VerificationError(
            subject="validate_final_report_readiness",
            reason=(
                f"Run must be in RUNNING state to produce a final report, "
                f"got {run.status.value}."
            ),
        )

    # No unresolved failed evidence
    summary = summarize_verification_evidence(run)
    if summary["failed"] > 0:
        raise VerificationError(
            subject="validate_final_report_readiness",
            reason=(
                f"Run has {summary['failed']} failed verification "
                f"evidence records. All evidence must pass before "
                f"final report."
            ),
        )


# ---------------------------------------------------------------------------
# Final report building
# ---------------------------------------------------------------------------


def build_final_report(run: RunState) -> FinalReportDraft:
    """Build a deterministic FinalReportDraft from *run*.

    No LLM calls.  No model-generated text.  No domain-specific behavior.

    Parameters
    ----------
    run
        The run to build the report for.

    Returns
    -------
    FinalReportDraft
        A populated draft report.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    # Step summaries
    changes = [
        f"step {s.step_id}: {s.status.value}" for s in run.steps
    ]

    # Verification summary
    v_summary = summarize_verification_evidence(run)

    # Risks from failed/warning evidence
    risks: list[str] = []
    evidence = get_evidence_for_run(run)
    for e in evidence:
        if e.status == "failed":
            risks.append(f"[failed] {e.evidence_id}: {e.message or e.check_name}")
        elif e.status == "warning":
            risks.append(f"[warning] {e.evidence_id}: {e.message or e.check_name}")

    # Human approval required if any failed evidence
    human_approval_required = v_summary["failed"] > 0

    # Next steps from incomplete step statuses
    next_steps: list[str] = []
    for s in run.steps:
        if s.status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.BLOCKED):
            next_steps.append(
                f"step {s.step_id}: {s.status.value} requires action"
            )

    return FinalReportDraft(
        report_id=f"{run.run_id}-report",
        run_id=run.run_id,
        purpose_id=run.purpose_id,
        domain=run.domain,
        root_purpose=run.purpose_id,
        created_at=now,
        pbs_summary=f"run {run.run_id}: {len(run.steps)} steps",
        model_routing_summary=None,
        context_used=None,
        changes=changes,
        verification_summary=str(v_summary),
        rubric_judge_result_ids=[],
        security_summary=None,
        risks=risks,
        human_approval_required=human_approval_required,
        cost_summary=None,
        next_steps=next_steps,
    )
