"""Tests for the product iteration evidence summary."""

from __future__ import annotations

import os
from pathlib import Path

from task_intake.product_iteration_summary import (
    ProductIterationSummaryData,
    ProductIterationSummaryResult,
    ProductIterationSummaryStatus,
    build_product_iteration_summary,
    build_product_iteration_summary_from_store,
)
from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationRecord,
    ProductIterationStatus,
    record_product_iteration_signal,
    list_product_iteration_signals,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
# Empty summary
# ---------------------------------------------------------------------------


class TestEmptySummary:
    def test_empty_records(self):
        """Empty records → EMPTY, zero totals."""
        result = build_product_iteration_summary(())
        assert result.status == ProductIterationSummaryStatus.EMPTY
        assert result.summary is not None
        assert result.summary.total_records == 0
        assert result.summary.total_screen_time_seconds == 0
        assert result.summary.total_active_time_seconds == 0
        assert result.summary.total_idle_time_seconds == 0
        assert result.summary.active_ratio == 0.0
        assert result.summary.idle_ratio == 0.0
        assert result.summary.sessions_count == 0
        assert result.summary.latest_session_ref is None
        assert result.summary.run_refs_count == 0
        assert result.summary.feedback_refs_count == 0
        assert result.summary.confusion_refs_count == 0
        assert result.summary.report_refs_count == 0
        assert result.summary.decision_trace_refs_count == 0
        assert result.summary.records_with_human_note_count == 0


# ---------------------------------------------------------------------------
# Single record
# ---------------------------------------------------------------------------


class TestSingleRecord:
    def test_single_record_summary(self, tmp_path: Path):
        """Single record → correct totals."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.total_records == 1
        assert result.summary.total_screen_time_seconds == 1800
        assert result.summary.total_active_time_seconds == 1200
        assert result.summary.total_idle_time_seconds == 600
        assert result.summary.active_ratio == 0.6667
        assert result.summary.idle_ratio == 0.3333
        assert result.summary.sessions_count == 1
        assert result.summary.latest_session_ref == "session-001"
        assert result.summary.run_refs_count == 2
        assert result.summary.feedback_refs_count == 1
        assert result.summary.confusion_refs_count == 1
        assert result.summary.report_refs_count == 1
        assert result.summary.decision_trace_refs_count == 1
        assert result.summary.records_with_human_note_count == 1


# ---------------------------------------------------------------------------
# Multi-record aggregation
# ---------------------------------------------------------------------------


class TestMultiRecord:
    def test_multi_record_aggregation(self, tmp_path: Path):
        """Multiple records → aggregated totals."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store, session_ref="session-alpha", screen_time_seconds=900, active_time_seconds=600, idle_time_seconds=300)
        _record(tmp_path, store, session_ref="session-beta", screen_time_seconds=1800, active_time_seconds=1200, idle_time_seconds=600)
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.total_records == 2
        assert result.summary.total_screen_time_seconds == 2700
        assert result.summary.total_active_time_seconds == 1800
        assert result.summary.total_idle_time_seconds == 900
        assert result.summary.active_ratio == 0.6667
        assert result.summary.idle_ratio == 0.3333
        assert result.summary.sessions_count == 2
        assert result.summary.latest_session_ref in ("session-alpha", "session-beta")
        assert result.summary.run_refs_count == 4
        assert result.summary.feedback_refs_count == 2
        assert result.summary.confusion_refs_count == 2
        assert result.summary.report_refs_count == 2
        assert result.summary.decision_trace_refs_count == 2
        assert result.summary.records_with_human_note_count == 2


# ---------------------------------------------------------------------------
# Records with and without human notes
# ---------------------------------------------------------------------------


class TestHumanNoteCount:
    def test_records_without_notes(self, tmp_path: Path):
        """Records without human notes → records_with_human_note_count=0."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store, human_iteration_note="")
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.records_with_human_note_count == 0

    def test_mixed_notes(self, tmp_path: Path):
        """Mixed notes → correct count."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store, session_ref="session-a", human_iteration_note="Note A")
        _record(tmp_path, store, session_ref="session-b", human_iteration_note="")
        _record(tmp_path, store, session_ref="session-c", human_iteration_note="Note C")
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.records_with_human_note_count == 2


# ---------------------------------------------------------------------------
# Zero time values
# ---------------------------------------------------------------------------


class TestZeroTime:
    def test_zero_time_ratios(self, tmp_path: Path):
        """Zero active+idle time → ratios are 0.0."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store, active_time_seconds=0, idle_time_seconds=0)
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.active_ratio == 0.0
        assert result.summary.idle_ratio == 0.0


# ---------------------------------------------------------------------------
# From store
# ---------------------------------------------------------------------------


class TestFromStore:
    def test_from_store_empty(self, tmp_path: Path):
        """Empty store → EMPTY."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        result = build_product_iteration_summary_from_store(store_dir=store)
        assert result.status == ProductIterationSummaryStatus.EMPTY

    def test_from_store_missing(self, tmp_path: Path):
        """Missing store → EMPTY."""
        store = _store_dir(tmp_path, "nonexistent")
        result = build_product_iteration_summary_from_store(store_dir=store)
        assert result.status == ProductIterationSummaryStatus.EMPTY

    def test_from_store_valid(self, tmp_path: Path):
        """Valid store → READY with summary."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_summary_from_store(store_dir=store)
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.total_records == 1

    def test_from_store_filtered(self, tmp_path: Path):
        """Filter by session_ref works."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store, session_ref="session-alpha")
        _record(tmp_path, store, session_ref="session-beta")
        result = build_product_iteration_summary_from_store(store_dir=store, session_ref="session-alpha")
        assert result.status == ProductIterationSummaryStatus.READY
        assert result.summary is not None
        assert result.summary.total_records == 1
        assert result.summary.sessions_count == 1


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    def test_no_mutation_of_input(self, tmp_path: Path):
        """build_product_iteration_summary does not mutate input records."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        records_before = list(list_result.records)
        result = build_product_iteration_summary(list_result.records)
        assert result.status == ProductIterationSummaryStatus.READY
        # Records unchanged
        assert list(list_result.records) == records_before


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_summary_from_store(store_dir=store)
        assert result.status == ProductIterationSummaryStatus.READY
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.product_iteration_summary
        doc = task_intake.product_iteration_summary.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.product_iteration_summary import build_product_iteration_summary
        source = inspect.getsource(build_product_iteration_summary)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
