"""Tests for the execution artifact envelope."""

from __future__ import annotations

import json
import re

from runner.execution_envelope import build_execution_envelope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_request(**overrides: object) -> dict:
    base = {
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "task_intake_id": "task_a1b2c3",
        "context_preview_id": "cp-001",
        "requested_adapter": "noop-v1",
        "execution_mode": "dry_run",
        "inputs": {},
        "constraints": [],
    }
    base.update(overrides)
    return base


def _valid_result(**overrides: object) -> dict:
    base = {
        "execution_result_id": "er-001-result",
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "status": "completed",
        "adapter": "noop-v1",
        "artifacts": [],
        "evidence": [
            {
                "evidence_id": "ev-noop-001",
                "kind": "execution_note",
                "summary": "No real execution performed.",
                "status": "passed",
            },
        ],
        "errors": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid input
# ---------------------------------------------------------------------------


class TestValidEnvelope:
    def test_builds_envelope(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["envelope_id"].startswith("env_")
        assert env["schema_version"] == "0.1"

    def test_includes_request_id(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["execution_request_id"] == "er-001"

    def test_includes_result_id(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["execution_result_id"] == "er-001-result"

    def test_includes_run_id(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["run_id"] == "run-001"

    def test_status_matches_result(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["status"] == "completed"

    def test_artifacts_present(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert isinstance(env["artifacts"], list)

    def test_evidence_present(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert isinstance(env["evidence"], list)

    def test_evidence_preserved(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert len(env["evidence"]) == 1
        assert env["evidence"][0]["evidence_id"] == "ev-noop-001"
        assert env["evidence"][0]["status"] == "passed"

    def test_metadata_includes_adapter(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["metadata"]["adapter"] == "noop-v1"

    def test_metadata_includes_execution_mode(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        assert env["metadata"]["execution_mode"] == "dry_run"

    def test_deterministic(self):
        req = _valid_request()
        res = _valid_result()
        r1 = build_execution_envelope(req, res)
        r2 = build_execution_envelope(req, res)
        assert r1 == r2

    def test_json_serializable(self):
        env = build_execution_envelope(_valid_request(), _valid_result())
        dumped = json.dumps(env, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == env


# ---------------------------------------------------------------------------
# Artifact normalization
# ---------------------------------------------------------------------------


class TestArtifactNormalization:
    def test_artifacts_preserved(self):
        result = _valid_result(artifacts=[{"artifact_id": "art-001", "kind": "patch"}])
        env = build_execution_envelope(_valid_request(), result)
        assert len(env["artifacts"]) == 1
        assert env["artifacts"][0]["artifact_id"] == "art-001"

    def test_missing_artifact_id_filled(self):
        result = _valid_result(artifacts=[{"kind": "patch"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"][0]["artifact_id"] == "artifact-er-001-result-0"

    def test_multiple_artifacts_have_sequential_indices(self):
        result = _valid_result(artifacts=[{}, {}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"][0]["artifact_id"].endswith("-0")
        assert env["artifacts"][1]["artifact_id"].endswith("-1")

    def test_path_aliased_to_relative_path(self):
        result = _valid_result(artifacts=[{"path": "services/x.py"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"][0]["relative_path"] == "services/x.py"

    def test_absolute_path_warning(self):
        result = _valid_result(artifacts=[{"relative_path": "/tmp/secret.txt"}])
        env = build_execution_envelope(_valid_request(), result)
        assert any("absolute" in w.lower() for w in env["warnings"])

    def test_digest_preserved_when_present(self):
        result = _valid_result(artifacts=[{"artifact_id": "a1", "digest": "abc123"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"][0]["digest"] == "abc123"

    def test_non_list_artifacts_treated_as_empty(self):
        result = _valid_result(artifacts=None)
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"] == []

    def test_artifact_producer_defaults(self):
        result = _valid_result(artifacts=[{"artifact_id": "a1"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["artifacts"][0]["producer"] == "execution_adapter"


# ---------------------------------------------------------------------------
# Evidence normalization
# ---------------------------------------------------------------------------


class TestEvidenceNormalization:
    def test_evidence_preserved(self):
        ev = {"evidence_id": "ev-001", "kind": "execution_note", "status": "passed"}
        result = _valid_result(evidence=[ev])
        env = build_execution_envelope(_valid_request(), result)
        assert env["evidence"][0]["evidence_id"] == "ev-001"
        assert env["evidence"][0]["status"] == "passed"

    def test_missing_evidence_id_filled(self):
        result = _valid_result(evidence=[{"kind": "execution_note"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["evidence"][0]["evidence_id"] == "evidence-er-001-result-0"

    def test_non_list_evidence_treated_as_empty(self):
        result = _valid_result(evidence=None)
        env = build_execution_envelope(_valid_request(), result)
        assert env["evidence"] == []

    def test_evidence_producer_defaults(self):
        result = _valid_result(evidence=[{"evidence_id": "e1"}])
        env = build_execution_envelope(_valid_request(), result)
        assert env["evidence"][0]["producer"] == "execution_adapter"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_non_dict_request_returns_error(self):
        env = build_execution_envelope("bad", _valid_result())
        assert len(env["errors"]) > 0
        assert env["status"] == "failed"

    def test_non_dict_result_returns_error(self):
        env = build_execution_envelope(_valid_request(), "bad")
        assert len(env["errors"]) > 0
        assert env["status"] == "failed"

    def test_missing_execution_request_id(self):
        req = _valid_request(execution_request_id="")
        env = build_execution_envelope(req, _valid_result())
        assert any("execution_request_id" in str(e) for e in env["errors"])

    def test_missing_execution_result_id(self):
        res = _valid_result(execution_result_id="")
        env = build_execution_envelope(_valid_request(), res)
        assert any("execution_result_id" in str(e) for e in env["errors"])

    def test_missing_run_id(self):
        req = _valid_request(run_id="")
        env = build_execution_envelope(req, _valid_result())
        assert any("run_id" in str(e) for e in env["errors"])

    def test_error_envelope_has_empty_id(self):
        env = build_execution_envelope("bad", _valid_result())
        assert env["envelope_id"] == ""


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import inspect
        source = inspect.getsource(build_execution_envelope)
        clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "open(" not in clean
        assert "write(" not in clean
        assert "Path(" not in clean
        assert "read_text" not in clean
        assert "write_text" not in clean
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "docker" not in clean.lower()
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "socket" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
        assert "importlib" not in clean
        assert "pkg_resources" not in clean
        assert "entry_points" not in clean
        assert "uuid" not in clean
        assert "datetime.now" not in clean
        assert "time.time" not in clean
        assert "random" not in clean
