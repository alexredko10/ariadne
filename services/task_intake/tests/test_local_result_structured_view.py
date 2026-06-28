"""Tests for the structured result view on the local interaction page."""

from __future__ import annotations

import asyncio
import json

from task_intake.server import app


# ---------------------------------------------------------------------------
# ASGI test harness
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, str, dict]:
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

    return response_status, response_body.decode("utf-8", errors="replace")


def _request(method: str, path: str, body: bytes | None = None) -> tuple[int, str]:
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# GET / page content
# ---------------------------------------------------------------------------


class TestStructuredViewPage:
    def test_page_returns_200(self):
        status, _ = _request("GET", "/")
        assert status == 200

    def test_page_contains_status_summary(self):
        _, html = _request("GET", "/")
        assert "runtime_status" in html or "Runtime status" in html or "Status" in html

    def test_page_contains_execution_request_section(self):
        _, html = _request("GET", "/")
        assert "execution_request" in html.lower() or "Execution Request" in html

    def test_page_contains_execution_result_section(self):
        _, html = _request("GET", "/")
        assert "execution_result" in html.lower() or "Execution Result" in html

    def test_page_contains_execution_envelope_section(self):
        _, html = _request("GET", "/")
        assert "execution_envelope" in html.lower() or "Execution Envelope" in html

    def test_page_contains_review_boundary_section(self):
        _, html = _request("GET", "/")
        assert "review_boundary" in html.lower() or "Review Boundary" in html

    def test_page_contains_warnings_errors_section(self):
        _, html = _request("GET", "/")
        assert "Warnings" in html and "Errors" in html

    def test_page_contains_raw_json_area(self):
        _, html = _request("GET", "/")
        assert "<pre" in html

    def test_page_references_runs_execute(self):
        _, html = _request("GET", "/")
        assert "/runs/execute" in html

    def test_page_has_no_external_assets(self):
        _, html = _request("GET", "/")
        assert "src=\"" not in html
        assert "cdn" not in html.lower()
        assert "unpkg" not in html.lower()
        assert "jsdelivr" not in html.lower()
        assert "react" not in html.lower()
        assert "vue" not in html.lower()
        assert "svelte" not in html.lower()
        assert "vite" not in html.lower()
        assert "webpack" not in html.lower()
        assert "npm" not in html.lower()
        assert "yarn" not in html.lower()
        assert "pnpm" not in html.lower()


# ---------------------------------------------------------------------------
# POST /runs/execute preserved
# ---------------------------------------------------------------------------


class TestRunsExecutePreserved:
    def test_returns_runtime_status(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        status, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert status == 200
        assert "runtime_status" in data
        assert data["runtime_status"] == "completed"

    def test_returns_execution_request(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_request" in data

    def test_returns_execution_result(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_result" in data
        assert data["execution_result"]["status"] == "completed"

    def test_returns_execution_envelope(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_envelope" in data
        assert data["execution_envelope"]["envelope_id"].startswith("env_")

    def test_returns_review_boundary(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "review_boundary" in data
        assert "decision" in data["review_boundary"]

    def test_deterministic(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, r1r = _request("POST", "/runs/execute", body=body)
        _, r2r = _request("POST", "/runs/execute", body=body)
        d1 = json.loads(r1r)
        d2 = json.loads(r2r)
        assert d1 == d2
