"""Tests for the local app runtime entrypoint."""

from __future__ import annotations

import json
import re

from task_intake.app import build_runtime_config, main


# ---------------------------------------------------------------------------
# build_runtime_config
# ---------------------------------------------------------------------------


class TestBuildRuntimeConfig:
    def test_defaults(self):
        cfg = build_runtime_config([])
        assert cfg["host"] == "127.0.0.1"
        assert cfg["port"] == 8000
        assert cfg["check"] is False

    def test_custom_host(self):
        cfg = build_runtime_config(["--host", "0.0.0.0"])
        assert cfg["host"] == "0.0.0.0"

    def test_custom_port(self):
        cfg = build_runtime_config(["--port", "9000"])
        assert cfg["port"] == 9000

    def test_check_flag(self):
        cfg = build_runtime_config(["--check"])
        assert cfg["check"] is True

    def test_check_json(self):
        cfg = build_runtime_config(["--check", "--json"])
        assert cfg["check"] is True

    def test_check_output_service(self):
        cfg = build_runtime_config(["--check"])
        assert cfg["service"] == "task_intake"

    def test_check_output_routes(self):
        cfg = build_runtime_config(["--check"])
        assert "/runs/execute" in cfg["routes"]

    def test_check_output_routes_count(self):
        cfg = build_runtime_config(["--check"])
        assert len(cfg["routes"]) >= 8

    def test_check_output_status_ready(self):
        cfg = build_runtime_config(["--check"])
        assert cfg["status"] == "ready"

    def test_default_adapter_noop(self):
        cfg = build_runtime_config(["--check"])
        assert cfg["default_adapter"] == "noop"

    def test_dependencies_uvicorn(self):
        cfg = build_runtime_config(["--check"])
        assert "uvicorn" in cfg["dependencies"]

    def test_json_serializable(self):
        cfg = build_runtime_config(["--check"])
        dumped = json.dumps(cfg, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == cfg

    def test_deterministic(self):
        c1 = build_runtime_config(["--check"])
        c2 = build_runtime_config(["--check"])
        assert c1 == c2


# ---------------------------------------------------------------------------
# main (non-blocking only)
# ---------------------------------------------------------------------------


class TestMain:
    def test_check_returns_0(self):
        code = main(["--check"])
        assert code == 0

    def test_check_json_returns_0(self):
        code = main(["--check", "--json"])
        assert code == 0


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import inspect
        src = inspect.getsource(build_runtime_config)
        clean = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "docker" not in clean.lower()
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "urllib" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
        assert "uuid" not in clean
        assert "datetime.now" not in clean
        assert "time.time" not in clean
        assert "random" not in clean
