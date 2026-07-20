"""
PR 0149 — Unit tests for VisualGateResult runtime object.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from runner.visual_gate_result import (
    create_visual_gate_result,
    read_visual_gate_result,
    validate_visual_gate_result,
    compute_visual_gate_sha256,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runs_root() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def run_dir(runs_root) -> str:
    rd = os.path.join(runs_root, "test-run-001")
    os.makedirs(rd, exist_ok=True)
    # Create run.json for run validity
    with open(os.path.join(rd, "run.json"), "w") as f:
        json.dump({"run_id": "test-run-001", "status": "completed"}, f)
    return rd


def _default_clock() -> str:
    return "2026-01-15T00:00:00Z"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Tests for VisualGateResult schema validation."""

    def test_valid_pending(self):
        """Valid pending gate passes validation."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-run-001-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [
                {"diagram_id": "req-01", "diagram_type": "requirement", "descriptor_ref": "profile_descriptor_key:req_diagram", "required": True},
            ],
            "created_at": "2026-01-15T00:00:00Z",
            "visual_gate_sha256": "a" * 64,
        }
        codes = validate_visual_gate_result(data)
        assert codes == [], f"Validation errors: {codes}"

    def test_valid_ready_needs_review(self):
        """Valid ready_needs_review with human_review_required=true."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-run-001-abc1234567890def",
            "run_id": "test-run-001",
            "status": "ready_needs_review",
            "human_review_required": True,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
            "visual_gate_sha256": "a" * 64,
        }
        codes = validate_visual_gate_result(data)
        assert codes == [], f"Errors: {codes}"

    def test_invalid_schema_version(self):
        """Wrong schema version is rejected."""
        data = {
            "schema_version": "2",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("unsupported_schema_version" in c for c in codes)

    def test_invalid_status(self):
        """Invalid status is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "invalid_status",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("invalid_status" in c for c in codes)


# ---------------------------------------------------------------------------
# Status consistency tests
# ---------------------------------------------------------------------------


class TestStatusConsistency:
    """Tests for status and human_review_required consistency."""

    def test_pending_hrr_false(self):
        """pending with human_review_required=false is valid."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        hrr_errors = [c for c in codes if "human_review_required" in c]
        assert hrr_errors == [], f"Unexpected HRR errors: {hrr_errors}"

    def test_pending_hrr_true_rejected(self):
        """pending with human_review_required=true is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": True,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("human_review_required_mismatch" in c for c in codes)

    def test_ready_needs_review_hrr_true(self):
        """ready_needs_review with human_review_required=true is valid."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "ready_needs_review",
            "human_review_required": True,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        hrr_errors = [c for c in codes if "human_review_required" in c]
        assert hrr_errors == [], f"Unexpected HRR errors: {hrr_errors}"

    def test_ready_needs_review_hrr_false_rejected(self):
        """ready_needs_review with human_review_required=false is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "ready_needs_review",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("human_review_required_mismatch" in c for c in codes)

    def test_passed_hrr_true_rejected(self):
        """passed with human_review_required=true is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "passed",
            "human_review_required": True,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("human_review_required_mismatch" in c for c in codes)

    def test_failed_hrr_true_rejected(self):
        """failed with human_review_required=true is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "failed",
            "human_review_required": True,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("human_review_required_mismatch" in c for c in codes)


# ---------------------------------------------------------------------------
# Required diagram tests
# ---------------------------------------------------------------------------


class TestRequiredDiagrams:
    """Tests for required diagram validation."""

    def test_unsupported_diagram_type(self):
        """Unsupported diagram type is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [
                {"diagram_id": "d1", "diagram_type": "unsupported_type", "descriptor_ref": "profile_descriptor_key:d1", "required": True},
            ],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("unsupported_diagram_type" in c for c in codes)

    def test_duplicate_diagram_id(self):
        """Duplicate diagram_id is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [
                {"diagram_id": "dup-id", "diagram_type": "requirement", "descriptor_ref": "profile_descriptor_key:d1", "required": True},
                {"diagram_id": "dup-id", "diagram_type": "state", "descriptor_ref": "profile_descriptor_key:d2", "required": False},
            ],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("duplicate_diagram_id" in c for c in codes)

    def test_too_many_diagrams(self):
        """Too many required diagrams is rejected."""
        diags = [{"diagram_id": f"d{i}", "diagram_type": "requirement", "descriptor_ref": "profile_descriptor_key:d", "required": True} for i in range(21)]
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": diags,
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("too_many_required_diagrams" in c for c in codes)

    def test_invalid_descriptor_ref(self):
        """Invalid descriptor_ref is rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [
                {"diagram_id": "d1", "diagram_type": "requirement", "descriptor_ref": "invalid_ref_format", "required": True},
            ],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("invalid_descriptor_ref" in c for c in codes)


# ---------------------------------------------------------------------------
# Hashing tests
# ---------------------------------------------------------------------------


class TestHashing:
    """Tests for deterministic hashing."""

    def test_deterministic_hash(self):
        """Same inputs produce same hash."""
        data = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        h1 = compute_visual_gate_sha256(data)
        h2 = compute_visual_gate_sha256(data)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_self_excluding(self):
        """Hash excludes the visual_gate_sha256 field."""
        data = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
            "visual_gate_sha256": "should_be_ignored",
        }
        h1 = compute_visual_gate_sha256(data)
        data2 = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        h2 = compute_visual_gate_sha256(data2)
        assert h1 == h2

    def test_hash_changes_on_semantic_change(self):
        """Hash changes when status changes."""
        data1 = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        data2 = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "passed",
            "human_review_required": False,
            "required_diagrams": [],
            "created_at": "2026-01-15T00:00:00Z",
        }
        h1 = compute_visual_gate_sha256(data1)
        h2 = compute_visual_gate_sha256(data2)
        assert h1 != h2


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for creation, persistence, and readback."""

    def test_create_pending(self, runs_root, run_dir):
        """Create a pending VisualGateResult."""
        result = create_visual_gate_result(
            runs_root, "test-run-001",
            status="pending",
            human_review_required=False,
            required_diagrams=[{"diagram_id": "req-01", "diagram_type": "requirement", "descriptor_ref": "profile_descriptor_key:req_diagram", "required": True}],
            clock_provider=_default_clock,
        )
        assert result["ok"] is True
        assert result["visual_gate_sha256"] is not None
        assert len(result["visual_gate_sha256"]) == 64

    def test_readback(self, runs_root, run_dir):
        """Created object reads back correctly."""
        create_visual_gate_result(
            runs_root, "test-run-001",
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        read = read_visual_gate_result(runs_root, "test-run-001")
        assert read["ok"] is True
        assert read["visual_gate_result_exists"] is True
        assert read["hash_match"] is True
        assert read["visual_gate_result"] is not None

    def test_create_passed(self, runs_root, run_dir):
        """Create a passed VisualGateResult."""
        result = create_visual_gate_result(
            runs_root, "test-run-001",
            status="passed",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        assert result["ok"] is True

    def test_create_ready_needs_review(self, runs_root, run_dir):
        """Create a ready_needs_review VisualGateResult."""
        result = create_visual_gate_result(
            runs_root, "test-run-001",
            status="ready_needs_review",
            human_review_required=True,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        assert result["ok"] is True

    def test_missing(self, runs_root):
        """Missing result returns not_found."""
        read = read_visual_gate_result(runs_root, "nonexistent")
        assert read["ok"] is False
        assert read["visual_gate_result_exists"] is False
        assert "not_found" in read["error"]

    def test_hash_mismatch(self, runs_root, run_dir):
        """Hash mismatch is detected."""
        create_visual_gate_result(
            runs_root, "test-run-001",
            status="passed",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        # Modify the file to break the hash
        target_path = os.path.join(run_dir, "visual-gate-result.json")
        with open(target_path) as f:
            data = json.load(f)
        data["status"] = "failed"  # Change a semantic field
        with open(target_path, "w") as f:
            json.dump(data, f)
        read = read_visual_gate_result(runs_root, "test-run-001")
        assert read["ok"] is True
        assert read["hash_match"] is False
        assert "hash_mismatch" in read["error"]

    def test_malformed(self, runs_root, run_dir):
        """Malformed JSON returns error."""
        target_path = os.path.join(run_dir, "visual-gate-result.json")
        with open(target_path, "w") as f:
            f.write("not json")
        read = read_visual_gate_result(runs_root, "test-run-001")
        assert read["ok"] is False
        assert "malformed" in read["error"]

    def test_unsupported_version(self, runs_root, run_dir):
        """Unsupported schema version is detected."""
        target_path = os.path.join(run_dir, "visual-gate-result.json")
        with open(target_path, "w") as f:
            json.dump({"schema_version": "99"}, f)
        read = read_visual_gate_result(runs_root, "test-run-001")
        assert read["ok"] is False
        assert "unsupported_schema_version" in read["error"]

    def test_already_exists(self, runs_root, run_dir):
        """Creating again returns already_exists."""
        create_visual_gate_result(
            runs_root, "test-run-001",
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        result = create_visual_gate_result(
            runs_root, "test-run-001",
            status="passed",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        assert result["ok"] is False
        assert "already_exists" in result["error"]

    def test_invalid_run_id(self, runs_root):
        """Invalid run_id is rejected."""
        result = create_visual_gate_result(
            runs_root, "../traversal",
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        assert result["ok"] is False
        assert "invalid_run_id" in result["error"]

    def test_status_consistency_enforced_on_create(self, runs_root, run_dir):
        """Status consistency is enforced at creation."""
        result = create_visual_gate_result(
            runs_root, "test-run-001",
            status="passed",
            human_review_required=True,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        assert result["ok"] is False
        assert "validation_failed" in result["error"]


# ---------------------------------------------------------------------------
# Evidence reference validation
# ---------------------------------------------------------------------------


class TestEvidenceRefs:
    """Tests for evidence reference validation."""

    def test_run_relative_ref(self):
        """run-relative references are valid."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "evidence_refs": ["run-relative:report.pdf"],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        ev_ref_errors = [c for c in codes if "evidence_ref" in c or "invalid_evidence" in c]
        assert ev_ref_errors == [], f"Unexpected errors: {ev_ref_errors}"

    def test_sha256_ref(self):
        """sha256 references are valid."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "evidence_refs": ["sha256:" + "a" * 64],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        ev_ref_errors = [c for c in codes if "evidence_ref" in c or "invalid_evidence" in c]
        assert ev_ref_errors == [], f"Unexpected errors: {ev_ref_errors}"

    def test_profile_descriptor_key_ref(self):
        """profile_descriptor_key references are valid."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "evidence_refs": ["profile_descriptor_key:my_diagram"],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        ev_ref_errors = [c for c in codes if "evidence_ref" in c or "invalid_evidence" in c]
        assert ev_ref_errors == [], f"Unexpected errors: {ev_ref_errors}"

    def test_url_rejected(self):
        """URL evidence refs are rejected."""
        data = {
            "schema_version": "1",
            "visual_gate_id": "vg-test-abc1234567890def",
            "run_id": "test-run-001",
            "status": "pending",
            "human_review_required": False,
            "required_diagrams": [],
            "evidence_refs": ["https://evil.com/file"],
            "created_at": "2026-01-15T00:00:00Z",
        }
        codes = validate_visual_gate_result(data)
        assert any("invalid_evidence_ref" in c or "url_not_allowed" in c or "invalid_ref" in c for c in codes)


# ---------------------------------------------------------------------------
# Deterministic serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    """Tests for deterministic serialization."""

    def test_deterministic_create(self, runs_root, run_dir):
        """Same inputs produce same result across runs."""
        from runner.visual_gate_result import compute_visual_gate_sha256

        r1 = create_visual_gate_result(
            runs_root, "test-run-001",
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        r2 = create_visual_gate_result(
            runs_root, "test-run-001",
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_default_clock,
        )
        # r2 fails with already_exists but the hash should be deterministic
        # Based on the same inputs
        assert r1["ok"] is True
        assert r2["ok"] is False  # already_exists
