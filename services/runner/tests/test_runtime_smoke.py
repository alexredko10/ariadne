"""Tests for the runner runtime smoke demo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from runner.runtime_smoke import run_runtime_smoke_demo


# ---------------------------------------------------------------------------
# Smoke callable
# ---------------------------------------------------------------------------


class TestRunRuntimeSmokeDemo:
    def test_returns_dict(self):
        result = run_runtime_smoke_demo()
        assert isinstance(result, dict)

    def test_smoke_demo_marker(self):
        result = run_runtime_smoke_demo()
        assert result["smoke_demo"] == "runtime"

    def test_run_id_deterministic(self):
        result = run_runtime_smoke_demo()
        assert result["run_id"] == "smoke-run-001"

    def test_final_report_present(self):
        result = run_runtime_smoke_demo()
        assert result["final_report_present"] is True

    def test_step_count(self):
        result = run_runtime_smoke_demo()
        assert result["step_count"] == 2

    def test_checkpoint_count(self):
        result = run_runtime_smoke_demo()
        assert result["checkpoint_count"] == 1

    def test_evidence_summary_total(self):
        result = run_runtime_smoke_demo()
        assert result["evidence_summary"]["total"] == 2

    def test_evidence_summary_passed(self):
        result = run_runtime_smoke_demo()
        assert result["evidence_summary"]["passed"] == 1

    def test_evidence_summary_warning(self):
        result = run_runtime_smoke_demo()
        assert result["evidence_summary"]["warning"] == 1

    def test_evidence_summary_no_failures(self):
        result = run_runtime_smoke_demo()
        assert result["evidence_summary"]["failed"] == 0
        assert result["evidence_summary"]["failing_evidence_ids"] == []

    def test_evidence_summary_warning_ids(self):
        result = run_runtime_smoke_demo()
        assert "ev-warn-001" in result["evidence_summary"]["warning_evidence_ids"]

    def test_final_report_id_deterministic(self):
        result = run_runtime_smoke_demo()
        assert result["final_report_id"] == "smoke-run-001-report"

    def test_json_serializable(self):
        result = run_runtime_smoke_demo()
        dumped = json.dumps(result, sort_keys=True)
        assert isinstance(dumped, str)
        # Verify roundtrip
        parsed = json.loads(dumped)
        assert parsed["run_id"] == "smoke-run-001"

    def test_same_output_across_calls(self):
        r1 = run_runtime_smoke_demo()
        r2 = run_runtime_smoke_demo()
        assert r1 == r2


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


class TestRuntimeSmokeCLI:
    @staticmethod
    def _get_pythonpath() -> str:
        """Build PYTHONPATH for subprocess."""
        test_dir = Path(__file__).resolve().parent  # services/runner/tests
        runner_src = test_dir.parent / "src"          # services/runner/src
        services_dir = test_dir.parent.parent          # services/
        core_src = services_dir / "core" / "src"       # services/core/src
        return f"{core_src}:{runner_src}"

    def test_cli_succeeds(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "runner", "runtime-smoke"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_cli_output_is_json(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "runner", "runtime-smoke"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        parsed = json.loads(result.stdout)
        assert parsed["smoke_demo"] == "runtime"
        assert parsed["run_id"] == "smoke-run-001"
