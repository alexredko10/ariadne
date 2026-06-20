"""Tests for runtime verification evidence and final report building."""

from __future__ import annotations

import datetime

import pytest

from core.runtime_substrate import (
    FinalReportDraft,
    RunState,
    StepBoundary,
    StepStatus,
    AgentRole,
    create_run_state,
)
from core.runtime.verification import (
    VerificationError,
    VerificationEvidence,
    attach_verification_evidence,
    build_final_report,
    create_verification_evidence,
    get_evidence_for_run,
    summarize_verification_evidence,
    validate_final_report_readiness,
    _reset_evidence_store,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_evidence_store():
    """Reset the in-memory evidence store before each test."""
    _reset_evidence_store()
    yield


@pytest.fixture
def run() -> RunState:
    rs = create_run_state("run-001", "task-001", "p-001", "coding")
    rs.steps.append(
        StepBoundary(step_id="s1", agent_role=AgentRole.WORKER_CODER, status=StepStatus.COMPLETED)
    )
    rs.current_step_id = "s1"
    return rs


@pytest.fixture
def running_run(run: RunState) -> RunState:
    run.status = run.status.__class__("running")  # RunStatus.RUNNING
    return run


# ---------------------------------------------------------------------------
# create_verification_evidence
# ---------------------------------------------------------------------------


class TestCreateVerificationEvidence:
    def test_creates_evidence_with_deterministic_fields(self):
        ev = create_verification_evidence(
            evidence_id="ev-001",
            step_id="s1",
            check_name="pytest",
            status="passed",
            message="All tests passed",
        )
        assert ev.evidence_id == "ev-001"
        assert ev.step_id == "s1"
        assert ev.check_name == "pytest"
        assert ev.status == "passed"

    def test_invalid_status_raises(self):
        with pytest.raises(VerificationError) as exc:
            create_verification_evidence(
                evidence_id="ev-001",
                step_id="s1",
                check_name="check",
                status="invalid_status",
            )
        assert exc.value.subject == "create_verification_evidence"

    def test_empty_evidence_id_raises(self):
        with pytest.raises(VerificationError):
            create_verification_evidence(
                evidence_id="",
                step_id="s1",
                check_name="check",
                status="passed",
            )

    def test_empty_step_id_raises(self):
        with pytest.raises(VerificationError):
            create_verification_evidence(
                evidence_id="ev-001",
                step_id="",
                check_name="check",
                status="passed",
            )

    def test_metadata_is_stored(self):
        ev = create_verification_evidence(
            evidence_id="ev-001",
            step_id="s1",
            check_name="check",
            status="passed",
            extra_field="value",
            count=42,
        )
        assert ev.metadata["extra_field"] == "value"
        assert ev.metadata["count"] == 42


# ---------------------------------------------------------------------------
# attach_verification_evidence
# ---------------------------------------------------------------------------


class TestAttachVerificationEvidence:
    def test_attach_to_existing_step(self, run: RunState):
        ev = create_verification_evidence("ev-001", "s1", "check", "passed")
        attach_verification_evidence(run, ev)
        assert len(get_evidence_for_run(run)) == 1

    def test_attach_to_nonexistent_step_raises(self, run: RunState):
        ev = create_verification_evidence("ev-001", "nonexistent", "check", "passed")
        with pytest.raises(VerificationError) as exc:
            attach_verification_evidence(run, ev)
        assert "nonexistent" in exc.value.reason
        assert exc.value.evidence_id == "ev-001"
        assert exc.value.step_id == "nonexistent"

    def test_duplicate_evidence_id_raises(self, run: RunState):
        ev1 = create_verification_evidence("ev-001", "s1", "check", "passed")
        ev2 = create_verification_evidence("ev-001", "s1", "check2", "failed")
        attach_verification_evidence(run, ev1)
        with pytest.raises(VerificationError) as exc:
            attach_verification_evidence(run, ev2)
        assert "Duplicate" in exc.value.reason

    def test_attach_to_terminal_run(self, run: RunState):
        run.status = run.status.__class__("completed")
        ev = create_verification_evidence("ev-001", "s1", "check", "passed")
        # Attaching evidence to terminal runs is allowed (post-mortem audit)
        attach_verification_evidence(run, ev)
        assert len(get_evidence_for_run(run)) == 1


# ---------------------------------------------------------------------------
# get_evidence_for_run
# ---------------------------------------------------------------------------


class TestGetEvidenceForRun:
    def test_empty_for_run_with_no_evidence(self, run: RunState):
        assert get_evidence_for_run(run) == []

    def test_returns_evidence_after_attachment(self, run: RunState):
        ev = create_verification_evidence("ev-001", "s1", "check", "passed")
        attach_verification_evidence(run, ev)
        result = get_evidence_for_run(run)
        assert len(result) == 1
        assert result[0].evidence_id == "ev-001"


# ---------------------------------------------------------------------------
# summarize_verification_evidence
# ---------------------------------------------------------------------------


class TestSummarizeVerificationEvidence:
    def test_counts_all_statuses_correctly(self, run: RunState):
        attach_verification_evidence(run, create_verification_evidence("ev-001", "s1", "c1", "passed"))
        attach_verification_evidence(run, create_verification_evidence("ev-002", "s1", "c2", "failed"))
        attach_verification_evidence(run, create_verification_evidence("ev-003", "s1", "c3", "warning"))
        attach_verification_evidence(run, create_verification_evidence("ev-004", "s1", "c4", "skipped"))
        attach_verification_evidence(run, create_verification_evidence("ev-005", "s1", "c5", "not_run"))

        summary = summarize_verification_evidence(run)
        assert summary["total"] == 5
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["warning"] == 1
        assert summary["skipped"] == 1
        assert summary["not_run"] == 1

    def test_deterministic_ordering(self, run: RunState):
        attach_verification_evidence(run, create_verification_evidence("ev-c", "s1", "c1", "failed"))
        attach_verification_evidence(run, create_verification_evidence("ev-a", "s1", "c2", "failed"))
        attach_verification_evidence(run, create_verification_evidence("ev-w1", "s1", "c3", "warning"))
        attach_verification_evidence(run, create_verification_evidence("ev-w2", "s1", "c4", "warning"))

        s1 = summarize_verification_evidence(run)
        s2 = summarize_verification_evidence(run)
        assert s1 == s2
        assert s1["failing_evidence_ids"] == ["ev-a", "ev-c"]
        assert s1["warning_evidence_ids"] == ["ev-w1", "ev-w2"]

    def test_no_evidence_returns_zero_counts(self, run: RunState):
        summary = summarize_verification_evidence(run)
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["failing_evidence_ids"] == []


# ---------------------------------------------------------------------------
# validate_final_report_readiness
# ---------------------------------------------------------------------------


class TestValidateFinalReportReadiness:
    def test_valid_when_running_with_completed_step_and_no_failed_evidence(
        self, running_run: RunState,
    ):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "check", "passed"),
        )
        # Should not raise
        validate_final_report_readiness(running_run)

    def test_no_completed_steps_raises(self, run: RunState):
        run.steps.clear()
        run.status = run.status.__class__("running")
        with pytest.raises(VerificationError) as exc:
            validate_final_report_readiness(run)
        assert "no completed steps" in exc.value.reason.lower()

    def test_failed_evidence_raises(self, running_run: RunState):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "check", "failed"),
        )
        with pytest.raises(VerificationError) as exc:
            validate_final_report_readiness(running_run)
        assert "failed" in exc.value.reason.lower()

    def test_paused_run_raises(self, run: RunState):
        run.status = run.status.__class__("paused")
        with pytest.raises(VerificationError):
            validate_final_report_readiness(run)


# ---------------------------------------------------------------------------
# build_final_report
# ---------------------------------------------------------------------------


class TestBuildFinalReport:
    def test_returns_final_report_draft(self, running_run: RunState):
        report = build_final_report(running_run)
        assert isinstance(report, FinalReportDraft)

    def test_includes_run_id(self, running_run: RunState):
        report = build_final_report(running_run)
        assert report.run_id == "run-001"

    def test_includes_final_status_via_verification_summary(self, running_run: RunState):
        report = build_final_report(running_run)
        assert report.verification_summary is not None

    def test_includes_step_summaries(self, running_run: RunState):
        report = build_final_report(running_run)
        assert "step s1: completed" in report.changes[0]

    def test_includes_verification_summary(self, running_run: RunState):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "check", "passed"),
        )
        report = build_final_report(running_run)
        assert report.verification_summary is not None
        assert "'passed': 1" in report.verification_summary

    def test_includes_risks_from_failed_evidence(self, running_run: RunState):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "pytest", "failed", message="Tests failed"),
        )
        report = build_final_report(running_run)
        assert any("ev-001" in r for r in report.risks)
        assert any("failed" in r for r in report.risks)

    def test_sets_human_approval_required_when_failed(self, running_run: RunState):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "check", "failed"),
        )
        report = build_final_report(running_run)
        assert report.human_approval_required is True

    def test_no_human_approval_when_all_passed(self, running_run: RunState):
        attach_verification_evidence(
            running_run,
            create_verification_evidence("ev-001", "s1", "check", "passed"),
        )
        report = build_final_report(running_run)
        assert report.human_approval_required is False

    def test_next_steps_from_incomplete_steps(self, running_run: RunState):
        running_run.steps.append(
            StepBoundary(step_id="s2", agent_role=AgentRole.WORKER_CODER, status=StepStatus.PENDING)
        )
        report = build_final_report(running_run)
        assert any("s2" in ns for ns in report.next_steps)

    def test_no_raw_repository_dumps(self, running_run: RunState):
        report = build_final_report(running_run)
        # Check dict form for absence of large content
        d = report.to_dict()
        for v in d.values():
            if isinstance(v, str) and len(v) > 2000:
                pytest.fail("Report contains a string over 2000 chars — possible raw dump")
        assert True

    def test_round_trip_serialization(self, running_run: RunState):
        report = build_final_report(running_run)
        d = report.to_dict()
        restored = FinalReportDraft.from_dict(d)
        assert restored.report_id == report.report_id
        assert restored.run_id == report.run_id


# ---------------------------------------------------------------------------
# VerificationError
# ---------------------------------------------------------------------------


class TestVerificationError:
    def test_includes_subject(self):
        try:
            create_verification_evidence("ev-001", "", "check", "passed")
        except VerificationError as exc:
            assert exc.subject == "create_verification_evidence"

    def test_includes_reason(self):
        try:
            create_verification_evidence("ev-001", "", "check", "passed")
        except VerificationError as exc:
            assert isinstance(exc.reason, str)
            assert len(exc.reason) > 0

    def test_evidence_id_when_applicable(self, run: RunState):
        ev = create_verification_evidence("ev-001", "nonexistent", "check", "passed")
        try:
            attach_verification_evidence(run, ev)
        except VerificationError as exc:
            assert exc.evidence_id == "ev-001"
            assert exc.step_id == "nonexistent"
