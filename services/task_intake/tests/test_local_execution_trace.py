"""Tests for the visible execution trace on the local page."""

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
) -> tuple[int, str]:
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
# Execution trace on page
# ---------------------------------------------------------------------------


class TestExecutionTrace:
    def test_page_contains_execution_trace_section(self):
        _, html = _request("GET", "/")
        assert "Execution Trace" in html or "trace" in html.lower()

    def test_trace_contains_task_received_step(self):
        _, html = _request("GET", "/")
        assert "Task received" in html

    def test_trace_contains_execution_request_step(self):
        _, html = _request("GET", "/")
        assert "Execution request built" in html

    def test_trace_contains_handoff_step(self):
        _, html = _request("GET", "/")
        assert "Handoff prepared" in html

    def test_trace_contains_harness_step(self):
        _, html = _request("GET", "/")
        assert "Local harness invoked" in html

    def test_trace_contains_runner_step(self):
        _, html = _request("GET", "/")
        assert "Runner selected" in html

    def test_trace_contains_result_step(self):
        _, html = _request("GET", "/")
        assert "Execution result returned" in html

    def test_trace_contains_envelope_step(self):
        _, html = _request("GET", "/")
        assert "Execution envelope created" in html

    def test_trace_contains_review_step(self):
        _, html = _request("GET", "/")
        assert "Review boundary derived" in html

    def test_trace_has_placeholder_indicators(self):
        _, html = _request("GET", "/")
        # Check for the unicode square or the renderTrace function
        assert "\\u2b1c" in html or "trace-steps" in html

    def test_page_still_has_structured_view(self):
        _, html = _request("GET", "/")
        assert "structured-view" in html

    def test_page_still_has_raw_json(self):
        _, html = _request("GET", "/")
        assert "<pre" in html

    def test_page_still_has_runner_selection(self):
        _, html = _request("GET", "/")
        assert 'name="runner"' in html

    def test_external_assets_are_only_bulma_cdn(self):
        _, html = _request("GET", "/")
        import re
        urls = set()
        for m in re.finditer(r'(?:href|src)="([^"]+)"', html):
            u = m.group(1)
            if u.startswith("http") or u.startswith("//"):
                urls.add(u)
        assert urls == {"https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css"}, f"unexpected external URLs: {urls}"
        assert "unpkg" not in html.lower()
        assert "jsdelivr" not in html.lower()
        assert "react" not in html.lower()


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

    def test_deterministic(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, r1r = _request("POST", "/runs/execute", body=body)
        _, r2r = _request("POST", "/runs/execute", body=body)
        d1 = json.loads(r1r)
        d2 = json.loads(r2r)
        assert d1 == d2
