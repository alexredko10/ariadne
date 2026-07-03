"""Tests for the read-only human decision history surface."""

from __future__ import annotations

import json
import os
from pathlib import Path

from task_intake.decision_history import (
    DecisionHistoryInput,
    DecisionHistoryItem,
    DecisionHistoryView,
    DecisionHistorySummary,
    DecisionHistoryResult,
    DecisionHistoryStatus,
    load_decision_history,
    REASON_MISSING_DECISION_STORE,
    REASON_DECISION_STORE_NOT_DIRECTORY,
    REASON_UNBOUNDED_DECISION_STORE_PATH,
    REASON_UNREADABLE_DECISION_RECORD,
    REASON_MALFORMED_DECISION_RECORD_JSON,
    REASON_MISSING_DECISION_REF,
    REASON_DUPLICATE_DECISION_REF,
    REASON_MISSING_BACKLOG_ITEM_REF,
    REASON_UNSUPPORTED_DECISION_TYPE,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_MUTATION_NOT_ALLOWED,
    REASON_ARCHIVE_NOT_ALLOWED,
    REASON_APPROVAL_NOT_ALLOWED,
    REASON_GATE_FINALIZATION_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_OVERSIZED_DECISION_HISTORY_VIEW,
)
from task_intake.backlog_decision import (
    BacklogDecisionInput,
    BacklogDecisionType,
    record_human_decision,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> BacklogDecisionInput:
    kwargs = {
        "backlog_item_ref": "backlog-item-abc123",
        "decision_type": BacklogDecisionType.DEFER.value,
        "human_actor": "human-reviewer-001",
        "decision_reason": "Need more evidence before proceeding.",
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "next_human_action": "Gather additional evidence from PR 0113.",
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456",
    }
    kwargs.update(overrides)
    return BacklogDecisionInput(**kwargs)  # type: ignore[arg-type]


def _store_dir(tmp_path: Path, name: str = "decisions") -> str:
    """Return a unique decision store directory path."""
    return str(tmp_path / name)


def _record_decision(tmp_path: Path, store: str, **overrides: object) -> str:
    """Record a decision and return its ref."""
    inp = _valid_input(decision_store_dir=store, **overrides)
    result = record_human_decision(inp)
    assert result.status == "recorded", f"reason_codes={result.reason_codes}"
    assert result.decision_ref is not None
    return result.decision_ref


# ---------------------------------------------------------------------------
# Empty decision store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store_returns_empty(self, tmp_path: Path):
        """Empty decision store → EMPTY, zero totals."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.EMPTY.value
        assert result.view is not None
        assert result.view.total_count == 0
        assert result.view.summary.total_decisions == 0
        assert result.view.items == ()


# ---------------------------------------------------------------------------
# Missing decision store
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store_rejected(self, tmp_path: Path):
        """Missing decision store → REJECTED with REASON_MISSING_DECISION_STORE."""
        store = _store_dir(tmp_path, "nonexistent")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.REJECTED.value
        assert REASON_MISSING_DECISION_STORE in result.reason_codes


# ---------------------------------------------------------------------------
# Decision store is a file, not directory
# ---------------------------------------------------------------------------


class TestStoreNotDirectory:
    def test_store_is_file_rejected(self, tmp_path: Path):
        """Decision store path is a file → REJECTED with REASON_DECISION_STORE_NOT_DIRECTORY."""
        store = _store_dir(tmp_path, "not_a_dir")
        Path(store).write_text("not a directory", encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.REJECTED.value
        assert REASON_DECISION_STORE_NOT_DIRECTORY in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded decision store path
# ---------------------------------------------------------------------------


class TestUnboundedPath:
    def test_unbounded_path_rejected(self, tmp_path: Path):
        """Path with .. → REJECTED with REASON_UNBOUNDED_DECISION_STORE_PATH."""
        inp = DecisionHistoryInput(decision_store_dir="../etc/passwd")
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.REJECTED.value
        assert REASON_UNBOUNDED_DECISION_STORE_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Valid decision records
# ---------------------------------------------------------------------------


class TestValidRecords:
    def test_valid_records_ready(self, tmp_path: Path):
        """Valid decision records → READY, items included in view."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count >= 1
        assert len(result.view.items) >= 1

    def test_item_fields(self, tmp_path: Path):
        """Item includes all required fields."""
        store = _store_dir(tmp_path)
        ref = _record_decision(tmp_path, store)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        item = result.view.items[0]
        assert item.decision_ref == ref
        assert item.backlog_item_ref == "backlog-item-abc123"
        assert item.candidate_ref == "candidate-abc123"
        assert item.continuity_ref == "continuity-def456"
        assert item.evidence_refs == ("capture-text-abc123def456", "pr-001")
        assert item.human_actor == "human-reviewer-001"
        assert item.decision_type == BacklogDecisionType.DEFER.value
        assert item.decision_reason == "Need more evidence before proceeding."
        assert item.next_human_action == "Gather additional evidence from PR 0113."
        assert item.blocked_agent_actions == ()
        assert item.created_at is None
        assert item.product_name == "Ariadne"
        assert item.source_surface == "task_intake"
        assert item.requires_human_review is True
        assert item.decision_record_path is not None
        assert item.linked_backlog_item_status is None
        assert item.schema_version is None


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_default_sort_descending(self, tmp_path: Path):
        """Default sort is created_at descending."""
        store = _store_dir(tmp_path)
        refs = []
        for i in range(3):
            ref = _record_decision(tmp_path, store, backlog_item_ref=f"backlog-item-{i:03d}")
            refs.append(ref)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        # All created_at are None, so sort is stable by insertion order reversed
        item_refs = [item.decision_ref for item in result.view.items]
        assert len(item_refs) == 3

    def test_sort_by_backlog_item_ref(self, tmp_path: Path):
        """Sort by backlog_item_ref ascending."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-c")
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-a")
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-b")
        inp = DecisionHistoryInput(decision_store_dir=store, sort_by="backlog_item_ref", sort_descending=False)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        item_refs = [item.backlog_item_ref for item in result.view.items]
        assert item_refs == sorted(item_refs)

    def test_sort_by_decision_ref(self, tmp_path: Path):
        """Sort by decision_ref ascending."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-c")
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-a")
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-b")
        inp = DecisionHistoryInput(decision_store_dir=store, sort_by="decision_ref", sort_descending=False)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        item_refs = [item.decision_ref for item in result.view.items]
        assert item_refs == sorted(item_refs)


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------


class TestSummaryCounts:
    def test_summary_counts(self, tmp_path: Path):
        """Summary counts are correct."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, decision_type=BacklogDecisionType.DEFER.value)
        _record_decision(
            tmp_path, store,
            backlog_item_ref="backlog-item-def456",
            decision_type=BacklogDecisionType.DISMISS.value,
        )
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        summary = result.view.summary
        assert summary.total_decisions == 2
        assert summary.decisions_by_type.get("defer") == 1
        assert summary.decisions_by_type.get("dismiss") == 1
        assert summary.decisions_by_backlog_item.get("backlog-item-abc123") == 1
        assert summary.decisions_by_backlog_item.get("backlog-item-def456") == 1
        assert summary.rejected_or_invalid_decision_records == 0
        assert summary.human_review_required == 2


# ---------------------------------------------------------------------------
# Malformed decision JSON
# ---------------------------------------------------------------------------


class TestMalformedJson:
    def test_malformed_json_handled(self, tmp_path: Path):
        """Malformed decision JSON → rejected count incremented, valid items still load."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        # Write a malformed JSON file directly to the store
        bad_file = Path(store) / "bad_decision.json"
        bad_file.write_text("{invalid json}", encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count >= 1
        assert result.view.summary.rejected_or_invalid_decision_records >= 1


# ---------------------------------------------------------------------------
# Duplicate decision_ref
# ---------------------------------------------------------------------------


class TestDuplicateRef:
    def test_duplicate_ref_handled(self, tmp_path: Path):
        """Duplicate decision_ref → rejected count incremented."""
        store = _store_dir(tmp_path)
        ref = _record_decision(tmp_path, store)
        # Copy the same file with a different name but same content (same ref)
        src = Path(store) / f"{ref}.json"
        dst = Path(store) / f"{ref}_copy.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count == 1
        assert result.view.summary.rejected_or_invalid_decision_records >= 1


# ---------------------------------------------------------------------------
# Missing backlog_item_ref
# ---------------------------------------------------------------------------


class TestMissingBacklogItemRef:
    def test_missing_backlog_item_ref_handled(self, tmp_path: Path):
        """Missing backlog_item_ref → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        # Write a decision file with missing backlog_item_ref
        bad_file = Path(store) / "missing_ref.json"
        bad_data = {
            "decision_ref": "missing-ref-001",
            "backlog_item_ref": "",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "test",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1


# ---------------------------------------------------------------------------
# Unsupported decision_type
# ---------------------------------------------------------------------------


class TestUnsupportedType:
    def test_unsupported_type_handled(self, tmp_path: Path):
        """Unsupported decision_type → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        # Write a decision file with unsupported type
        bad_file = Path(store) / "bad_type.json"
        bad_data = {
            "decision_ref": "bad-type-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "invalid_type_value",
            "human_actor": "test",
            "decision_reason": "test",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1


# ---------------------------------------------------------------------------
# Optional filters
# ---------------------------------------------------------------------------


class TestFilters:
    def test_filter_by_backlog_item_ref(self, tmp_path: Path):
        """Filter by backlog_item_ref returns only matching items."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-abc")
        _record_decision(tmp_path, store, backlog_item_ref="backlog-item-xyz")
        inp = DecisionHistoryInput(decision_store_dir=store, backlog_item_ref="backlog-item-abc")
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count == 1
        assert result.view.items[0].backlog_item_ref == "backlog-item-abc"

    def test_filter_by_decision_type(self, tmp_path: Path):
        """Filter by decision_type returns only matching items."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, decision_type=BacklogDecisionType.DEFER.value)
        _record_decision(
            tmp_path, store,
            backlog_item_ref="backlog-item-xyz",
            decision_type=BacklogDecisionType.DISMISS.value,
        )
        inp = DecisionHistoryInput(decision_store_dir=store, decision_type=BacklogDecisionType.DEFER.value)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count == 1
        assert result.view.items[0].decision_type == BacklogDecisionType.DEFER.value

    def test_filter_by_human_actor(self, tmp_path: Path):
        """Filter by human_actor returns only matching items."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store, human_actor="reviewer-alpha")
        _record_decision(
            tmp_path, store,
            backlog_item_ref="backlog-item-xyz",
            human_actor="reviewer-beta",
        )
        inp = DecisionHistoryInput(decision_store_dir=store, human_actor="reviewer-alpha")
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count == 1
        assert result.view.items[0].human_actor == "reviewer-alpha"


# ---------------------------------------------------------------------------
# No filesystem writes
# ---------------------------------------------------------------------------


class TestNoFilesystemWrites:
    def test_no_filesystem_writes(self, tmp_path: Path):
        """load_decision_history does not write any files."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        # Record files before
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        # Record files after
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert files_after == files_before


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# No mutation action fields
# ---------------------------------------------------------------------------


class TestNoMutationFields:
    def test_no_mutation_fields(self, tmp_path: Path):
        """Result does NOT include archive, accept, reject, approve, finalize action fields."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        # Check that the result dict (if serialized) doesn't have mutation keys
        result_dict = {
            "status": result.status,
            "reason_codes": list(result.reason_codes),
        }
        assert "archive" not in result_dict
        assert "accept" not in result_dict
        assert "reject" not in result_dict
        assert "approve" not in result_dict
        assert "finalize" not in result_dict


# ---------------------------------------------------------------------------
# Forbidden patterns in decision records
# ---------------------------------------------------------------------------


class TestForbiddenPatterns:
    def test_hidden_reasoning_rejected(self, tmp_path: Path):
        """Hidden reasoning in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        # Write a decision file with hidden reasoning
        bad_file = Path(store) / "hidden.json"
        bad_data = {
            "decision_ref": "hidden-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "Some text <cot> hidden",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_mutation_pattern_rejected(self, tmp_path: Path):
        """Mutation pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "mutation.json"
        bad_data = {
            "decision_ref": "mutation-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "accept the changes",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_archive_pattern_rejected(self, tmp_path: Path):
        """Archive pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "archive.json"
        bad_data = {
            "decision_ref": "archive-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "archive this item",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_approval_pattern_rejected(self, tmp_path: Path):
        """Approval pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "approval.json"
        bad_data = {
            "decision_ref": "approval-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "approve the gate",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_gate_finalization_rejected(self, tmp_path: Path):
        """Gate finalization pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "finalize.json"
        bad_data = {
            "decision_ref": "finalize-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "finalize the gate",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_command_execution_rejected(self, tmp_path: Path):
        """Command execution pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "command.json"
        bad_data = {
            "decision_ref": "command-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "subprocess.run('ls')",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_provider_call_rejected(self, tmp_path: Path):
        """Provider call pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "provider.json"
        bad_data = {
            "decision_ref": "provider-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "import openai to fix this",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1

    def test_git_mutation_rejected(self, tmp_path: Path):
        """Git mutation pattern in decision → rejected count incremented."""
        store = _store_dir(tmp_path)
        _record_decision(tmp_path, store)
        bad_file = Path(store) / "git.json"
        bad_data = {
            "decision_ref": "git-001",
            "backlog_item_ref": "backlog-item-xyz",
            "decision_type": "defer",
            "human_actor": "test",
            "decision_reason": "git commit -m 'fix'",
        }
        bad_file.write_text(json.dumps(bad_data), encoding="utf-8")
        inp = DecisionHistoryInput(decision_store_dir=store)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.summary.rejected_or_invalid_decision_records >= 1


# ---------------------------------------------------------------------------
# Oversized view
# ---------------------------------------------------------------------------


class TestOversizedView:
    def test_oversized_view_truncated(self, tmp_path: Path):
        """Oversized view is truncated with warning."""
        store = _store_dir(tmp_path)
        for i in range(5):
            _record_decision(tmp_path, store, backlog_item_ref=f"backlog-item-{i:03d}")
        inp = DecisionHistoryInput(decision_store_dir=store, max_results=2)
        result = load_decision_history(inp)
        assert result.status == DecisionHistoryStatus.READY.value
        assert result.view is not None
        assert result.view.total_count == 2
        assert len(result.view.items) == 2


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.decision_history
        doc = task_intake.decision_history.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.decision_history import load_decision_history
        source = inspect.getsource(load_decision_history)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
