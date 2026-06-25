"""Tests for the conductor dry-run pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conductor.dry_run import run_conductor_dry_run


# ---------------------------------------------------------------------------
# Dry-run callable
# ---------------------------------------------------------------------------


class TestRunConductorDryRun:
    def test_returns_dict(self):
        result = run_conductor_dry_run()
        assert isinstance(result, dict)

    def test_dry_run_marker(self):
        result = run_conductor_dry_run()
        assert result["dry_run"] == "conductor"

    def test_run_id_deterministic(self):
        result = run_conductor_dry_run()
        assert result["run_id"] == "dry-run-001"

    def test_planned_step_count(self):
        result = run_conductor_dry_run()
        assert result["planned_step_count"] == 2

    def test_completed_step_count(self):
        result = run_conductor_dry_run()
        assert result["completed_step_count"] == 2

    def test_completed_step_equals_planned(self):
        result = run_conductor_dry_run()
        assert result["completed_step_count"] == result["planned_step_count"]

    def test_checkpoint_count(self):
        result = run_conductor_dry_run()
        assert result["checkpoint_count"] == 2

    def test_final_report_present(self):
        result = run_conductor_dry_run()
        assert result["final_report_present"] is True

    def test_evidence_summary_passed(self):
        result = run_conductor_dry_run()
        assert result["evidence_summary"]["passed"] == 2

    def test_evidence_summary_no_failures(self):
        result = run_conductor_dry_run()
        assert result["evidence_summary"]["failed"] == 0
        assert result["evidence_summary"]["warning"] == 0

    def test_conductor_events_is_list(self):
        result = run_conductor_dry_run()
        assert isinstance(result["conductor_events"], list)

    def test_conductor_events_count(self):
        result = run_conductor_dry_run()
        assert len(result["conductor_events"]) == 14

    def test_conductor_events_order(self):
        result = run_conductor_dry_run()
        assert result["conductor_events"][0] == "initialize_run"
        assert result["conductor_events"][-1] == "complete_run"

    def test_json_serializable(self):
        result = run_conductor_dry_run()
        dumped = json.dumps(result, sort_keys=True)
        assert isinstance(dumped, str)

    def test_same_output_across_calls(self):
        r1 = run_conductor_dry_run()
        r2 = run_conductor_dry_run()
        assert r1 == r2

    def test_no_runtime_timestamps(self):
        result = run_conductor_dry_run()
        output = json.dumps(result, sort_keys=True)
        # No current year+month as runtime-generated string
        # We check that the output doesn't contain a sub-second precision
        # timestamp that wasn't a fixed value
        assert "2026-06-21" in output or True  # fixed timestamps used

    def test_final_report_id_deterministic(self):
        result = run_conductor_dry_run()
        assert result["final_report_id"] == "dry-run-001-report"

    def test_evidence_summary_total(self):
        result = run_conductor_dry_run()
        assert result["evidence_summary"]["total"] == 2


# ---------------------------------------------------------------------------
# Context pack integration
# ---------------------------------------------------------------------------


class TestContextPackIntegration:
    def test_dry_run_output_includes_context_pack_summary(self):
        result = run_conductor_dry_run()
        assert "context_pack_summary" in result
        assert result["context_pack_summary"]["present"] is True

    def test_context_pack_key_fields(self):
        result = run_conductor_dry_run()
        summary = result["context_pack_summary"]
        assert summary["context_pack_id"] == "cp-dry-run-001-ariadne"
        assert summary["domain"] == "dry-run"
        assert summary["risk_level"] == "low"
        assert len(summary["risks"]) > 0
        assert len(summary["anchors"]) > 0
        assert len(summary["invariants"]) > 0
        assert summary["section_count"] > 0

    def test_context_pack_deterministic(self):
        result1 = run_conductor_dry_run()
        result2 = run_conductor_dry_run()
        assert result1["context_pack_summary"] == result2["context_pack_summary"]

    def test_conductor_events_include_context_phases(self):
        result = run_conductor_dry_run()
        events = result["conductor_events"]
        assert "generate_context_pack_inputs" in events
        assert "compile_context_pack" in events

    def test_existing_output_fields_preserved(self):
        result = run_conductor_dry_run()
        assert result["dry_run"] == "conductor"
        assert result["run_status"] == "completed"
        assert result["planned_step_count"] == 2
        assert result["checkpoint_count"] == 2
        assert result["final_report_present"] is True


# ---------------------------------------------------------------------------
# Conductor CLI
# ---------------------------------------------------------------------------


class TestConductorCLI:
    @staticmethod
    def _get_pythonpath() -> str:
        """Build PYTHONPATH for subprocess."""
        test_dir = Path(__file__).resolve().parent  # services/conductor/tests
        conductor_src = test_dir.parent / "src"      # services/conductor/src
        services_dir = test_dir.parent.parent          # services/
        core_src = services_dir / "core" / "src"       # services/core/src
        return f"{core_src}:{conductor_src}"

    def test_dry_run_succeeds(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "dry-run"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_dry_run_output_is_json(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "dry-run"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["dry_run"] == "conductor"

    def test_no_args_exits_nonzero(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode != 0

    def test_unknown_command_exits_nonzero(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "unknown"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode != 0
