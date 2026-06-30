"""Tests for the Docker agent runner adapter."""

from __future__ import annotations

import json
import re

from runner.docker_agent_adapter import (
    build_docker_agent_command,
    run_docker_agent_execution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_request(**overrides: object) -> dict:
    base = {
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "task_intake_id": "task_a1b2c3",
        "context_preview_id": "cp-001",
        "requested_adapter": "docker-agent-v1",
        "execution_mode": "dry_run",
        "inputs": {"task_goal": "Implement JWT auth"},
        "constraints": [],
    }
    base.update(overrides)
    return base


def _fake_successful_executor(cmd: dict) -> dict:
    return {
        "exit_code": 0,
        "stdout": "Execution completed successfully.",
        "stderr": "",
        "success": True,
    }


def _fake_failing_executor(cmd: dict) -> dict:
    return {
        "exit_code": 1,
        "stdout": "",
        "stderr": "Container exited with error.",
        "success": False,
    }


# ---------------------------------------------------------------------------
# Opt-in
# ---------------------------------------------------------------------------


class TestOptIn:
    def test_no_allow_docker_returns_blocked(self):
        result = run_docker_agent_execution(_valid_request())
        assert result["status"] == "blocked"

    def test_no_allow_docker_has_optin_evidence(self):
        result = run_docker_agent_execution(_valid_request())
        ev = result.get("evidence", [])
        assert any("allow_docker" in e.get("summary", "") for e in ev)

    def test_allow_docker_with_fake_executor_requires_review(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        assert result["status"] == "requires_review"

    def test_allow_docker_with_fake_failing_executor_fails(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        assert result["status"] == "failed"
        assert len(result.get("errors", [])) > 0


# ---------------------------------------------------------------------------
# build_docker_agent_command
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_returns_dict(self):
        cmd = build_docker_agent_command(_valid_request())
        assert isinstance(cmd, dict)

    def test_includes_adapter(self):
        cmd = build_docker_agent_command(_valid_request())
        assert cmd["adapter"] == "docker-agent-v1"

    def test_includes_container_image(self):
        cmd = build_docker_agent_command(_valid_request())
        assert cmd["container_image"] == "ariadne-agent-base:latest"

    def test_environment_has_run_id(self):
        cmd = build_docker_agent_command(_valid_request())
        assert cmd["environment"]["ARIADNE_RUN_ID"] == "run-001"

    def test_environment_has_request_id(self):
        cmd = build_docker_agent_command(_valid_request())
        assert cmd["environment"]["ARIADNE_REQUEST_ID"] == "er-001"

    def test_environment_has_task_goal(self):
        cmd = build_docker_agent_command(_valid_request())
        assert cmd["environment"]["ARIADNE_TASK_GOAL"] == "Implement JWT auth"

    def test_network_mode_none_for_dry_run(self):
        cmd = build_docker_agent_command(_valid_request(execution_mode="dry_run"))
        assert cmd["network_mode"] == "none"

    def test_network_mode_bridge_for_execute(self):
        cmd = build_docker_agent_command(_valid_request(execution_mode="execute"))
        assert cmd["network_mode"] == "bridge"

    def test_deterministic(self):
        req = _valid_request()
        c1 = build_docker_agent_command(req)
        c2 = build_docker_agent_command(req)
        assert c1 == c2


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


class TestResultShape:
    def test_adapter_is_docker_agent_v1(self):
        result = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        assert result["adapter"] == "docker-agent-v1"

    def test_has_execution_result_id(self):
        result = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        assert result["execution_result_id"] == "er-001-result"

    def test_has_evidence(self):
        result = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        assert len(result.get("evidence", [])) >= 1

    def test_deterministic_with_same_executor(self):
        req = _valid_request()
        r1 = run_docker_agent_execution(req, allow_docker=True, executor=_fake_successful_executor)
        r2 = run_docker_agent_execution(req, allow_docker=True, executor=_fake_successful_executor)
        assert r1 == r2

    def test_json_serializable(self):
        result = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import inspect
        file_path = inspect.getfile(run_docker_agent_execution)
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        clean = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "import docker" not in clean
        assert "from docker" not in clean
        assert "docker.from_env" not in clean
        assert "os.system" not in clean
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "urllib" not in clean.lower()
        assert "socket" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
        assert "uuid" not in clean
        assert "datetime.now" not in clean
        assert "time.time" not in clean
        assert "random" not in clean
        assert "importlib" not in clean
        assert "pkg_resources" not in clean
        assert "entry_points" not in clean


# ---------------------------------------------------------------------------
# Run artifact tests
# ---------------------------------------------------------------------------


class TestRunArtifacts:
    """Tests that docker_agent_adapter now populates artifacts and evidence
    via the new docker_run_artifacts module."""

    def test_blocked_has_command_meta_artifact(self):
        result = run_docker_agent_execution(_valid_request())
        artifacts = result.get("artifacts", [])
        kinds = [a["kind"] for a in artifacts]
        assert "docker_command_metadata" in kinds

    def test_completed_has_four_artifacts(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        artifacts = result.get("artifacts", [])
        assert len(artifacts) == 4

    def test_failed_has_four_artifacts(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        artifacts = result.get("artifacts", [])
        assert len(artifacts) == 4

    def test_completed_artifact_kinds(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        kinds = [a["kind"] for a in result.get("artifacts", [])]
        assert "docker_stdout" in kinds
        assert "docker_stderr" in kinds
        assert "docker_execution_metadata" in kinds
        assert "docker_command_metadata" in kinds

    def test_artifact_content_matches_executor_output(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        stdout_artifact = [a for a in result.get("artifacts", []) if a["kind"] == "docker_stdout"][0]
        assert stdout_artifact["content"] == "Execution completed successfully."

    def test_evidence_passed_for_completed(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        evidence = result.get("evidence", [])
        assert evidence[0]["status"] == "passed"

    def test_evidence_failed_for_failed(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        evidence = result.get("evidence", [])
        assert evidence[0]["status"] == "failed"

    def test_blocked_evidence_skipped(self):
        result = run_docker_agent_execution(_valid_request())
        evidence = result.get("evidence", [])
        assert evidence[0]["status"] == "skipped"


# ---------------------------------------------------------------------------
# Human review boundary for real Docker runs
# ---------------------------------------------------------------------------


class TestHumanReviewBoundary:
    """Tests that real docker-agent executions produce the correct status
    for the existing derive_review_boundary()."""

    def test_successful_real_execution_requires_review(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        assert result["status"] == "requires_review"

    def test_failed_real_execution_failed(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        assert result["status"] == "failed"

    def test_blocked_execution_blocked(self):
        result = run_docker_agent_execution(_valid_request())
        assert result["status"] == "blocked"

    def test_requires_review_failed_blocked_are_distinct(self):
        r_requires = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        r_failed = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_failing_executor,
        )
        r_blocked = run_docker_agent_execution(_valid_request())
        statuses = {r_requires["status"], r_failed["status"], r_blocked["status"]}
        assert len(statuses) == 3

    def test_review_required_field_is_false(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        # review_required is a different field from status — it stays False
        # The boundary function reads status, not review_required
        assert result["review_required"] is False

    def test_pr_0095_artifact_kinds_preserved_requires_review(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        kinds = [a["kind"] for a in result.get("artifacts", [])]
        assert "docker_stdout" in kinds
        assert "docker_stderr" in kinds
        assert "docker_execution_metadata" in kinds
        assert "docker_command_metadata" in kinds

    def test_pr_0095_evidence_preserved_requires_review(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        evidence = result.get("evidence", [])
        assert evidence[0]["evidence_kind"] == "execution_log"
        assert evidence[0]["status"] == "passed"

    def test_pr_0095_artifact_kinds_preserved_failed(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        kinds = [a["kind"] for a in result.get("artifacts", [])]
        assert "docker_stdout" in kinds
        assert "docker_stderr" in kinds
        assert "docker_execution_metadata" in kinds
        assert "docker_command_metadata" in kinds

    def test_pr_0095_evidence_preserved_failed(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_failing_executor,
        )
        evidence = result.get("evidence", [])
        assert evidence[0]["evidence_kind"] == "execution_log"
        assert evidence[0]["status"] == "failed"

    def test_pr_0094_dual_gate_compatibility(self):
        allow_docker_false = run_docker_agent_execution(
            _valid_request(), allow_docker=False,
        )
        allow_docker_true = run_docker_agent_execution(
            _valid_request(), allow_docker=True, executor=_fake_successful_executor,
        )
        # allow_docker=False must be blocked
        assert allow_docker_false["status"] == "blocked"
        # allow_docker=True must NOT be blocked
        assert allow_docker_true["status"] != "blocked"


# ---------------------------------------------------------------------------
# Audit invariants integration
# ---------------------------------------------------------------------------


class TestAuditInvariants:
    """Tests that audit invariant checks match actual docker_agent_adapter
    behavior. Uses real source text for the audit module."""

    def _get_adapter_source(self) -> str:
        import inspect
        from runner.docker_agent_adapter import run_docker_agent_execution
        return inspect.getsource(run_docker_agent_execution)

    def test_audit_requires_review_matches_adapter(self):
        """The audit's requires_review check passes when given the real
        adapter source."""
        from runner.execution_substrate_audit import run_execution_substrate_audit
        source = self._get_adapter_source()
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=source,
        )
        check = [c for c in report["checks"] if c["check_id"] == "docker_success_requires_review"]
        assert len(check) == 1
        assert check[0]["passed"] is True

    def test_audit_blocked_matches_adapter(self):
        """The audit's blocked check passes when given the real adapter source."""
        from runner.execution_substrate_audit import run_execution_substrate_audit
        source = self._get_adapter_source()
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=source,
        )
        check = [c for c in report["checks"] if c["check_id"] == "docker_blocked_unchanged"]
        assert len(check) == 1
        assert check[0]["passed"] is True

    def test_audit_failed_matches_adapter(self):
        """The audit's failed check passes when given the real adapter source."""
        from runner.execution_substrate_audit import run_execution_substrate_audit
        source = self._get_adapter_source()
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=source,
        )
        check = [c for c in report["checks"] if c["check_id"] == "docker_failed_unchanged"]
        assert len(check) == 1
        assert check[0]["passed"] is True
