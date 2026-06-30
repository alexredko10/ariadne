"""Tests for the docker subprocess executor module."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from runner.docker_subprocess_executor import (
    _build_docker_argv,
    run_docker_subprocess,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _full_command_metadata(**overrides: object) -> dict:
    base = {
        "container_image": "ariadne-agent-base:latest",
        "container_command": [
            "agent", "run",
            "--run-id", "run-001",
            "--request-id", "er-001",
            "--mode", "execute",
        ],
        "workdir": "/workspace",
        "volumes": {
            "/host/project": {"bind": "/workspace", "mode": "rw"},
        },
        "environment": {
            "ARIADNE_RUN_ID": "run-001",
            "ARIADNE_REQUEST_ID": "er-001",
        },
        "network_mode": "bridge",
        "memory_limit": "4g",
        "cpu_count": 2,
        "timeout_seconds": 300,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# argv construction
# ---------------------------------------------------------------------------


class TestArgvConstruction:
    def test_argv_is_list(self):
        cmd = _full_command_metadata()
        argv = _build_docker_argv(cmd)
        assert isinstance(argv, list)
        assert all(isinstance(a, str) for a in argv)

    def test_no_shell_true_reference(self):
        # Directly verify that shell=True does not appear in argv
        cmd = _full_command_metadata()
        argv = _build_docker_argv(cmd)
        assert "True" not in " ".join(argv)
        assert "shell" not in " ".join(argv).lower()

    def test_basic_docker_args(self):
        cmd = _full_command_metadata()
        argv = _build_docker_argv(cmd)
        assert argv[0] == "docker"
        assert argv[1] == "run"
        assert argv[2] == "--rm"

    def test_workdir_included(self):
        cmd = _full_command_metadata(workdir="/workspace")
        argv = _build_docker_argv(cmd)
        assert "--workdir" in argv
        assert argv[argv.index("--workdir") + 1] == "/workspace"

    def test_workdir_omitted_when_empty(self):
        cmd = _full_command_metadata(workdir="")
        argv = _build_docker_argv(cmd)
        assert "--workdir" not in argv

    def test_volumes_included(self):
        cmd = _full_command_metadata(volumes={"/src": {"bind": "/dst", "mode": "ro"}})
        argv = _build_docker_argv(cmd)
        assert "--volume" in argv
        vol_idx = argv.index("--volume")
        assert argv[vol_idx + 1] == "/src:/dst:ro"

    def test_volumes_default_mode(self):
        cmd = _full_command_metadata(volumes={"/src": {"bind": "/dst", "mode": ""}})
        argv = _build_docker_argv(cmd)
        vol_idx = argv.index("--volume")
        assert argv[vol_idx + 1] == "/src:/dst"

    def test_environment_included(self):
        cmd = _full_command_metadata(
            environment={"FOO": "bar", "BAZ": "qux"},
        )
        argv = _build_docker_argv(cmd)
        assert "--env" in argv
        env_idx = argv.index("--env")
        assert argv[env_idx + 1] in ("FOO=bar", "BAZ=qux")

    def test_network_mode_included(self):
        cmd = _full_command_metadata(network_mode="none")
        argv = _build_docker_argv(cmd)
        assert "--network" in argv
        assert argv[argv.index("--network") + 1] == "none"

    def test_network_mode_omitted_when_empty(self):
        cmd = _full_command_metadata(network_mode="")
        argv = _build_docker_argv(cmd)
        assert "--network" not in argv

    def test_memory_limit_included(self):
        cmd = _full_command_metadata(memory_limit="2g")
        argv = _build_docker_argv(cmd)
        assert "--memory" in argv
        assert argv[argv.index("--memory") + 1] == "2g"

    def test_memory_limit_omitted_when_empty(self):
        cmd = _full_command_metadata(memory_limit="")
        argv = _build_docker_argv(cmd)
        assert "--memory" not in argv

    def test_cpu_count_included(self):
        cmd = _full_command_metadata(cpu_count=4)
        argv = _build_docker_argv(cmd)
        assert "--cpus" in argv
        assert argv[argv.index("--cpus") + 1] == "4"

    def test_cpu_count_omitted_when_zero(self):
        cmd = _full_command_metadata(cpu_count=0)
        argv = _build_docker_argv(cmd)
        assert "--cpus" not in argv

    def test_container_image_at_end_before_command(self):
        cmd = _full_command_metadata()
        argv = _build_docker_argv(cmd)
        assert "ariadne-agent-base:latest" in argv
        img_idx = argv.index("ariadne-agent-base:latest")
        # The command args come after the image
        assert argv[img_idx + 1:] == cmd["container_command"]

    def test_full_argv_matches_expected_flags(self):
        cmd = _full_command_metadata()
        argv = _build_docker_argv(cmd)
        assert "-" in " ".join(argv)
        assert argv.count("--volume") == 1
        assert argv.count("--env") == 2
        assert len(argv) > 10


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestSuccessPath:
    def test_returns_success_dict(self):
        cmd = _full_command_metadata()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Build succeeded."
            mock_run.return_value.stderr = ""
            result = run_docker_subprocess(cmd)
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Build succeeded" in result["stdout"]
        assert result["stderr"] == ""

    def test_subprocess_run_called_with_list(self):
        cmd = _full_command_metadata()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            run_docker_subprocess(cmd)
        args, kwargs = mock_run.call_args
        # First positional argument should be argv list
        assert isinstance(args[0], list)
        assert kwargs.get("shell") is None or kwargs.get("shell") is False
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True
        assert kwargs.get("timeout") == cmd["timeout_seconds"]


# ---------------------------------------------------------------------------
# Non-zero exit
# ---------------------------------------------------------------------------


class TestNonZeroExit:
    def test_returns_failure(self):
        cmd = _full_command_metadata()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "Container exited with error."
            result = run_docker_subprocess(cmd)
        assert result["success"] is False
        assert result["exit_code"] == 1
        assert "Container exited with error" in result["stderr"]


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_returns_timeout_failure(self):
        cmd = _full_command_metadata(timeout_seconds=30)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="mock", timeout=30,
            )
            result = run_docker_subprocess(cmd)
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"].lower()
        assert "30" in result["stderr"]

    def test_no_uncaught_timeout(self):
        """TimeoutExpired from subprocess.run must always be caught."""
        cmd = _full_command_metadata()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="mock", timeout=300,
            )
            result = run_docker_subprocess(cmd)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# FileNotFoundError
# ---------------------------------------------------------------------------


class TestFileNotFound:
    def test_returns_missing_docker(self):
        cmd = _full_command_metadata()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = run_docker_subprocess(cmd)
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Docker executable not found" in result["stderr"]
