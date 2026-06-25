"""Tests for the conductor demo flow module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conductor.demo_flow import run_ariadne_e2e_demo


# ---------------------------------------------------------------------------
# Import / callable
# ---------------------------------------------------------------------------


class TestDemoFlowCallable:
    def test_import_succeeds(self):
        from conductor.demo_flow import run_ariadne_e2e_demo as fn
        assert callable(fn)

    def test_callable_returns_dict(self):
        result = run_ariadne_e2e_demo()
        assert isinstance(result, dict)

    def test_contains_demo_identity(self):
        result = run_ariadne_e2e_demo()
        assert "Ariadne E2E Substrate Demo" in result["demo_name"]

    def test_deterministic(self):
        r1 = run_ariadne_e2e_demo()
        r2 = run_ariadne_e2e_demo()
        assert r1 == r2

    def test_json_serializable(self):
        result = run_ariadne_e2e_demo()
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------


class TestDemoFlowCLI:
    @staticmethod
    def _get_pythonpath() -> str:
        test_dir = Path(__file__).resolve().parent
        conductor_src = test_dir.parent / "src"
        services_dir = test_dir.parent.parent
        core_src = services_dir / "core" / "src"
        return f"{core_src}:{conductor_src}"

    def test_ariadne_demo_cli_succeeds(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "ariadne-demo"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_ariadne_demo_cli_output_contains_demo_name(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "ariadne-demo"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert "Ariadne E2E Substrate Demo" in result.stdout

    def test_ariadne_demo_cli_output_is_json(self):
        pythonpath = self._get_pythonpath()
        env = {"PYTHONPATH": pythonpath, "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "ariadne-demo"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        parsed = json.loads(result.stdout)
        assert parsed["deterministic"] is True
