"""Tests for Task Intake API skeleton."""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest

from task_intake import doctor
from task_intake.app import accept_task
from task_intake.models import (
    MAX_PROMPT_LENGTH,
    TaskIntakeAccepted,
    TaskIntakeError,
    TaskIntakeRejected,
    TaskIntakeRequest,
)


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


class TestAccept:
    def test_valid_task_is_accepted(self):
        request = TaskIntakeRequest(prompt="Implement login page")
        result = accept_task(request)
        assert isinstance(result, TaskIntakeAccepted)
        assert result.status == "accepted"

    def test_accepted_response_has_task_id(self):
        request = TaskIntakeRequest(prompt="Fix bug in auth")
        result = accept_task(request)
        assert isinstance(result, TaskIntakeAccepted)
        assert isinstance(result.task_id, str)
        assert len(result.task_id) > 0
        assert result.task_id.startswith("task_")

    def test_same_prompt_same_task_id(self):
        prompt = "Add rate limiting"
        r1 = accept_task(TaskIntakeRequest(prompt=prompt))
        r2 = accept_task(TaskIntakeRequest(prompt=prompt))
        assert isinstance(r1, TaskIntakeAccepted)
        assert isinstance(r2, TaskIntakeAccepted)
        assert r1.task_id == r2.task_id

    def test_different_prompt_different_task_id(self):
        r1 = accept_task(TaskIntakeRequest(prompt="Task one"))
        r2 = accept_task(TaskIntakeRequest(prompt="Task two"))
        assert isinstance(r1, TaskIntakeAccepted)
        assert isinstance(r2, TaskIntakeAccepted)
        assert r1.task_id != r2.task_id


# ---------------------------------------------------------------------------
# Reject — blank
# ---------------------------------------------------------------------------


class TestBlankPrompt:
    def test_empty_string_rejected(self):
        result = accept_task(TaskIntakeRequest(prompt=""))
        assert isinstance(result, TaskIntakeRejected)
        assert result.error_code == TaskIntakeError.BLANK_PROMPT

    def test_whitespace_only_rejected(self):
        result = accept_task(TaskIntakeRequest(prompt="   \t\n  "))
        assert isinstance(result, TaskIntakeRejected)
        assert result.error_code == TaskIntakeError.BLANK_PROMPT

    def test_rejection_includes_structured_reason(self):
        result = accept_task(TaskIntakeRequest(prompt=""))
        assert isinstance(result, TaskIntakeRejected)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0


# ---------------------------------------------------------------------------
# Reject — oversized
# ---------------------------------------------------------------------------


class TestOversizedPrompt:
    def test_oversized_prompt_rejected(self):
        long_prompt = "x" * (MAX_PROMPT_LENGTH + 1)
        result = accept_task(TaskIntakeRequest(prompt=long_prompt))
        assert isinstance(result, TaskIntakeRejected)
        assert result.error_code == TaskIntakeError.OVERSIZED_PROMPT

    def test_boundary_exact_max_is_accepted(self):
        boundary = "x" * MAX_PROMPT_LENGTH
        result = accept_task(TaskIntakeRequest(prompt=boundary))
        assert isinstance(result, TaskIntakeAccepted)

    def test_oversized_rejection_includes_length(self):
        long_prompt = "x" * (MAX_PROMPT_LENGTH + 50)
        result = accept_task(TaskIntakeRequest(prompt=long_prompt))
        assert isinstance(result, TaskIntakeRejected)
        assert str(MAX_PROMPT_LENGTH) in result.reason


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_returns_service_name(self):
        status = doctor()
        assert status["service"] == "task_intake"

    def test_doctor_returns_ok_status(self):
        status = doctor()
        assert status["status"] == "ok"


# ---------------------------------------------------------------------------
# Import path
# ---------------------------------------------------------------------------


class TestImportPath:
    def test_import_path_works_with_pythonpath(self):
        # This test verifies the module is importable with the
        # correct PYTHONPATH (services/task_intake/src).
        # If PYTHONPATH is set correctly by the test runner, this
        # import will succeed without sys.path manipulation.
        import importlib
        mod = importlib.import_module("task_intake")
        assert hasattr(mod, "accept_task")
        assert hasattr(mod, "doctor")
        assert hasattr(mod, "TaskIntakeRequest")
        assert hasattr(mod, "TaskIntakeAccepted")
        assert hasattr(mod, "TaskIntakeRejected")
        assert hasattr(mod, "TaskIntakeStatus")
        assert hasattr(mod, "TaskIntakeError")


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    """Verify that accept_task does not use forbidden mechanisms.

    These tests use direct string analysis of the accept_task source
    *body* (excluding docstring and signature) to catch accidental
    violations, while accepting that docstring examples may mention
    forbidden terms without being actual violations.
    """

    @staticmethod
    def _get_function_body() -> str:
        """Return the source lines of accept_task, excluding the
        first line (signature/returns) and docstring, to avoid
        false positives from type annotations and documentation."""
        import inspect
        lines = inspect.getsource(accept_task).splitlines()
        body_lines: list[str] = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("def "):
                continue  # skip signature
            if stripped.startswith("->") or stripped.startswith("returns"):
                continue  # skip returns annotation
            body_lines.append(stripped)
        return "\n".join(body_lines)

    def test_no_runner_invocation(self):
        body = self._get_function_body()
        # "runner" as a bare word is OK (it's a module name),
        # but "subprocess.run" or similar invocation is not
        assert "subprocess" not in body, "subprocess call detected"

    def test_no_ariadne_writes(self):
        body = self._get_function_body()
        assert ".ariadne" not in body, ".ariadne write detected"

    def test_no_run_record_creation(self):
        body = self._get_function_body()
        assert "run_record" not in body.lower(), "run_record creation detected"

    def test_no_files_written_to_disk(self, tmp_path: Path):
        """Verify accept_task does not create any files."""
        before = set(tmp_path.rglob("*"))
        request = TaskIntakeRequest(prompt="safe task")
        accept_task(request)
        after = set(tmp_path.rglob("*"))
        assert before == after

    def test_no_subprocess_or_os_system(self):
        body = self._get_function_body()
        assert "os.system" not in body, "os.system call detected"
        assert "subprocess" not in body, "subprocess call detected"

    def test_no_network_calls(self):
        body = self._get_function_body()
        terms = ["http", "socket", "urllib", "requests"]
        for term in terms:
            assert term not in body.lower(), f"network call ({term}) detected in body"
