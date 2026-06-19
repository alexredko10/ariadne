"""Tests for the Task Intake smoke/demo command.

Tests use monkeypatching of the HTTP helper instead of a real server.
No running HTTP server required.  No external network.  No Docker.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from task_intake.smoke import (
    check_blank_prompt_rejected,
    check_health,
    check_submit_accepted,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dummy_request_ok(
    _base_url: str,
    _method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict[str, Any]]:
    """Simulate a successful server response."""
    if "/health" in path:
        return 200, {"service": "task_intake", "status": "ok"}
    if "/submit" in path and body and body.get("prompt"):
        return 200, {"status": "accepted", "task_id": "task_a1b2c3d4e5f6"}
    if "/submit" in path and body and not body.get("prompt"):
        return 200, {
            "status": "rejected",
            "reason": "Prompt must not be blank.",
            "error_code": "blank_prompt",
        }
    return 404, {"error": "Not Found"}


def _dummy_request_health_fail(
    _base_url: str,
    _method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict[str, Any]]:
    """Simulate a health check failure."""
    return 200, {"service": "task_intake", "status": "degraded"}


def _dummy_request_accepted_fail(
    _base_url: str,
    _method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict[str, Any]]:
    """Simulate an accepted submit failure (no task_id)."""
    return 200, {"status": "accepted", "task_id": ""}


def _dummy_request_rejected_fail(
    _base_url: str,
    _method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict[str, Any]]:
    """Simulate a blank prompt rejection failure (wrong error_code)."""
    return 200, {
        "status": "rejected",
        "reason": "Invalid prompt.",
        "error_code": "invalid_prompt",
    }


# ---------------------------------------------------------------------------
# Fixture: patch _request_json
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ``smoke._request_json`` to avoid real HTTP calls."""
    monkeypatch.setattr("task_intake.smoke._request_json", _dummy_request_ok)


# ---------------------------------------------------------------------------
# check_health
# ---------------------------------------------------------------------------


class TestCheckHealth:
    def test_ok_status_returns_true(self):
        ok, msg = check_health("http://localhost:8001")
        assert ok is True
        assert msg == "ok"

    def test_non_ok_status_returns_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_health_fail
        )
        ok, msg = check_health("http://localhost:8001")
        assert ok is False
        assert "degraded" in msg


# ---------------------------------------------------------------------------
# check_submit_accepted
# ---------------------------------------------------------------------------


class TestCheckSubmitAccepted:
    def test_valid_prompt_returns_ok(self):
        ok, msg = check_submit_accepted("http://localhost:8001")
        assert ok is True
        assert msg.startswith("task_")

    def test_returns_task_id(self):
        ok, msg = check_submit_accepted("http://localhost:8001")
        assert ok is True
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_missing_task_id_returns_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_accepted_fail
        )
        ok, msg = check_submit_accepted("http://localhost:8001")
        assert ok is False
        assert "expected accepted" in msg


# ---------------------------------------------------------------------------
# check_blank_prompt_rejected
# ---------------------------------------------------------------------------


class TestCheckBlankPromptRejected:
    def test_blank_prompt_returns_ok(self):
        ok, msg = check_blank_prompt_rejected("http://localhost:8001")
        assert ok is True
        assert msg == "blank_prompt"

    def test_wrong_error_code_returns_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_rejected_fail
        )
        ok, msg = check_blank_prompt_rejected("http://localhost:8001")
        assert ok is False
        assert "blank_prompt" in msg


# ---------------------------------------------------------------------------
# Main exit codes
# ---------------------------------------------------------------------------


class TestMainExitCode:
    def test_all_checks_pass_returns_zero(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_ok
        )
        exit_code = main(["--base-url", "http://localhost:8001"])
        assert exit_code == 0

    def test_health_fail_returns_nonzero(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_health_fail
        )
        exit_code = main(["--base-url", "http://localhost:8001"])
        assert exit_code == 1

    def test_accepted_fail_returns_nonzero(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_accepted_fail
        )
        exit_code = main(["--base-url", "http://localhost:8001"])
        assert exit_code == 1

    def test_rejected_fail_returns_nonzero(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "task_intake.smoke._request_json", _dummy_request_rejected_fail
        )
        exit_code = main(["--base-url", "http://localhost:8001"])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# No side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        """Verify that the smoke module does not import forbidden modules."""
        import inspect
        source = inspect.getsource(check_health)
        assert "subprocess" not in source
        assert "docker" not in source.lower()
        assert "run_record" not in source.lower()
        assert ".ariadne" not in source
        assert "runner" not in source.lower()
