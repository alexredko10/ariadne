"""Tests for the minimal no-op runner adapter."""

from __future__ import annotations

import inspect
import json

import pytest

from runner.noop_adapter import run_noop_execution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_request(**overrides: object) -> dict:
    """Build a minimal valid no-op execution request."""
    base = {
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "task_intake_id": "task_a1b2c3d4e5f6",
        "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
        "requested_adapter": "noop-v1",
        "execution_mode": "dry_run",
        "inputs": {"note": "test"},
        "constraints": ["no_git_mutation"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid request — completed
# ---------------------------------------------------------------------------


class TestValidRequest:
    def test_returns_completed(self):
        result = run_noop_execution(_valid_request())
        assert result["status"] == "completed"

    def test_has_deterministic_result_id(self):
        result = run_noop_execution(_valid_request())
        assert result["execution_result_id"] == "er-001-result"

    def test_has_evidence(self):
        result = run_noop_execution(_valid_request())
        assert len(result["evidence"]) >= 1

    def test_evidence_states_no_execution(self):
        result = run_noop_execution(_valid_request())
        summary = result["evidence"][0]["summary"]
        assert "no real execution" in summary.lower()
        assert "Docker" not in summary or "No Docker" in summary
        assert "subprocess" in summary or "no subprocess" in summary
        assert "no model" in summary.lower()

    def test_has_empty_artifacts(self):
        result = run_noop_execution(_valid_request())
        assert result["artifacts"] == []

    def test_has_empty_errors(self):
        result = run_noop_execution(_valid_request())
        assert result["errors"] == []

    def test_has_next(self):
        result = run_noop_execution(_valid_request())
        assert result["next"] == "/runs/run-001/status"

    def test_json_serializable(self):
        result = run_noop_execution(_valid_request())
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_deterministic(self):
        r1 = run_noop_execution(_valid_request())
        r2 = run_noop_execution(_valid_request())
        assert r1 == r2

    def test_preview_mode_succeeds(self):
        result = run_noop_execution(_valid_request(execution_mode="preview"))
        assert result["status"] == "completed"
        assert result["adapter"] == "noop-v1"

    def test_dry_run_mode_succeeds(self):
        result = run_noop_execution(_valid_request(execution_mode="dry_run"))
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Approval — blocked
# ---------------------------------------------------------------------------


class TestApprovalBlocked:
    def test_approval_pending_returns_blocked(self):
        result = run_noop_execution(_valid_request(
            approval={"required": True, "approved": False},
        ))
        assert result["status"] == "blocked"
        assert result["review_required"] is False

    def test_blocked_has_warning(self):
        result = run_noop_execution(_valid_request(
            approval={"required": True, "approved": False},
        ))
        assert len(result["warnings"]) > 0


class TestApprovalReview:
    def test_approval_review_returns_requires_review(self):
        result = run_noop_execution(_valid_request(
            approval={"required": True, "after_execution": True},
        ))
        assert result["status"] == "requires_review"
        assert result["review_required"] is True


# ---------------------------------------------------------------------------
# Invalid / edge case — failed
# ---------------------------------------------------------------------------


class TestInvalidRequest:
    def test_missing_execution_request_id_returns_failed(self):
        result = run_noop_execution(_valid_request(execution_request_id=""))
        assert result["status"] == "failed"
        assert len(result["errors"]) > 0

    def test_missing_run_id_returns_failed(self):
        result = run_noop_execution(_valid_request(run_id=""))
        assert result["status"] == "failed"

    def test_missing_task_intake_id_returns_failed(self):
        result = run_noop_execution(_valid_request(task_intake_id=""))
        assert result["status"] == "failed"

    def test_unsupported_adapter_returns_failed(self):
        result = run_noop_execution(_valid_request(requested_adapter="docker-coder-v1"))
        assert result["status"] == "failed"
        assert any("unsupported_adapter" in e.get("code", "") for e in result["errors"])

    def test_unsupported_mode_returns_failed(self):
        result = run_noop_execution(_valid_request(execution_mode="execute"))
        assert result["status"] == "failed"
        assert any("unsupported_mode" in e.get("code", "") for e in result["errors"])

    def test_empty_adapter_returns_failed(self):
        result = run_noop_execution(_valid_request(requested_adapter=""))
        assert result["status"] == "failed"

    def test_double_run_returns_same_output(self):
        r1 = run_noop_execution(_valid_request(execution_mode="dry_run"))
        r2 = run_noop_execution(_valid_request(execution_mode="dry_run"))
        assert r1 == r2


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        """Verify that the module does not import forbidden modules."""
        source = inspect.getsource(run_noop_execution)
        # Remove docstrings and string literals to avoid false positives
        # from safety-guarantee text in evidence summaries.
        import re
        # Remove triple-quoted strings (both """ and ''')
        clean = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", '', clean, flags=re.DOTALL)
        # Remove single-quoted strings
        clean = re.sub(r"'[^']*'", '', clean)
        # Remove double-quoted strings
        clean = re.sub(r'"[^"]*"', '', clean)
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "os.system" not in clean
        assert "docker" not in clean.lower()
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "urllib" not in clean.lower()
        assert "socket" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
