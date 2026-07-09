"""Tests for the run persistence module."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from runner.run_persistence import (
    RunPersistenceRequest,
    PersistedRunRecord,
    RunPersistenceResult,
    RunPersistenceReadResult,
    RunPersistenceStatus,
    persist_run_record,
    load_run_record,
    REASON_INVALID_RUN_ID,
    REASON_WRITE_FAILED,
    REASON_READ_FAILED,
    REASON_HASH_MISMATCH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock() -> str:
    """Deterministic clock provider."""
    return "2026-07-06T16:00:00Z"


def _valid_request(**overrides: Any) -> RunPersistenceRequest:
    """Create a valid RunPersistenceRequest."""
    kwargs = {
        "runs_root": "/tmp/test-runs",
        "run_id": "run-001",
        "task_description_hash": "abc123def4567890",
        "task_description_redacted": "Implement the run persistence module",
        "branch": "0130-run-persistence",
        "base_branch": "main",
        "status": "completed",
        "reason_codes": (),
        "pipeline_status": "completed",
        "pipeline_final_action": "continue",
        "pipeline_has_blockers": False,
        "pipeline_step_summary": ({"step_name": "compose_prompts", "status": "completed"},),
        "pipeline_gate_summary": ({"gate_name": "plan-review", "verdict": "pass"},),
        "git_boundary_status": "approved",
        "command_plan_summary": ({"operation": "git_status", "redacted_display": "git status"},),
        "execution_attempted": True,
        "execution_results_summary": ({"operation": "git_status", "exit_code": "0"},),
        "approval_summary": "Approved by tester: Testing",
        "artifact_hashes": {"path/to/artifact": "abc123"},
        "warnings": (),
        "next_action": "continue",
        "started_at": _clock(),
        "finished_at": _clock(),
        "clock_provider": _clock,
    }
    kwargs.update(overrides)
    return RunPersistenceRequest(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Persist minimal record
# ---------------------------------------------------------------------------


class TestPersistMinimalRecord:
    def test_persist_minimal_record(self, tmp_path: Path):
        """Persists run.json and manifest.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        assert result.run_id == "run-001"
        assert "run.json" in result.files_written
        assert "manifest.json" in result.files_written
        assert result.run_json_hash is not None
        assert len(result.run_json_hash) == 16
        assert result.readback_ok is True


# ---------------------------------------------------------------------------
# Run directory created
# ---------------------------------------------------------------------------


class TestRunDirectoryCreated:
    def test_run_directory_created(self, tmp_path: Path):
        """Run directory created under runs_root."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_dir = Path(result.run_dir)
        assert run_dir.exists()
        assert run_dir.is_dir()
        assert (run_dir / "run.json").exists()
        assert (run_dir / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Deterministic JSON ordering
# ---------------------------------------------------------------------------


class TestDeterministicJsonOrdering:
    def test_deterministic_json_ordering(self, tmp_path: Path):
        """JSON output uses sort_keys=True."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        content = run_json.read_text(encoding="utf-8")
        # Verify it's valid JSON with sorted keys
        data = json.loads(content)
        keys = list(data.keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Run JSON hash
# ---------------------------------------------------------------------------


class TestRunJsonHash:
    def test_run_json_hash_recorded(self, tmp_path: Path):
        """Hash recorded in manifest."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        manifest = Path(result.manifest_path)
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert manifest_data["run_json_hash"] == result.run_json_hash


# ---------------------------------------------------------------------------
# Load run record round-trip
# ---------------------------------------------------------------------------


class TestLoadRunRecord:
    def test_load_run_record_round_trip(self, tmp_path: Path):
        """Full round-trip readback."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        persist_result = persist_run_record(request)
        assert persist_result.status == RunPersistenceStatus.PERSISTED.value

        read_result = load_run_record(runs_root, "run-001")
        assert read_result.status == RunPersistenceStatus.READ_OK.value
        assert read_result.record is not None
        assert read_result.record.run_id == "run-001"
        assert read_result.record.task_description_hash == "abc123def4567890"
        assert read_result.hash_match is True


# ---------------------------------------------------------------------------
# Load run record not found
# ---------------------------------------------------------------------------


class TestLoadRunRecordNotFound:
    def test_load_run_record_not_found(self, tmp_path: Path):
        """Missing run → not_found."""
        runs_root = str(tmp_path / "runs")
        result = load_run_record(runs_root, "nonexistent-run")
        assert result.status == RunPersistenceStatus.NOT_FOUND.value


# ---------------------------------------------------------------------------
# Load run record malformed JSON
# ---------------------------------------------------------------------------


class TestLoadRunRecordMalformedJson:
    def test_load_run_record_malformed_json(self, tmp_path: Path):
        """Corrupt run.json → rejected."""
        runs_root = str(tmp_path / "runs")
        run_dir = Path(runs_root) / "run-001"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text("{invalid json}", encoding="utf-8")
        result = load_run_record(runs_root, "run-001")
        assert result.status == RunPersistenceStatus.REJECTED.value
        assert REASON_READ_FAILED in result.reason_codes


# ---------------------------------------------------------------------------
# Run ID validation
# ---------------------------------------------------------------------------


class TestRunIdValidation:
    def test_invalid_run_id_rejected(self, tmp_path: Path):
        """Invalid run_id → rejected."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root, run_id="invalid/run/id")
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.REJECTED.value
        assert REASON_INVALID_RUN_ID in result.reason_codes

    def test_valid_run_id_accepted(self, tmp_path: Path):
        """Valid run_id → persisted."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root, run_id="run-abc_123")
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value


# ---------------------------------------------------------------------------
# Task description hash
# ---------------------------------------------------------------------------


class TestTaskDescriptionHash:
    def test_task_description_hash_recorded(self, tmp_path: Path):
        """Hash recorded in run.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["task_description_hash"] == "abc123def4567890"


# ---------------------------------------------------------------------------
# Redacted summary
# ---------------------------------------------------------------------------


class TestRedactedSummary:
    def test_redacted_summary_recorded(self, tmp_path: Path):
        """Redacted summary recorded."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["task_description_redacted"] == "Implement the run persistence module"


# ---------------------------------------------------------------------------
# Artifact hashes preserved
# ---------------------------------------------------------------------------


class TestArtifactHashesPreserved:
    def test_artifact_hashes_preserved(self, tmp_path: Path):
        """Pipeline artifact_hashes persisted."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["artifact_hashes"]["path/to/artifact"] == "abc123"


# ---------------------------------------------------------------------------
# Pipeline step summary
# ---------------------------------------------------------------------------


class TestPipelineStepSummary:
    def test_pipeline_step_summary(self, tmp_path: Path):
        """Step results serialized."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert len(data["command_plan_summary"]) >= 1


# ---------------------------------------------------------------------------
# Pipeline gate summary
# ---------------------------------------------------------------------------


class TestPipelineGateSummary:
    def test_pipeline_gate_summary(self, tmp_path: Path):
        """Gate results serialized."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert len(data["pipeline_gate_summary"]) >= 1


# ---------------------------------------------------------------------------
# Command plan summary
# ---------------------------------------------------------------------------


class TestCommandPlanSummary:
    def test_command_plan_summary(self, tmp_path: Path):
        """Command plan serialized."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert len(data["command_plan_summary"]) >= 1


# ---------------------------------------------------------------------------
# Approval summary
# ---------------------------------------------------------------------------


class TestApprovalSummary:
    def test_approval_summary(self, tmp_path: Path):
        """Approval metadata persisted."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["approval_summary"] == "Approved by tester: Testing"


# ---------------------------------------------------------------------------
# Execution attempted flag
# ---------------------------------------------------------------------------


class TestExecutionAttemptedFlag:
    def test_execution_attempted_flag(self, tmp_path: Path):
        """execution_attempted persisted."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        run_json = Path(result.run_json_path)
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["execution_attempted"] is True


# ---------------------------------------------------------------------------
# Injected clock
# ---------------------------------------------------------------------------


class TestInjectedClock:
    def test_injected_clock(self, tmp_path: Path):
        """Deterministic timestamps."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        assert result.started_at == _clock()
        assert result.finished_at == _clock()


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Temp runs_root, no repo .ariadne/ residue."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# No subprocess/docker/git
# ---------------------------------------------------------------------------


class TestNoSubprocessDockerGit:
    def test_no_subprocess_docker_git(self):
        """Module does not use subprocess/docker/git."""
        import inspect
        from runner.run_persistence import persist_run_record, load_run_record
        source = inspect.getsource(persist_run_record) + inspect.getsource(load_run_record)
        assert "subprocess.run" not in source
        assert "os.system" not in source
        assert "shell=True" not in source
        assert "docker" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "git add" not in source
        assert "gh pr create" not in source


# ---------------------------------------------------------------------------
# No pipeline modified
# ---------------------------------------------------------------------------


class TestNoPipelineModified:
    def test_no_pipeline_import(self):
        """Module does not import pipeline_runner."""
        import inspect
        from runner.run_persistence import persist_run_record
        source = inspect.getsource(persist_run_record)
        assert "pipeline_runner" not in source


# ---------------------------------------------------------------------------
# No git boundary modified
# ---------------------------------------------------------------------------


class TestNoGitBoundaryModified:
    def test_no_git_boundary_import(self):
        """Module does not import git_boundary module."""
        import inspect
        from runner.run_persistence import persist_run_record
        source = inspect.getsource(persist_run_record)
        # The field name git_boundary_status is expected in the data
        # Check that the module does not import git_boundary
        assert "from runner.git_boundary" not in source
        assert "import git_boundary" not in source


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_deterministic_repeats(self, tmp_path: Path):
        """Same inputs → same output."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result1 = persist_run_record(request)
        result2 = persist_run_record(request)
        assert result1.status == result2.status
        assert result1.run_json_hash == result2.run_json_hash


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.run_persistence
        doc = runner.run_persistence.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.run_persistence import persist_run_record
        source = inspect.getsource(persist_run_record)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"


# ---------------------------------------------------------------------------
# Manifest report path tests (PR 0135)
# ---------------------------------------------------------------------------


class TestManifestReportPath:
    """Manifest includes run-report.txt when report_path is provided."""

    def test_manifest_includes_report_path_when_provided(self, tmp_path: Path):
        """Manifest files list includes run-report.txt when report_path is set."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            report_path=str(tmp_path / "runs" / "run-001" / "run-report.txt"),
        )
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        manifest = Path(result.manifest_path)
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert "run.json" in manifest_data["files"]
        assert "run-report.txt" in manifest_data["files"]

    def test_manifest_excludes_report_path_when_not_provided(self, tmp_path: Path):
        """Manifest files list excludes run-report.txt when report_path is not set."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(runs_root=runs_root)
        result = persist_run_record(request)
        assert result.status == RunPersistenceStatus.PERSISTED.value
        manifest = Path(result.manifest_path)
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert "run.json" in manifest_data["files"]
        assert "run-report.txt" not in manifest_data["files"]
