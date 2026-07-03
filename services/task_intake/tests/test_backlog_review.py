"""Tests for the local human review backlog view (task_intake HTTP route).

Tests the ``build_backlog_review_json()`` function directly (synchronous)
and the ASGI route via synchronous helpers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from task_intake.backlog_review import (
    BacklogReviewInput,
    build_backlog_review_json,
)
from runner.backlog_surface import (
    REASON_MISSING_BACKLOG_STORE,
    REASON_DUPLICATE_BACKLOG_ITEM_REF,
)
from runner.improvement_backlog import (
    BacklogItemInput,
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
        "session_label": "PR 0111 backlog item",
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
# build_backlog_review_json — empty store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store_returns_empty(self, tmp_path: Path):
        """Empty backlog store → status empty, zero totals."""
        store = _store_dir(tmp_path, "empty")
        os.makedirs(store, exist_ok=True)
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "empty"
        assert result["read_only"] is True
        assert result["surface"]["total_count"] == 0
        assert result["surface"]["items"] == []


# ---------------------------------------------------------------------------
# build_backlog_review_json — missing store
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store_rejected(self, tmp_path: Path):
        """Missing backlog store → status rejected, missing_backlog_store."""
        store = _store_dir(tmp_path, "nonexistent")
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "rejected"
        assert result["read_only"] is True
        assert REASON_MISSING_BACKLOG_STORE in result["reason_codes"]


# ---------------------------------------------------------------------------
# build_backlog_review_json — valid store
# ---------------------------------------------------------------------------


class TestValidStore:
    def test_valid_store_returns_ready(self, tmp_path: Path):
        """Valid backlog store → status ready, read_only true, items."""
        store = _store_dir(tmp_path, "valid")
        _enqueue_item(tmp_path, store)
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert result["read_only"] is True
        assert "surface" in result
        assert result["surface"]["total_count"] >= 1
        assert len(result["surface"]["items"]) >= 1
        item = result["surface"]["items"][0]
        assert "backlog_item_ref" in item
        assert "candidate_ref" in item
        assert "continuity_ref" in item
        assert "evidence_refs" in item
        assert "improvement_category" in item
        assert "next_safe_action" in item
        assert "blocked_actions" in item
        assert "drift_risks" in item
        assert "requires_human_review" in item
        assert "status" in item


# ---------------------------------------------------------------------------
# build_backlog_review_json — status filter
# ---------------------------------------------------------------------------


class TestStatusFilter:
    def test_status_filter_works(self, tmp_path: Path):
        """Status filter returns only items with matching status."""
        store = _store_dir(tmp_path, "filter_status")
        _enqueue_item(tmp_path, store)
        inp = BacklogReviewInput(backlog_store_dir=store, status_filter="new")
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert result["surface"]["total_count"] >= 1

    def test_status_filter_no_match(self, tmp_path: Path):
        """Status filter with no matches → empty."""
        store = _store_dir(tmp_path, "filter_status_none")
        _enqueue_item(tmp_path, store)
        inp = BacklogReviewInput(backlog_store_dir=store, status_filter="archived")
        result = build_backlog_review_json(inp)
        assert result["status"] == "empty"


# ---------------------------------------------------------------------------
# build_backlog_review_json — category filter
# ---------------------------------------------------------------------------


class TestCategoryFilter:
    def test_category_filter_works(self, tmp_path: Path):
        """Category filter returns only items with matching category."""
        store = _store_dir(tmp_path, "filter_cat")
        _enqueue_item(tmp_path, store, improvement_category="self_improvement")
        inp = BacklogReviewInput(backlog_store_dir=store, category_filter="self_improvement")
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert result["surface"]["total_count"] == 1


# ---------------------------------------------------------------------------
# build_backlog_review_json — max_items
# ---------------------------------------------------------------------------


class TestMaxItems:
    def test_max_items_limit(self, tmp_path: Path):
        """max_items limit restricts number of items in view."""
        store = _store_dir(tmp_path, "max_items")
        for i in range(3):
            _enqueue_item(tmp_path, store, candidate_ref=f"candidate-{i:03d}")
        inp = BacklogReviewInput(backlog_store_dir=store, max_items=1)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert result["surface"]["total_count"] == 1
        assert len(result["surface"]["items"]) == 1


# ---------------------------------------------------------------------------
# Response always includes read_only: true
# ---------------------------------------------------------------------------


class TestReadOnlyFlag:
    def test_read_only_flag_present(self, tmp_path: Path):
        """Every response includes read_only: true."""
        store = _store_dir(tmp_path, "readonly_flag")
        os.makedirs(store, exist_ok=True)

        # Empty store
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["read_only"] is True

        # Valid store
        _enqueue_item(tmp_path, store)
        result = build_backlog_review_json(inp)
        assert result["read_only"] is True

        # Missing store
        inp2 = BacklogReviewInput(backlog_store_dir=_store_dir(tmp_path, "missing"))
        result2 = build_backlog_review_json(inp2)
        assert result2["read_only"] is True


# ---------------------------------------------------------------------------
# No mutation action fields
# ---------------------------------------------------------------------------


class TestNoMutationFields:
    def test_no_mutation_fields(self, tmp_path: Path):
        """Response does NOT include archive, accept, reject, approve, finalize action fields."""
        store = _store_dir(tmp_path, "no_mutation")
        _enqueue_item(tmp_path, store)
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert "archive" not in result
        assert "accept" not in result
        assert "reject" not in result
        assert "approve" not in result
        assert "finalize" not in result


# ---------------------------------------------------------------------------
# Malformed item in store
# ---------------------------------------------------------------------------


class TestMalformedItem:
    def test_malformed_item(self, tmp_path: Path):
        """Malformed item in store → valid items still load."""
        store = _store_dir(tmp_path, "malformed")
        _enqueue_item(tmp_path, store)
        # Write a malformed JSON file directly to the store
        bad_file = Path(store) / "bad_item.json"
        bad_file.write_text("{invalid json}", encoding="utf-8")
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        # list_backlog skips malformed files, so valid items still load
        assert result["status"] == "ready"
        assert result["surface"]["total_count"] >= 1


# ---------------------------------------------------------------------------
# Duplicate ref in store
# ---------------------------------------------------------------------------


class TestDuplicateRef:
    def test_duplicate_ref(self, tmp_path: Path):
        """Duplicate ref in store → rejection with duplicate_backlog_item_ref."""
        store = _store_dir(tmp_path, "duplicate")
        ref = _enqueue_item(tmp_path, store)
        # Copy the same file with a different name but same content (same ref)
        src = Path(store) / f"{ref}.json"
        dst = Path(store) / f"{ref}_copy.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "rejected"
        assert REASON_DUPLICATE_BACKLOG_ITEM_REF in result["reason_codes"]


# ---------------------------------------------------------------------------
# No filesystem writes
# ---------------------------------------------------------------------------


class TestNoFilesystemWrites:
    def test_no_filesystem_writes(self, tmp_path: Path):
        """build_backlog_review_json does not write any files."""
        store = _store_dir(tmp_path, "no_writes")
        _enqueue_item(tmp_path, store)
        # Record files before
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        # Record files after
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        assert files_after == files_before


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------


class TestSummaryCounts:
    def test_summary_counts(self, tmp_path: Path):
        """Summary counts by status and category are correct."""
        store = _store_dir(tmp_path, "summary")
        _enqueue_item(tmp_path, store, improvement_category="self_improvement")
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-drift",
            improvement_category="drift_risk",
            drift_risks=("Scope creep",),
        )
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        summary = result["surface"]["summary"]
        assert summary["total"] == 2
        assert summary["by_status"]["new"] == 2
        assert summary["by_category"]["self_improvement"] == 1
        assert summary["by_category"]["drift_risk"] == 1


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_items_sorted_by_ref(self, tmp_path: Path):
        """Items sorted deterministically by backlog_item_ref."""
        store = _store_dir(tmp_path, "ordering")
        refs = []
        for i in range(3):
            ref = _enqueue_item(tmp_path, store, candidate_ref=f"candidate-{i:03d}")
            refs.append(ref)
        refs.sort()
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        item_refs = [item["backlog_item_ref"] for item in result["surface"]["items"]]
        assert item_refs == sorted(item_refs)


# ---------------------------------------------------------------------------
# Human review required count
# ---------------------------------------------------------------------------


class TestHumanReviewCount:
    def test_human_review_required_count(self, tmp_path: Path):
        """human_review_required_count matches items with requires_human_review=True."""
        store = _store_dir(tmp_path, "human_review")
        _enqueue_item(tmp_path, store, requires_human_review=True)
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-review",
            requires_human_review=True,
        )
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert result["surface"]["human_review_required_count"] == 2


# ---------------------------------------------------------------------------
# Drift risk items
# ---------------------------------------------------------------------------


class TestDriftRiskItems:
    def test_drift_risk_items(self, tmp_path: Path):
        """drift_risk_items contains items with non-empty drift_risks."""
        store = _store_dir(tmp_path, "drift")
        _enqueue_item(tmp_path, store, drift_risks=("Scope creep", "Missing tests"))
        _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-drift",
            drift_risks=(),
        )
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert len(result["surface"]["drift_risk_items"]) == 1
        drift_item = result["surface"]["drift_risk_items"][0]
        assert "drift_risks" in drift_item
        assert drift_item["drift_risks"] == ["Missing tests", "Scope creep"]


# ---------------------------------------------------------------------------
# Ready for review items
# ---------------------------------------------------------------------------


class TestReadyForReview:
    def test_ready_for_review_items(self, tmp_path: Path):
        """ready_for_review_items contains refs where status=new and requires_human_review=True."""
        store = _store_dir(tmp_path, "ready")
        ref1 = _enqueue_item(tmp_path, store, requires_human_review=True)
        ref2 = _enqueue_item(
            tmp_path, store,
            candidate_ref="candidate-no-review",
            requires_human_review=True,
        )
        inp = BacklogReviewInput(backlog_store_dir=store)
        result = build_backlog_review_json(inp)
        assert result["status"] == "ready"
        assert ref1 in result["surface"]["ready_for_review_items"]
        assert ref2 in result["surface"]["ready_for_review_items"]


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.backlog_review
        doc = task_intake.backlog_review.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.backlog_review import build_backlog_review_json
        source = inspect.getsource(build_backlog_review_json)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
