"""Tests for the deterministic self-improvement backlog store."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.improvement_backlog import (
    BacklogItem,
    BacklogItemInput,
    BacklogResult,
    BacklogStatus,
    enqueue_backlog_item,
    list_backlog,
    archive_backlog_item,
    REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_DUPLICATE_CANDIDATE,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_INVALID_BACKLOG_ITEM,
    REASON_INVALID_BACKLOG_STATUS,
    REASON_MISSING_CANDIDATE_REF,
    REASON_MISSING_EVIDENCE_REFS,
    REASON_MISSING_HUMAN_REVIEW_BOUNDARY,
    REASON_MISSING_NEXT_SAFE_ACTION,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_OVERSIZED_BACKLOG_ITEM,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> BacklogItemInput:
    kwargs = {
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456",
        "product_state_ref": "abc123",
        "source_reason_codes": ("missing_proof_refs",),
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "improvement_category": "self_improvement",
        "next_safe_action": "Review and merge the improvement candidate",
        "blocked_actions": ("Waiting for PR 0108 merge",),
        "drift_risks": ("Scope must not include frontend",),
        "requires_human_review": True,
        "phase_id": "phase-1",
        "run_id": "run-001",
        "output_path": "backlog/item.json",
        "session_label": "PR 0109 backlog item",
    }
    kwargs.update(overrides)
    return BacklogItemInput(**kwargs)  # type: ignore[arg-type]


def _store_dir(tmp_path: Path, name: str = "store") -> str:
    """Return a unique backlog store directory path."""
    return str(tmp_path / name)


# ---------------------------------------------------------------------------
# Enqueue valid item
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_valid_item(self, tmp_path: Path):
        """Valid input → status=enqueued, item has backlog_item_ref."""
        inp = _valid_input()
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "enqueued", f"reason_codes={result.reason_codes}"
        assert result.reason_codes == ()
        assert result.backlog_item is not None
        assert result.backlog_item.backlog_item_ref is not None
        assert len(result.backlog_item.backlog_item_ref) == 16
        int(result.backlog_item.backlog_item_ref, 16)  # should not raise
        assert result.backlog_item.status == BacklogStatus.NEW.value
        assert result.backlog_item.created_at is None
        assert result.backlog_item.archived_at is None

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()

    def test_enqueue_same_input_twice_duplicate(self, tmp_path: Path):
        """Same input twice → status=duplicate."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        result1 = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        assert result1.status == "enqueued"

        result2 = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        assert result2.status == "duplicate"
        assert REASON_DUPLICATE_CANDIDATE in result2.reason_codes

    def test_different_candidate_ref_different_ref(self, tmp_path: Path):
        """Different candidate_ref produces different backlog_item_ref."""
        store = _store_dir(tmp_path)
        inp1 = _valid_input(candidate_ref="candidate-001")
        inp2 = _valid_input(candidate_ref="candidate-002")
        result1 = enqueue_backlog_item(inp1, backlog_store_dir=store, output_dir=str(tmp_path))
        result2 = enqueue_backlog_item(inp2, backlog_store_dir=store, output_dir=str(tmp_path / "other"))
        assert result1.backlog_item is not None
        assert result2.backlog_item is not None
        assert result1.backlog_item.backlog_item_ref != result2.backlog_item.backlog_item_ref

    def test_enqueue_deterministic_output_fields(self, tmp_path: Path):
        """Item includes all required output fields."""
        inp = _valid_input()
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "enqueued"
        item = result.backlog_item
        assert item is not None
        assert item.candidate_ref == "candidate-abc123"
        assert item.continuity_ref == "continuity-def456"
        assert item.product_state_ref == "abc123"
        assert item.source_reason_codes == ("missing_proof_refs",)
        assert item.evidence_refs == ("capture-text-abc123def456", "pr-001")
        assert item.improvement_category == "self_improvement"
        assert item.next_safe_action == "Review and merge the improvement candidate"
        assert item.blocked_actions == ("Waiting for PR 0108 merge",)
        assert item.drift_risks == ("Scope must not include frontend",)
        assert item.requires_human_review is True
        assert item.status == "new"
        assert item.phase_id == "phase-1"
        assert item.run_id == "run-001"
        assert item.session_label == "PR 0109 backlog item"

    def test_enqueue_artifact_json_deterministic(self, tmp_path: Path):
        """Same input produces identical JSON."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        result1 = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        result2 = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path / "other"))
        # Second should be duplicate
        assert result2.status == "duplicate"

        # Read first artifact
        art1 = json.loads((tmp_path / result1.artifact_path).read_text(encoding="utf-8"))
        # Read from backlog store
        store_file = os.path.join(store, f"{result1.backlog_item.backlog_item_ref}.json")
        art2 = json.loads(open(store_file, encoding="utf-8").read())
        assert art1 == art2


# ---------------------------------------------------------------------------
# List backlog
# ---------------------------------------------------------------------------


class TestList:
    def test_list_empty(self, tmp_path: Path):
        """List with no items returns empty list."""
        result = list_backlog(backlog_store_dir=_store_dir(tmp_path, "empty"))
        assert result.status == "listed"
        assert result.total_count == 0
        assert result.backlog_items == ()

    def test_list_after_enqueue(self, tmp_path: Path):
        """List after enqueue returns 1 item."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        result = list_backlog(backlog_store_dir=store)
        assert result.status == "listed"
        assert result.total_count >= 1

    def test_list_with_status_filter(self, tmp_path: Path):
        """List with status filter returns only matching items."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        result = list_backlog(backlog_store_dir=store, status_filter="new")
        assert result.status == "listed"
        assert result.total_count >= 1
        for item in result.backlog_items:
            assert item.status == "new"

    def test_list_with_non_matching_filter(self, tmp_path: Path):
        """List with non-matching filter returns empty."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        result = list_backlog(backlog_store_dir=store, status_filter="archived")
        assert result.status == "listed"
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Archive backlog
# ---------------------------------------------------------------------------


class TestArchive:
    def test_archive_new_to_archived(self, tmp_path: Path):
        """Archive changes status from new to archived."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enq = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        assert enq.backlog_item is not None
        ref = enq.backlog_item.backlog_item_ref
        result = archive_backlog_item(ref, target_status="archived", backlog_store_dir=store)
        assert result.status == "archived"
        assert result.backlog_item is not None
        assert result.backlog_item.status == "archived"

    def test_archive_new_to_rejected(self, tmp_path: Path):
        """Archive changes status from new to rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enq = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        assert enq.backlog_item is not None
        ref = enq.backlog_item.backlog_item_ref
        result = archive_backlog_item(ref, target_status="rejected", backlog_store_dir=store)
        assert result.status == "rejected"
        assert result.backlog_item is not None
        assert result.backlog_item.status == "rejected"

    def test_archive_invalid_transition(self, tmp_path: Path):
        """Archived → new is invalid."""
        store = _store_dir(tmp_path)
        inp = _valid_input()
        enq = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
        assert enq.backlog_item is not None
        ref = enq.backlog_item.backlog_item_ref
        # First archive
        archive_backlog_item(ref, target_status="archived", backlog_store_dir=store)
        # Try to go back to new
        result = archive_backlog_item(ref, target_status="new", backlog_store_dir=store)
        assert result.status == "rejected"
        assert REASON_INVALID_BACKLOG_STATUS in result.reason_codes

    def test_archive_nonexistent_ref(self):
        """Nonexistent ref → rejected."""
        result = archive_backlog_item("nonexistent-ref", target_status="archived")
        assert result.status == "rejected"
        assert REASON_INVALID_BACKLOG_ITEM in result.reason_codes


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_candidate_ref_fails(self, tmp_path: Path):
        inp = _valid_input(candidate_ref="")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_MISSING_CANDIDATE_REF in result.reason_codes

    def test_missing_product_state_ref_fails(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_evidence_refs_fails(self, tmp_path: Path):
        inp = _valid_input(evidence_refs=())
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_MISSING_EVIDENCE_REFS in result.reason_codes

    def test_missing_next_safe_action_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_MISSING_NEXT_SAFE_ACTION in result.reason_codes

    def test_missing_human_review_boundary_fails(self, tmp_path: Path):
        inp = _valid_input(requires_human_review=False)
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_MISSING_HUMAN_REVIEW_BOUNDARY in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="Some text <cot> hidden")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only evidence
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_external_url_only_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="http://example.com/evidence")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


class TestForbiddenActions:
    def test_autonomous_code_change_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="Run pip install requests")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED in result.reason_codes

    def test_git_mutation_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="Run git commit -m 'fix'")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_GIT_MUTATION_NOT_ALLOWED in result.reason_codes

    def test_provider_call_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="import openai to fix this")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_PROVIDER_CALL_NOT_ALLOWED in result.reason_codes

    def test_command_execution_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="subprocess.run('ls')")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_COMMAND_EXECUTION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_unbounded_output_path_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="../escape/item.json")
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized item
# ---------------------------------------------------------------------------


class TestOversizedItem:
    def test_oversized_item_fails(self, tmp_path: Path):
        long_action = "x" * 4097
        inp = _valid_input(next_safe_action=long_action)
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        assert REASON_OVERSIZED_BACKLOG_ITEM in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_write_when_rejected(self, tmp_path: Path):
        inp = _valid_input(candidate_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = enqueue_backlog_item(inp, backlog_store_dir=_store_dir(tmp_path), output_dir=str(tmp_path))
        assert result.status == "rejected"
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.improvement_backlog
        doc = runner.improvement_backlog.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The improvement_backlog source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(enqueue_backlog_item)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
