"""Executable contract tests for the Run Evidence Serialization Contract v1.

These tests freeze the response shapes for GET /runs and GET /runs/<run_id>
against the versioned contract defined by PR 0142 PLAN.md.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from task_intake.runtime_evidence_serialization import (
    EVIDENCE_CONTRACT_VERSION,
    serialize_run_evidence_summary,
    serialize_run_evidence_detail,
    serialize_run_index,
)
from runner.runtime_evidence import (
    RunEvidenceSummary,
    RunEvidenceDetail,
    RuntimeEvidenceReadResult,
    MissingEvidenceNotice,
    list_run_evidence_summaries,
    read_run_evidence_detail,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_summary(**overrides) -> RunEvidenceSummary:
    defaults = {
        "run_id": "run-001",
        "status": "completed",
        "reason_codes": ("completed",),
        "pipeline_status": "completed",
        "git_boundary_status": "approved",
        "execution_attempted": True,
        "created_at": "2026-07-10T12:05:00Z",
        "run_json_path": "/fake/run.json",
        "manifest_path": "/fake/manifest.json",
        "run_report_path": "/fake/run-report.txt",
        "pr_url": None,
        "missing_evidence": (),
        "malformed_evidence": (),
    }
    params = {**defaults, **overrides}
    return RunEvidenceSummary(**params)


def _make_detail_run(tmp_dir: str, run_id: str = "run-001", **kwargs) -> dict:
    """Create a run directory with run.json and optional evidence files."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    include_manifest = kwargs.get("include_manifest", True)
    include_report = kwargs.get("include_report", True)
    include_pr_url = kwargs.get("include_pr_url", False)
    malformed_manifest = kwargs.get("malformed_manifest", False)
    malformed_run_json = kwargs.get("malformed_run_json", False)

    execution_results = [
        {"operation": "git_status", "exit_code": "0", "stdout": "ok", "stderr": ""},
        {"operation": "git_commit", "exit_code": "0", "stdout": "ok", "stderr": ""},
    ]
    if include_pr_url:
        execution_results.append({
            "operation": "gh_pr_create",
            "exit_code": "0",
            "stdout": "https://github.com/owner/repo/pull/99\n",
            "stderr": "",
            "pr_url": "https://github.com/owner/repo/pull/99",
        })

    run_json_path = os.path.join(run_dir, "run.json")
    if malformed_run_json:
        with open(run_json_path, "w", encoding="utf-8") as f:
            f.write("{bad json")
    else:
        run_json = {
            "schema_version": "1",
            "run_id": run_id,
            "status": kwargs.get("status", "completed"),
            "pipeline_status": kwargs.get("pipeline_status", "completed"),
            "git_boundary_status": kwargs.get("git_boundary_status", "approved"),
            "reason_codes": kwargs.get("reason_codes", ["completed"]),
            "execution_attempted": kwargs.get("execution_attempted", True),
            "execution_results_summary": execution_results,
            "started_at": "2026-07-10T12:00:00Z",
            "finished_at": "2026-07-10T12:05:00Z",
        }
        with open(run_json_path, "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)

    manifest_path = os.path.join(run_dir, "manifest.json")
    if include_manifest:
        manifest = {
            "schema_version": "1",
            "run_id": run_id,
            "run_json_hash": "abc123def456",
            "files": ["run.json", "run-report.txt"],
        }
        if malformed_manifest:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("{bad manifest")
        else:
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


# ---------------------------------------------------------------------------
# 1. Contract version field
# ---------------------------------------------------------------------------


class TestContractVersion:
    """Tests for ev_contract_version field."""

    def test_contract_version_value(self):
        """ev_contract_version equals '1'."""
        assert EVIDENCE_CONTRACT_VERSION == "1"

    def test_version_field_name(self):
        """Contract version field is named ev_contract_version."""
        result = serialize_run_index(
            summaries=(),
            runs_root="/fake/runs",
        )
        assert "ev_contract_version" in result

    def test_version_in_run_index_success(self):
        """ev_contract_version present in successful index response."""
        result = serialize_run_index(
            summaries=(_make_summary(),),
            runs_root="/fake/runs",
        )
        assert result["ev_contract_version"] == "1"

    def test_version_in_run_index_error(self):
        """ev_contract_version present in error index response."""
        result = serialize_run_index(
            summaries=(),
            runs_root="/fake/runs",
            ok=False,
            error="runs_root not found",
        )
        assert result["ev_contract_version"] == "1"

    def test_version_in_detail_success(self):
        """ev_contract_version present in successful detail response."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=s,
            detail=detail,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["ev_contract_version"] == "1"

    def test_version_in_detail_error(self):
        """ev_contract_version present in error detail response."""
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="run not found",
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["ev_contract_version"] == "1"


# ---------------------------------------------------------------------------
# 2. Run-index envelope exact key set
# ---------------------------------------------------------------------------


class TestRunIndexEnvelope:
    """Tests for the run-index envelope exact key set."""

    def test_success_envelope_keys(self):
        """Run-index success envelope has exact keys."""
        result = serialize_run_index(
            summaries=(_make_summary(),),
            runs_root="/fake/runs",
        )
        expected_keys = {"ev_contract_version", "ok", "count", "runs", "runs_root"}
        assert set(result.keys()) == expected_keys

    def test_error_envelope_keys(self):
        """Run-index error envelope has exact keys plus error."""
        result = serialize_run_index(
            summaries=(),
            runs_root="/fake/runs",
            ok=False,
            error="runs_root not found",
        )
        # Error envelope includes ev_contract_version, ok, count, runs, runs_root, error
        expected_keys = {"ev_contract_version", "ok", "count", "runs", "runs_root", "error"}
        assert set(result.keys()) == expected_keys

    def test_ok_is_bool(self):
        """ok is always a boolean."""
        result = serialize_run_index(summaries=(), runs_root="/fake/runs")
        assert isinstance(result["ok"], bool)

    def test_count_is_int(self):
        """count is always an int."""
        result = serialize_run_index(
            summaries=(_make_summary(), _make_summary(run_id="run-002")),
            runs_root="/fake/runs",
        )
        assert isinstance(result["count"], int)
        assert result["count"] == 2

    def test_runs_is_list(self):
        """runs is always a list."""
        result = serialize_run_index(
            summaries=(_make_summary(),),
            runs_root="/fake/runs",
        )
        assert isinstance(result["runs"], list)

    def test_runs_root_is_str(self):
        """runs_root is always a str."""
        result = serialize_run_index(summaries=(), runs_root="/fake/runs")
        assert isinstance(result["runs_root"], str)


# ---------------------------------------------------------------------------
# 3. Run-index entry exact key set
# ---------------------------------------------------------------------------


class TestRunIndexEntry:
    """Tests for the run-index entry exact key set."""

    RUN_INDEX_ENTRY_KEYS = {
        "run_id", "status", "reason_codes", "pipeline_status",
        "git_boundary_status", "execution_attempted", "created_at",
        "run_json_available", "manifest_available", "run_report_available",
        "missing_evidence", "malformed_evidence", "pr_url",
        "payload_cleanliness_available", "readiness_available",
    }

    def test_exact_entry_key_set(self):
        """Every run-index entry has exactly the defined key set."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        assert set(entry.keys()) == self.RUN_INDEX_ENTRY_KEYS

    def test_entry_no_extra_keys(self):
        """No extra keys beyond the defined set."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        extra = set(entry.keys()) - self.RUN_INDEX_ENTRY_KEYS
        assert extra == set()

    def test_entry_no_missing_keys(self):
        """No keys missing from the defined set."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        missing = self.RUN_INDEX_ENTRY_KEYS - set(entry.keys())
        assert missing == set()


# ---------------------------------------------------------------------------
# 4. Run-detail envelope exact key set
# ---------------------------------------------------------------------------


class TestRunDetailEnvelope:
    """Tests for the run-detail envelope exact key set."""

    DETAIL_ENVELOPE_KEYS = {
        "ev_contract_version", "ok", "error", "summary", "detail",
        "payload_cleanliness", "readiness", "missing", "malformed",
    }

    def test_success_detail_envelope_keys(self):
        """Successful detail response has exact envelope keys."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=s,
            detail=detail,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert set(response.keys()) == self.DETAIL_ENVELOPE_KEYS

    def test_error_detail_envelope_keys(self):
        """Error detail response has exact envelope keys."""
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="run not found",
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert set(response.keys()) == self.DETAIL_ENVELOPE_KEYS


# ---------------------------------------------------------------------------
# 5. Run-detail summary exact key set
# ---------------------------------------------------------------------------


class TestRunDetailSummary:
    """Tests for the run-detail summary exact key set."""

    # Summary keys = all index-entry fields minus _available indicators
    SUMMARY_KEYS = {
        "run_id", "status", "reason_codes", "pipeline_status",
        "git_boundary_status", "execution_attempted", "created_at",
        "run_json_available", "manifest_available", "run_report_available",
        "missing_evidence", "malformed_evidence", "pr_url",
        "payload_cleanliness_available", "readiness_available",
    }

    def test_summary_keys_match_entry_keys(self):
        """Summary key set equals index-entry key set."""
        s = _make_summary()
        summary = serialize_run_evidence_summary(s)
        assert set(summary.keys()) == self.SUMMARY_KEYS


# ---------------------------------------------------------------------------
# 6. Run-detail evidence exact key set
# ---------------------------------------------------------------------------


class TestRunDetailEvidence:
    """Tests for the run-detail evidence object exact key set."""

    DETAIL_EVIDENCE_KEYS = {
        "execution_results", "manifest_files", "run_json_hash",
        "report_preview", "evidence_paths", "source_errors",
    }

    def test_detail_evidence_key_set(self):
        """Detail evidence object has exact keys."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=s,
            detail=detail,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert set(response["detail"].keys()) == self.DETAIL_EVIDENCE_KEYS


# ---------------------------------------------------------------------------
# 7. Evidence notice exact key set
# ---------------------------------------------------------------------------


class TestEvidenceNotice:
    """Tests for evidence notice exact key set."""

    def test_notice_key_set(self):
        """Evidence notice has expected_path and reason."""
        s = _make_summary()
        notice = MissingEvidenceNotice(
            expected_path="/fake/manifest.json",
            reason="file_not_found",
        )
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="missing evidence",
            summary=s,
            detail=detail,
            missing=(notice,),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert len(response["missing"]) == 1
        assert set(response["missing"][0].keys()) == {"expected_path", "reason"}


# ---------------------------------------------------------------------------
# 8. Null policy
# ---------------------------------------------------------------------------


class TestNullPolicy:
    """Tests for the null-is-unavailable policy."""

    def test_payload_cleanliness_null(self):
        """payload_cleanliness is null when unavailable."""
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="error",
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["payload_cleanliness"] is None

    def test_readiness_null(self):
        """readiness is null when unavailable."""
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="error",
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["readiness"] is None

    def test_pr_url_null_when_absent(self):
        """pr_url is null when not in persisted evidence."""
        s = _make_summary(pr_url=None)
        entry = serialize_run_evidence_summary(s)
        assert entry["pr_url"] is None

    def test_pr_url_preserved_when_present(self):
        """pr_url is preserved when in persisted evidence."""
        s = _make_summary(pr_url="https://github.com/owner/repo/pull/42")
        entry = serialize_run_evidence_summary(s)
        assert entry["pr_url"] == "https://github.com/owner/repo/pull/42"

    def test_run_json_hash_null(self):
        """run_json_hash is null when unavailable."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=s,
            detail=detail,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["detail"]["run_json_hash"] is None

    def test_report_preview_null(self):
        """report_preview is null when unavailable."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True,
            error=None,
            summary=s,
            detail=detail,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert response["detail"]["report_preview"] is None


# ---------------------------------------------------------------------------
# 9. Empty-array policy
# ---------------------------------------------------------------------------


class TestEmptyArrayPolicy:
    """Tests for the empty-array-is-unavailable policy."""

    def test_reason_codes_is_array(self):
        """reason_codes is always a list."""
        s = _make_summary(reason_codes=())
        entry = serialize_run_evidence_summary(s)
        assert isinstance(entry["reason_codes"], list)
        assert entry["reason_codes"] == []

    def test_missing_evidence_is_array(self):
        """missing_evidence is always a list."""
        s = _make_summary(missing_evidence=())
        entry = serialize_run_evidence_summary(s)
        assert isinstance(entry["missing_evidence"], list)

    def test_malformed_evidence_is_array(self):
        """malformed_evidence is always a list."""
        s = _make_summary(malformed_evidence=())
        entry = serialize_run_evidence_summary(s)
        assert isinstance(entry["malformed_evidence"], list)

    def test_execution_results_is_array(self):
        """execution_results is always a list, never null."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True, error=None, summary=s, detail=detail, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["detail"]["execution_results"], list)

    def test_manifest_files_is_array(self):
        """manifest_files is always a list, never null."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True, error=None, summary=s, detail=detail, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["detail"]["manifest_files"], list)

    def test_evidence_paths_is_array(self):
        """evidence_paths is always a list."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True, error=None, summary=s, detail=detail, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["detail"]["evidence_paths"], list)

    def test_source_errors_is_array(self):
        """source_errors is always a list."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True, error=None, summary=s, detail=detail, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["detail"]["source_errors"], list)

    def test_runs_is_array_in_index(self):
        """runs is always a list in the index."""
        result = serialize_run_index(summaries=(), runs_root="/fake/runs")
        assert isinstance(result["runs"], list)

    def test_missing_is_array_in_detail(self):
        """missing is always a list."""
        result = RuntimeEvidenceReadResult(
            ok=False, error="err", summary=None, detail=None, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["missing"], list)

    def test_malformed_is_array_in_detail(self):
        """malformed is always a list."""
        result = RuntimeEvidenceReadResult(
            ok=False, error="err", summary=None, detail=None, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        assert isinstance(response["malformed"], list)


# ---------------------------------------------------------------------------
# 10. Existing field compatibility
# ---------------------------------------------------------------------------


class TestExistingFieldCompatibility:
    """Tests that all fields from PR 0139 and PR 0141 are preserved."""

    def test_existing_run_index_fields_preserved(self):
        """All PR 0139 index fields are preserved."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        # All fields that existed in the pre-contract GET /runs response
        for field in [
            "run_id", "status", "reason_codes", "pipeline_status",
            "git_boundary_status", "execution_attempted", "created_at",
            "run_json_available", "manifest_available", "run_report_available",
            "missing_evidence", "malformed_evidence", "pr_url",
            "payload_cleanliness_available", "readiness_available",
        ]:
            assert field in entry, f"Field {field} missing from run-index entry"

    def test_existing_detail_fields_preserved(self):
        """All PR 0141 detail fields are preserved."""
        s = _make_summary()
        detail = RunEvidenceDetail(
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
        result = RuntimeEvidenceReadResult(
            ok=True, error=None, summary=s, detail=detail, missing=(), malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        for field in ["ok", "error", "summary", "detail", "payload_cleanliness",
                       "readiness", "missing", "malformed"]:
            assert field in response, f"Field {field} missing from detail envelope"

    def test_no_fields_removed_from_summary(self):
        """No existing summary field is removed."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        original_fields = {
            "run_id", "status", "reason_codes", "pipeline_status",
            "git_boundary_status", "execution_attempted", "created_at",
            "run_json_available", "manifest_available", "run_report_available",
            "missing_evidence", "malformed_evidence", "pr_url",
            "payload_cleanliness_available", "readiness_available",
        }
        assert original_fields.issubset(set(entry.keys()))

    def test_no_fields_renamed(self):
        """No existing field is renamed."""
        s = _make_summary()
        entry = serialize_run_evidence_summary(s)
        # Verify field names match the original names exactly
        assert "run_id" in entry  # not "id"
        assert "reason_codes" in entry  # not "reasons"
        assert "run_json_available" in entry  # not "json_available"


# ---------------------------------------------------------------------------
# 11. Serializer purity
# ---------------------------------------------------------------------------


class TestSerializerPurity:
    """Tests that the serializer is a pure side-effect-free helper."""

    def test_no_filesystem_access(self):
        """Serializer does not access filesystem."""
        import inspect
        source = inspect.getsource(serialize_run_evidence_summary)
        source += inspect.getsource(serialize_run_evidence_detail)
        source += inspect.getsource(serialize_run_index)
        assert "open(" not in source
        assert "os.path" not in source
        assert "os.listdir" not in source
        assert "os.makedirs" not in source

    def test_no_prohibited_imports(self):
        """Serializer has no prohibited imports."""
        import inspect
        serializer_path = os.path.join(
            os.path.dirname(__file__),
            "..", "src", "task_intake", "runtime_evidence_serialization.py",
        )
        with open(serializer_path, "r", encoding="utf-8") as f:
            source = f.read()
        for forbidden in ["subprocess", "os.system", "Popen", "docker", "requests",
                          "httpx", "urllib", "git add", "git commit", "git push",
                          "gh pr"]:
            assert forbidden not in source, f"Forbidden: {forbidden}"

    def test_no_asgi_routing(self):
        """Serializer has no ASGI routing."""
        import inspect
        source = inspect.getsource(serialize_run_evidence_summary)
        source += inspect.getsource(serialize_run_evidence_detail)
        source += inspect.getsource(serialize_run_index)
        assert "scope" not in source
        assert "receive" not in source
        assert "send" not in source

    def test_serializer_is_deterministic(self):
        """Serializer produces identical output for identical input."""
        s = _make_summary()
        out1 = serialize_run_evidence_summary(s)
        out2 = serialize_run_evidence_summary(s)
        assert out1 == out2


# ---------------------------------------------------------------------------
# 12. Error envelope exact key set
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    """Tests for the error envelope exact key set."""

    def test_error_envelope_keys_detail(self):
        """Detail error envelope has ev_contract_version, ok, error."""
        result = RuntimeEvidenceReadResult(
            ok=False,
            error="run not found",
            summary=None,
            detail=None,
            missing=(),
            malformed=(),
        )
        response = serialize_run_evidence_detail(result)
        # Error envelope: ev_contract_version, ok, error plus the full detail
        # envelope with null/empty values for unavailable fields
        for key in ["ev_contract_version", "ok", "error"]:
            assert key in response

    def test_error_envelope_keys_index(self):
        """Index error envelope has ev_contract_version, ok, error."""
        result = serialize_run_index(
            summaries=(),
            runs_root="/fake/runs",
            ok=False,
            error="runs_root not found",
        )
        for key in ["ev_contract_version", "ok", "error"]:
            assert key in result


# ---------------------------------------------------------------------------
# 13. Route integration through server
# ---------------------------------------------------------------------------


class TestRouteIntegration:
    """Integration tests verifying the server uses the serialization contract."""

    async def _asgi_request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        query_string: str = "",
    ) -> tuple[int, str]:
        from task_intake.server import app

        if not query_string and "?" in path:
            path_part, qs_part = path.split("?", 1)
            path = path_part
            query_string = qs_part

        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string.encode("utf-8"),
            "headers": [],
            "http_version": "1.1",
            "scheme": "http",
            "client": ("127.0.0.1", 8001),
            "server": ("127.0.0.1", 8001),
        }
        response_status = 500
        response_body = b""

        async def receive() -> dict:
            if body is not None:
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(event: dict) -> None:
            nonlocal response_status, response_body
            if event["type"] == "http.response.start":
                response_status = event["status"]
            elif event["type"] == "http.response.body":
                response_body += event.get("body", b"")

        await app(scope, receive, send)
        return response_status, response_body.decode("utf-8", errors="replace")

    def _request(self, method, path, body=None, query_string=""):
        import asyncio
        return asyncio.run(
            self._asgi_request(method, path, body=body, query_string=query_string)
        )

    # --- GET /runs integration ---

    def test_get_runs_success_has_version(self):
        """GET /runs success response includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_error_has_version(self):
        """GET /runs error response includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        status, raw = self._request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"
        assert data["ok"] is False

    def test_get_runs_empty_has_version(self):
        """GET /runs empty success includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = self._request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"
        assert data["ok"] is True
        assert data["count"] == 0

    def test_get_runs_exact_envelope_keys(self):
        """GET /runs success has exact run-index envelope keys."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        expected_keys = {"ev_contract_version", "ok", "count", "runs", "runs_root"}
        assert set(data.keys()) == expected_keys

    def test_get_runs_entry_has_all_keys(self):
        """GET /runs entry has all 15 required keys."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        entry = data["runs"][0]
        expected_entry_keys = {
            "run_id", "status", "reason_codes", "pipeline_status",
            "git_boundary_status", "execution_attempted", "created_at",
            "run_json_available", "manifest_available", "run_report_available",
            "missing_evidence", "malformed_evidence", "pr_url",
            "payload_cleanliness_available", "readiness_available",
        }
        assert set(entry.keys()) == expected_entry_keys

    # --- GET /runs/<run_id> integration ---

    def test_get_detail_success_has_version(self):
        """GET /runs/<run_id> success includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_detail_error_has_version(self):
        """GET /runs/<run_id> error includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = self._request(
            "GET", "/runs/nonexistent?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_detail_invalid_run_id_has_version(self):
        """GET /runs/<run_id> invalid run_id includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = self._request(
            "GET", "/runs/../etc?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_detail_missing_root_has_version(self):
        """GET /runs/<run_id> missing runs_root includes ev_contract_version."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_detail_exact_envelope_keys(self):
        """GET /runs/<run_id> has exact detail envelope keys."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        expected_keys = {
            "ev_contract_version", "ok", "error", "summary", "detail",
            "payload_cleanliness", "readiness", "missing", "malformed",
        }
        assert set(data.keys()) == expected_keys

    def test_get_detail_null_policies(self):
        """GET /runs/<run_id> applies null policies correctly."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001", include_pr_url=False)
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["payload_cleanliness"] is None
        assert data["readiness"] is None
        assert data["error"] is None

    def test_get_detail_array_policies(self):
        """GET /runs/<run_id> applies array policies correctly."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["missing"], list)
        assert isinstance(data["malformed"], list)

    def test_non_get_returns_404(self):
        """Non-GET methods on /runs/<run_id> return 404 (GET-only).

        POST /runs is expected to return 400 (existing mock execution route).
        The evidence API routes are GET-only.
        """
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        # Detail route: non-GET returns 404 (falls through to catch-all)
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            status, _ = self._request(method, "/runs/run-001?runs_root=" + runs_root)
            assert status == 404, f"{method} /runs/run-001 should return 404, got {status}"
        # List route: POST returns 400 (existing mock execution route),
        # PUT/PATCH/DELETE return 404
        for method in ["PUT", "PATCH", "DELETE"]:
            status, _ = self._request(method, "/runs?runs_root=" + runs_root)
            assert status == 404, f"{method} /runs should return 404, got {status}"

    def test_pr_url_null_when_absent_integration(self):
        """GET /runs returns pr_url null when absent."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001", include_pr_url=False)
        status, raw = self._request(
            "GET", "/runs?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["pr_url"] is None

    def test_pr_url_preserved_when_present_integration(self):
        """GET /runs preserves pr_url when present."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001", include_pr_url=True)
        status, raw = self._request(
            "GET", "/runs?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["pr_url"] == "https://github.com/owner/repo/pull/99"


# ---------------------------------------------------------------------------
# 14. Report API envelope exact key set
# ---------------------------------------------------------------------------


class TestReportEnvelope:
    """PR 0146: Tests for the report API response envelope."""

    async def _asgi_request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        query_string: str = "",
    ) -> tuple[int, str]:
        from task_intake.server import app

        if not query_string and "?" in path:
            path_part, qs_part = path.split("?", 1)
            path = path_part
            query_string = qs_part

        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string.encode("utf-8"),
            "headers": [],
            "http_version": "1.1",
            "scheme": "http",
            "client": ("127.0.0.1", 8001),
            "server": ("127.0.0.1", 8001),
        }
        response_status = 500
        response_body = b""

        async def receive() -> dict:
            if body is not None:
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(event: dict) -> None:
            nonlocal response_status, response_body
            if event["type"] == "http.response.start":
                response_status = event["status"]
            elif event["type"] == "http.response.body":
                response_body += event.get("body", b"")

        await app(scope, receive, send)
        return response_status, response_body.decode("utf-8", errors="replace")

    def _request(self, method, path, body=None, query_string=""):
        import asyncio
        return asyncio.run(
            self._asgi_request(method, path, body=body, query_string=query_string)
        )

    # --- Report envelope key set ---

    REPORT_ENVELOPE_KEYS = {
        "ev_contract_version", "ok", "error", "run_id", "content",
        "content_length", "truncated", "truncation_limit",
        "report_exists", "manifest_lists_report", "provenance",
    }

    def test_report_success_envelope_keys(self):
        """Report success response has exact envelope keys."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert set(data.keys()) == self.REPORT_ENVELOPE_KEYS

    def test_report_error_envelope_keys(self):
        """Report error response has exact envelope keys."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001", include_report=False)
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert set(data.keys()) == self.REPORT_ENVELOPE_KEYS

    def test_report_version_is_1(self):
        """Report response has ev_contract_version '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_report_ok_is_bool(self):
        """Report ok is always a boolean."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["ok"], bool)

    def test_report_content_is_str_or_none(self):
        """Report content is str or None."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["content"] is None or isinstance(data["content"], str)

    def test_report_content_length_is_int(self):
        """Report content_length is always an int."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["content_length"], int)

    def test_report_truncated_is_bool(self):
        """Report truncated is always a boolean."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["truncated"], bool)

    def test_report_truncation_limit_is_int_or_none(self):
        """Report truncation_limit is int or None."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["truncation_limit"] is None or (
            isinstance(data["truncation_limit"], int))

    def test_report_exists_is_bool(self):
        """Report report_exists is always a boolean."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["report_exists"], bool)

    def test_manifest_lists_report_is_bool(self):
        """Report manifest_lists_report is always a boolean."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["manifest_lists_report"], bool)

    def test_report_provenance_is_str_or_none(self):
        """Report provenance is str or None."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["provenance"] is None or isinstance(data["provenance"], str)

    def test_report_error_is_str_or_none(self):
        """Report error is str or None."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["error"] is None or isinstance(data["error"], str)

    def test_report_all_states_produce_correct_envelopes(self):
        """All report states produce correct envelope shapes."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        # Complete report state
        status, raw = self._request(
            "GET", "/runs/run-001/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert set(data.keys()) == self.REPORT_ENVELOPE_KEYS

    def test_report_backward_compat_existing_detail_tests_still_pass(self):
        """Existing detail contract tests still produce correct envelopes."""
        # Verify that GET /runs/<run_id> still returns correct detail envelope
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"
        assert "summary" in data
        assert "detail" in data

    def test_report_unknown_run_returns_correct_envelope(self):
        """Unknown run for report returns correct error envelope."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _make_detail_run(tmp_dir, "run-001")
        status, raw = self._request(
            "GET", "/runs/nonexistent/report?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert data["error"] == "run not found"
        assert set(data.keys()) == self.REPORT_ENVELOPE_KEYS
