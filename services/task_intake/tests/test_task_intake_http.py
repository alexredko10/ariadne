"""Tests for the Task Intake HTTP endpoint (stdlib ASGI).

All tests use stdlib-only ``asyncio.run()`` — no pytest-asyncio required.
"""

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
) -> tuple[int, dict[str, object]]:
    """Send a request to the ASGI app and return (status, body dict)."""
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
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
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

    return response_status, parsed  # type: ignore[return-value]


def _request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, object]]:
    """Synchronous wrapper around :func:`_asgi_request`."""
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealth:
    def test_get_health_returns_service_name(self):
        status, data = _request("GET", "/health")
        assert status == 200
        assert data["service"] == "task_intake"

    def test_get_health_returns_ok_status(self):
        status, data = _request("GET", "/health")
        assert status == 200
        assert data["status"] == "ok"


class TestSubmitAccepted:
    def test_valid_prompt_is_accepted(self):
        body = json.dumps({"prompt": "Fix the login bug"}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert data["status"] == "accepted"

    def test_accepted_response_has_task_id(self):
        body = json.dumps({"prompt": "Implement rate limiting"}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert "task_id" in data
        assert data["task_id"].startswith("task_")


class TestSubmitAlias:
    def test_task_intake_submit_works_like_submit(self):
        body = json.dumps({"prompt": "Alias test"}).encode("utf-8")
        s1, d1 = _request("POST", "/submit", body=body)
        s2, d2 = _request("POST", "/task-intake/submit", body=body)
        assert s1 == 200 and s2 == 200
        assert d1 == d2

    def test_task_intake_submit_rejected_blank(self):
        body = json.dumps({"prompt": ""}).encode("utf-8")
        status, data = _request("POST", "/task-intake/submit", body=body)
        assert status == 200
        assert data["status"] == "rejected"


class TestSubmitRejected:
    def test_blank_prompt_is_rejected(self):
        body = json.dumps({"prompt": ""}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert data["status"] == "rejected"

    def test_rejected_response_has_reason(self):
        body = json.dumps({"prompt": ""}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert "reason" in data
        assert len(data["reason"]) > 0

    def test_rejected_response_has_error_code(self):
        body = json.dumps({"prompt": ""}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert "error_code" in data
        assert data["error_code"] == "blank_prompt"

    def test_whitespace_only_rejected(self):
        body = json.dumps({"prompt": "   \t\n  "}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200
        assert data["status"] == "rejected"
        assert data["error_code"] == "blank_prompt"


class TestMalformedInput:
    def test_missing_prompt_is_rejected(self):
        body = json.dumps({}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 400
        assert data["status"] == "rejected"

    def test_empty_json_body(self):
        body = json.dumps({}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 400
        assert data["status"] == "rejected"

    def test_non_json_body(self):
        body = b"not json"
        status, data = _request("POST", "/submit", body=body)
        assert status == 400
        assert data["status"] == "rejected"

    def test_non_dict_json(self):
        body = json.dumps(["not", "a", "dict"]).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 400
        assert data["status"] == "rejected"


class TestNoSideEffects:
    def test_uses_existing_accept_task(self):
        body = json.dumps({"prompt": "test"}).encode("utf-8")
        status, data = _request("POST", "/submit", body=body)
        assert status == 200

    def test_no_forbidden_source_strings(self):
        """Verify that the server source does not contain forbidden patterns."""
        import inspect
        path = inspect.getfile(app)
        content = Path(path).read_text(encoding="utf-8")
        assert "subprocess" not in content
        assert "docker" not in content.lower()
        assert "fastapi" not in content
        assert "starlette" not in content
