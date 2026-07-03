"""Tests for the local product iteration signal contract."""

from __future__ import annotations

import json
import os
from pathlib import Path

from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationRecord,
    ProductIterationResult,
    ProductIterationStatus,
    record_product_iteration_signal,
    list_product_iteration_signals,
    REASON_MISSING_SESSION_REF,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_MUTATION_NOT_ALLOWED,
    REASON_ARCHIVE_NOT_ALLOWED,
    REASON_APPROVAL_NOT_ALLOWED,
    REASON_GATE_FINALIZATION_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_UNBOUNDED_STORE_PATH,
    REASON_OVERSIZED_PAYLOAD,
    REASON_DUPLICATE_ITERATION_REF,
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


# ---------------------------------------------------------------------------
# Valid signal
# ---------------------------------------------------------------------------


class TestValidSignal:
    def test_valid_signal_recorded(self, tmp_path: Path):
        """Valid signal → status recorded, iteration_ref present."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.iteration_ref is not None
        assert len(result.iteration_ref) == 16
        assert result.record is not None
        assert result.record.session_ref == "session-001"
        assert result.record.screen_time_seconds == 1800
        assert result.record.active_time_seconds == 1200
        assert result.record.idle_time_seconds == 600
        assert result.record.created_at is None
        assert result.record.schema_version == "1"

    def test_record_file_written(self, tmp_path: Path):
        """Record JSON file is written to store."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.iteration_ref is not None
        record_file = Path(store) / f"{result.iteration_ref}.json"
        assert record_file.exists()
        data = json.loads(record_file.read_text(encoding="utf-8"))
        assert data["iteration_ref"] == result.iteration_ref
        assert data["session_ref"] == "session-001"
        assert data["screen_time_seconds"] == 1800
        assert data["active_time_seconds"] == 1200
        assert data["idle_time_seconds"] == 600
        assert data["created_at"] is None
        assert data["schema_version"] == "1"


# ---------------------------------------------------------------------------
# Missing session_ref
# ---------------------------------------------------------------------------


class TestMissingSessionRef:
    def test_missing_session_ref_rejected(self, tmp_path: Path):
        """Missing session_ref → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, session_ref="")
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.REJECTED
        assert REASON_MISSING_SESSION_REF in result.reason_codes


# ---------------------------------------------------------------------------
# Deterministic ref
# ---------------------------------------------------------------------------


class TestDeterministicRef:
    def test_same_input_same_ref(self, tmp_path: Path):
        """Same input → same iteration_ref."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result1 = record_product_iteration_signal(inp)
        assert result1.status == ProductIterationStatus.RECORDED
        ref1 = result1.iteration_ref

        store2 = _store_dir(tmp_path, "store2")
        inp2 = _valid_input(store_dir=store2)
        result2 = record_product_iteration_signal(inp2)
        assert result2.status == ProductIterationStatus.RECORDED
        ref2 = result2.iteration_ref

        assert ref1 == ref2


# ---------------------------------------------------------------------------
# Record fields
# ---------------------------------------------------------------------------


class TestRecordFields:
    def test_record_includes_all_fields(self, tmp_path: Path):
        """Record includes all required fields."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        record = result.record
        assert record.iteration_ref is not None
        assert record.session_ref == "session-001"
        assert record.started_at == "2026-07-03T18:00:00Z"
        assert record.ended_at == "2026-07-03T18:30:00Z"
        assert record.screen_time_seconds == 1800
        assert record.active_time_seconds == 1200
        assert record.idle_time_seconds == 600
        assert "run-001" in record.run_refs
        assert "feedback-001" in record.feedback_refs
        assert "confusion-001" in record.confusion_refs
        assert "report-001" in record.report_refs
        assert "trace-001" in record.decision_trace_refs
        assert record.human_iteration_note == "Tested the backlog review flow."
        assert record.product_signal_status == "recorded"
        assert record.created_at is None
        assert record.source_surface == "task_intake"
        assert record.schema_version == "1"


# ---------------------------------------------------------------------------
# Empty store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store(self, tmp_path: Path):
        """Empty store → empty."""
        store = _store_dir(tmp_path)
        os.makedirs(store, exist_ok=True)
        result = list_product_iteration_signals(store_dir=store)
        assert result.status == ProductIterationStatus.EMPTY
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Missing store
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store(self, tmp_path: Path):
        """Missing store → empty."""
        store = _store_dir(tmp_path, "nonexistent")
        result = list_product_iteration_signals(store_dir=store)
        assert result.status == ProductIterationStatus.EMPTY
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Read back
# ---------------------------------------------------------------------------


class TestReadBack:
    def test_read_after_write(self, tmp_path: Path):
        """Read after write matches."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED

        list_result = list_product_iteration_signals(store_dir=store)
        assert list_result.status == ProductIterationStatus.RECORDED
        assert list_result.total_count == 1
        assert list_result.records[0].iteration_ref == result.iteration_ref
        assert list_result.records[0].session_ref == "session-001"


# ---------------------------------------------------------------------------
# Filter by session_ref
# ---------------------------------------------------------------------------


class TestFilterBySessionRef:
    def test_filter_by_session_ref(self, tmp_path: Path):
        """Filter by session_ref works."""
        store = _store_dir(tmp_path)
        inp1 = _valid_input(store_dir=store, session_ref="session-alpha")
        inp2 = _valid_input(store_dir=store, session_ref="session-beta")
        record_product_iteration_signal(inp1)
        record_product_iteration_signal(inp2)

        result = list_product_iteration_signals(store_dir=store, session_ref="session-alpha")
        assert result.status == ProductIterationStatus.RECORDED
        assert result.total_count == 1
        assert result.records[0].session_ref == "session-alpha"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_items_sorted_by_ref(self, tmp_path: Path):
        """Items sorted deterministically by iteration_ref."""
        store = _store_dir(tmp_path)
        inp_a = _valid_input(store_dir=store, session_ref="session-a")
        inp_b = _valid_input(store_dir=store, session_ref="session-b")
        record_product_iteration_signal(inp_a)
        record_product_iteration_signal(inp_b)

        result = list_product_iteration_signals(store_dir=store)
        assert result.status == ProductIterationStatus.RECORDED
        refs = [r.iteration_ref for r in result.records]
        assert refs == sorted(refs)


# ---------------------------------------------------------------------------
# Run refs
# ---------------------------------------------------------------------------


class TestRunRefs:
    def test_run_refs_stored(self, tmp_path: Path):
        """Run refs stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, run_refs=("run-abc", "run-xyz"))
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert "run-abc" in result.record.run_refs
        assert "run-xyz" in result.record.run_refs


# ---------------------------------------------------------------------------
# Confusion refs
# ---------------------------------------------------------------------------


class TestConfusionRefs:
    def test_confusion_refs_stored(self, tmp_path: Path):
        """Confusion refs stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, confusion_refs=("confusion-abc",))
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert "confusion-abc" in result.record.confusion_refs


# ---------------------------------------------------------------------------
# Feedback refs
# ---------------------------------------------------------------------------


class TestFeedbackRefs:
    def test_feedback_refs_stored(self, tmp_path: Path):
        """Feedback refs stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, feedback_refs=("feedback-abc",))
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert "feedback-abc" in result.record.feedback_refs


# ---------------------------------------------------------------------------
# Report refs
# ---------------------------------------------------------------------------


class TestReportRefs:
    def test_report_refs_stored(self, tmp_path: Path):
        """Report refs stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, report_refs=("report-abc",))
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert "report-abc" in result.record.report_refs


# ---------------------------------------------------------------------------
# Decision trace refs
# ---------------------------------------------------------------------------


class TestDecisionTraceRefs:
    def test_decision_trace_refs_stored(self, tmp_path: Path):
        """Decision trace refs stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, decision_trace_refs=("trace-abc",))
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert "trace-abc" in result.record.decision_trace_refs


# ---------------------------------------------------------------------------
# Human iteration note
# ---------------------------------------------------------------------------


class TestHumanIterationNote:
    def test_human_note_stored(self, tmp_path: Path):
        """Human note stored and returned."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, human_iteration_note="Found a bug in the trace view.")
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert result.record.human_iteration_note == "Found a bug in the trace view."


# ---------------------------------------------------------------------------
# Source surface
# ---------------------------------------------------------------------------


class TestSourceSurface:
    def test_source_surface_stored(self, tmp_path: Path):
        """Source surface stored."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, source_surface="task_intake")
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert result.record is not None
        assert result.record.source_surface == "task_intake"


# ---------------------------------------------------------------------------
# No hidden reasoning
# ---------------------------------------------------------------------------


class TestNoHiddenReasoning:
    def test_hidden_reasoning_rejected(self, tmp_path: Path):
        """Hidden reasoning in note → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, human_iteration_note="Some text <cot> hidden")
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# No backlog mutation
# ---------------------------------------------------------------------------


class TestNoBacklogMutation:
    def test_no_backlog_mutation(self, tmp_path: Path):
        """Backlog store not modified."""
        store = _store_dir(tmp_path)
        backlog_store = tmp_path / "backlog"
        os.makedirs(backlog_store, exist_ok=True)
        backlog_file = backlog_store / "item.json"
        backlog_file.write_text('{"backlog_item_ref": "test"}', encoding="utf-8")
        backlog_mtime = backlog_file.stat().st_mtime

        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED

        assert backlog_file.exists()
        assert backlog_file.stat().st_mtime == backlog_mtime
        assert backlog_file.read_text(encoding="utf-8") == '{"backlog_item_ref": "test"}'


# ---------------------------------------------------------------------------
# No decision mutation
# ---------------------------------------------------------------------------


class TestNoDecisionMutation:
    def test_no_decision_mutation(self, tmp_path: Path):
        """Decision store not modified."""
        store = _store_dir(tmp_path)
        decision_store = tmp_path / "decisions"
        os.makedirs(decision_store, exist_ok=True)
        decision_file = decision_store / "decision.json"
        decision_file.write_text('{"decision_ref": "test"}', encoding="utf-8")
        decision_mtime = decision_file.stat().st_mtime

        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED

        assert decision_file.exists()
        assert decision_file.stat().st_mtime == decision_mtime


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Unbounded path
# ---------------------------------------------------------------------------


class TestUnboundedPath:
    def test_unbounded_path_rejected(self, tmp_path: Path):
        """Unbounded store path → rejected."""
        inp = _valid_input(store_dir="../etc/passwd")
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.REJECTED
        assert REASON_UNBOUNDED_STORE_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized payload
# ---------------------------------------------------------------------------


class TestOversizedPayload:
    def test_oversized_payload_rejected(self, tmp_path: Path):
        """Oversized payload → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store, human_iteration_note="x" * 200_000)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.REJECTED
        assert REASON_OVERSIZED_PAYLOAD in result.reason_codes


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------


class TestDuplicate:
    def test_duplicate_rejected(self, tmp_path: Path):
        """Duplicate signal → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(store_dir=store)
        result1 = record_product_iteration_signal(inp)
        assert result1.status == ProductIterationStatus.RECORDED

        result2 = record_product_iteration_signal(inp)
        assert result2.status == ProductIterationStatus.REJECTED
        assert REASON_DUPLICATE_ITERATION_REF in result2.reason_codes


# ---------------------------------------------------------------------------
# No filesystem writes outside store
# ---------------------------------------------------------------------------


class TestNoWritesOutside:
    def test_no_writes_outside(self, tmp_path: Path):
        """Only product-iterations files written."""
        store = _store_dir(tmp_path)
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        inp = _valid_input(store_dir=store)
        result = record_product_iteration_signal(inp)
        assert result.status == ProductIterationStatus.RECORDED
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert len(files_after) == len(files_before) + 1


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.product_iteration
        doc = task_intake.product_iteration.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.product_iteration import record_product_iteration_signal
        source = inspect.getsource(record_product_iteration_signal)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
