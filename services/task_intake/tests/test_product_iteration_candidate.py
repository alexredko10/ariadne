"""Tests for the product iteration recommendation candidate."""

from __future__ import annotations

import json
import os
from pathlib import Path

from task_intake.product_iteration_candidate import (
    ProductIterationCandidate,
    ProductIterationCandidateResult,
    ProductIterationCandidateStatus,
    build_product_iteration_candidate,
    build_product_iteration_candidate_from_store,
    RC_NO_RECORDS_YET,
    RC_HIGH_IDLE_RATIO,
    RC_LOW_ACTIVE_RATIO,
    RC_HIGH_CONFUSION_SIGNAL_COUNT,
    RC_FEEDBACK_PRESENT,
    RC_HUMAN_NOTES_PRESENT,
    RC_LONG_SCREEN_TIME_WITHOUT_REFS,
    RC_HEALTHY_USAGE_SIGNAL,
    RC_INSUFFICIENT_EVIDENCE,
    HIGH_IDLE_RATIO_THRESHOLD,
    LOW_ACTIVE_RATIO_THRESHOLD,
    HIGH_CONFUSION_SIGNAL_THRESHOLD,
    LONG_SCREEN_TIME_THRESHOLD_SECONDS,
    HEALTHY_ACTIVE_RATIO_THRESHOLD,
    HEALTHY_IDLE_RATIO_MAX,
    INSUFFICIENT_EVIDENCE_RECORDS,
)
from task_intake.product_iteration_summary import (
    ProductIterationSummaryData,
    build_product_iteration_summary_from_store,
)
from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationStatus,
    record_product_iteration_signal,
    list_product_iteration_signals,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _summary(**overrides: object) -> ProductIterationSummaryData:
    kwargs = {
        "total_records": 5,
        "total_screen_time_seconds": 9000,
        "total_active_time_seconds": 6000,
        "total_idle_time_seconds": 3000,
        "active_ratio": 0.6667,
        "idle_ratio": 0.3333,
        "sessions_count": 2,
        "latest_session_ref": "session-001",
        "run_refs_count": 3,
        "feedback_refs_count": 1,
        "confusion_refs_count": 1,
        "report_refs_count": 1,
        "decision_trace_refs_count": 1,
        "records_with_human_note_count": 1,
    }
    kwargs.update(overrides)
    return ProductIterationSummaryData(**kwargs)  # type: ignore[arg-type]


def _valid_input(**overrides: object) -> ProductIterationInput:
    kwargs = {
        "session_ref": "session-001",
        "started_at": "2026-07-03T18:00:00Z",
        "ended_at": "2026-07-03T18:30:00Z",
        "screen_time_seconds": 1800,
        "active_time_seconds": 1200,
        "idle_time_seconds": 600,
        "run_refs": ("run-001", "run-002"),
        "feedback_refs": ("feedback-001",),
        "confusion_refs": ("confusion-001",),
        "report_refs": ("report-001",),
        "decision_trace_refs": ("trace-001",),
        "human_iteration_note": "Tested the backlog review flow.",
        "source_surface": "task_intake",
        "product_signal_status": "recorded",
    }
    kwargs.update(overrides)
    return ProductIterationInput(**kwargs)  # type: ignore[arg-type]


def _store_dir(tmp_path: Path, name: str = "product-iterations") -> str:
    return str(tmp_path / name)


def _record(tmp_path: Path, store: str, **overrides: object) -> str:
    inp = _valid_input(store_dir=store, **overrides)
    result = record_product_iteration_signal(inp)
    assert result.status == ProductIterationStatus.RECORDED, f"reason_codes={result.reason_codes}"
    assert result.iteration_ref is not None
    return result.iteration_ref


# ---------------------------------------------------------------------------
# No records
# ---------------------------------------------------------------------------


class TestNoRecords:
    def test_no_records(self):
        """Empty summary → no_records_yet."""
        s = _summary(total_records=0)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_NO_RECORDS_YET in result.candidate.reason_codes
        assert result.candidate.candidate_status == "insufficient_evidence"
        assert result.candidate.priority == "none"


# ---------------------------------------------------------------------------
# High idle ratio
# ---------------------------------------------------------------------------


class TestHighIdleRatio:
    def test_high_idle_ratio(self):
        """High idle ratio → high_idle_ratio."""
        s = _summary(idle_ratio=0.6, active_ratio=0.4)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_HIGH_IDLE_RATIO in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "high"


# ---------------------------------------------------------------------------
# Low active ratio
# ---------------------------------------------------------------------------


class TestLowActiveRatio:
    def test_low_active_ratio(self):
        """Low active ratio → low_active_ratio."""
        s = _summary(active_ratio=0.1, idle_ratio=0.9)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_LOW_ACTIVE_RATIO in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "high"


# ---------------------------------------------------------------------------
# High confusion signals
# ---------------------------------------------------------------------------


class TestHighConfusionSignals:
    def test_high_confusion_signals(self):
        """High confusion signals → high_confusion_signal_count."""
        s = _summary(confusion_refs_count=5)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_HIGH_CONFUSION_SIGNAL_COUNT in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "high"


# ---------------------------------------------------------------------------
# Feedback present
# ---------------------------------------------------------------------------


class TestFeedbackPresent:
    def test_feedback_present(self):
        """Feedback present → feedback_present."""
        s = _summary(feedback_refs_count=2)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_FEEDBACK_PRESENT in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "medium"


# ---------------------------------------------------------------------------
# Human notes present
# ---------------------------------------------------------------------------


class TestHumanNotesPresent:
    def test_human_notes_present(self):
        """Human notes present → human_notes_present."""
        s = _summary(records_with_human_note_count=2)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_HUMAN_NOTES_PRESENT in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "medium"


# ---------------------------------------------------------------------------
# Long screen time without refs
# ---------------------------------------------------------------------------


class TestLongScreenTimeWithoutRefs:
    def test_long_screen_time_without_refs(self):
        """Long screen time without run refs → long_screen_time_without_refs."""
        s = _summary(total_screen_time_seconds=7200, run_refs_count=0)
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_LONG_SCREEN_TIME_WITHOUT_REFS in result.candidate.reason_codes
        assert result.candidate.candidate_status == "recommended"
        assert result.candidate.priority == "medium"


# ---------------------------------------------------------------------------
# Healthy usage
# ---------------------------------------------------------------------------


class TestHealthyUsage:
    def test_healthy_usage(self):
        """Healthy usage → healthy_usage_signal."""
        s = _summary(
            active_ratio=0.7,
            idle_ratio=0.2,
            confusion_refs_count=0,
            feedback_refs_count=0,
            records_with_human_note_count=0,
        )
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_HEALTHY_USAGE_SIGNAL in result.candidate.reason_codes
        assert result.candidate.candidate_status == "no_recommendation"
        assert result.candidate.priority == "low"


# ---------------------------------------------------------------------------
# Insufficient evidence
# ---------------------------------------------------------------------------


class TestInsufficientEvidence:
    def test_insufficient_evidence(self):
        """Few records + no strong signals → insufficient_evidence."""
        s = _summary(
            total_records=1,
            active_ratio=0.5,
            idle_ratio=0.5,
            confusion_refs_count=0,
            feedback_refs_count=0,
            records_with_human_note_count=0,
            run_refs_count=0,
            total_screen_time_seconds=100,
        )
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_INSUFFICIENT_EVIDENCE in result.candidate.reason_codes
        assert result.candidate.candidate_status == "insufficient_evidence"
        assert result.candidate.priority == "low"


# ---------------------------------------------------------------------------
# Multiple reason codes
# ---------------------------------------------------------------------------


class TestMultipleReasonCodes:
    def test_multiple_reason_codes(self):
        """Multiple triggers → multiple reason codes."""
        s = _summary(
            idle_ratio=0.6,
            active_ratio=0.4,
            confusion_refs_count=5,
            feedback_refs_count=2,
            records_with_human_note_count=2,
        )
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert RC_HIGH_IDLE_RATIO in result.candidate.reason_codes
        assert RC_HIGH_CONFUSION_SIGNAL_COUNT in result.candidate.reason_codes
        assert RC_FEEDBACK_PRESENT in result.candidate.reason_codes
        assert RC_HUMAN_NOTES_PRESENT in result.candidate.reason_codes
        # Priority should be the most significant (high_idle_ratio)
        assert result.candidate.priority == "high"


# ---------------------------------------------------------------------------
# Deterministic ref
# ---------------------------------------------------------------------------


class TestDeterministicRef:
    def test_same_summary_same_ref(self):
        """Same summary → same candidate_ref."""
        s = _summary()
        result1 = build_product_iteration_candidate(s)
        result2 = build_product_iteration_candidate(s)
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_ref == result2.candidate.candidate_ref

    def test_different_summary_different_ref(self):
        """Different summary → different candidate_ref."""
        s1 = _summary(total_records=5)
        s2 = _summary(total_records=10)
        result1 = build_product_iteration_candidate(s1)
        result2 = build_product_iteration_candidate(s2)
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_ref != result2.candidate.candidate_ref


# ---------------------------------------------------------------------------
# Candidate fields
# ---------------------------------------------------------------------------


class TestCandidateFields:
    def test_candidate_includes_all_fields(self):
        """Candidate includes all required fields."""
        s = _summary()
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        c = result.candidate
        assert c.candidate_ref is not None
        assert len(c.candidate_ref) == 16
        assert c.candidate_status in ("recommended", "no_recommendation", "insufficient_evidence")
        assert c.priority in ("high", "medium", "low", "none")
        assert c.confidence in ("high", "medium", "low")
        assert isinstance(c.reason_codes, tuple)
        assert isinstance(c.summary_snapshot, str)
        assert isinstance(c.recommended_focus, str)
        assert isinstance(c.human_review_required, bool)
        assert isinstance(c.evidence_counts, dict)
        assert isinstance(c.explanation_lines, tuple)


# ---------------------------------------------------------------------------
# Evidence counts shape
# ---------------------------------------------------------------------------


class TestEvidenceCounts:
    def test_evidence_counts_shape(self):
        """Evidence counts includes all key metrics."""
        s = _summary()
        result = build_product_iteration_candidate(s)
        assert result.candidate is not None
        ec = result.candidate.evidence_counts
        assert "total_records" in ec
        assert "total_screen_time_seconds" in ec
        assert "total_active_time_seconds" in ec
        assert "total_idle_time_seconds" in ec
        assert "active_ratio" in ec
        assert "idle_ratio" in ec
        assert "sessions_count" in ec
        assert "run_refs_count" in ec
        assert "feedback_refs_count" in ec
        assert "confusion_refs_count" in ec
        assert "report_refs_count" in ec
        assert "decision_trace_refs_count" in ec
        assert "records_with_human_note_count" in ec


# ---------------------------------------------------------------------------
# Explanation lines
# ---------------------------------------------------------------------------


class TestExplanationLines:
    def test_explanation_lines_shape(self):
        """Explanation lines match reason codes."""
        s = _summary(idle_ratio=0.6, active_ratio=0.4)
        result = build_product_iteration_candidate(s)
        assert result.candidate is not None
        assert len(result.candidate.explanation_lines) == len(result.candidate.reason_codes)
        for line in result.candidate.explanation_lines:
            assert isinstance(line, str)
            assert len(line) > 0


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    def test_no_mutation_of_input(self):
        """build_product_iteration_candidate does not mutate input summary."""
        s = _summary()
        s_copy = _summary()
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        # Summary unchanged
        assert s.total_records == s_copy.total_records
        assert s.active_ratio == s_copy.active_ratio
        assert s.idle_ratio == s_copy.idle_ratio


# ---------------------------------------------------------------------------
# No filesystem writes
# ---------------------------------------------------------------------------


class TestNoWrites:
    def test_no_writes(self, tmp_path: Path):
        """build_product_iteration_candidate does not write any files."""
        s = _summary()
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert files_after == files_before


# ---------------------------------------------------------------------------
# No backlog mutation
# ---------------------------------------------------------------------------


class TestNoBacklogMutation:
    def test_no_backlog_mutation(self, tmp_path: Path):
        """Backlog store not modified."""
        s = _summary()
        backlog_store = tmp_path / "backlog"
        os.makedirs(backlog_store, exist_ok=True)
        backlog_file = backlog_store / "item.json"
        backlog_file.write_text('{"backlog_item_ref": "test"}', encoding="utf-8")
        backlog_mtime = backlog_file.stat().st_mtime

        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY

        assert backlog_file.exists()
        assert backlog_file.stat().st_mtime == backlog_mtime


# ---------------------------------------------------------------------------
# No decision mutation
# ---------------------------------------------------------------------------


class TestNoDecisionMutation:
    def test_no_decision_mutation(self, tmp_path: Path):
        """Decision store not modified."""
        s = _summary()
        decision_store = tmp_path / "decisions"
        os.makedirs(decision_store, exist_ok=True)
        decision_file = decision_store / "decision.json"
        decision_file.write_text('{"decision_ref": "test"}', encoding="utf-8")
        decision_mtime = decision_file.stat().st_mtime

        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY

        assert decision_file.exists()
        assert decision_file.stat().st_mtime == decision_mtime


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        s = _summary()
        result = build_product_iteration_candidate(s)
        assert result.status == ProductIterationCandidateStatus.READY
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# From store convenience
# ---------------------------------------------------------------------------


class TestFromStoreConvenience:
    def test_from_store_empty(self, tmp_path: Path):
        """Empty store → EMPTY."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        result = build_product_iteration_candidate_from_store(store_dir=store)
        assert result.status == ProductIterationCandidateStatus.EMPTY

    def test_from_store_valid(self, tmp_path: Path):
        """Valid store → READY with candidate."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_candidate_from_store(store_dir=store)
        assert result.status == ProductIterationCandidateStatus.READY
        assert result.candidate is not None
        assert result.candidate.candidate_ref is not None


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.product_iteration_candidate
        doc = task_intake.product_iteration_candidate.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.product_iteration_candidate import build_product_iteration_candidate
        source = inspect.getsource(build_product_iteration_candidate)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
