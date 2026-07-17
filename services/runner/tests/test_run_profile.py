"""
PR 0147C — Unit tests for run profile schema validation and persistence.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from runner.run_profile import (
    create_run_profile,
    read_run_profile,
    validate_profile_dict,
    compute_profile_sha256,
    validate_reference,
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
    with open(os.path.join(rd, "run.json"), "w") as f:
        json.dump({"run_id": "test-run-001", "status": "completed"}, f)
    return rd


@pytest.fixture
def valid_presentation() -> dict:
    return {
        "title": "Test Run",
        "status_label": "Completed",
        "neutral_facts": [
            {
                "key": "project_name",
                "label": "Project Name",
                "value": "Demo Project",
                "value_type": "text",
                "display_order": 1,
                "source": "operator",
            },
            {
                "key": "total_cost",
                "label": "Total Cost",
                "value": 150000.0,
                "value_type": "number",
                "unit": "USD",
                "display_order": 2,
                "source": "adapter",
            },
        ],
    }


@pytest.fixture
def valid_groups() -> dict:
    return {
        "reports": {"key": "reports", "label": "Reports", "display_order": 1},
        "data": {"key": "data", "label": "Data Files", "display_order": 2},
    }


@pytest.fixture
def valid_descriptors() -> list:
    return [
        {
            "key": "summary_pdf",
            "label": "Summary Report",
            "kind": "summary",
            "evidence_role": "report",
            "media_type": "application/pdf",
            "ref": "run-relative:report.pdf",
            "group_key": "reports",
            "display_order": 1,
            "required": True,
        },
        {
            "key": "source_csv",
            "label": "Source Data",
            "kind": "spreadsheet",
            "evidence_role": "input",
            "media_type": "text/csv",
            "ref": "run-relative:data.csv",
            "group_key": "data",
            "display_order": 2,
            "required": False,
        },
    ]


# ---------------------------------------------------------------------------
# Profile schema tests
# ---------------------------------------------------------------------------


class TestProfileSchema:
    """Tests for profile schema validation."""

    def test_valid_profile(self, valid_presentation, valid_groups, valid_descriptors):
        """A valid profile passes validation."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": valid_presentation,
            "artifact_groups": valid_groups,
            "artifact_descriptors": valid_descriptors,
        }
        codes = validate_profile_dict(data)
        assert codes == [], f"Validation errors: {codes}"

    def test_invalid_schema_version(self):
        """Wrong schema version is rejected."""
        data = {
            "schema_version": "2",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
        }
        codes = validate_profile_dict(data)
        assert any("unsupported_schema_version" in c for c in codes)

    def test_invalid_profile_key(self):
        """Invalid profile key is rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "UPPERCASE-KEY",
            "run_id": "test-run-001",
        }
        codes = validate_profile_dict(data)
        assert any("invalid_profile_key" in c for c in codes)

    def test_missing_run_id(self):
        """Missing run_id is rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "",
        }
        codes = validate_profile_dict(data)
        assert len(codes) > 0

    def test_duplicate_fact_key(self):
        """Duplicate fact keys are rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "dup_key", "label": "A", "value": "a", "value_type": "text", "display_order": 1},
                    {"key": "dup_key", "label": "B", "value": "b", "value_type": "text", "display_order": 2},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert any("duplicate_fact_key" in c for c in codes)

    def test_unsupported_value_type(self):
        """Unsupported value type is rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "bad_type", "label": "Bad", "value": "x", "value_type": "unsupported", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert any("unsupported_value_type" in c for c in codes)

    def test_too_many_facts(self):
        """More than 50 facts is rejected."""
        facts = [{"key": f"fact_{i}", "label": f"Fact {i}", "value": str(i), "value_type": "text", "display_order": i} for i in range(51)]
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {"neutral_facts": facts},
        }
        codes = validate_profile_dict(data)
        assert any("too_many_facts" in c for c in codes)

    def test_too_many_groups(self):
        """More than 20 groups is rejected."""
        groups = {f"group_{i}": {"key": f"group_{i}", "label": f"Group {i}", "display_order": i} for i in range(21)}
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "artifact_groups": groups,
        }
        codes = validate_profile_dict(data)
        assert any("too_many_groups" in c for c in codes)

    def test_too_many_descriptors(self):
        """More than 100 descriptors is rejected."""
        descs = [{"key": f"desc_{i}", "label": f"Desc {i}", "kind": "text", "evidence_role": "input", "media_type": "text/plain", "ref": f"run-relative:file{i}.txt", "group_key": "default", "display_order": i, "required": False} for i in range(101)]
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "artifact_groups": {"default": {"key": "default", "label": "Default", "display_order": 0}},
            "artifact_descriptors": descs,
        }
        codes = validate_profile_dict(data)
        assert any("too_many_descriptors" in c for c in codes)


# ---------------------------------------------------------------------------
# Profile hashing tests
# ---------------------------------------------------------------------------


class TestProfileHashing:
    """Tests for deterministic profile hashing."""

    def test_deterministic_hash(self, valid_presentation, valid_groups, valid_descriptors):
        """Same inputs produce same hash."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": valid_presentation,
            "artifact_groups": valid_groups,
            "artifact_descriptors": valid_descriptors,
        }
        hash1 = compute_profile_sha256(data)
        hash2 = compute_profile_sha256(data)
        assert hash1 == hash2
        assert len(hash1) == 64  # Full sha256 hex

    def test_hash_stability(self):
        """Hash is stable for unchanged data."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
        }
        h = compute_profile_sha256(data)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_changes_on_change(self):
        """Hash changes when data changes."""
        data1 = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {"title": "First"},
        }
        data2 = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {"title": "Second"},
        }
        h1 = compute_profile_sha256(data1)
        h2 = compute_profile_sha256(data2)
        assert h1 != h2

    def test_hash_self_excluding(self):
        """Hash excludes the profile_sha256 field itself."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "profile_sha256": "should_not_affect_hash",
        }
        h = compute_profile_sha256(data)
        # Verify hash is deterministic regardless of profile_sha256 field
        data2 = {"schema_version": "1", "profile_key": "domain-neutral-v1", "run_id": "test-run-001"}
        h2 = compute_profile_sha256(data2)
        assert h == h2


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestProfilePersistence:
    """Tests for profile creation, persistence, and readback."""

    def test_create_and_read(self, runs_root, run_dir, valid_presentation, valid_groups, valid_descriptors):
        """Create a profile and read it back."""
        result = create_run_profile(
            runs_root, "test-run-001",
            presentation=valid_presentation,
            artifact_groups=valid_groups,
            artifact_descriptors=valid_descriptors,
        )
        assert result["ok"] is True
        assert result["profile_sha256"] is not None
        assert len(result["profile_sha256"]) == 64

        read = read_run_profile(runs_root, "test-run-001")
        assert read["ok"] is True
        assert read["profile_exists"] is True
        assert read["hash_match"] is True
        assert read["profile_sha256"] == result["profile_sha256"]

    def test_missing_profile(self, runs_root):
        """Reading a missing profile returns not found."""
        read = read_run_profile(runs_root, "nonexistent")
        assert read["ok"] is False
        assert read["profile_exists"] is False
        assert "not found" in read["error"]

    def test_invalid_run_id(self, runs_root):
        """Invalid run_id returns error."""
        read = read_run_profile(runs_root, "../traversal")
        assert read["ok"] is False
        assert read["profile_exists"] is False

    def test_profile_file_persists(self, runs_root, run_dir, valid_presentation):
        """Profile file is written to run directory."""
        result = create_run_profile(runs_root, "test-run-001", presentation=valid_presentation)
        assert result["ok"] is True
        profile_path = os.path.join(run_dir, "run-profile.json")
        assert os.path.isfile(profile_path)
        with open(profile_path) as f:
            data = json.load(f)
        assert data["schema_version"] == "1"
        assert data["run_id"] == "test-run-001"
        assert data["profile_sha256"] == result["profile_sha256"]

    def test_readback_hash_mismatch(self, runs_root, run_dir):
        """Hash mismatch is detected on read."""
        # Create a profile manually with wrong hash
        profile_path = os.path.join(run_dir, "run-profile.json")
        bad_data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "profile_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        with open(profile_path, "w") as f:
            json.dump(bad_data, f)

        read = read_run_profile(runs_root, "test-run-001")
        assert read["ok"] is True
        assert read["hash_match"] is False
        assert "hash mismatch" in read["error"]

    def test_malformed_profile(self, runs_root, run_dir):
        """Malformed profile returns error."""
        profile_path = os.path.join(run_dir, "run-profile.json")
        with open(profile_path, "w") as f:
            f.write("not valid json")

        read = read_run_profile(runs_root, "test-run-001")
        assert read["ok"] is False
        assert "malformed" in read["error"]

    def test_unsupported_version(self, runs_root, run_dir):
        """Unsupported schema version is detected."""
        profile_path = os.path.join(run_dir, "run-profile.json")
        bad_data = {
            "schema_version": "99",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
        }
        with open(profile_path, "w") as f:
            json.dump(bad_data, f)

        read = read_run_profile(runs_root, "test-run-001")
        assert read["ok"] is False
        assert "unsupported profile version" in read["error"]


# ---------------------------------------------------------------------------
# Reference security tests
# ---------------------------------------------------------------------------


class TestReferenceSecurity:
    """Tests for controlled reference validation."""

    def test_run_relative_allowed(self):
        """run-relative references are allowed."""
        codes: list[str] = []
        result = validate_reference("run-relative:report.pdf", codes)
        assert result == "run-relative"
        assert codes == []

    def test_sha256_allowed(self):
        """sha256 references are allowed."""
        codes: list[str] = []
        result = validate_reference("sha256:" + "a" * 64, codes)
        assert result == "sha256"
        assert codes == []

    def test_absolute_path_rejected(self):
        """Absolute paths are rejected."""
        codes: list[str] = []
        validate_reference("/etc/passwd", codes)
        assert any("absolute_path" in c for c in codes)

    def test_traversal_rejected(self):
        """Traversal paths are rejected."""
        codes: list[str] = []
        validate_reference("run-relative:../../.git/config", codes)
        assert any("traversal" in c for c in codes)

    def test_https_url_rejected(self):
        """HTTPS URLs are rejected."""
        codes: list[str] = []
        validate_reference("https://example.com/file.pdf", codes)
        assert any("url" in c for c in codes)

    def test_http_url_rejected(self):
        """HTTP URLs are rejected."""
        codes: list[str] = []
        validate_reference("http://evil.com/file", codes)
        assert any("url" in c for c in codes)

    def test_file_url_rejected(self):
        """file: URLs are rejected."""
        codes: list[str] = []
        validate_reference("file:///etc/passwd", codes)
        assert any("url" in c for c in codes)

    def test_javascript_url_rejected(self):
        """javascript: URLs are rejected."""
        codes: list[str] = []
        validate_reference("javascript:alert(1)", codes)
        assert any("url" in c for c in codes)

    def test_data_url_rejected(self):
        """data: URLs are rejected."""
        codes: list[str] = []
        validate_reference("data:text/html,<script>", codes)
        assert any("url" in c for c in codes)

    def test_malformed_sha256_rejected(self):
        """Malformed sha256 refs are rejected."""
        codes: list[str] = []
        validate_reference("sha256:not-a-valid-hex", codes)
        assert len(codes) > 0


# ---------------------------------------------------------------------------
# Neutral fact type tests
# ---------------------------------------------------------------------------


class TestNeutralFacts:
    """Tests for neutral fact value types."""

    def test_text_fact(self):
        """Text fact with valid string."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "desc", "label": "Desc", "value": "Some text", "value_type": "text", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == []

    def test_number_fact(self):
        """Number fact with valid number."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "cost", "label": "Cost", "value": 100.5, "value_type": "number", "unit": "USD", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == [], f"Errors: {codes}"

    def test_date_fact(self):
        """Date fact with valid ISO date."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "start_date", "label": "Start", "value": "2026-01-15", "value_type": "date", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == []

    def test_boolean_fact(self):
        """Boolean fact."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "is_active", "label": "Active", "value": True, "value_type": "boolean", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == []

    def test_enum_fact(self):
        """Enum fact with valid value."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "status_code", "label": "Status", "value": "in_progress", "value_type": "enum", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == []

    def test_currency_fact(self):
        """Currency fact with valid value."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "budget", "label": "Budget", "value": 50000, "value_type": "currency", "currency": "USD", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert codes == []

    def test_invalid_date_rejected(self):
        """Malformed date is rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "bad_date", "label": "Bad", "value": "not-a-date", "value_type": "date", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert len(codes) > 0

    def test_infinity_rejected(self):
        """Infinity is rejected for number type."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "bad_num", "label": "Bad", "value": float("inf"), "value_type": "number", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert len(codes) > 0

    def test_non_bool_rejected(self):
        """Non-boolean for boolean type is rejected."""
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": "test-run-001",
            "run_presentation": {
                "neutral_facts": [
                    {"key": "bad_bool", "label": "Bad", "value": "yes", "value_type": "boolean", "display_order": 1},
                ]
            },
        }
        codes = validate_profile_dict(data)
        assert len(codes) > 0
