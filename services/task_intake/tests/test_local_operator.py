"""
PR 0147A — Unit tests for local operator module configuration and validation.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

# Add the task_intake source to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from task_intake.local_operator import (
    _build_arg_parser,
    _ensure_runs_root,
    _get_repo_root,
    _print_check_json,
    _resolve_runs_root,
    _validate_host,
    _validate_port,
    main,
)


class TestDefaultConfiguration:
    """Tests for default operator configuration."""

    def test_default_host_is_loopback(self):
        """Default host is 127.0.0.1."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.host == "127.0.0.1"

    def test_default_port_is_8000(self):
        """Default port is 8000."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.port == 8000

    def test_default_runs_root_is_none(self):
        """Default runs-root is None (resolved to .ariadne/runs)."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.runs_root is None

    def test_allow_public_bind_false_by_default(self):
        """--allow-public-bind is False by default."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.allow_public_bind is False

    def test_allow_privileged_port_false_by_default(self):
        """--allow-privileged-port is False by default."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.allow_privileged_port is False

    def test_check_false_by_default(self):
        """--check is False by default."""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.check is False


class TestHostValidation:
    """Tests for host validation."""

    def test_loopback_allowed_by_default(self):
        """127.0.0.1 is allowed without flags."""
        result = _validate_host("127.0.0.1", False)
        assert result == "127.0.0.1"

    def test_localhost_allowed(self):
        """localhost is allowed without flags."""
        result = _validate_host("localhost", False)
        assert result == "localhost"

    def test_public_bind_blocked_by_default(self):
        """0.0.0.0 is blocked without --allow-public-bind."""
        with pytest.raises(SystemExit) as exc:
            _validate_host("0.0.0.0", False)
        assert exc.value.code == 1

    def test_public_bind_allowed_with_flag(self):
        """0.0.0.0 is allowed with --allow-public-bind."""
        result = _validate_host("0.0.0.0", True)
        assert result == "0.0.0.0"

    def test_ipv6_any_blocked_by_default(self):
        """:: is blocked without --allow-public-bind."""
        with pytest.raises(SystemExit) as exc:
            _validate_host("::", False)
        assert exc.value.code == 1


class TestPortValidation:
    """Tests for port validation."""

    def test_port_8000_allowed(self):
        """Port 8000 is allowed."""
        result = _validate_port(8000, False)
        assert result == 8000

    def test_port_8080_allowed(self):
        """Port 8080 is allowed."""
        result = _validate_port(8080, False)
        assert result == 8080

    def test_port_1024_allowed(self):
        """Port 1024 (non-privileged boundary) is allowed."""
        result = _validate_port(1024, False)
        assert result == 1024

    def test_privileged_port_blocked(self):
        """Ports <1024 are blocked without --allow-privileged-port."""
        with pytest.raises(SystemExit) as exc:
            _validate_port(80, False)
        assert exc.value.code == 1

    def test_privileged_port_allowed_with_flag(self):
        """Ports <1024 are allowed with --allow-privileged-port."""
        result = _validate_port(80, True)
        assert result == 80

    def test_port_zero_blocked(self):
        """Port 0 is rejected."""
        with pytest.raises(SystemExit) as exc:
            _validate_port(0, False)
        assert exc.value.code == 1

    def test_port_above_65535_blocked(self):
        """Ports >65535 are rejected."""
        with pytest.raises(SystemExit) as exc:
            _validate_port(70000, False)
        assert exc.value.code == 1


class TestRunsRoot:
    """Tests for runs-root resolution and creation."""

    def test_resolve_default_runs_root(self):
        """Default runs-root resolves to .ariadne/runs under repo root."""
        result = _resolve_runs_root(None, "/tmp/repo")
        assert result == "/tmp/repo/.ariadne/runs"

    def test_resolve_custom_runs_root(self):
        """Custom runs-root is resolved to absolute path."""
        result = _resolve_runs_root("/custom/path", "/tmp/repo")
        assert result == "/custom/path"

    def test_resolve_relative_runs_root(self):
        """Relative runs-root is resolved to absolute path."""
        result = _resolve_runs_root("relative/path", "/tmp/repo")
        assert os.path.isabs(result)
        assert result.endswith("relative/path")

    def test_ensure_runs_root_creates_directory(self):
        """_ensure_runs_root creates the directory if absent."""
        with tempfile.TemporaryDirectory() as tmp:
            rr = os.path.join(tmp, "new-dir")
            assert not os.path.exists(rr)
            _ensure_runs_root(rr)
            assert os.path.isdir(rr)

    def test_ensure_runs_root_accepts_existing_directory(self):
        """_ensure_runs_root does not error on existing directory."""
        with tempfile.TemporaryDirectory() as tmp:
            _ensure_runs_root(tmp)  # Should not raise

    def test_get_repo_root_returns_directory(self):
        """_get_repo_root returns a valid directory."""
        result = _get_repo_root()
        assert os.path.isdir(result)


class TestCheckMode:
    """Tests for --check mode."""

    def test_check_prints_valid_json(self):
        """--check mode outputs valid JSON."""
        import io

        stdout = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            _print_check_json("127.0.0.1", 8000, "/tmp/runs")
            output = stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        data = json.loads(output)
        assert data["host"] == "127.0.0.1"
        assert data["port"] == 8000
        assert data["runs_root"] == "/tmp/runs"
        assert "health_url" in data
        assert "workspace_url" in data
        assert data["status"] == "READ-ONLY"

    def test_check_mode_returns_zero(self):
        """--check mode exits 0 for valid config."""
        with tempfile.TemporaryDirectory() as tmp:
            rr = os.path.join(tmp, "test-runs")
            os.makedirs(rr)
            result = main(["--check", "--runs-root", rr])
            assert result == 0

    def test_check_mode_does_not_start_server(self):
        """--check mode does not import uvicorn or start server."""
        with tempfile.TemporaryDirectory() as tmp:
            rr = os.path.join(tmp, "test-runs")
            os.makedirs(rr)
            result = main(["--check", "--runs-root", rr])
            assert result == 0

    def test_invalid_port_fails_nonzero(self):
        """Invalid port returns non-zero."""
        result = main(["--port", "99999"])
        assert result == 1


class TestReadOnlyMessaging:
    """Tests for read-only status messaging."""

    def test_read_only_status_in_check_json(self):
        """Check JSON includes READ-ONLY status."""
        import io

        stdout = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            _print_check_json("127.0.0.1", 8000, "/tmp/runs")
            output = stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        data = json.loads(output)
        assert data["status"] == "READ-ONLY"

    def test_no_agent_references_in_module_source(self):
        """local_operator.py does not reference agent launch."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        # The module may mention that orchestration is unavailable in status messages
        # ("no orchestration"), but must not implement agent launch behavior.
        assert "agent launch" not in source.lower(), "module must not reference agent launch"
        assert "agent execution" not in source.lower() or "no agent execution" in source.lower(), (
            "module must not claim agent execution capability"
        )

    def test_no_git_references_in_module_source(self):
        """local_operator.py does not reference git commands."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "git " not in source.lower()

    def test_no_docker_references_in_module_source(self):
        """local_operator.py does not reference Docker."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "docker" not in source.lower()

    def test_no_subprocess_in_module_source(self):
        """local_operator.py does not reference subprocess."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "subprocess" not in source
        assert "Popen" not in source

    def test_no_eval_in_module_source(self):
        """local_operator.py does not use eval."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "eval(" not in source

    def test_no_os_system_in_module_source(self):
        """local_operator.py does not use os.system."""
        import os as _os

        path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "local_operator.py",
        )
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "os.system" not in source
