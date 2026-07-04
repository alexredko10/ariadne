"""Tests for the product iteration session capture surface."""

from __future__ import annotations

import os
from pathlib import Path

from task_intake.product_iteration_surface import (
    SessionSurfaceResult,
    SessionSurfaceStatus,
    generate_session_ref,
    normalize_session_ref,
    bounded_screen_time,
    bounded_active_time,
    bounded_idle_time,
    normalize_ref_list,
    normalize_human_note,
    build_product_iteration_input,
    record_session_signal,
    _MAX_SCREEN_TIME_SECONDS,
    _MAX_ACTIVE_TIME_SECONDS,
    _MAX_IDLE_TIME_SECONDS,
    _MAX_HUMAN_NOTE_LENGTH,
    _MAX_REFS_COUNT,
)
from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationStatus,
    record_product_iteration_signal,
)


# ---------------------------------------------------------------------------
# Session ref generation
# ---------------------------------------------------------------------------


class TestSessionRefGeneration:
    def test_generate_session_ref_returns_string(self):
        """generate_session_ref returns a 16-char hex string."""
        ref = generate_session_ref()
        assert isinstance(ref, str)
        assert len(ref) == 16
        # Hex string
        int(ref, 16)

    def test_generate_session_ref_deterministic_within_call(self):
        """generate_session_ref returns different values on successive calls."""
        ref1 = generate_session_ref()
        ref2 = generate_session_ref()
        # Monotonic time changes, so refs should differ
        assert ref1 != ref2


# ---------------------------------------------------------------------------
# Session ref normalization
# ---------------------------------------------------------------------------


class TestSessionRefNormalization:
    def test_normalize_session_ref_keeps_valid_chars(self):
        """Normalize keeps alphanumeric and hyphen/underscore."""
        ref = normalize_session_ref("session-abc_123!@#")
        assert "session-abc_123" in ref
        assert "!" not in ref
        assert "@" not in ref

    def test_normalize_session_ref_bounded_length(self):
        """Normalize bounds to 64 chars."""
        long_ref = "a" * 200
        result = normalize_session_ref(long_ref)
        assert len(result) == 64

    def test_normalize_session_ref_empty(self):
        """Empty input → empty string."""
        assert normalize_session_ref("") == ""


# ---------------------------------------------------------------------------
# Bounded screen time
# ---------------------------------------------------------------------------


class TestBoundedScreenTime:
    def test_bounded_screen_time_clamps_negative(self):
        """Negative → 0."""
        assert bounded_screen_time(-1) == 0

    def test_bounded_screen_time_clamps_overflow(self):
        """Over max → max."""
        assert bounded_screen_time(_MAX_SCREEN_TIME_SECONDS + 1) == _MAX_SCREEN_TIME_SECONDS

    def test_bounded_screen_time_passes_valid(self):
        """Valid value passes through."""
        assert bounded_screen_time(1800) == 1800


# ---------------------------------------------------------------------------
# Bounded active time
# ---------------------------------------------------------------------------


class TestBoundedActiveTime:
    def test_bounded_active_time_clamps_negative(self):
        """Negative → 0."""
        assert bounded_active_time(-1) == 0

    def test_bounded_active_time_clamps_overflow(self):
        """Over max → max."""
        assert bounded_active_time(_MAX_ACTIVE_TIME_SECONDS + 1) == _MAX_ACTIVE_TIME_SECONDS

    def test_bounded_active_time_passes_valid(self):
        """Valid value passes through."""
        assert bounded_active_time(1200) == 1200


# ---------------------------------------------------------------------------
# Bounded idle time
# ---------------------------------------------------------------------------


class TestBoundedIdleTime:
    def test_bounded_idle_time_clamps_negative(self):
        """Negative → 0."""
        assert bounded_idle_time(-1) == 0

    def test_bounded_idle_time_clamps_overflow(self):
        """Over max → max."""
        assert bounded_idle_time(_MAX_IDLE_TIME_SECONDS + 1) == _MAX_IDLE_TIME_SECONDS

    def test_bounded_idle_time_passes_valid(self):
        """Valid value passes through."""
        assert bounded_idle_time(600) == 600


# ---------------------------------------------------------------------------
# Ref list normalization
# ---------------------------------------------------------------------------


class TestRefListNormalization:
    def test_normalize_ref_list_deduplicates(self):
        """Duplicate refs are removed."""
        result = normalize_ref_list(("run-001", "run-001", "run-002"))
        assert result == ("run-001", "run-002")

    def test_normalize_ref_list_sorts(self):
        """Refs are sorted."""
        result = normalize_ref_list(("run-003", "run-001", "run-002"))
        assert result == ("run-001", "run-002", "run-003")

    def test_normalize_ref_list_bounds_count(self):
        """Refs are bounded to max_count."""
        many_refs = tuple(f"run-{i:03d}" for i in range(200))
        result = normalize_ref_list(many_refs, max_count=5)
        assert len(result) == 5

    def test_normalize_ref_list_sanitizes(self):
        """Unsafe chars are removed."""
        result = normalize_ref_list(("run!@#",))
        assert "run" in result[0]
        assert "!" not in result[0]

    def test_normalize_ref_list_empty(self):
        """Empty tuple → empty tuple."""
        assert normalize_ref_list(()) == ()


# ---------------------------------------------------------------------------
# Human note normalization
# ---------------------------------------------------------------------------


class TestHumanNoteNormalization:
    def test_normalize_human_note_trims(self):
        """Note is trimmed."""
        assert normalize_human_note("  hello  ") == "hello"

    def test_normalize_human_note_bounds_length(self):
        """Note is bounded."""
        long_note = "x" * (_MAX_HUMAN_NOTE_LENGTH + 100)
        result = normalize_human_note(long_note)
        assert len(result) == _MAX_HUMAN_NOTE_LENGTH

    def test_normalize_human_note_empty(self):
        """Empty → empty."""
        assert normalize_human_note("") == ""


# ---------------------------------------------------------------------------
# Build ProductIterationInput
# ---------------------------------------------------------------------------


class TestBuildInput:
    def test_build_input_returns_valid_input(self):
        """build_product_iteration_input returns ProductIterationInput."""
        inp = build_product_iteration_input(
            session_ref="session-001",
            screen_time_seconds=1800,
            active_time_seconds=1200,
            idle_time_seconds=600,
            run_refs=("run-001",),
            feedback_refs=("feedback-001",),
            confusion_refs=("confusion-001",),
            report_refs=("report-001",),
            decision_trace_refs=("trace-001",),
            human_iteration_note="Test note.",
        )
        assert isinstance(inp, ProductIterationInput)
        assert inp.session_ref == "session-001"
        assert inp.screen_time_seconds == 1800
        assert inp.active_time_seconds == 1200
        assert inp.idle_time_seconds == 600
        assert inp.run_refs == ("run-001",)
        assert inp.feedback_refs == ("feedback-001",)
        assert inp.confusion_refs == ("confusion-001",)
        assert inp.report_refs == ("report-001",)
        assert inp.decision_trace_refs == ("trace-001",)
        assert inp.human_iteration_note == "Test note."

    def test_build_input_bounds_values(self):
        """build_product_iteration_input bounds all values."""
        inp = build_product_iteration_input(
            session_ref="session-001",
            screen_time_seconds=-1,
            active_time_seconds=-1,
            idle_time_seconds=-1,
            run_refs=("run!@#", "run-001", "run-001"),
            human_iteration_note="  hello  ",
        )
        assert inp.screen_time_seconds == 0
        assert inp.active_time_seconds == 0
        assert inp.idle_time_seconds == 0
        # "run!@#" is sanitized to "run", then sorted with "run-001"
        assert "run" in inp.run_refs
        assert "run-001" in inp.run_refs
        assert len(inp.run_refs) == 2
        assert inp.human_iteration_note == "hello"


# ---------------------------------------------------------------------------
# Record session signal
# ---------------------------------------------------------------------------


class TestRecordSessionSignal:
    def test_record_session_signal_recorded(self, tmp_path: Path):
        """Valid session signal → recorded."""
        store = str(tmp_path / "product-iterations")
        result = record_session_signal(
            session_ref="session-001",
            screen_time_seconds=1800,
            active_time_seconds=1200,
            idle_time_seconds=600,
            run_refs=("run-001",),
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.RECORDED
        assert result.iteration_ref is not None
        assert len(result.iteration_ref) == 16

    def test_record_session_signal_empty_ref(self, tmp_path: Path):
        """Empty session ref → invalid."""
        store = str(tmp_path / "product-iterations")
        result = record_session_signal(
            session_ref="",
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.INVALID
        assert "empty_session_ref" in result.reason_codes

    def test_record_session_signal_rejected(self, tmp_path: Path):
        """Hidden reasoning in note → rejected."""
        store = str(tmp_path / "product-iterations")
        result = record_session_signal(
            session_ref="session-001",
            human_iteration_note="Some text <cot> hidden",
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.REJECTED
        assert len(result.reason_codes) > 0


# ---------------------------------------------------------------------------
# No external analytics / provider / network / Docker / subprocess / git
# ---------------------------------------------------------------------------


class TestNoExternalBehavior:
    def test_no_external_behavior(self):
        """Surface module does not import forbidden modules."""
        import task_intake.product_iteration_surface
        source = task_intake.product_iteration_surface.__doc__ or ""
        # The docstring says "does not perform network calls" — check that
        # the module does not import forbidden runtime modules
        import inspect
        mod_source = inspect.getsource(task_intake.product_iteration_surface)
        forbidden_imports = ["requests", "urllib", "subprocess", "docker", "openai", "anthropic"]
        for fi in forbidden_imports:
            assert f"import {fi}" not in mod_source, f"Forbidden import found: {fi}"


# ---------------------------------------------------------------------------
# No backlog mutation
# ---------------------------------------------------------------------------


class TestNoBacklogMutation:
    def test_no_backlog_mutation(self, tmp_path: Path):
        """Backlog store not modified by surface."""
        store = str(tmp_path / "product-iterations")
        backlog_store = tmp_path / "backlog"
        os.makedirs(backlog_store, exist_ok=True)
        backlog_file = backlog_store / "item.json"
        backlog_file.write_text('{"backlog_item_ref": "test"}', encoding="utf-8")
        backlog_mtime = backlog_file.stat().st_mtime

        result = record_session_signal(
            session_ref="session-001",
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.RECORDED

        assert backlog_file.exists()
        assert backlog_file.stat().st_mtime == backlog_mtime


# ---------------------------------------------------------------------------
# No decision mutation
# ---------------------------------------------------------------------------


class TestNoDecisionMutation:
    def test_no_decision_mutation(self, tmp_path: Path):
        """Decision store not modified by surface."""
        store = str(tmp_path / "product-iterations")
        decision_store = tmp_path / "decisions"
        os.makedirs(decision_store, exist_ok=True)
        decision_file = decision_store / "decision.json"
        decision_file.write_text('{"decision_ref": "test"}', encoding="utf-8")
        decision_mtime = decision_file.stat().st_mtime

        result = record_session_signal(
            session_ref="session-001",
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.RECORDED

        assert decision_file.exists()
        assert decision_file.stat().st_mtime == decision_mtime


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = str(tmp_path / "product-iterations")
        result = record_session_signal(
            session_ref="session-001",
            store_dir=store,
        )
        assert result.status == SessionSurfaceStatus.RECORDED
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.product_iteration_surface
        doc = task_intake.product_iteration_surface.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.product_iteration_surface import record_session_signal
        source = inspect.getsource(record_session_signal)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
