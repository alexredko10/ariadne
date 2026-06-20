"""
Ariadne runtime state transition validation.

Pure functions that validate run-state, step, checkpoint, agent-record,
and final-report transitions according to the defined state machine rules.
"""

from __future__ import annotations

from core.runtime_substrate import (
    AgentExecutionRecord,
    Checkpoint,
    FinalReportDraft,
    RunState,
    RunStatus,
    StepBoundary,
    StepStatus,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class TransitionError(Exception):
    """Raised when an invalid state transition is attempted.

    Attributes
    ----------
    current_state
        The current state at the time of the invalid transition.
    attempted_transition
        A short description of the attempted transition.
    reason
        Human-readable explanation of why the transition is invalid.
    """

    def __init__(
        self,
        current_state: str,
        attempted_transition: str,
        reason: str,
    ) -> None:
        self.current_state = current_state
        self.attempted_transition = attempted_transition
        self.reason = reason
        super().__init__(
            f"Cannot transition from {current_state} via "
            f"{attempted_transition}: {reason}"
        )


# ---------------------------------------------------------------------------
# RunState transitions
# ---------------------------------------------------------------------------

_RUN_ALLOWED: dict[RunStatus, set[RunStatus]] = {
    RunStatus.PENDING: {RunStatus.RUNNING},
    RunStatus.RUNNING: {RunStatus.PAUSED, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.PAUSED: {RunStatus.RUNNING, RunStatus.FAILED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}


def validate_run_transition(
    current_status: RunStatus,
    new_status: RunStatus,
) -> None:
    """Validate a RunState status transition.

    Parameters
    ----------
    current_status
        The current run status.
    new_status
        The desired new run status.

    Raises
    ------
    TransitionError
        If the transition is not in the allowed transition table.
    """
    allowed = _RUN_ALLOWED.get(current_status, set())
    if new_status not in allowed:
        raise TransitionError(
            current_state=current_status.value,
            attempted_transition=f"{current_status.value} → {new_status.value}",
            reason=(
                f"Transition from {current_status.value} to "
                f"{new_status.value} is not allowed."
            ),
        )


# ---------------------------------------------------------------------------
# StepBoundary transitions
# ---------------------------------------------------------------------------

_STEP_ALLOWED: dict[StepStatus, set[StepStatus]] = {
    StepStatus.PENDING: {StepStatus.RUNNING},
    StepStatus.RUNNING: {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.BLOCKED},
    StepStatus.BLOCKED: {StepStatus.RUNNING, StepStatus.FAILED},
    StepStatus.COMPLETED: set(),
    StepStatus.FAILED: set(),
}


def validate_step_transition(
    current_status: StepStatus,
    new_status: StepStatus,
) -> None:
    """Validate a StepBoundary status transition.

    Parameters
    ----------
    current_status
        The current step status.
    new_status
        The desired new status.

    Raises
    ------
    TransitionError
        If the transition is not in the allowed transition table.
    """
    allowed = _STEP_ALLOWED.get(current_status, set())
    if new_status not in allowed:
        raise TransitionError(
            current_state=current_status.value,
            attempted_transition=f"{current_status.value} → {new_status.value}",
            reason=(
                f"Step transition from {current_status.value} to "
                f"{new_status.value} is not allowed."
            ),
        )


# ---------------------------------------------------------------------------
# Checkpoint attachment
# ---------------------------------------------------------------------------


def validate_checkpoint_attachment(
    run: RunState,
    checkpoint: Checkpoint,
) -> None:
    """Validate that *checkpoint* may be attached to *run*.

    Parameters
    ----------
    run
        The run to validate against.
    checkpoint
        The checkpoint to validate.

    Raises
    ------
    TransitionError
        If the checkpoint cannot be attached.
    """
    # Checkpoint may only be attached to RUNNING or PAUSED run
    if run.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
        raise TransitionError(
            current_state=run.status.value,
            attempted_transition=f"attach-checkpoint-{checkpoint.checkpoint_id}",
            reason=(
                f"Checkpoint may only be attached to a run in "
                f"RUNNING or PAUSED state, got {run.status.value}."
            ),
        )

    # Checkpoint must reference an existing step_id
    step_ids = {s.step_id for s in run.steps}
    if checkpoint.step_id not in step_ids:
        raise TransitionError(
            current_state=run.status.value,
            attempted_transition=f"attach-checkpoint-{checkpoint.checkpoint_id}",
            reason=(
                f"Checkpoint references step_id {checkpoint.step_id!r} "
                f"which does not exist in the run."
            ),
        )

    # Duplicate checkpoint_id must be rejected
    existing_cp_ids = {
        s.checkpoint_id for s in run.steps if s.checkpoint_id is not None
    }
    if checkpoint.checkpoint_id in existing_cp_ids:
        raise TransitionError(
            current_state=run.status.value,
            attempted_transition=f"attach-checkpoint-{checkpoint.checkpoint_id}",
            reason=(
                f"Checkpoint ID {checkpoint.checkpoint_id!r} "
                f"is already attached to a step."
            ),
        )


# ---------------------------------------------------------------------------
# AgentExecutionRecord attachment
# ---------------------------------------------------------------------------


def validate_agent_record_attachment(
    step: StepBoundary,
    record: AgentExecutionRecord,
) -> None:
    """Validate that *record* may be attached to *step*.

    Parameters
    ----------
    step
        The target step.
    record
        The agent execution record to attach.

    Raises
    ------
    TransitionError
        If the record cannot be attached.
    """
    # Record may only be added to a step in RUNNING state
    if step.status != StepStatus.RUNNING:
        raise TransitionError(
            current_state=step.status.value,
            attempted_transition=f"attach-agent-record-{record.contract_id}",
            reason=(
                f"Agent record may only be attached to a step in "
                f"RUNNING state, got {step.status.value}."
            ),
        )

    # step_id in record must match target step
    if record.step_id != step.step_id:
        raise TransitionError(
            current_state=step.status.value,
            attempted_transition=f"attach-agent-record-{record.contract_id}",
            reason=(
                f"Record step_id {record.step_id!r} does not match "
                f"target step_id {step.step_id!r}."
            ),
        )


# ---------------------------------------------------------------------------
# FinalReportDraft attachment
# ---------------------------------------------------------------------------


def validate_final_report_attachment(
    run: RunState,
    report: FinalReportDraft,
) -> None:
    """Validate that *report* may be attached to *run*.

    Parameters
    ----------
    run
        The run to validate.
    report
        The final report draft to attach.

    Raises
    ------
    TransitionError
        If the report cannot be attached.
    """
    # Final report may only be attached when run is in RUNNING state
    if run.status != RunStatus.RUNNING:
        raise TransitionError(
            current_state=run.status.value,
            attempted_transition=f"attach-final-report-{report.report_id}",
            reason=(
                f"Final report may only be attached when run is in "
                f"RUNNING state, got {run.status.value}."
            ),
        )

    # Run must have at least one completed step
    completed_steps = [s for s in run.steps if s.status == StepStatus.COMPLETED]
    if not completed_steps:
        raise TransitionError(
            current_state=run.status.value,
            attempted_transition=f"attach-final-report-{report.report_id}",
            reason=(
                "Final report requires at least one completed step "
                "in the run."
            ),
        )
