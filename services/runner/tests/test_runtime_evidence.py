"""Tests for the runtime evidence read model."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from runner.runtime_evidence import (
    RunEvidenceSummary,
    RunEvidenceDetail,
    ArtifactEvidenceRef,
    MissingEvidenceNotice,
    RuntimeEvidenceReadResult,
    list_run_evidence_summaries,
    read_run_evidence_detail,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_complete_run(
    tmp_dir: str,
    run_id: str = "test-run-001",
    include_report: bool = True,
    include_manifest: bool = True,
    include_pr_url: bool = False,
) -> dict[str, str]:
    """Create a complete run directory with run.json and optional extras.

    Parameters
    ----------
    tmp_dir:
        Temporary root directory.
    run_id:
        Run ID to create.
    include_report:
        Whether to create run-report.txt.
    include_manifest:
        Whether to create manifest.json.
    include_pr_url:
        Whether to include a PR URL in execution results.

    Returns
    -------
    dict
        Paths to created files.
    """
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    execution_results: list[dict[str, Any]] = [
        {"operation": "git_status", "exit_code": "0", "stdout": "ok", "stderr": ""},
        {"operation": "git_add", "exit_code": "0", "stdout": "ok", "stderr": ""},
        {"operation": "git_commit", "exit_code": "0", "stdout": "ok", "stderr": ""},
        {"operation": "git_push", "exit_code": "0", "stdout": "ok", "stderr": ""},
    ]
    if include_pr_url:
        execution_results.append(
            {
                "operation": "gh_pr_create",
                "exit_code": "0",
                "stdout": "https://github.com/owner/repo/pull/123\n",
                "stderr": "",
                "pr_url": "https://github.com/owner/repo/pull/123",
            }
        )

    run_json = {
        "schema_version": "1",
        "run_id": run_id,
        "status": "completed",
        "pipeline_status": "completed",
        "pipeline_final_action": "continue",
        "pipeline_has_blockers": False,
        "git_boundary_status": "approved",
        "reason_codes": ["completed"],
        "execution_attempted": True,
        "execution_results_summary": execution_results,
        "started_at": "2026-07-10T12:00:00Z",
        "finished_at": "2026-07-10T12:05:00Z",
    }
    run_json_path = os.path.join(run_dir, "run.json")
    with open(run_json_path, "w", encoding="utf-8") as f:
        json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)

    manifest_path = os.path.join(run_dir, "manifest.json")
    if include_manifest:
        manifest = {
            "schema_version": "1",
            "run_id": run_id,
            "run_json_hash": "abc123def4567890",
            "files": ["run.json", "run-report.txt"] if include_report else ["run.json"],
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)

    report_path = os.path.join(run_dir, "run-report.txt")
    if include_report:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Ariadne Run Report\nRun ID: " + run_id + "\nStatus: completed\n")

    return {
        "runs_root": runs_root,
        "run_dir": run_dir,
        "run_json_path": run_json_path,
        "manifest_path": manifest_path,
        "report_path": report_path,
    }


def _create_malformed_run_json(tmp_dir: str, run_id: str = "malformed-run") -> dict[str, str]:
    """Create a run directory with malformed run.json."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    run_json_path = os.path.join(run_dir, "run.json")
    with open(run_json_path, "w", encoding="utf-8") as f:
        f.write("{invalid json content")

    return {
        "runs_root": runs_root,
        "run_dir": run_dir,
        "run_json_path": run_json_path,
    }


def _create_malformed_manifest(tmp_dir: str, run_id: str = "malformed-manifest") -> dict[str, str]:
    """Create a run directory with valid run.json but malformed manifest.json."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    run_json_path = os.path.join(run_dir, "run.json")
    run_json = {
        "schema_version": "1",
        "run_id": run_id,
        "status": "completed",
        "reason_codes": ["completed"],
        "execution_attempted": True,
        "execution_results_summary": [],
    }
    with open(run_json_path, "w", encoding="utf-8") as f:
        json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)

    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("{bad manifest")

    return {
        "runs_root": runs_root,
        "run_dir": run_dir,
        "run_json_path": run_json_path,
        "manifest_path": manifest_path,
    }


# ---------------------------------------------------------------------------
# Tests: list_run_evidence_summaries
# ---------------------------------------------------------------------------


class TestListRunEvidenceSummaries:
    """Tests for listing run evidence summaries."""

    def test_empty_runs_directory_returns_empty_list(self, tmp_path: Path):
        """Empty runs directory returns empty list without failure."""
        runs_root = os.path.join(str(tmp_path), ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        summaries = list_run_evidence_summaries(runs_root)
        assert len(summaries) == 0

    def test_missing_runs_directory_returns_empty_list(self, tmp_path: Path):
        """Missing runs directory returns empty list without failure."""
        runs_root = os.path.join(str(tmp_path), ".ariadne", "runs")
        summaries = list_run_evidence_summaries(runs_root)
        assert len(summaries) == 0

    def test_complete_run_is_summarized(self, tmp_path: Path):
        """Complete run with run.json, manifest.json, and run-report.txt is summarized."""
        paths = _create_complete_run(str(tmp_path))
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert s.run_id == "test-run-001"
        assert s.status == "completed"
        assert s.pipeline_status == "completed"
        assert s.git_boundary_status == "approved"
        assert s.execution_attempted is True
        assert s.created_at is not None
        assert s.run_json_path is not None
        assert s.manifest_path is not None
        assert s.run_report_path is not None
        assert len(s.missing_evidence) == 0
        assert len(s.malformed_evidence) == 0

    def test_missing_manifest_reported(self, tmp_path: Path):
        """Missing manifest is reported as missing evidence."""
        paths = _create_complete_run(str(tmp_path), include_manifest=False)
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert "manifest.json" in s.missing_evidence

    def test_missing_run_report_reported(self, tmp_path: Path):
        """Missing run-report is reported as missing evidence."""
        paths = _create_complete_run(str(tmp_path), include_report=False)
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert "run-report.txt" in s.missing_evidence

    def test_malformed_run_json_reported(self, tmp_path: Path):
        """Malformed run.json is reported as malformed evidence."""
        paths = _create_malformed_run_json(str(tmp_path))
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert "run.json" in s.malformed_evidence

    def test_pr_url_surfaced_when_present(self, tmp_path: Path):
        """PR URL is surfaced only when present in persisted evidence."""
        paths = _create_complete_run(str(tmp_path), include_pr_url=True)
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert s.pr_url == "https://github.com/owner/repo/pull/123"

    def test_no_pr_url_fabricated(self, tmp_path: Path):
        """No PR URL is fabricated when absent."""
        paths = _create_complete_run(str(tmp_path), include_pr_url=False)
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        s = summaries[0]
        assert s.pr_url is None

    def test_deterministic_ordering(self, tmp_path: Path):
        """Runs are sorted deterministically (newest first by run_id)."""
        runs_root = os.path.join(str(tmp_path), ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        _create_complete_run(str(tmp_path), run_id="run-003")
        _create_complete_run(str(tmp_path), run_id="run-001")
        _create_complete_run(str(tmp_path), run_id="run-002")
        summaries = list_run_evidence_summaries(runs_root)
        assert len(summaries) == 3
        # Reverse sort: run-003, run-002, run-001
        assert summaries[0].run_id == "run-003"
        assert summaries[1].run_id == "run-002"
        assert summaries[2].run_id == "run-001"


# ---------------------------------------------------------------------------
# Tests: read_run_evidence_detail
# ---------------------------------------------------------------------------


class TestReadRunEvidenceDetail:
    """Tests for reading a single run detail."""

    def test_complete_run_detail_includes_execution_results(self, tmp_path: Path):
        """Run detail includes execution results from run.json."""
        paths = _create_complete_run(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.detail is not None
        assert len(result.detail.execution_results) > 0
        ops = [r["operation"] for r in result.detail.execution_results]
        assert "git_status" in ops
        assert "git_add" in ops
        assert "git_commit" in ops
        assert "git_push" in ops

    def test_complete_run_detail_includes_manifest_files(self, tmp_path: Path):
        """Run detail includes manifest file list."""
        paths = _create_complete_run(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.detail is not None
        assert "run.json" in result.detail.manifest_files
        assert "run-report.txt" in result.detail.manifest_files

    def test_complete_run_detail_includes_report_preview(self, tmp_path: Path):
        """Run detail includes run-report path or preview."""
        paths = _create_complete_run(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.detail is not None
        assert result.detail.report_preview is not None
        assert "Ariadne Run Report" in result.detail.report_preview

    def test_missing_manifest_reported_in_detail(self, tmp_path: Path):
        """Missing manifest is reported as missing evidence in detail."""
        paths = _create_complete_run(str(tmp_path), include_manifest=False)
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is False
        assert len(result.missing) > 0
        assert any("manifest.json" in n.expected_path for n in result.missing)

    def test_missing_run_report_reported_in_detail(self, tmp_path: Path):
        """Missing run-report is reported as missing evidence in detail."""
        paths = _create_complete_run(str(tmp_path), include_report=False)
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is False
        assert len(result.missing) > 0
        assert any("run-report.txt" in n.expected_path for n in result.missing)

    def test_malformed_run_json_reported_in_detail(self, tmp_path: Path):
        """Malformed run.json is reported as malformed evidence in detail."""
        paths = _create_malformed_run_json(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "malformed-run")
        assert result.ok is False
        assert len(result.malformed) > 0
        assert any("run.json" in n.expected_path for n in result.malformed)

    def test_malformed_manifest_reported_in_detail(self, tmp_path: Path):
        """Malformed manifest.json is reported as malformed evidence in detail."""
        paths = _create_malformed_manifest(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "malformed-manifest")
        assert result.ok is False
        assert len(result.malformed) > 0
        assert any("manifest.json" in n.expected_path for n in result.malformed)

    def test_pr_url_in_detail_when_present(self, tmp_path: Path):
        """PR URL is surfaced in detail when present in persisted evidence."""
        paths = _create_complete_run(str(tmp_path), include_pr_url=True)
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.summary is not None
        assert result.summary.pr_url == "https://github.com/owner/repo/pull/123"

    def test_no_pr_url_in_detail_when_absent(self, tmp_path: Path):
        """No PR URL in detail when absent from persisted evidence."""
        paths = _create_complete_run(str(tmp_path), include_pr_url=False)
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.summary is not None
        assert result.summary.pr_url is None

    def test_detail_includes_evidence_paths(self, tmp_path: Path):
        """Run detail includes evidence paths."""
        paths = _create_complete_run(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.detail is not None
        assert len(result.detail.evidence_paths) > 0
        assert any("run.json" in p for p in result.detail.evidence_paths)
        assert any("manifest.json" in p for p in result.detail.evidence_paths)
        assert any("run-report.txt" in p for p in result.detail.evidence_paths)

    def test_detail_includes_run_json_hash(self, tmp_path: Path):
        """Run detail includes run_json_hash when available."""
        paths = _create_complete_run(str(tmp_path))
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True
        assert result.detail is not None
        assert result.detail.run_json_hash is not None

    def test_nonexistent_run_id_returns_not_ok(self, tmp_path: Path):
        """Nonexistent run_id returns not-ok result."""
        runs_root = os.path.join(str(tmp_path), ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        result = read_run_evidence_detail(runs_root, "nonexistent-run")
        assert result.ok is False
        assert result.summary is None
        assert result.detail is None


# ---------------------------------------------------------------------------
# Tests: safety and isolation
# ---------------------------------------------------------------------------


class TestReadModelSafety:
    """Tests for read model safety guarantees."""

    def test_reader_uses_explicit_tmp_roots(self, tmp_path: Path):
        """Reader uses explicit tmp roots in tests."""
        runs_root = os.path.join(str(tmp_path), ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        summaries = list_run_evidence_summaries(runs_root)
        assert len(summaries) == 0
        # Verify no real project .ariadne was accessed
        assert not os.path.exists(os.path.join(os.getcwd(), ".ariadne", "runs"))

    def test_reader_does_not_shell_out(self):
        """Reader does not shell out."""
        import inspect
        from runner.runtime_evidence import (
            list_run_evidence_summaries,
            read_run_evidence_detail,
        )
        source = inspect.getsource(list_run_evidence_summaries)
        source += inspect.getsource(read_run_evidence_detail)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "shell=True" not in source
        assert "git add" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "gh pr create" not in source
        assert "import docker" not in source

    def test_reader_does_not_mutate_files(self, tmp_path: Path):
        """Reader does not mutate files."""
        paths = _create_complete_run(str(tmp_path))
        # Record file hashes before reading
        import hashlib
        hashes_before: dict[str, str] = {}
        for fname in ["run.json", "manifest.json", "run-report.txt"]:
            fpath = os.path.join(paths["run_dir"], fname)
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    hashes_before[fname] = hashlib.sha256(f.read()).hexdigest()

        # Read
        list_run_evidence_summaries(paths["runs_root"])
        read_run_evidence_detail(paths["runs_root"], "test-run-001")

        # Verify hashes unchanged
        for fname, hash_before in hashes_before.items():
            fpath = os.path.join(paths["run_dir"], fname)
            with open(fpath, "rb") as f:
                hash_after = hashlib.sha256(f.read()).hexdigest()
            assert hash_after == hash_before, f"File was mutated: {fname}"

    def test_reader_does_not_invoke_run_ariadne_task(self):
        """Reader does not invoke run_ariadne_task."""
        import inspect
        from runner.runtime_evidence import (
            list_run_evidence_summaries,
            read_run_evidence_detail,
        )
        source = inspect.getsource(list_run_evidence_summaries)
        source += inspect.getsource(read_run_evidence_detail)
        assert "run_ariadne_task" not in source

    def test_reader_does_not_require_real_git_repo(self, tmp_path: Path):
        """Reader does not require real git repo."""
        paths = _create_complete_run(str(tmp_path))
        summaries = list_run_evidence_summaries(paths["runs_root"])
        assert len(summaries) == 1
        result = read_run_evidence_detail(paths["runs_root"], "test-run-001")
        assert result.ok is True

    def test_tests_do_not_use_real_project_ariadne(self, tmp_path: Path):
        """Tests do not use real project .ariadne."""
        # Verify no real .ariadne/runs exists in the project
        real_ariadne_runs = os.path.join(os.getcwd(), ".ariadne", "runs")
        assert not os.path.exists(real_ariadne_runs), (
            "Test would accidentally read real .ariadne/runs"
        )


# ---------------------------------------------------------------------------
# Tests: type structure validation
# ---------------------------------------------------------------------------


class TestTypeStructures:
    """Tests for type structure correctness."""

    def test_run_evidence_summary_fields(self):
        """RunEvidenceSummary has all required fields."""
        s = RunEvidenceSummary(
            run_id="test",
            status="completed",
            reason_codes=(),
            pipeline_status=None,
            git_boundary_status=None,
            execution_attempted=False,
            created_at=None,
            run_json_path=None,
            manifest_path=None,
            run_report_path=None,
            pr_url=None,
            missing_evidence=(),
            malformed_evidence=(),
        )
        assert s.run_id == "test"
        assert s.status == "completed"

    def test_run_evidence_detail_fields(self):
        """RunEvidenceDetail has all required fields."""
        s = RunEvidenceSummary(
            run_id="test",
            status="completed",
            reason_codes=(),
            pipeline_status=None,
            git_boundary_status=None,
            execution_attempted=False,
            created_at=None,
            run_json_path=None,
            manifest_path=None,
            run_report_path=None,
            pr_url=None,
            missing_evidence=(),
            malformed_evidence=(),
        )
        d = RunEvidenceDetail(
            summary=s,
            execution_results=(),
            manifest_files=(),
            run_json_hash=None,
            report_preview=None,
            payload_cleanliness=None,
            readiness=None,
            evidence_paths=(),
            source_errors=(),
        )
        assert d.summary.run_id == "test"
        assert len(d.execution_results) == 0

    def test_artifact_evidence_ref_fields(self):
        """ArtifactEvidenceRef has all required fields."""
        ref = ArtifactEvidenceRef(
            path="/some/path",
            exists=True,
            file_size=100,
            description="test artifact",
        )
        assert ref.path == "/some/path"
        assert ref.exists is True
        assert ref.file_size == 100

    def test_missing_evidence_notice_fields(self):
        """MissingEvidenceNotice has all required fields."""
        notice = MissingEvidenceNotice(
            expected_path="/some/path",
            reason="file_not_found",
        )
        assert notice.expected_path == "/some/path"
        assert notice.reason == "file_not_found"

    def test_runtime_evidence_read_result_fields(self):
        """RuntimeEvidenceReadResult has all required fields."""
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        assert result.ok is True
        assert result.error is None
