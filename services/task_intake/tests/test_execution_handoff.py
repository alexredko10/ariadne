"""Tests for the mock-run to runner-dispatcher handoff."""

from __future__ import annotations

import hashlib
import inspect
import json
import re

from task_intake.execution_handoff import run_mock_execution_handoff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_raw(**overrides: object) -> dict:
    """Build a minimal valid raw handoff request."""
    base = {"raw_task": "Implement JWT authentication middleware"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid handoff
# ---------------------------------------------------------------------------


class TestValidHandoff:
    def test_returns_ok(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert result["ok"] is True

    def test_has_execution_result(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert "execution_result" in result
        assert result["execution_result"]["status"] == "completed"
        assert result["execution_result"]["adapter"] == "noop-v1"

    def test_has_execution_request(self):
        result = run_mock_execution_handoff(_valid_raw())
        req = result["execution_request"]
        assert req["requested_adapter"] == "noop"
        assert req["execution_mode"] == "dry_run"
        assert "execution_request_id" in req
        assert req["execution_request_id"].startswith("er_")

    def test_has_mock_loop_result(self):
        result = run_mock_execution_handoff(_valid_raw())
        mlr = result["mock_loop_result"]
        assert mlr["loop_id"].startswith("loop_")
        assert mlr["task_goal"] == "Implement JWT authentication middleware"

    def test_has_evidence_of_no_execution(self):
        result = run_mock_execution_handoff(_valid_raw())
        ev = result["execution_result"]["evidence"]
        assert len(ev) >= 1
        assert any("no real execution" in e["summary"].lower() for e in ev)

    def test_no_errors(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert result["errors"] == []

    def test_deterministic(self):
        r1 = run_mock_execution_handoff(_valid_raw())
        r2 = run_mock_execution_handoff(_valid_raw())
        assert r1 == r2

    def test_json_serializable(self):
        result = run_mock_execution_handoff(_valid_raw())
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_handoff_id_deterministic(self):
        r1 = run_mock_execution_handoff(_valid_raw())
        r2 = run_mock_execution_handoff(_valid_raw())
        assert r1["handoff_id"] == r2["handoff_id"]
        assert r1["handoff_id"].startswith("handoff_")

    def test_handoff_contains_execution_envelope(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert "execution_envelope" in result
        assert result["execution_envelope"]["envelope_id"].startswith("env_")

    def test_handoff_contains_review_boundary(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert "review_boundary" in result
        assert "decision" in result["review_boundary"]

    def test_handoff_runtime_status(self):
        result = run_mock_execution_handoff(_valid_raw())
        assert "runtime_status" in result
        assert result["runtime_status"] == "completed"
        assert result["runtime_status"] == result["review_boundary"]["decision"]


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------


class TestApproval:
    def test_approval_pending_returns_blocked(self):
        result = run_mock_execution_handoff(
            _valid_raw(execution_approval={"required": True, "approved": False}),
        )
        assert result["execution_result"]["status"] == "blocked"

    def test_blocked_includes_warning(self):
        result = run_mock_execution_handoff(
            _valid_raw(execution_approval={"required": True, "approved": False}),
        )
        assert len(result["execution_result"].get("warnings", [])) > 0

    def test_review_after_execution(self):
        result = run_mock_execution_handoff(
            _valid_raw(execution_approval={"required": True, "after_execution": True}),
        )
        assert result["execution_result"]["status"] == "requires_review"
        assert result["execution_result"]["review_required"] is True


# ---------------------------------------------------------------------------
# Invalid / edge cases
# ---------------------------------------------------------------------------


class TestInvalidInput:
    def test_missing_raw_task_fails(self):
        result = run_mock_execution_handoff({"source": "cli"})
        assert result["ok"] is False
        assert len(result["errors"]) > 0
        assert result["execution_request"] is None
        assert result["execution_result"] is None

    def test_non_dict_request_fails(self):
        result = run_mock_execution_handoff("not a dict")
        assert result["ok"] is False
        assert len(result["errors"]) > 0

    def test_unsupported_adapter_returns_failed_result(self):
        result = run_mock_execution_handoff(
            _valid_raw(requested_adapter="docker-coder-v1"),
        )
        # Handoff itself succeeded — dispatcher returned failed result
        assert result["ok"] is True
        assert result["execution_result"]["status"] == "failed"
        assert any("unsupported_adapter" in str(e) for e in result["execution_result"].get("errors", []))

    def test_unsupported_execution_mode_returns_failed_result(self):
        result = run_mock_execution_handoff(
            _valid_raw(execution_mode="execute"),
        )
        # No-op adapter returns failed for "execute" mode — dispatcher passes through
        assert result["execution_result"]["status"] == "failed"
        assert any("unsupported_mode" in str(e) for e in result["execution_result"].get("errors", []))


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        source = inspect.getsource(run_mock_execution_handoff)
        source += inspect.getsource(_valid_raw)
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
        assert "importlib" not in clean
        assert "pkg_resources" not in clean
        assert "entry_points" not in clean
