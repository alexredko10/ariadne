"""Tests for the human review runtime boundary."""

from __future__ import annotations

import json
import re

from runner.review_boundary import derive_review_boundary


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


def _valid_result(**overrides: object) -> dict:
    base = {
        "execution_result_id": "er-001-result",
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "status": "completed",
        "adapter": "noop-v1",
        "artifacts": [],
        "evidence": [],
        "errors": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Completed
# ---------------------------------------------------------------------------


class TestCompleted:
    def test_no_approval(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["decision"] == "completed"
        assert b["completed"] is True

    def test_approval_not_required(self):
        req = _valid_request(approval={"required": False})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "completed"

    def test_approved_completed(self):
        req = _valid_request(approval={"required": True, "status": "approved"})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "completed"

    def test_no_approval_field(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["decision"] == "completed"

    def test_approval_none(self):
        req = _valid_request(approval=None)
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "completed"


# ---------------------------------------------------------------------------
# Requires review
# ---------------------------------------------------------------------------


class TestRequiresReview:
    def test_approval_pending(self):
        req = _valid_request(approval={"required": True, "status": "pending"})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "requires_review"
        assert b["requires_review"] is True
        assert b["reason_code"] == "approval_pending"

    def test_approval_required_missing_status(self):
        req = _valid_request(approval={"required": True})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "requires_review"
        assert b["requires_review"] is True

    def test_result_requires_review(self):
        res = _valid_result(status="requires_review")
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "requires_review"
        assert b["requires_review"] is True
        assert b["reason_code"] == "requires_review"

    def test_after_execution_completed(self):
        req = _valid_request(approval={"required": True, "after_execution": True})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "requires_review"
        assert b["requires_review"] is True
        assert b["reason_code"] == "requires_review"


# ---------------------------------------------------------------------------
# Blocked
# ---------------------------------------------------------------------------


class TestBlocked:
    def test_approval_denied(self):
        req = _valid_request(approval={"required": True, "status": "denied"})
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "blocked"
        assert b["blocked"] is True

    def test_result_blocked(self):
        res = _valid_result(status="blocked")
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "blocked"
        assert b["blocked"] is True


# ---------------------------------------------------------------------------
# Failed
# ---------------------------------------------------------------------------


class TestFailed:
    def test_result_failed(self):
        res = _valid_result(status="failed")
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "failed"
        assert b["failed"] is True
        assert b["reason_code"] == "execution_failed"

    def test_result_error(self):
        res = _valid_result(status="error")
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "failed"
        assert b["failed"] is True

    def test_missing_result_status(self):
        res = _valid_result()
        del res["status"]
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "failed"
        assert b["failed"] is True
        assert len(b["warnings"]) > 0


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class TestError:
    def test_non_dict_request(self):
        b = derive_review_boundary("bad", _valid_result())
        assert b["decision"] == "error"
        assert len(b["errors"]) > 0

    def test_non_dict_result(self):
        b = derive_review_boundary(_valid_request(), "bad")
        assert b["decision"] == "error"
        assert len(b["errors"]) > 0

    def test_missing_execution_request_id(self):
        req = _valid_request(execution_request_id="")
        b = derive_review_boundary(req, _valid_result())
        assert b["decision"] == "error"
        assert len(b["errors"]) > 0

    def test_missing_execution_result_id(self):
        res = _valid_result(execution_result_id="")
        b = derive_review_boundary(_valid_request(), res)
        assert b["decision"] == "error"
        assert len(b["errors"]) > 0


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------


class TestGeneral:
    def test_has_execution_request_id(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["execution_request_id"] == "er-001"

    def test_has_execution_result_id(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["execution_result_id"] == "er-001-result"

    def test_has_run_id(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["run_id"] == "run-001"

    def test_has_metadata(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        assert b["metadata"]["execution_adapter"] == "noop-v1"
        assert b["metadata"]["execution_mode"] == "dry_run"

    def test_approval_preserved(self):
        req = _valid_request(approval={"required": True, "status": "pending", "reviewer": "human-001", "reason": "Need approval"})
        b = derive_review_boundary(req, _valid_result())
        assert b["approval"]["required"] is True
        assert b["approval"]["status"] == "pending"
        assert b["approval"]["reviewer"] == "human-001"

    def test_deterministic(self):
        req = _valid_request()
        res = _valid_result()
        r1 = derive_review_boundary(req, res)
        r2 = derive_review_boundary(req, res)
        assert r1 == r2

    def test_json_serializable(self):
        b = derive_review_boundary(_valid_request(), _valid_result())
        dumped = json.dumps(b, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == b


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import inspect
        source = inspect.getsource(derive_review_boundary)
        clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "open(" not in clean
        assert "write(" not in clean
        assert "Path(" not in clean
        assert "read_text" not in clean
        assert "write_text" not in clean
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
        assert "uuid" not in clean
        assert "datetime.now" not in clean
        assert "time.time" not in clean
        assert "random" not in clean


# ---------------------------------------------------------------------------
# Real Docker boundary integration
# ---------------------------------------------------------------------------


class TestRealDockerBoundaryIntegration:
    """Tests that real docker-agent execution status values produce the
    correct review boundary decisions."""

    def _docker_request(self, **overrides: object) -> dict:
        req = dict(_valid_request())
        req.update(overrides)
        req["requested_adapter"] = "docker-agent-v1"
        return req

    def _docker_result(self, status: str = "requires_review", **overrides: object) -> dict:
        res = dict(_valid_result())
        res.update(overrides)
        res["status"] = status
        res["adapter"] = "docker-agent-v1"
        return res

    def test_requires_review_status_to_decision(self):
        b = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="requires_review"),
        )
        assert b["decision"] == "requires_review"
        assert b["requires_review"] is True
        assert b["reason_code"] == "requires_review"

    def test_failed_to_decision(self):
        b = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="failed"),
        )
        assert b["decision"] == "failed"
        assert b["failed"] is True
        assert b["reason_code"] == "execution_failed"

    def test_blocked_to_decision(self):
        b = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="blocked"),
        )
        assert b["decision"] == "blocked"
        assert b["blocked"] is True

    def test_three_states_distinct(self):
        b_review = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="requires_review"),
        )
        b_failed = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="failed"),
        )
        b_blocked = derive_review_boundary(
            self._docker_request(),
            self._docker_result(status="blocked"),
        )
        decisions = {b_review["decision"], b_failed["decision"], b_blocked["decision"]}
        assert len(decisions) == 3

    def test_noop_completed_unchanged(self):
        b = derive_review_boundary(
            _valid_request(),
            _valid_result(status="completed", adapter="noop-v1"),
        )
        assert b["decision"] == "completed"
        assert b["completed"] is True
