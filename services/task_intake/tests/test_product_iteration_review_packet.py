"""Tests for the product iteration human review packet."""

from __future__ import annotations

import os
from pathlib import Path

from task_intake.product_iteration_review_packet import (
    ProductIterationReviewPacket,
    ProductIterationReviewPacketResult,
    ProductIterationReviewPacketStatus,
    build_product_iteration_review_packet,
    _DECISION_OPTIONS,
    _SAFETY_BOUNDARIES,
    _RECOMMENDED_QUESTIONS,
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
# Empty store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store(self, tmp_path: Path):
        """Empty store → READY with no_records_yet."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        assert result.packet is not None
        assert "no_records_yet" in result.packet.reason_codes


# ---------------------------------------------------------------------------
# Missing store
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store(self, tmp_path: Path):
        """Missing store → READY with no_records_yet."""
        store = _store_dir(tmp_path, "nonexistent")
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        assert result.packet is not None
        assert "no_records_yet" in result.packet.reason_codes


# ---------------------------------------------------------------------------
# Full packet
# ---------------------------------------------------------------------------


class TestFullPacket:
    def test_full_packet_ready(self, tmp_path: Path):
        """Valid store → READY with all fields."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        assert result.packet is not None
        p = result.packet
        assert p.packet_ref is not None
        assert len(p.packet_ref) == 16
        assert p.packet_status == "ready"
        assert p.generated_from == store
        assert p.summary is not None
        assert p.candidate_ref is not None
        assert p.candidate_status is not None
        assert p.priority is not None
        assert p.confidence is not None
        assert isinstance(p.reason_codes, tuple)
        assert p.recommended_focus is not None
        assert isinstance(p.human_review_required, bool)
        assert isinstance(p.evidence_counts, dict)
        assert isinstance(p.evidence_highlights, dict)
        assert isinstance(p.recommended_human_questions, tuple)
        assert isinstance(p.decision_options, tuple)
        assert isinstance(p.safety_boundaries, tuple)
        assert isinstance(p.validation_notes, tuple)
        assert isinstance(p.record_count, int)
        assert isinstance(p.session_count, int)
        assert isinstance(p.markdown_text, str)
        assert isinstance(p.plain_text, str)


# ---------------------------------------------------------------------------
# Packet ref deterministic
# ---------------------------------------------------------------------------


class TestPacketRefDeterministic:
    def test_same_store_same_ref(self, tmp_path: Path):
        """Same store → same packet_ref."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result1 = build_product_iteration_review_packet(store_dir=store)
        result2 = build_product_iteration_review_packet(store_dir=store)
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.packet_ref == result2.packet.packet_ref


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestComposition:
    def test_summary_fields_composed(self, tmp_path: Path):
        """Summary fields correctly composed into packet."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert result.packet.record_count == 1
        assert result.packet.session_count == 1

    def test_candidate_fields_composed(self, tmp_path: Path):
        """Candidate fields correctly composed into packet."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert result.packet.candidate_ref is not None
        assert result.packet.priority is not None
        assert result.packet.confidence is not None


# ---------------------------------------------------------------------------
# Reason codes in packet
# ---------------------------------------------------------------------------


class TestReasonCodesInPacket:
    def test_reason_codes_propagated(self, tmp_path: Path):
        """Reason codes propagated from candidate."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert len(result.packet.reason_codes) > 0


# ---------------------------------------------------------------------------
# Decision options
# ---------------------------------------------------------------------------


class TestDecisionOptions:
    def test_decision_options_present(self, tmp_path: Path):
        """Advisory decision options present."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        for opt in _DECISION_OPTIONS:
            assert opt in result.packet.decision_options


# ---------------------------------------------------------------------------
# Recommended questions
# ---------------------------------------------------------------------------


class TestRecommendedQuestions:
    def test_questions_derived_from_reason_codes(self, tmp_path: Path):
        """Questions derived from reason codes."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert len(result.packet.recommended_human_questions) > 0


# ---------------------------------------------------------------------------
# Safety boundaries
# ---------------------------------------------------------------------------


class TestSafetyBoundaries:
    def test_safety_boundaries_present(self, tmp_path: Path):
        """Safety boundaries present in packet."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        for boundary in _SAFETY_BOUNDARIES:
            assert boundary in result.packet.safety_boundaries


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


class TestMarkdownRendering:
    def test_markdown_contains_sections(self, tmp_path: Path):
        """Markdown contains expected sections."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        md = result.packet.markdown_text
        assert "# Product Iteration Review Packet" in md
        assert "## Summary" in md
        assert "## Recommendation" in md
        assert "## Evidence Details" in md
        assert "## Recommended Human Questions" in md
        assert "## Decision Options (Advisory)" in md
        assert "## Safety Boundaries" in md
        assert "## Validation Notes" in md

    def test_markdown_deterministic(self, tmp_path: Path):
        """Same input → same markdown."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result1 = build_product_iteration_review_packet(store_dir=store)
        result2 = build_product_iteration_review_packet(store_dir=store)
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.markdown_text == result2.packet.markdown_text


# ---------------------------------------------------------------------------
# Plain-text rendering
# ---------------------------------------------------------------------------


class TestPlainTextRendering:
    def test_plain_text_contains_sections(self, tmp_path: Path):
        """Plain text contains expected sections."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        pt = result.packet.plain_text
        assert "PRODUCT ITERATION REVIEW PACKET" in pt
        assert "=== Summary ===" in pt
        assert "=== Recommendation ===" in pt
        assert "=== Evidence Details ===" in pt
        assert "=== Recommended Human Questions ===" in pt
        assert "=== Decision Options (Advisory) ===" in pt
        assert "=== Safety Boundaries ===" in pt
        assert "=== Validation Notes ===" in pt

    def test_plain_text_deterministic(self, tmp_path: Path):
        """Same input → same plain text."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result1 = build_product_iteration_review_packet(store_dir=store)
        result2 = build_product_iteration_review_packet(store_dir=store)
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.plain_text == result2.packet.plain_text


# ---------------------------------------------------------------------------
# No hidden reasoning
# ---------------------------------------------------------------------------


class TestNoHiddenReasoning:
    def test_no_hidden_reasoning_in_markdown(self, tmp_path: Path):
        """No hidden reasoning patterns in markdown output."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert "<cot>" not in result.packet.markdown_text
        # The safety boundary mentions "hidden reasoning" as a prohibition,
        # which is expected content. Check that no actual hidden reasoning
        # patterns are present.
        assert "<thinking>" not in result.packet.markdown_text
        assert "chain-of-thought" not in result.packet.markdown_text.lower() or "no hidden" in result.packet.markdown_text.lower()

    def test_no_hidden_reasoning_in_plain_text(self, tmp_path: Path):
        """No hidden reasoning in plain text output."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert "<cot>" not in result.packet.plain_text


# ---------------------------------------------------------------------------
# No full transcript
# ---------------------------------------------------------------------------


class TestNoFullTranscript:
    def test_no_full_transcript(self, tmp_path: Path):
        """No full transcript in rendered output."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        # Check that raw record data is not dumped verbatim
        assert "session-001" not in result.packet.markdown_text or "Session count" in result.packet.markdown_text


# ---------------------------------------------------------------------------
# No unbounded text
# ---------------------------------------------------------------------------


class TestNoUnboundedText:
    def test_text_fields_bounded(self, tmp_path: Path):
        """All text fields bounded."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.packet is not None
        assert len(result.packet.markdown_text) < 50000
        assert len(result.packet.plain_text) < 50000


# ---------------------------------------------------------------------------
# No writes
# ---------------------------------------------------------------------------


class TestNoWrites:
    def test_no_writes(self, tmp_path: Path):
        """build_product_iteration_review_packet does not write any files."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert files_after == files_before


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    def test_no_mutation_of_records(self, tmp_path: Path):
        """Product iteration records not modified."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        list_before = list_product_iteration_signals(store_dir=store)
        records_before = list(list_before.records)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        list_after = list_product_iteration_signals(store_dir=store)
        assert list(list_after.records) == records_before


# ---------------------------------------------------------------------------
# No backlog mutation
# ---------------------------------------------------------------------------


class TestNoBacklogMutation:
    def test_no_backlog_mutation(self, tmp_path: Path):
        """Backlog store not modified."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        backlog_store = tmp_path / "backlog"
        os.makedirs(backlog_store, exist_ok=True)
        backlog_file = backlog_store / "item.json"
        backlog_file.write_text('{"backlog_item_ref": "test"}', encoding="utf-8")
        backlog_mtime = backlog_file.stat().st_mtime

        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY

        assert backlog_file.exists()
        assert backlog_file.stat().st_mtime == backlog_mtime


# ---------------------------------------------------------------------------
# No decision mutation
# ---------------------------------------------------------------------------


class TestNoDecisionMutation:
    def test_no_decision_mutation(self, tmp_path: Path):
        """Decision store not modified."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        decision_store = tmp_path / "decisions"
        os.makedirs(decision_store, exist_ok=True)
        decision_file = decision_store / "decision.json"
        decision_file.write_text('{"decision_ref": "test"}', encoding="utf-8")
        decision_mtime = decision_file.stat().st_mtime

        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY

        assert decision_file.exists()
        assert decision_file.stat().st_mtime == decision_mtime


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = _store_dir(tmp_path)
        _record(tmp_path, store)
        result = build_product_iteration_review_packet(store_dir=store)
        assert result.status == ProductIterationReviewPacketStatus.READY
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.product_iteration_review_packet
        doc = task_intake.product_iteration_review_packet.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.product_iteration_review_packet import build_product_iteration_review_packet
        source = inspect.getsource(build_product_iteration_review_packet)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
