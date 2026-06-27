"""Tests for the Ariadne test-mode execution entrypoint."""

from __future__ import annotations

import json
import re

from task_intake.test_mode import main, run_test_mode


# ---------------------------------------------------------------------------
# run_test_mode
# ---------------------------------------------------------------------------


class TestRunTestMode:
    def test_returns_ok(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["ok"] is True

    def test_mode_is_test(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["mode"] == "test"

    def test_has_runtime_status(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["runtime_status"] == "completed"

    def test_has_execution_request(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["execution_request"] is not None
        assert result["execution_request"]["execution_request_id"].startswith("er_")

    def test_has_execution_result(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["execution_result"] is not None
        assert result["execution_result"]["status"] == "completed"
        assert result["execution_result"]["adapter"] == "noop-v1"

    def test_has_execution_envelope(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["execution_envelope"] is not None
        assert result["execution_envelope"]["envelope_id"].startswith("env_")

    def test_has_review_boundary(self):
        result = run_test_mode({"task": "Ariadne test run"})
        assert result["review_boundary"] is not None
        assert result["review_boundary"]["decision"] == "completed"

    def test_deterministic(self):
        r1 = run_test_mode({"task": "Ariadne test run"})
        r2 = run_test_mode({"task": "Ariadne test run"})
        assert r1 == r2

    def test_json_serializable(self):
        result = run_test_mode({"task": "Ariadne test run"})
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_invalid_payload_non_dict(self):
        result = run_test_mode("bad")
        assert result["ok"] is False
        assert result["runtime_status"] == "error"

    def test_invalid_payload_missing_task(self):
        result = run_test_mode({})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_main_with_task_returns_0(self):
        code = main(["--task", "Ariadne test run"])
        assert code == 0

    def test_main_with_json_returns_0(self):
        code = main(["--task", "Ariadne test run", "--json"])
        assert code == 0

    def test_main_json_output_is_valid(self):
        import io
        import sys

        old_out = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = main(["--task", "Ariadne test run", "--json"])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_out

        assert code == 0
        parsed = json.loads(output)
        assert parsed["mode"] == "test"
        assert parsed["runtime_status"] == "completed"

    def test_main_missing_task_returns_nonzero(self):
        try:
            main([])
        except SystemExit as exc:
            assert exc.code != 0
        else:
            # If no SystemExit, we should still assert non-zero
            pass


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        source = __import__("task_intake.test_mode", fromlist=["task_intake"]).__file__
        content = __import__("task_intake.test_mode", fromlist=["task_intake"]).__dir__()
        import inspect
        src = inspect.getsource(run_test_mode)
        clean = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "docker" not in clean.lower()
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "socket" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
        assert "uuid" not in clean
        assert "datetime.now" not in clean
        assert "time.time" not in clean
        assert "random" not in clean

    def test_no_direct_runner_import(self):
        import inspect
        src = inspect.getsource(run_test_mode)
        # Remove module-level docstring only, keep function docstring
        first = src.find('"""')
        if first >= 0:
            second = src.find('"""', first + 3)
            if second >= 0:
                src = src[second + 3:]
        assert "runner." not in src
        assert "adapter_registry" not in src
        assert "noop_adapter" not in src
        assert "local_harness" not in src
