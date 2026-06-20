"""Tests for runtime state transition validation."""

from __future__ import annotations

import datetime

import pytest

from core.runtime_substrate import (
    AgentExecutionRecord,
    AgentRole,
    Checkpoint,
    FinalReportDraft,
    RunState,
    RunStatus,
    StepBoundary,
    StepStatus,
    create_run_state,
    record_checkpoint,
    record_agent_execution,
    build_final_report_draft,
)
from core.runtime.transitions import (
    TransitionError,
    validate_agent_record_attachment,
    validate_checkpoint_attachment,
    validate_final_report_attachment,
    validate_run_transition,
    validate_step_transition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(step_id: str = "s1", status: StepStatus = StepStatus.PENDING) -> StepBoundary:
    return StepBoundary(step_id=step_id, agent_role=AgentRole.WORKER_CODER, status=status)


def _run(
    status: RunStatus = RunStatus.PENDING,
    steps: list[StepBoundary] | None = None,
) -> RunState:
    rs = create_run_state("run-001", "task-001", "p-001", "coding")
    rs.status = status
    if steps:
        for s in steps:
            s.status = s.status  # preserve
            rs.steps.append(s)
        if steps:
            rs.current_step_id = steps[-1].step_id
    return rs


def _checkpoint(checkpoint_id: str = "cp-001", step_id: str = "s1") -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id="run-001",
        step_id=step_id,
        captured_at=datetime.datetime.now(datetime.timezone.utc),
        run_state_hash="abc123",
    )


def _agent_record(contract_id: str = "ec-001", step_id: str = "s1") -> AgentExecutionRecord:
    return AgentExecutionRecord(
        contract_id=contract_id,
        run_id="run-001",
        step_id=step_id,
        role=AgentRole.WORKER_CODER,
        purpose="Implement",
        pbs_node="node-001",
    )


def _report_draft() -> FinalReportDraft:
    return FinalReportDraft(
        report_id="fr-001",
        run_id="run-001",
        purpose_id="p-001",
        domain="coding",
        root_purpose="Test",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


# ---------------------------------------------------------------------------
# RunState transitions
# ---------------------------------------------------------------------------


class TestValidateRunTransition:
    def test_pending_to_running(self):
        validate_run_transition(RunStatus.PENDING, RunStatus.RUNNING)

    def test_running_to_paused(self):
        validate_run_transition(RunStatus.RUNNING, RunStatus.PAUSED)

    def test_running_to_completed(self):
        validate_run_transition(RunStatus.RUNNING, RunStatus.COMPLETED)

    def test_running_to_failed(self):
        validate_run_transition(RunStatus.RUNNING, RunStatus.FAILED)

    def test_running_to_cancelled(self):
        validate_run_transition(RunStatus.RUNNING, RunStatus.CANCELLED)

    def test_paused_to_running(self):
        validate_run_transition(RunStatus.PAUSED, RunStatus.RUNNING)

    def test_paused_to_failed(self):
        validate_run_transition(RunStatus.PAUSED, RunStatus.FAILED)

    def test_completed_to_running_raises(self):
        with pytest.raises(TransitionError) as exc:
            validate_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        assert exc.value.current_state == "completed"
        assert "completed → running" in exc.value.attempted_transition

    def test_failed_to_running_raises(self):
        with pytest.raises(TransitionError):
            validate_run_transition(RunStatus.FAILED, RunStatus.RUNNING)

    def test_completed_to_completed_raises(self):
        with pytest.raises(TransitionError):
            validate_run_transition(RunStatus.COMPLETED, RunStatus.COMPLETED)

    def test_cancelled_to_running_raises(self):
        with pytest.raises(TransitionError):
            validate_run_transition(RunStatus.CANCELLED, RunStatus.RUNNING)

    def test_paused_to_completed_raises(self):
        # No final report — status-only validation rejects PAUSED → COMPLETED
        with pytest.raises(TransitionError):
            validate_run_transition(RunStatus.PAUSED, RunStatus.COMPLETED)

    def test_running_to_pending_raises(self):
        with pytest.raises(TransitionError):
            validate_run_transition(RunStatus.RUNNING, RunStatus.PENDING)


# ---------------------------------------------------------------------------
# StepBoundary transitions
# ---------------------------------------------------------------------------


class TestValidateStepTransition:
    def test_pending_to_running(self):
        validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)

    def test_running_to_completed(self):
        validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)

    def test_running_to_failed(self):
        validate_step_transition(StepStatus.RUNNING, StepStatus.FAILED)

    def test_running_to_blocked(self):
        validate_step_transition(StepStatus.RUNNING, StepStatus.BLOCKED)

    def test_blocked_to_running(self):
        validate_step_transition(StepStatus.BLOCKED, StepStatus.RUNNING)

    def test_blocked_to_failed(self):
        validate_step_transition(StepStatus.BLOCKED, StepStatus.FAILED)

    def test_completed_to_running_raises(self):
        with pytest.raises(TransitionError):
            validate_step_transition(StepStatus.COMPLETED, StepStatus.RUNNING)

    def test_failed_to_running_raises(self):
        with pytest.raises(TransitionError):
            validate_step_transition(StepStatus.FAILED, StepStatus.RUNNING)

    def test_completed_to_failed_raises(self):
        with pytest.raises(TransitionError):
            validate_step_transition(StepStatus.COMPLETED, StepStatus.FAILED)


# ---------------------------------------------------------------------------
# Checkpoint attachment
# ---------------------------------------------------------------------------


class TestValidateCheckpointAttachment:
    def test_attach_to_running_with_existing_step(self):
        s1 = _step("s1")
        run = _run(RunStatus.RUNNING, [s1])
        cp = _checkpoint("cp-001", "s1")
        validate_checkpoint_attachment(run, cp)

    def test_attach_to_paused_with_existing_step(self):
        s1 = _step("s1")
        run = _run(RunStatus.PAUSED, [s1])
        cp = _checkpoint("cp-001", "s1")
        validate_checkpoint_attachment(run, cp)

    def test_attach_to_completed_raises(self):
        s1 = _step("s1")
        run = _run(RunStatus.COMPLETED, [s1])
        cp = _checkpoint("cp-001", "s1")
        with pytest.raises(TransitionError):
            validate_checkpoint_attachment(run, cp)

    def test_attach_to_failed_raises(self):
        s1 = _step("s1")
        run = _run(RunStatus.FAILED, [s1])
        cp = _checkpoint("cp-001", "s1")
        with pytest.raises(TransitionError):
            validate_checkpoint_attachment(run, cp)

    def test_attach_to_cancelled_raises(self):
        s1 = _step("s1")
        run = _run(RunStatus.CANCELLED, [s1])
        cp = _checkpoint("cp-001", "s1")
        with pytest.raises(TransitionError):
            validate_checkpoint_attachment(run, cp)

    def test_nonexistent_step_id_raises(self):
        run = _run(RunStatus.RUNNING, [_step("s1")])
        cp = _checkpoint("cp-001", "nonexistent")
        with pytest.raises(TransitionError) as exc:
            validate_checkpoint_attachment(run, cp)
        assert "nonexistent" in exc.value.reason

    def test_duplicate_checkpoint_id_raises(self):
        s1 = _step("s1")
        s2 = _step("s2")
        run = _run(RunStatus.RUNNING, [s1, s2])
        cp1 = _checkpoint("cp-001", "s1")
        validate_checkpoint_attachment(run, cp1)
        # Simulate attaching cp1 to s1
        run.steps[0].checkpoint_id = "cp-001"
        # Now try attaching same checkpoint_id to s2
        cp_dup = _checkpoint("cp-001", "s2")
        with pytest.raises(TransitionError) as exc:
            validate_checkpoint_attachment(run, cp_dup)
        assert "already attached" in exc.value.reason


# ---------------------------------------------------------------------------
# AgentExecutionRecord attachment
# ---------------------------------------------------------------------------


class TestValidateAgentRecordAttachment:
    def test_attach_to_running_step(self):
        step = _step("s1", StepStatus.RUNNING)
        rec = _agent_record("ec-001", "s1")
        validate_agent_record_attachment(step, rec)

    def test_attach_to_completed_step_raises(self):
        step = _step("s1", StepStatus.COMPLETED)
        rec = _agent_record("ec-001", "s1")
        with pytest.raises(TransitionError):
            validate_agent_record_attachment(step, rec)

    def test_attach_to_failed_step_raises(self):
        step = _step("s1", StepStatus.FAILED)
        rec = _agent_record("ec-001", "s1")
        with pytest.raises(TransitionError):
            validate_agent_record_attachment(step, rec)

    def test_step_id_mismatch_raises(self):
        step = _step("s1", StepStatus.RUNNING)
        rec = _agent_record("ec-001", "s2")  # step_id mismatch
        with pytest.raises(TransitionError) as exc:
            validate_agent_record_attachment(step, rec)
        assert "s2" in exc.value.reason
        assert "s1" in exc.value.reason


# ---------------------------------------------------------------------------
# FinalReportDraft attachment
# ---------------------------------------------------------------------------


class TestValidateFinalReportAttachment:
    def test_attach_when_running_with_completed_step(self):
        s1 = _step("s1", StepStatus.COMPLETED)
        run = _run(RunStatus.RUNNING, [s1])
        report = _report_draft()
        validate_final_report_attachment(run, report)

    def test_attach_when_paused_raises(self):
        s1 = _step("s1", StepStatus.COMPLETED)
        run = _run(RunStatus.PAUSED, [s1])
        report = _report_draft()
        with pytest.raises(TransitionError):
            validate_final_report_attachment(run, report)

    def test_attach_with_no_completed_steps_raises(self):
        s1 = _step("s1", StepStatus.PENDING)
        run = _run(RunStatus.RUNNING, [s1])
        report = _report_draft()
        with pytest.raises(TransitionError) as exc:
            validate_final_report_attachment(run, report)
        assert "completed step" in exc.value.reason

    def test_attach_to_completed_run_raises(self):
        s1 = _step("s1", StepStatus.COMPLETED)
        run = _run(RunStatus.COMPLETED, [s1])
        report = _report_draft()
        with pytest.raises(TransitionError):
            validate_final_report_attachment(run, report)

    def test_attach_to_failed_run_raises(self):
        s1 = _step("s1", StepStatus.COMPLETED)
        run = _run(RunStatus.FAILED, [s1])
        report = _report_draft()
        with pytest.raises(TransitionError):
            validate_final_report_attachment(run, report)

    def test_attach_to_cancelled_run_raises(self):
        s1 = _step("s1", StepStatus.COMPLETED)
        run = _run(RunStatus.CANCELLED, [s1])
        report = _report_draft()
        with pytest.raises(TransitionError):
            validate_final_report_attachment(run, report)


# ---------------------------------------------------------------------------
# TransitionError structure
# ---------------------------------------------------------------------------


class TestTransitionError:
    def test_includes_current_state(self):
        try:
            validate_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        except TransitionError as exc:
            assert exc.current_state == "completed"

    def test_includes_attempted_transition(self):
        try:
            validate_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        except TransitionError as exc:
            assert "completed → running" in exc.attempted_transition

    def test_includes_reason(self):
        try:
            validate_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        except TransitionError as exc:
            assert isinstance(exc.reason, str)
            assert len(exc.reason) > 0

    def test_message_contains_state_and_transition(self):
        try:
            validate_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        except TransitionError as exc:
            msg = str(exc)
            assert "completed" in msg
            assert "running" in msg
