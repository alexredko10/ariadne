"""
PR 0149 — Tests for GET /runs/<run_id>/visual-gate-result API route.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.visual_gate_result import create_visual_gate_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runs_root() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def _create_test_run(runs_root: str, run_id: str = "test-run-001") -> str:
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    request = RunPersistenceRequest(
        runs_root=runs_root, run_id=run_id,
        task_description_hash="test-hash",
        task_description_redacted="Test run",
        branch="main", base_branch="main", status="completed",
        reason_codes=(), pipeline_status="passed",
        pipeline_final_action=None, pipeline_has_blockers=False,
        pipeline_step_summary=(), pipeline_gate_summary=(),
        git_boundary_status="clean", command_plan_summary=(),
        execution_attempted=True,
        execution_results_summary=(),
        approval_summary="test", artifact_hashes={},
        warnings=(), next_action="none",
        started_at=None, finished_at=None,
    )
    result = persist_run_record(request)
    assert result.status == "persisted"
    return run_id


# ---------------------------------------------------------------------------
# API response tests (without starting the server)
# ---------------------------------------------------------------------------


class TestVisualGateAPI:
    """Tests for visual gate API behavior."""

    def test_available(self, runs_root):
        """Available visual gate result returns versioned response."""
        run_id = _create_test_run(runs_root)
        create_visual_gate_result(
            runs_root, run_id,
            status="pending",
            human_review_required=False,
            required_diagrams=[{"diagram_id": "d1", "diagram_type": "requirement", "descriptor_ref": "profile_descriptor_key:d1", "required": True}],
        )
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is True
        assert result["visual_gate_result_exists"] is True
        assert result["hash_match"] is True
        assert result["visual_gate_result"] is not None
        assert result["visual_gate_result"]["schema_version"] == "1"

    def test_not_found(self, runs_root):
        """Missing result returns not-found."""
        run_id = _create_test_run(runs_root)
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is False
        assert result["visual_gate_result_exists"] is False
        assert "not_found" in result["error"]

    def test_hash_mismatch(self, runs_root):
        """Hash mismatch is reported."""
        run_id = _create_test_run(runs_root)
        create_visual_gate_result(
            runs_root, run_id,
            status="passed",
            human_review_required=False,
            required_diagrams=[],
        )
        # Modify the file
        run_dir = os.path.join(runs_root, run_id)
        target = os.path.join(run_dir, "visual-gate-result.json")
        with open(target) as f:
            data = json.load(f)
        data["status"] = "failed"
        with open(target, "w") as f:
            json.dump(data, f)
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is True
        assert result["hash_match"] is False

    def test_unsupported_version(self, runs_root):
        """Unsupported version returns error."""
        run_id = _create_test_run(runs_root)
        run_dir = os.path.join(runs_root, run_id)
        target = os.path.join(run_dir, "visual-gate-result.json")
        with open(target, "w") as f:
            json.dump({"schema_version": "2"}, f)
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is False
        assert "unsupported_schema_version" in result["error"]

    def test_malformed(self, runs_root):
        """Malformed profile returns error."""
        run_id = _create_test_run(runs_root)
        run_dir = os.path.join(runs_root, run_id)
        target = os.path.join(run_dir, "visual-gate-result.json")
        with open(target, "w") as f:
            f.write("not json")
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is False
        assert "malformed" in result["error"]

    def test_legacy_run_no_gate(self, runs_root):
        """Legacy run without visual gate is valid."""
        run_id = _create_test_run(runs_root)
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, run_id)
        assert result["ok"] is False
        assert result["visual_gate_result_exists"] is False

    def test_invalid_run_id(self, runs_root):
        """Invalid run_id is rejected."""
        from runner.visual_gate_result import read_visual_gate_result
        result = read_visual_gate_result(runs_root, "../bad")
        assert result["ok"] is False
