"""Tests for the docker run artifacts module."""

from __future__ import annotations

import json

from runner.docker_run_artifacts import build_docker_artifacts, build_docker_evidence


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _command_metadata(**overrides: object) -> dict:
    base = {
        "container_image": "ariadne-agent-base:latest",
        "container_command": ["agent", "run", "--run-id", "run-001", "--request-id", "er-001"],
        "workdir": "/workspace",
        "volumes": {
            "/host/project": {"bind": "/workspace", "mode": "rw"},
        },
        "environment": {
            "ARIADNE_RUN_ID": "run-001",
            "ARIADNE_REQUEST_ID": "er-001",
            "ARIADNE_MODE": "execute",
            "ARIADNE_TASK_GOAL": "Implement JWT auth",
        },
        "network_mode": "bridge",
        "memory_limit": "4g",
        "cpu_count": 2,
        "timeout_seconds": 300,
    }
    base.update(overrides)
    return base


def _successful_result(**overrides: object) -> dict:
    base = {
        "exit_code": 0,
        "stdout": "Build succeeded.",
        "stderr": "",
        "success": True,
    }
    base.update(overrides)
    return base


def _failing_result(**overrides: object) -> dict:
    base = {
        "exit_code": 1,
        "stdout": "",
        "stderr": "Container exited with error.",
        "success": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Artifact shapes
# ---------------------------------------------------------------------------


class TestArtifactShape:
    def test_completed_returns_four_artifacts(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        assert len(artifacts) == 4

    def test_failed_returns_four_artifacts(self):
        artifacts = build_docker_artifacts(
            _failing_result(),
            _command_metadata(),
            "er-001",
        )
        assert len(artifacts) == 4

    def test_blocked_returns_one_artifact(self):
        artifacts = build_docker_artifacts(
            {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
            _command_metadata(),
            "er-001",
        )
        assert len(artifacts) == 1
        assert artifacts[0]["kind"] == "docker_command_metadata"

    def test_completed_has_stdout_kind(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        kinds = [a["kind"] for a in artifacts]
        assert "docker_stdout" in kinds

    def test_completed_has_stderr_kind(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        kinds = [a["kind"] for a in artifacts]
        assert "docker_stderr" in kinds

    def test_completed_has_exec_metadata_kind(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        kinds = [a["kind"] for a in artifacts]
        assert "docker_execution_metadata" in kinds

    def test_completed_has_command_meta_kind(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        kinds = [a["kind"] for a in artifacts]
        assert "docker_command_metadata" in kinds


# ---------------------------------------------------------------------------
# Artifact content
# ---------------------------------------------------------------------------


class TestArtifactContent:
    def test_stdout_content_matches(self):
        artifacts = build_docker_artifacts(
            _successful_result(stdout="Hello world"),
            _command_metadata(),
            "er-001",
        )
        stdout_artifact = [a for a in artifacts if a["kind"] == "docker_stdout"][0]
        assert stdout_artifact["content"] == "Hello world"

    def test_stderr_content_matches(self):
        artifacts = build_docker_artifacts(
            _failing_result(stderr="Error occurred"),
            _command_metadata(),
            "er-001",
        )
        stderr_artifact = [a for a in artifacts if a["kind"] == "docker_stderr"][0]
        assert stderr_artifact["content"] == "Error occurred"


# ---------------------------------------------------------------------------
# Bounding
# ---------------------------------------------------------------------------


class TestBounding:
    def test_stdout_truncated_when_over_limit(self):
        long_output = "x" * 15_000
        artifacts = build_docker_artifacts(
            _successful_result(stdout=long_output),
            _command_metadata(),
            "er-001",
        )
        stdout_artifact = [a for a in artifacts if a["kind"] == "docker_stdout"][0]
        # 10k chars + "\n... [truncated at 10000 characters]" (36 chars) = 10036
        assert len(stdout_artifact["content"]) == 10_036
        assert "[truncated at 10000 characters]" in stdout_artifact["content"]

    def test_stderr_truncated_when_over_limit(self):
        long_output = "y" * 20_000
        artifacts = build_docker_artifacts(
            _failing_result(stderr=long_output),
            _command_metadata(),
            "er-001",
        )
        stderr_artifact = [a for a in artifacts if a["kind"] == "docker_stderr"][0]
        assert "[truncated at 10000 characters]" in stderr_artifact["content"]

    def test_short_stdout_not_truncated(self):
        artifacts = build_docker_artifacts(
            _successful_result(stdout="short"),
            _command_metadata(),
            "er-001",
        )
        stdout_artifact = [a for a in artifacts if a["kind"] == "docker_stdout"][0]
        assert stdout_artifact["content"] == "short"


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


class TestRedaction:
    def test_no_environment_values_in_exec_metadata(self):
        cmd = _command_metadata(
            environment={
                "ARIADNE_RUN_ID": "run-001",
                "ARIADNE_REQUEST_ID": "er-001",
                "ARIADNE_MODE": "execute",
                "ARIADNE_TASK_GOAL": "secret-task-details",
            },
        )
        artifacts = build_docker_artifacts(
            _successful_result(),
            cmd,
            "er-001",
        )
        meta = [a for a in artifacts if a["kind"] == "docker_execution_metadata"][0]
        content = meta["content"]
        env_keys = content["environment_keys"]
        assert isinstance(env_keys, list)
        # Should only contain safe keys, not ARIADNE_TASK_GOAL
        assert "ARIADNE_TASK_GOAL" not in env_keys
        assert "ARIADNE_RUN_ID" in env_keys
        assert content["env_var_count"] == 3  # only safe keys counted

    def test_no_raw_environment_values_in_command_meta(self):
        cmd = _command_metadata(
            environment={
                "ARIADNE_RUN_ID": "run-001",
                "ARIADNE_REQUEST_ID": "er-001",
                "SECRET_TOKEN": "s3cr3t!",
            },
        )
        artifacts = build_docker_artifacts(
            _successful_result(),
            cmd,
            "er-001",
        )
        meta = [a for a in artifacts if a["kind"] == "docker_command_metadata"][0]
        content = meta["content"]
        # env_var_keys lists key names only, not values
        assert "s3cr3t" not in json.dumps(content)

    def test_volume_host_paths_absent(self):
        cmd = _command_metadata(
            volumes={
                "/home/user/secret-project": {"bind": "/workspace", "mode": "rw"},
            },
        )
        artifacts = build_docker_artifacts(
            _successful_result(),
            cmd,
            "er-001",
        )
        meta = [a for a in artifacts if a["kind"] == "docker_command_metadata"][0]
        content = meta["content"]
        # Host path should not appear raw
        assert "/home/user" not in json.dumps(content)
        # Container-side mount point is preserved
        assert "/workspace" in content["volume_mounts"]


# ---------------------------------------------------------------------------
# Evidence shape
# ---------------------------------------------------------------------------


class TestEvidenceShape:
    def test_completed_evidence_passed(self):
        evidence = build_docker_evidence(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        assert len(evidence) == 1
        assert evidence[0]["status"] == "passed"
        assert evidence[0]["evidence_kind"] == "execution_log"

    def test_failed_evidence_failed(self):
        evidence = build_docker_evidence(
            _failing_result(),
            _command_metadata(),
            "er-001",
        )
        assert len(evidence) == 1
        assert evidence[0]["status"] == "failed"
        assert evidence[0]["evidence_kind"] == "execution_log"

    def test_blocked_evidence_skipped(self):
        evidence = build_docker_evidence(
            {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
            _command_metadata(),
            "er-001",
        )
        assert len(evidence) == 1
        assert evidence[0]["status"] == "skipped"
        assert evidence[0]["evidence_kind"] == "execution_note"
        assert "opt-in" in evidence[0]["summary"].lower()


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------


class TestDeterministicIds:
    def test_artifact_ids_deterministic(self):
        a1 = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        a2 = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        for pair in zip(a1, a2):
            assert pair[0]["artifact_id"] == pair[1]["artifact_id"]

    def test_artifact_ids_include_request_id(self):
        artifacts = build_docker_artifacts(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        for a in artifacts:
            assert "er-001" in a["artifact_id"]

    def test_evidence_ids_deterministic(self):
        e1 = build_docker_evidence(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        e2 = build_docker_evidence(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        assert e1[0]["evidence_id"] == e2[0]["evidence_id"]

    def test_blocked_evidence_id(self):
        evidence = build_docker_evidence(
            {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
            _command_metadata(),
            "er-001",
        )
        assert "docker-blocked-evidence" in evidence[0]["evidence_id"]


# ---------------------------------------------------------------------------
# JSON serializable
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_artifacts_json_serializable(self):
        artifacts = build_docker_artifacts(
            _successful_result(stdout="some output"),
            _command_metadata(),
            "er-001",
        )
        dumped = json.dumps(artifacts, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == artifacts

    def test_evidence_json_serializable(self):
        evidence = build_docker_evidence(
            _successful_result(),
            _command_metadata(),
            "er-001",
        )
        dumped = json.dumps(evidence, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == evidence


# ---------------------------------------------------------------------------
# No secrets in blocked evidence
# ---------------------------------------------------------------------------


class TestBlockedNoSecrets:
    def test_blocked_evidence_summary_no_metadata(self):
        evidence = build_docker_evidence(
            {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
            _command_metadata(
                environment={"ARIADNE_TASK_GOAL": "secret-project"},
            ),
            "er-001",
        )
        # The blocked evidence summary should not contain task details
        assert "secret-project" not in evidence[0]["summary"]
        assert evidence[0]["details"] is None
