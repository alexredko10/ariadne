"""Tests for the task intake normalize mock endpoint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from task_intake.server import app


# ---------------------------------------------------------------------------
# ASGI test harness
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, object]]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "http_version": "1.1",
        "scheme": "http",
        "client": ("127.0.0.1", 8001),
        "server": ("127.0.0.1", 8001),
    }

    response_status = 500
    response_body = b""

    async def receive() -> dict:
        if body is not None:
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict) -> None:
        nonlocal response_status, response_body
        if event["type"] == "http.response.start":
            response_status = event["status"]
        elif event["type"] == "http.response.body":
            response_body += event.get("body", b"")

    await app(scope, receive, send)

    try:
        parsed = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError:
        parsed = {"raw": response_body.decode("utf-8", errors="replace")}

    return response_status, parsed


def _request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict]:
    """Synchronous wrapper around :func:`_asgi_request`."""
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# Normalize endpoint
# ---------------------------------------------------------------------------


class TestNormalizeEndpoint:
    def test_valid_request_returns_200(self):
        body = json.dumps({"raw_task": "Implement JWT auth middleware"}).encode("utf-8")
        status, _ = _request("POST", "/task-intake/normalize", body=body)
        assert status == 200

    def test_valid_request_has_ok_true(self):
        body = json.dumps({"raw_task": "Add login page"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["ok"] is True

    def test_valid_request_has_task_intake_id(self):
        body = json.dumps({"raw_task": "Add login page"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["task_intake_id"].startswith("task_")

    def test_valid_request_has_normalized_task(self):
        body = json.dumps({"raw_task": "Add login page"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert "normalized_task" in data
        assert "task_goal" in data["normalized_task"]

    def test_valid_request_has_next(self):
        body = json.dumps({"raw_task": "Add login page"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["next"] == "/context/preview"

    def test_valid_request_deterministic(self):
        body = json.dumps({"raw_task": "Add login page"}).encode("utf-8")
        _, r1 = _request("POST", "/task-intake/normalize", body=body)
        _, r2 = _request("POST", "/task-intake/normalize", body=body)
        assert r1 == r2


class TestRequestFieldsPreserved:
    def test_raw_task_preserved(self):
        task = "Implement JWT auth"
        body = json.dumps({"raw_task": task}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["raw_task"] == task

    def test_source_defaults_to_manual(self):
        body = json.dumps({"raw_task": "Fix bug"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["source"] == "manual"

    def test_source_preserved(self):
        body = json.dumps({"raw_task": "Fix bug", "source": "cli"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["source"] == "cli"

    def test_metadata_preserved(self):
        meta = {"requester": "bot", "priority": "high"}
        body = json.dumps({"raw_task": "Fix bug", "metadata": meta}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["metadata"] == meta

    def test_constraints_preserved(self):
        cons = ["no_git_mutation", "no_network"]
        body = json.dumps({"raw_task": "Fix bug", "constraints": cons}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        for c in cons:
            assert c in data["normalized_task"]["constraints"]

    def test_constraints_sorted(self):
        cons = ["z_constraint", "a_constraint"]
        body = json.dumps({"raw_task": "Fix bug", "constraints": cons}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["constraints"] == sorted(cons)

    def test_requested_output_defaults_to_plan(self):
        body = json.dumps({"raw_task": "Fix bug"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["requested_output"] == "plan"

    def test_requested_output_preserved(self):
        body = json.dumps({"raw_task": "Fix bug", "requested_output": "implement"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["requested_output"] == "implement"


class TestValidation:
    def test_missing_raw_task_returns_400(self):
        body = json.dumps({"source": "cli"}).encode("utf-8")
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_empty_raw_task_returns_400(self):
        body = json.dumps({"raw_task": ""}).encode("utf-8")
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_non_string_raw_task_returns_400(self):
        body = json.dumps({"raw_task": 123}).encode("utf-8")
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_non_dict_metadata_returns_400(self):
        body = json.dumps({"raw_task": "Fix", "metadata": "bad"}).encode("utf-8")
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_non_list_constraints_returns_400(self):
        body = json.dumps({"raw_task": "Fix", "constraints": "bad"}).encode("utf-8")
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_malformed_json_returns_400(self):
        body = b"not json"
        status, data = _request("POST", "/task-intake/normalize", body=body)
        assert status == 400
        assert data["ok"] is False


class TestInference:
    def test_inferred_mode_feature(self):
        body = json.dumps({"raw_task": "Add user authentication"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["inferred_mode"] == "feature"

    def test_inferred_mode_bugfix(self):
        body = json.dumps({"raw_task": "Fix login crash bug"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["inferred_mode"] == "bugfix"

    def test_inferred_mode_refactor(self):
        body = json.dumps({"raw_task": "Refactor auth controller"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["inferred_mode"] == "refactor"

    def test_inferred_mode_review(self):
        body = json.dumps({"raw_task": "Review the new API endpoint"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["inferred_mode"] == "review"

    def test_inferred_mode_test(self):
        body = json.dumps({"raw_task": "Add tests for auth"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        assert data["normalized_task"]["inferred_mode"] == "test"

    def test_inferred_domains_auth(self):
        body = json.dumps({"raw_task": "Add JWT login endpoint"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        domains = data["normalized_task"]["inferred_domains"]
        assert "auth" in domains

    def test_inferred_domains_testing(self):
        body = json.dumps({"raw_task": "Write test spec for coverage"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        domains = data["normalized_task"]["inferred_domains"]
        assert "testing" in domains

    def test_inferred_domains_sorted(self):
        body = json.dumps({"raw_task": "Add JWT db endpoint for test coverage"}).encode("utf-8")
        _, data = _request("POST", "/task-intake/normalize", body=body)
        domains = data["normalized_task"]["inferred_domains"]
        assert domains == sorted(domains)


class TestSafety:
    def test_no_forbidden_source_strings(self):
        import inspect
        from task_intake.normalize import normalize_task_intake
        source = inspect.getsource(normalize_task_intake)
        assert "subprocess" not in source
        assert "requests" not in source.lower()
        assert "docker" not in source.lower()
        assert "git " not in source.lower()
        assert "open(" not in source

    def test_no_side_effects_in_normalize(self):
        import inspect
        from task_intake.normalize import normalize_task_intake
        source = inspect.getsource(normalize_task_intake)
        assert ".project-memory" not in source
        assert ".ariadne" not in source
