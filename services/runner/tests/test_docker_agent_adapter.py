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

    def test_allow_docker_with_fake_executor_completes(self):
        result = run_docker_agent_execution(
            _valid_request(),
            allow_docker=True,
            executor=_fake_successful_executor,
        )
        assert result["status"] == "completed"

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
