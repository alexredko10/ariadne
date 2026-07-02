"""Tests for the read-only self-improvement backlog surfacing layer."""

from __future__ import annotations

import json
import os
from pathlib import Path

from runner.backlog_surface import (
    BacklogSurfaceInput,
    BacklogSurfaceView,
    BacklogSurfaceResult,
    BacklogSurfaceStatus,
    build_backlog_surface,
    REASON_MISSING_BACKLOG_STORE,
    REASON_BACKLOG_STORE_NOT_DIRECTORY,
    REASON_UNBOUNDED_BACKLOG_STORE_PATH,
    REASON_UNREADABLE_BACKLOG_ITEM,
    REASON_MALFORMED_BACKLOG_ITEM_JSON,
    REASON_DUPLICATE_BACKLOG_ITEM_REF,
    REASON_UNSUPPORTED_BACKLOG_STATUS,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_MUTATION_NOT_ALLOWED,
    REASON_ARCHIVE_NOT_ALLOWED,
    REASON_APPROVAL_NOT_ALLOWED,
    REASON_GATE_FINALIZATION_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_OVERSIZED_BACKLOG_VIEW,
)
from runner.improvement_backlog import (
    BacklogItemInput,
    BacklogStatus,
    enqueue_backlog_item,
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
        "session_label": "PR 0110 backlog item",
    }
    kwargs.update(overrides)
    return BacklogItemInput(**kwargs)  # type: ignore[arg-type]


def _store_dir(tmp_path: Path, name: str = "store") -> str:
    """Return a unique backlog store directory path."""
    return str(tmp_path / name)


def _enqueue_item(tmp_path: Path, store: str, **overrides: object) -> str:
    """Enqueue a backlog item and return its ref."""
    inp = _valid_input(**overrides)
    result = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
    assert result.status == "enqueued", f"reason_codes={result.reason_codes}"
    assert result.backlog_item is not None
    return result.backlog_item.backlog_item_ref


# ---------------------------------------------------------------------------
# Empty backlog store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store_returns_empty(self, tmp_path: Path):
        """Empty backlog store → EMPTY, zero totals."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.EMPTY
        assert result.surface_view is not None
        assert result.surface_view.total_count == 0
        assert result.surface_view.summary["total"] == 0
        assert result.surface_view.items == ()
        assert result.surface_view.drift_risk_items == ()
        assert result.surface_view.ready_for_review_items == ()


# ---------------------------------------------------------------------------
# Missing backlog store
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store_rejected(self, tmp_path: Path):
        """Missing backlog store → REJECTED with REASON_MISSING_BACKLOG_STORE."""
        store = _store_dir(tmp_path, "nonexistent")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_MISSING_BACKLOG_STORE in result.reason_codes


# ---------------------------------------------------------------------------
# Backlog store is a file, not directory
# ---------------------------------------------------------------------------


class TestStoreNotDirectory:
    def test_store_is_file_rejected(self, tmp_path: Path):
        """Backlog store path is a file → REJECTED with REASON_BACKLOG_STORE_NOT_DIRECTORY."""
        store = _store_dir(tmp_path, "not_a_dir")
        Path(store).write_text("not a directory", encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_BACKLOG_STORE_NOT_DIRECTORY in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded backlog store path
# ---------------------------------------------------------------------------


class TestUnboundedPath:
    def test_unbounded_path_rejected(self, tmp_path: Path):
        """Path with .. → REJECTED with REASON_UNBOUNDED_BACKLOG_STORE_PATH."""
        inp = BacklogSurfaceInput(backlog_store_dir="../etc/passwd")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_UNBOUNDED_BACKLOG_STORE_PATH in result.reason_codes

    def test_absolute_path_with_traversal_rejected(self, tmp_path: Path):
        """Absolute path with .. traversal → REJECTED with REASON_UNBOUNDED_BACKLOG_STORE_PATH."""
        inp = BacklogSurfaceInput(backlog_store_dir="/tmp/../etc/passwd")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_UNBOUNDED_BACKLOG_STORE_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Valid backlog items
# ---------------------------------------------------------------------------


class TestValidItems:
    def test_valid_items_ready(self, tmp_path: Path):
        """Valid backlog items → READY, items included in view."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store)
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.total_count >= 1
        assert len(result.surface_view.items) >= 1

    def test_item_fields_in_view(self, tmp_path: Path):
        """Item dict includes all required fields."""
        store = _store_dir(tmp_path)
        ref = _enqueue_item(tmp_path, store)
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        item = result.surface_view.items[0]
        assert item["backlog_item_ref"] == ref
        assert item["candidate_ref"] == "candidate-abc123"
        assert item["continuity_ref"] == "continuity-def456"
        assert item["product_state_ref"] == "abc123"
        assert item["source_reason_codes"] == ["missing_proof_refs"]
        assert item["evidence_refs"] == ["capture-text-abc123def456", "pr-001"]
        assert item["improvement_category"] == "self_improvement"
        assert item["next_safe_action"] == "Review and merge the improvement candidate"
        assert item["blocked_actions"] == ["Waiting for PR 0108 merge"]
        assert item["drift_risks"] == ["Scope must not include frontend"]
        assert item["requires_human_review"] is True
        assert item["status"] == "new"
        assert item["phase_id"] == "phase-1"
        assert item["run_id"] == "run-001"
        assert item["session_label"] == "PR 0110 backlog item"
        assert item["created_at"] is None
        assert item["archived_at"] is None


# ---------------------------------------------------------------------------
# Deterministic sorting
# ---------------------------------------------------------------------------


class TestSorting:
    def test_items_sorted_by_ref(self, tmp_path: Path):
        """Items sorted deterministically by backlog_item_ref."""
        store = _store_dir(tmp_path)
        refs = []
        for i in range(3):
            ref = _enqueue_item(tmp_path, store, candidate_ref=f"candidate-{i:03d}")
            refs.append(ref)
        refs.sort()
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        item_refs = [item["backlog_item_ref"] for item in result.surface_view.items]
        assert item_refs == sorted(item_refs)


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------


class TestSummaryCounts:
    def test_summary_counts_correct(self, tmp_path: Path):
        """Summary counts by status and category are correct."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store, improvement_category="self_improvement")
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-drift",
            improvement_category="drift_risk",
            drift_risks=("Scope creep",),
        )
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        summary = result.surface_view.summary
        assert summary["total"] == 2
        assert summary["by_status"]["new"] == 2
        assert summary["by_category"]["self_improvement"] == 1
        assert summary["by_category"]["drift_risk"] == 1


# ---------------------------------------------------------------------------
# Human review required count
# ---------------------------------------------------------------------------


class TestHumanReviewCount:
    def test_human_review_required_count(self, tmp_path: Path):
        """human_review_required_count matches items with requires_human_review=True."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store, requires_human_review=True)
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-review",
            requires_human_review=True,
        )
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.human_review_required_count == 2


# ---------------------------------------------------------------------------
# Drift risk items
# ---------------------------------------------------------------------------


class TestDriftRiskItems:
    def test_drift_risk_items(self, tmp_path: Path):
        """drift_risk_items contains items with non-empty drift_risks."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store, drift_risks=("Scope creep", "Missing tests"))
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-drift",
            drift_risks=(),
        )
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert len(result.surface_view.drift_risk_items) == 1
        drift_item = result.surface_view.drift_risk_items[0]
        assert "drift_risks" in drift_item
        assert drift_item["drift_risks"] == ["Missing tests", "Scope creep"]


# ---------------------------------------------------------------------------
# Ready for review items
# ---------------------------------------------------------------------------


class TestReadyForReview:
    def test_ready_for_review_items(self, tmp_path: Path):
        """ready_for_review_items contains refs where status=new and requires_human_review=True."""
        store = _store_dir(tmp_path)
        ref1 = _enqueue_item(tmp_path, store, requires_human_review=True)
        ref2 = _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-review",
            requires_human_review=True,
        )
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert ref1 in result.surface_view.ready_for_review_items
        assert ref2 in result.surface_view.ready_for_review_items


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


class TestStatusFilter:
    def test_status_filter_works(self, tmp_path: Path):
        """Status filter returns only items with matching status."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store)
        inp = BacklogSurfaceInput(backlog_store_dir=store, status_filter="new")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.total_count >= 1

    def test_status_filter_no_match(self, tmp_path: Path):
        """Status filter with no matches → EMPTY."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store)
        inp = BacklogSurfaceInput(backlog_store_dir=store, status_filter="archived")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.EMPTY
        assert result.surface_view is not None
        assert result.surface_view.total_count == 0


# ---------------------------------------------------------------------------
# Category filter
# ---------------------------------------------------------------------------


class TestCategoryFilter:
    def test_category_filter_works(self, tmp_path: Path):
        """Category filter returns only items with matching category."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store, improvement_category="self_improvement")
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-drift",
            improvement_category="drift_risk",
        )
        inp = BacklogSurfaceInput(backlog_store_dir=store, category_filter="self_improvement")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.total_count == 1
        assert result.surface_view.items[0]["improvement_category"] == "self_improvement"

    def test_category_filter_no_match(self, tmp_path: Path):
        """Category filter with no matches → EMPTY."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store, improvement_category="self_improvement")
        inp = BacklogSurfaceInput(backlog_store_dir=store, category_filter="validation_gap")
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.EMPTY


# ---------------------------------------------------------------------------
# Max items limit
# ---------------------------------------------------------------------------


class TestMaxItems:
    def test_max_items_limit_enforced(self, tmp_path: Path):
        """max_items limit restricts number of items in view."""
        store = _store_dir(tmp_path)
        for i in range(5):
            _enqueue_item(tmp_path, store, candidate_ref=f"candidate-{i:03d}")
        inp = BacklogSurfaceInput(backlog_store_dir=store, max_items=2)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.total_count == 2
        assert len(result.surface_view.items) == 2


# ---------------------------------------------------------------------------
# Malformed item JSON
# ---------------------------------------------------------------------------


class TestMalformedItem:
    def test_malformed_item_handled(self, tmp_path: Path):
        """Malformed item JSON in store is skipped (list_backlog handles it)."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store)
        # Write a malformed JSON file directly to the store
        bad_file = Path(store) / "bad_item.json"
        bad_file.write_text("{invalid json}", encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        # list_backlog skips malformed files, so valid items still load
        assert result.status == BacklogSurfaceStatus.READY
        assert result.surface_view is not None
        assert result.surface_view.total_count >= 1


# ---------------------------------------------------------------------------
# Duplicate backlog_item_ref
# ---------------------------------------------------------------------------


class TestDuplicateRef:
    def test_duplicate_ref_rejected(self, tmp_path: Path):
        """Duplicate backlog_item_ref → REJECTED with REASON_DUPLICATE_BACKLOG_ITEM_REF."""
        store = _store_dir(tmp_path)
        ref = _enqueue_item(tmp_path, store)
        # Copy the same file with a different name but same content (same ref)
        src = Path(store) / f"{ref}.json"
        dst = Path(store) / f"{ref}_copy.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_DUPLICATE_BACKLOG_ITEM_REF in result.reason_codes


# ---------------------------------------------------------------------------
# Unsupported status
# ---------------------------------------------------------------------------


class TestUnsupportedStatus:
    def test_unsupported_status_rejected(self, tmp_path: Path):
        """Item with unsupported status → REJECTED with REASON_UNSUPPORTED_BACKLOG_STATUS."""
        store = _store_dir(tmp_path)
        ref = _enqueue_item(tmp_path, store)
        # Overwrite the store file with an invalid status
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["status"] = "invalid_status_value"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_UNSUPPORTED_BACKLOG_STATUS in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_rejected(self, tmp_path: Path):
        """Item with hidden reasoning → REJECTED with REASON_HIDDEN_REASONING_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "Some text <cot> hidden"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only evidence
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_external_url_only_rejected(self, tmp_path: Path):
        """Item with URL-only evidence → REJECTED with REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["evidence_refs"] = ["http://example.com/evidence"]
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Mutation not allowed
# ---------------------------------------------------------------------------


class TestMutationNotAllowed:
    def test_mutation_not_allowed(self, tmp_path: Path):
        """Item with mutation request → REJECTED with REASON_MUTATION_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "accept the changes"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_MUTATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Archive not allowed
# ---------------------------------------------------------------------------


class TestArchiveNotAllowed:
    def test_archive_not_allowed(self, tmp_path: Path):
        """Item with archive request → REJECTED with REASON_ARCHIVE_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "archive this item"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_ARCHIVE_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Approval not allowed
# ---------------------------------------------------------------------------


class TestApprovalNotAllowed:
    def test_approval_not_allowed(self, tmp_path: Path):
        """Item with approval request → REJECTED with REASON_APPROVAL_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "approve the gate"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_APPROVAL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Gate finalization not allowed
# ---------------------------------------------------------------------------


class TestGateFinalizationNotAllowed:
    def test_gate_finalization_not_allowed(self, tmp_path: Path):
        """Item with gate finalization request → REJECTED with REASON_GATE_FINALIZATION_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "finalize the gate"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_GATE_FINALIZATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Command execution not allowed
# ---------------------------------------------------------------------------


class TestCommandExecutionNotAllowed:
    def test_command_execution_not_allowed(self, tmp_path: Path):
        """Item with command execution request → REJECTED with REASON_COMMAND_EXECUTION_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "subprocess.run('ls')"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_COMMAND_EXECUTION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Provider call not allowed
# ---------------------------------------------------------------------------


class TestProviderCallNotAllowed:
    def test_provider_call_not_allowed(self, tmp_path: Path):
        """Item with provider call request → REJECTED with REASON_PROVIDER_CALL_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "import openai to fix this"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_PROVIDER_CALL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Git mutation not allowed
# ---------------------------------------------------------------------------


class TestGitMutationNotAllowed:
    def test_git_mutation_not_allowed(self, tmp_path: Path):
        """Item with git mutation request → REJECTED with REASON_GIT_MUTATION_NOT_ALLOWED."""
        store = _store_dir(tmp_path)
        # Write item directly to store (enqueue would reject it)
        ref = _enqueue_item(tmp_path, store)
        store_file = Path(store) / f"{ref}.json"
        data = json.loads(store_file.read_text(encoding="utf-8"))
        data["next_safe_action"] = "git commit -m 'fix'"
        store_file.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.REJECTED
        assert REASON_GIT_MUTATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem writes
# ---------------------------------------------------------------------------


class TestNoFilesystemWrites:
    def test_no_filesystem_writes(self, tmp_path: Path):
        """build_backlog_surface does not write any files."""
        store = _store_dir(tmp_path)
        _enqueue_item(tmp_path, store)
        # Record files before surface build
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        inp = BacklogSurfaceInput(backlog_store_dir=store)
        result = build_backlog_surface(inp)
        assert result.status == BacklogSurfaceStatus.READY
        # Record files after surface build
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert files_after == files_before


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.backlog_surface
        doc = runner.backlog_surface.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.backlog_surface import build_backlog_surface
        source = inspect.getsource(build_backlog_surface)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
