"""Tests for the execution handoff HTTP endpoint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from task_intake.server import app


# ---------------------------------------------------------------------------
# ASGI test harness
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict]:
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
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# /runs/execute
# ---------------------------------------------------------------------------


class TestRunsExecuteEndpoint:
    def test_valid_request_returns_200(self):
        body = json.dumps({"raw_task": "Add JWT auth middleware"}).encode("utf-8")
        status, _ = _request("POST", "/runs/execute", body=body)
        assert status == 200

    def test_response_contains_handoff_id(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "handoff_id" in data
        assert data["handoff_id"].startswith("handoff_")

    def test_response_contains_execution_request(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "execution_request" in data
        assert "execution_request_id" in data["execution_request"]

    def test_response_contains_execution_result(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "execution_result" in data
        assert data["execution_result"]["status"] == "completed"
        assert data["execution_result"]["adapter"] == "noop-v1"

    def test_response_contains_mock_loop_result(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "mock_loop_result" in data
        assert data["mock_loop_result"]["loop_id"].startswith("loop_")

    def test_deterministic(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, r1 = _request("POST", "/runs/execute", body=body)
        _, r2 = _request("POST", "/runs/execute", body=body)
        assert r1 == r2

    def test_json_serializable(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        dumped = json.dumps(data, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == data


class TestRunsExecuteInvalid:
    def test_invalid_json_returns_400(self):
        body = b"not json"
        status, data = _request("POST", "/runs/execute", body=body)
        assert status == 400
        assert data.get("ok") is False

    def test_missing_raw_task_returns_400(self):
        body = json.dumps({}).encode("utf-8")
        status, data = _request("POST", "/runs/execute", body=body)
        assert status == 400
        assert data.get("ok") is False


# ---------------------------------------------------------------------------
# Existing routes unchanged
# ---------------------------------------------------------------------------


class TestExistingRoutes:
    def test_mock_loop_unchanged(self):
        """POST /mock-loop still returns mock loop, not execution result."""
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        status, data = _request("POST", "/mock-loop", body=body)
        assert status == 200
        # Mock loop uses "loop_id", not "handoff_id"
        assert "loop_id" in data
        assert "handoff_id" not in data

    def test_runs_unchanged(self):
        """POST /runs still returns mock run result."""
        body = json.dumps({
            "task_intake": {"task_goal": "test"},
            "context_preview": {"context_preview_id": "cp-001"},
        }).encode("utf-8")
        status, data = _request("POST", "/runs", body=body)
        assert status == 200
        assert data.get("ok") is True
        assert "run_id" in data

    def test_health_unchanged(self):
        status, data = _request("GET", "/health")
        assert status == 200
        assert data["service"] == "task_intake"


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


class TestSafety:
    def test_no_direct_adapter_call(self):
        """Server source does not import noop_adapter."""
        import inspect
        path = inspect.getfile(app)
        content = Path(path).read_text(encoding="utf-8")
        assert "noop_adapter" not in content
        assert "run_noop_execution" not in content

    def test_no_forbidden_source_strings(self):
        """Server source does not contain forbidden patterns.
        Docker string is allowed — the HTML explanation panel mentions
        Docker as an opt-in boundary."""
        import inspect
        path = inspect.getfile(app)
        content = Path(path).read_text(encoding="utf-8")
        assert "subprocess" not in content


class TestHarnessFields:
    def test_response_contains_execution_envelope(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "execution_envelope" in data
        assert data["execution_envelope"]["envelope_id"].startswith("env_")

    def test_response_contains_review_boundary(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "review_boundary" in data
        assert "decision" in data["review_boundary"]

    def test_response_runtime_status(self):
        body = json.dumps({"raw_task": "Add JWT auth"}).encode("utf-8")
        _, data = _request("POST", "/runs/execute", body=body)
        assert "runtime_status" in data
        assert data["runtime_status"] == "completed"
