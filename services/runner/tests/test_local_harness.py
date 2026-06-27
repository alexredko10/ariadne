"""Tests for the local execution harness."""

from __future__ import annotations

import json
import re

from runner.local_harness import run_local_execution_harness


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


# ---------------------------------------------------------------------------
# Valid request
# ---------------------------------------------------------------------------


class TestValidRequest:
    def test_returns_ok(self):
        result = run_local_execution_harness(_valid_request())
        assert result["ok"] is True

    def test_contains_execution_request(self):
        result = run_local_execution_harness(_valid_request())
        assert result["execution_request"]["execution_request_id"] == "er-001"

    def test_contains_execution_result(self):
        result = run_local_execution_harness(_valid_request())
        assert result["execution_result"]["status"] == "completed"
        assert result["execution_result"]["adapter"] == "noop-v1"

    def test_contains_execution_envelope(self):
        result = run_local_execution_harness(_valid_request())
        assert "execution_envelope" in result
        assert result["execution_envelope"]["envelope_id"].startswith("env_")

    def test_contains_review_boundary(self):
        result = run_local_execution_harness(_valid_request())
        assert "review_boundary" in result
        assert "decision" in result["review_boundary"]

    def test_runtime_status_matches_boundary(self):
        result = run_local_execution_harness(_valid_request())
        assert result["runtime_status"] == result["review_boundary"]["decision"]

    def test_runtime_status_completed(self):
        result = run_local_execution_harness(_valid_request())
        assert result["runtime_status"] == "completed"

    def test_deterministic(self):
        r1 = run_local_execution_harness(_valid_request())
        r2 = run_local_execution_harness(_valid_request())
        assert r1 == r2

    def test_json_serializable(self):
        result = run_local_execution_harness(_valid_request())
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_uses_dispatcher_not_direct_adapter(self):
        import inspect
        source = inspect.getsource(run_local_execution_harness)
        assert "noop_adapter" not in source
        assert "run_noop_execution" not in source


class TestInvalidInput:
    def test_non_dict_returns_error(self):
        result = run_local_execution_harness("bad")
        assert result["ok"] is False
        assert result["runtime_status"] == "error"
        assert len(result["errors"]) > 0

    def test_error_has_no_execution_result(self):
        result = run_local_execution_harness("bad")
        assert result["execution_result"] is None
        assert result["execution_envelope"] is None
        assert result["review_boundary"] is None


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import inspect
        source = inspect.getsource(run_local_execution_harness)
        clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
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
